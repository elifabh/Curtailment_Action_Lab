"""Diagnose a PSS/E planning export, without changing original source limits."""
from pathlib import Path
import sys, importlib.util, json, hashlib, contextlib, io, csv, argparse
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

SCRIPT_DIR = Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--raw',type=Path,default=SCRIPT_DIR.parent/'data/TYTFS2024_WP2024_V33.raw',help='TYTFS2024_WP2024_V33.raw from the EirGrid archive')
parser.add_argument('--output',type=Path,default=Path('irish_diagnostic_output'))
args=parser.parse_args()
HERE=args.output.resolve();HERE.mkdir(parents=True,exist_ok=True)
raw=args.raw.resolve()
expected='006db9ce2ff20a7bf2a67ffbd9988735a1b3d3dc8abbd6309395e7139b66cb24'
if hashlib.sha256(raw.read_bytes()).hexdigest()!=expected:
    raise SystemExit('This diagnostic is audited only for the supplied winter2024 source hash.')
case=raw.stem
from pypower.makeYbus import makeYbus
from pypower.makeSbus import makeSbus
from pypower.runpf import runpf
from pypower.ppoption import ppoption
from pypower.bustypes import bustypes
from grg_pssedata.io import parse_psse_case_file

spec=importlib.util.spec_from_file_location('source_importer', SCRIPT_DIR/'irish_legacy_importer.py')
importer=importlib.util.module_from_spec(spec); spec.loader.exec_module(importer)
importer.ROOT=HERE  # importer diagnostics must not overwrite another agent's work

with contextlib.redirect_stdout(io.StringIO()):
    ppc, old, branch_names, rev = importer.build(raw)
source=parse_psse_case_file(str(raw))
bus=ppc['bus']; branch=ppc['branch']; gen=ppc['gen']; base=ppc['baseMVA']

# Only active non-transformer, zero-R ties with source-equal voltage are merged.
# THRSHZ is not supplied in RAW; 1e-4 is an explicit diagnostic hypothesis.
ties=[]
for k,row in enumerate(branch):
    i,j=row[:2].astype(int)
    if branch_names[k].startswith('line:') and row[10] and abs(row[2])<1e-12 and abs(row[3])<=1.00001e-4:
        ties.append(k)
tie_indices=np.array(ties,dtype=int)
edges=branch[tie_indices,:2].astype(int)
adj=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(bus),len(bus)))
ng, labels=connected_components(adj,directed=False)
groups=[np.where(labels==g)[0] for g in range(ng)]

newbus=[]
for g,ix in enumerate(groups):
    x=bus[ix[0]].copy(); x[0]=g
    x[2:6]=bus[ix,2:6].sum(axis=0)
    x[11]=bus[ix,11].min();x[12]=bus[ix,12].max()
    if np.any(bus[ix,1]==3):x[1]=3
    elif np.any(bus[ix,1]==2):x[1]=2
    elif np.all(bus[ix,1]==4):x[1]=4
    else:x[1]=1
    newbus.append(x)
newbus=np.array(newbus)
newgen=gen.copy();newgen[:,0]=labels[gen[:,0].astype(int)]
newbranch=branch.copy();newbranch[:,:2]=labels[branch[:,:2].astype(int)]
keep=np.ones(len(branch),dtype=bool);keep[tie_indices]=False
# Preserve tie charging (none expected); endpoint shunts are already on bus records.
for k in ties:
    a,b=newbranch[k,:2].astype(int)
    newbus[a,5]+=newbranch[k,4]*base/2
    newbus[b,5]+=newbranch[k,4]*base/2
newbranch=newbranch[keep]
reduced={'version':'2','baseMVA':base,'bus':newbus,'gen':newgen,'branch':newbranch}
Y,_,_=makeYbus(base,newbus,newbranch)
V=newbus[:,7]*np.exp(1j*np.deg2rad(newbus[:,8]))
S=makeSbus(base,newbus,newgen)
residual=(V*np.conj(Y@V)-S)*base
ref,pv,pq=bustypes(newbus,newgen)
active=np.where(newbus[:,1]!=4)[0]
nonref=np.setdiff1d(active,ref)
hvdc_orig={r['bus'] for r in old['hvdc_terminal_boundary_injections']}
hvdc_groups={labels[i] for i,sid in rev.items() if sid in hvdc_orig}
nonref=np.array([i for i in nonref if i not in hvdc_groups])
pq=np.array([i for i in pq if i not in hvdc_groups and newbus[i,1]!=4])

# Exact modulus bound: if |dV| <= epsilon, then
# |d(V conj(YV))| <= epsilon|YV| + |V||Y|epsilon + epsilon|Y|epsilon.
# Source original buses: Vm 5 decimals, angle 4; transformer star points:
# inspect the stored tokens; conservative same precision unless higher is known.
eps_vm=np.full(len(V),5e-6);eps_angle=np.deg2rad(5e-5)
epsV=eps_vm+np.abs(V)*eps_angle+eps_vm*eps_angle
bound=base*(epsV*np.abs(Y@V)+np.abs(V)*(abs(Y)@epsV)+epsV*(abs(Y)@epsV))

def ids(group):return [int(rev[int(i)]) for i in groups[int(group)]]
def worst(ix,part):
    r=residual.real if part=='P' else residual.imag
    return [{'buses':ids(i),'residual':float(r[i]),'voltage_rounding_modulus_bound_MVA':float(bound[i]),'ratio_to_bound':float(abs(r[i])/max(bound[i],1e-15))}
            for i in sorted(ix,key=lambda i:abs(r[i]),reverse=True)[:12]]

run_results={};solutions={}
for name,alg in [('newton',1),('fast_decoupled_XB',2),('fast_decoupled_BX',3)]:
    with contextlib.redirect_stdout(io.StringIO()):
        out,success=runpf(reduced,ppoption(VERBOSE=0,OUT_ALL=0,PF_ALG=alg,PF_TOL=1e-9,PF_MAX_IT=50,PF_MAX_IT_FD=300,ENFORCE_Q_LIMS=False))
    row={'converged':bool(success)}
    if success:
        solutions[name]=out
        vm=out['bus'][:,7]-newbus[:,7]
        va=out['bus'][:,8]-newbus[:,8];va-=va[ref[0]]
        original_groups=np.array([g for g in active if any(rev[int(i)]<1000000 for i in groups[g])])
        row.update({'max_abs_vm_error_pu':float(max(abs(vm[original_groups]))),'max_abs_angle_error_deg':float(max(abs(va[original_groups]))),
                    'Vm_error_percentiles_pu':np.percentile(abs(vm[original_groups]),[50,95,99,100]).tolist(),
                    'Va_error_percentiles_deg':np.percentile(abs(va[original_groups]),[50,95,99,100]).tolist(),
                    'vm_within_half_last_digit_count':int(sum(abs(vm[original_groups])<=5e-6)),
                    'original_bus_group_count':len(original_groups)})
    run_results[name]=row

source_v_viol=[{'id':int(b.i),'name':b.name.strip(),'base_kV':b.basekv,'Vm':b.vm,'Vmin':b.nvlo,'Vmax':b.nvhi}
               for b in source.buses if b.ide!=4 and (b.vm<b.nvlo-1e-9 or b.vm>b.nvhi+1e-9)]
out=solutions.get('newton')
feasibility={}
if out is not None:
    br=out['branch'];flow=np.maximum(np.hypot(br[:,13],br[:,14]),np.hypot(br[:,15],br[:,16]));rated=(br[:,5]>0)&(br[:,10]>0)
    original_map=np.array([any(rev[int(i)]<1000000 for i in ix) for ix in groups])
    vbad=original_map & (newbus[:,1]!=4) & ((out['bus'][:,7]<newbus[:,12]-1e-6)|(out['bus'][:,7]>newbus[:,11]+1e-6))
    online=out['gen'][:,7]>0;g=out['gen']
    qex=np.maximum(np.maximum(g[:,4]-g[:,2],g[:,2]-g[:,3]),0)
    feasibility={'source_original_bus_voltage_violations':len(source_v_viol),'source_violations_at_or_above_100kV':sum(x['base_kV']>=100 for x in source_v_viol),
                 'solved_reduced_original_bus_voltage_violations':int(sum(vbad)),
                 'thermal_violations_positive_rateA':int(sum(rated & (flow>br[:,5]+1e-4))),
                 'max_loading_positive_rateA':float(max(flow[rated]/br[rated,5])),
                 'P_limit_violations':int(sum(online & ((g[:,1]<g[:,9]-1e-4)|(g[:,1]>g[:,8]+1e-4)))),
                 'Q_limit_violations':int(sum(online & ((g[:,2]<g[:,4]-1e-4)|(g[:,2]>g[:,3]+1e-4)))),
                 'max_Q_limit_excess_Mvar':float(max(qex[online])),
                 'Q_limit_violations_above_0_02_Mvar':int(sum(online & (qex>.02))),
                 'Q_limit_enforcement':False,'zero_tie_internal_thermal_check':'not implemented'}

cross={}
if 'newton' in solutions:
    a=solutions['newton']
    for name,b in solutions.items():
        if name=='newton':continue
        cross[name]={'max_Vm_difference_pu':float(max(abs(a['bus'][:,7]-b['bus'][:,7]))),
                     'max_angle_difference_deg':float(max(abs(a['bus'][:,8]-b['bus'][:,8]))),
                     'max_branch_PQ_difference_MVA_component':float(np.max(abs(a['branch'][:,13:17]-b['branch'][:,13:17])))}

# Independent direct-text bus parsing for source voltage-limit counts.
direct_bus=[]
for line in raw.read_text().splitlines()[3:]:
    if line.lstrip().startswith('0 /'):break
    f=next(csv.reader([line],quotechar="'",skipinitialspace=True))
    direct_bus.append({'id':int(f[0]),'type':int(f[3]),'kV':float(f[2]),'Vm':float(f[7]),'Vmax':float(f[9]),'Vmin':float(f[10])})
direct_bad=[b for b in direct_bus if b['type']!=4 and (b['Vm']<b['Vmin']-1e-9 or b['Vm']>b['Vmax']+1e-9)]

report={
 'source_file':raw.name,'source_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
 'status':'EXPLORATORY_NOT_VALIDATED_FOR_OPERATIONAL_ADVICE',
 'zero_tie_diagnosis':{'threshold_assumption_pu':1e-4,'active_nontransformer_ties':len(ties),
  'all_tie_endpoints_saved_equal_voltage':bool(all(np.allclose(bus[a,7:9],bus[b,7:9],rtol=0,atol=1e-12) for a,b in edges)),
  'original_internal_bus_count':len(bus),'reduced_bus_count':len(newbus),
  'old_max_nodal_P_MW':old['source_residual_nonHVDC_max_P_MW'],
  'merged_max_nodal_P_MW':float(max(abs(residual[nonref].real))),
  'merged_max_nodal_Q_Mvar_effective_PQ':float(max(abs(residual[pq].imag)))},
 'source_rounding_diagnostic':{'assumed_Vm_half_step_pu':5e-6,'assumed_Va_half_step_deg':5e-5,
  'meaning':'Necessary envelope only. Being inside this bound does not prove a jointly feasible solution exists inside all rounding intervals. No physical limit is changed.',
  'P_rows_above_bound':int(sum(abs(residual[nonref].real)>bound[nonref]+.001)),
  'Q_rows_above_bound':int(sum(abs(residual[pq].imag)>bound[pq]+.001)),
  'Q_rows_exceeding_envelope':[{'buses':ids(i),'residual_Mvar':float(residual[i].imag),'bound_MVA':float(bound[i])} for i in pq if abs(residual[i].imag)>bound[i]+.001],
  'worst_P':worst(nonref,'P'),'worst_Q':worst(pq,'Q')},
 'algorithms':run_results,'same_network_algorithm_crosscheck':cross,
 'crosscheck_scope':'Different numerical solvers using the same imported model; not an independent importer or PSS/E replication.',
 'independent_text_bus_check':{'bus_count':len(direct_bus),'source_voltage_violations':len(direct_bad),
    'violation_ids_agree_with_parser':sorted(b['id'] for b in direct_bad)==sorted(b['id'] for b in source_v_viol)},
 'equipment_inventory':{'two_terminal_DC':len(source.tt_dc_lines),'HVDC_boundary_calibrations':old['hvdc_terminal_boundary_injections'],
   'three_winding_star_buses':old['star_buses'],'active_correction_applications':old['fixed_tap_correction_count'],'multi_section_line_groups':len(source.line_groupings),
   'FACTS_modes':old['FACTS_modes'],'constant_current_or_impedance_active_loads':sum(bool(l.ip or l.iq or l.yp or l.yq) for l in source.loads if l.status)},
 'unchanged_limit_checks':feasibility,'source_voltage_violations':source_v_viol,
 'limitations':['Source THRSHZ is not recorded in RAW; 1e-4 assumed and saved-equal voltages verified.',
 'HVDC P/Q inferred from saved voltages, not independently reproduced.',
 'Tap positions, switched-shunt states and local generator voltage targets held fixed; remote regulation not reproduced.',
 'Generator reactive limits not enforced by these power flow solves.',
 'Internal flows within merged zero-impedance ties not recovered or thermally checked.',
 'No N-1, short-circuit, stability, frequency, outage permission or operational-control validation.',
 'Static hypothetical injections cannot establish historical curtailed MWh or an Ireland-wide reduction percentage.']}
(HERE/f'{case}_diagnosis.json').write_text(json.dumps(report,indent=2))
np.savez(HERE/f'{case}_merged_model.npz',**reduced)
print(json.dumps({k:v for k,v in report.items() if k not in ['source_voltage_violations','source_rounding_diagnostic']},indent=2))
