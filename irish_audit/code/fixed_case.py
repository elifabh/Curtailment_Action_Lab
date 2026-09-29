"""Audited fixed-control mathematical model; not an operational Irish digital twin.

This version respects fixed-Q generators and explicitly enforces aggregate bus
reactive capability. Remote voltage control and HVDC dynamics remain outside its
scope. Source limits are never widened.
"""
from pathlib import Path
from copy import deepcopy
import contextlib,io,json,hashlib
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from pypower.runpf import runpf
from pypower.ppoption import ppoption
from grg_pssedata.io import parse_psse_case_file
import legacy_importer

ROOT=Path(__file__).resolve().parents[1]

def build():
    raw=ROOT/'TYTFS2024_WP2024_V33.raw'
    assert hashlib.sha256(raw.read_bytes()).hexdigest()=='006db9ce2ff20a7bf2a67ffbd9988735a1b3d3dc8abbd6309395e7139b66cb24'
    legacy_importer.ROOT=ROOT/'results'
    with contextlib.redirect_stdout(io.StringIO()):
        full,old,names,rev=legacy_importer.build(raw)
        source=parse_psse_case_file(str(raw))
    b,g,br=full['bus'],full['gen'],full['branch']
    ties=np.array([k for k,r in enumerate(br) if names[k].startswith('line:') and r[10] and abs(r[2])<1e-12 and abs(r[3])<=1.00001e-4],dtype=int)
    e=br[ties,:2].astype(int)
    # This is an explicit V33 tie hypothesis, corroborated but not certified by V35.
    assert all(np.array_equal(b[i,7:9],b[j,7:9]) for i,j in e)
    ng,labels=connected_components(coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),shape=(len(b),len(b))),directed=False)
    groups=[np.flatnonzero(labels==i) for i in range(ng)]
    new=[]
    for i,ix in enumerate(groups):
        r=b[ix[0]].copy();r[0]=i;r[2:6]=b[ix,2:6].sum(0)
        r[11]=b[ix,11].min();r[12]=b[ix,12].max()
        r[1]=3 if np.any(b[ix,1]==3) else 2 if np.any(b[ix,1]==2) else 4 if np.all(b[ix,1]==4) else 1
        new.append(r)
    nb=np.array(new);nG=g.copy();nG[:,0]=labels[g[:,0].astype(int)]
    nBr=br.copy();nBr[:,:2]=labels[br[:,:2].astype(int)]
    keep=np.ones(len(br),dtype=bool);keep[ties]=False
    for k in ties:
        i,j=nBr[k,:2].astype(int)
        nb[i,5]+=nBr[k,4]*full['baseMVA']/2;nb[j,5]+=nBr[k,4]*full['baseMVA']/2
    ppc={'version':'2','baseMVA':full['baseMVA'],'bus':nb,'gen':nG,'branch':nBr[keep]}
    ids={sid:int(labels[i]) for i,sid in rev.items()}
    is_line=np.array([n.startswith('line:') for n in names])
    line_map={f'line:{x.i}:{abs(x.j)}:{x.ckt.strip()}':x for x in source.branches}
    terminal_shunts=np.zeros((len(names),2),complex)
    for k,name in enumerate(names):
        if name in line_map:
            x=line_map[name];terminal_shunts[k]=[x.gi+1j*x.bi,x.gj+1j*x.bj]
    metadata={'source':source,'full':full,'groups':groups,'labels':labels,'source_ids':ids,
        'reverse_ids':rev,'ties':ties,'kept_indices':np.flatnonzero(keep),
        'branch_names':[n for n,k in zip(names,keep) if k],'source_import':old,
        'current_rating':np.where(is_line[keep],source.nxfrat,source.xfrrat)>0,
        'is_line':is_line[keep],'terminal_shunts':terminal_shunts[keep]}
    return ppc,metadata

def solve(case,reactive_limits=True):
    work=deepcopy(case);fixed=[];switched=[]
    online=work['gen'][:,7]>0
    # A bus with no Q capability cannot impose an independent voltage target.
    for i in np.unique(work['gen'][online,0].astype(int)):
        ix=np.flatnonzero(online & (work['gen'][:,0]==i))
        if abs(sum(work['gen'][ix,3]-work['gen'][ix,4]))<1e-12 and work['bus'][i,1]!=3:
            work['gen'][ix,2]=work['gen'][ix,4]
            work['bus'][i,1]=1;fixed.append(int(i))
    opts=ppoption(VERBOSE=0,OUT_ALL=0,PF_TOL=1e-10,PF_MAX_IT=50,ENFORCE_Q_LIMS=False)
    for iteration in range(90):
        with contextlib.redirect_stdout(io.StringIO()):out,ok=runpf(work,opts)
        if not ok:return out,{'converged':False,'iterations':iteration+1,'fixed_Q_buses':fixed,'limited_buses':switched}
        change=False
        if reactive_limits:
            for i in np.unique(work['gen'][online,0].astype(int)):
                ix=np.flatnonzero(online & (work['gen'][:,0]==i));q=sum(out['gen'][ix,2])
                qlo=sum(work['gen'][ix,4]);qhi=sum(work['gen'][ix,3])
                if q<qlo-1e-7 or q>qhi+1e-7:
                    if work['bus'][i,1]==3:
                        return out,{'converged':True,'reactive_limit_failure':'reference bus limit cannot be enforced without a new slack policy','bus':int(i)}
                    if work['bus'][i,1]==1:continue
                    work['gen'][ix,2]=work['gen'][ix,4 if q<qlo else 3]
                    work['bus'][i,1]=1;switched.append(int(i));change=True
        if not change:
            return out,{'converged':True,'iterations':iteration+1,'fixed_Q_buses':fixed,'limited_buses':switched}
        work['bus'][:,7:9]=out['bus'][:,7:9]
    raise RuntimeError('Reactive-limit loop did not settle')

def direct_check(out,meta):
    """Independent branch-current calculation, without PYPOWER admittance builders."""
    b,g,br=out['bus'],out['gen'],out['branch'];base=out['baseMVA']
    V=b[:,7]*np.exp(1j*np.deg2rad(b[:,8]));S=np.zeros(len(b),complex)
    f,t=br[:,:2].astype(int).T
    z=br[:,2]+1j*br[:,3];active=br[:,10]>0
    y=np.zeros(len(br),complex);y[active]=1/z[active]
    tap=np.where(br[:,8]==0,1,br[:,8])*np.exp(1j*np.deg2rad(br[:,9]))
    sh=1j*br[:,4]*active/2
    I_f=(V[f]/tap - V[t])*y/np.conj(tap)+sh*V[f]/abs(tap)**2
    I_t=(V[t]-V[f]/tap)*y+sh*V[t]
    Sf=base*V[f]*np.conj(I_f);St=base*V[t]*np.conj(I_t)
    np.add.at(S,f,Sf);np.add.at(S,t,St)
    S+=(b[:,4]-1j*b[:,5])*abs(V)**2
    inj=-(b[:,2]+1j*b[:,3]);on=g[:,7]>0
    np.add.at(inj,g[on,0].astype(int),g[on,1]+1j*g[on,2])
    residual=S-inj
    original=np.array([any(meta['reverse_ids'][int(i)]<1_000_000 for i in ix) for ix in meta['groups']])
    live=b[:,1]!=4
    vbad=original&live&((b[:,7]<b[:,12]-1e-6)|(b[:,7]>b[:,11]+1e-6))
    rated=active&(br[:,5]>0)
    # RAW header XFRRAT=NXFRAT=+1 denotes current expressed as MVA at
    # nominal voltage, NOT an apparent-power limit independent of voltage.
    ifull=I_f+meta['terminal_shunts'][:,0]*V[f]*active
    itull=I_t+meta['terminal_shunts'][:,1]*V[t]*active
    apparent=np.maximum(abs(Sf),abs(St))
    current=base*np.where(meta['is_line'],np.maximum(abs(ifull),abs(itull)),abs(ifull))
    loading=np.where(meta['current_rating'],current,apparent)/np.where(br[:,5]>0,br[:,5],1)
    qbad=on&((g[:,2]<g[:,4]-1e-5)|(g[:,2]>g[:,3]+1e-5))
    pbad=on&((g[:,1]<g[:,9]-1e-5)|(g[:,1]>g[:,8]+1e-5))
    counts={'original_bus_groups_voltage':int(vbad.sum()),'voltage_ge_100kv':int(sum(vbad&(b[:,9]>=100))),
        'rated_branch_thermal':int(sum(rated&(loading>1+1e-6))),'generator_P':int(pbad.sum()),'generator_Q':int(qbad.sum())}
    return {'direct_balance_max_MVA':float(max(abs(residual[live]))),
        'direct_branch_flow_difference_MVA':float(max(np.max(abs(Sf-(br[:,13]+1j*br[:,14]))),np.max(abs(St-(br[:,15]+1j*br[:,16]))))),
        'violations':counts,'max_rated_branch_loading':float(max(loading[rated])),
        'voltage_violation_group_indices':np.flatnonzero(vbad).tolist(),
        'passes_implemented_checks':bool(not any(counts.values()) and max(abs(residual[live]))<=1e-4),
        'operationally_validated':False,'ideal_tie_internal_flows_checked':False,
        'rating_units':'Current expressed as MVA at nominal bus voltage; first winding for each transformer branch.',
        'rating_coverage':{'active_branches':int(active.sum()),'rateA_zero':int(sum(active&(br[:,5]<=0))),
            'rateA_ge_9999':int(sum(active&(br[:,5]>=9999))),
            'warning':'Large placeholder-like limits are preserved; they do not certify actual asset ratings.'}}

def recover_tie_flows(out,meta):
    """Recover unique tree tie flows; retain ambiguity for ideal cycles.

    Cyclic groups use inverse-X weighted flow allocation for diagnosis only.
    A thermal pass for this allocation does not certify all possible loop flows.
    """
    full=meta['full'];b=full['bus'];br=full['branch'];base=full['baseMVA']
    labels=meta['labels'];v=out['bus'][labels,7]
    remaining=-(b[:,2]+1j*b[:,3])-(b[:,4]-1j*b[:,5])*v*v
    live=out['gen'][:,7]>0
    np.add.at(remaining,full['gen'][live,0].astype(int),out['gen'][live,1]+1j*out['gen'][live,2])
    ends=br[meta['kept_indices'],:2].astype(int)
    np.add.at(remaining,ends[:,0],-(out['branch'][:,13]+1j*out['branch'][:,14]))
    np.add.at(remaining,ends[:,1],-(out['branch'][:,15]+1j*out['branch'][:,16]))
    for k in meta['ties']:
        i,j=br[k,:2].astype(int)
        remaining[i]+=1j*br[k,4]*base*v[i]**2/2
        remaining[j]+=1j*br[k,4]*base*v[j]**2/2
    details=[];max_residual=0.;max_group_residual=0.
    for ix in meta['groups']:
        if len(ix)<2:continue
        edge=[int(k) for k in meta['ties'] if int(br[k,0]) in ix]
        loc={int(n):i for i,n in enumerate(ix)};A=np.zeros((len(ix),len(edge)))
        for j,k in enumerate(edge):A[loc[int(br[k,0])],j]=1;A[loc[int(br[k,1])],j]=-1
        w=1/np.abs(br[edge,3]);L=(A*w)@A.T
        potential=np.zeros(len(ix),complex)
        potential[1:]=np.linalg.solve(L[1:,1:],remaining[ix][1:])
        F=w*(A.T@potential)
        err=A@F-remaining[ix]
        max_residual=max(max_residual,float(max(abs(err))))
        max_group_residual=max(max_group_residual,float(abs(sum(remaining[ix]))))
        cycles=len(edge)-len(ix)+1
        for j,k in enumerate(edge):
            rate=br[k,5];current_equiv=abs(F[j])/v[int(br[k,0])]
            details.append({'original_branch_index':k,'from_bus':meta['reverse_ids'][int(br[k,0])],
                'to_bus':meta['reverse_ids'][int(br[k,1])],'P_MW':float(F[j].real),'Q_Mvar':float(F[j].imag),
                'rateA':float(rate),'current_loading':float(current_equiv/rate) if rate>0 else None,
                'unique_tree_solution':cycles==0,'group_cycle_rank':cycles})
    return {'max_nodal_balance_residual_MVA':max_residual,'max_group_residual_MVA':max_group_residual,
        'tree_edges':sum(r['unique_tree_solution'] for r in details),'cyclic_group_edges':sum(not r['unique_tree_solution'] for r in details),
        'tree_overloads':sum(r['unique_tree_solution'] and r['current_loading'] is not None and r['current_loading']>1+1e-6 for r in details),
        'cyclic_allocation_overloads':sum(not r['unique_tree_solution'] and r['current_loading'] is not None and r['current_loading']>1+1e-6 for r in details),
        'all_internal_tie_limits_certified':not any(not r['unique_tree_solution'] for r in details),
        'flows':details}

def main():
    ppc,meta=build();out,status=solve(ppc)
    tie=recover_tie_flows(out,meta)
    report={'scope':'Fixed source taps/shunts/local voltage targets; inferred fixed HVDC boundary; explicit Q bounds.',
        'solve':status,'checks':direct_check(out,meta),'ideal_tie_recovery':{k:v for k,v in tie.items() if k!='flows'},
        'source_import':meta['source_import']}
    (ROOT/'results/ideal_tie_flows.json').write_text(json.dumps(tie,indent=2)+'\n')
    np.savez_compressed(ROOT/'results/fixed_Q_solution.npz',**{k:out[k] for k in ['baseMVA','bus','gen','branch']})
    (ROOT/'results/fixed_Q_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
