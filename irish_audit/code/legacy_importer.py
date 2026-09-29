"""Fixed-controls AC reconstruction of public planning snapshot; not operational validation.
No curtailment estimate. Source remote voltage controls held at solved local Vm;
source tap and switched-shunt positions held fixed. HVDC terminal injections inferred
from source solved voltages and explicitly excluded from independent residual check.
"""
import sys,json,contextlib,io,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
from grg_pssedata.io import parse_psse_case_file
from pypower.makeYbus import makeYbus
from pypower.makeSbus import makeSbus
from pypower.runpf import runpf
from pypower.ppoption import ppoption

def build(path):
 c=parse_psse_case_file(str(path)); B=c.sbase
 buses=[]; gens=[]; branches=[]; ids={}; names={}; meta=[]
 for b in c.buses:
  if b.ide==4:continue
  ids[b.i]=len(buses); names[b.i]=b.name.strip()
  buses.append([len(buses),b.ide,0,0,0,0,b.area,b.vm,b.va,b.basekv,b.zone,b.nvhi,b.nvlo])
 for l in c.loads:
  if not l.status or l.i not in ids:continue
  b=buses[ids[l.i]]
  if l.ip or l.iq:raise ValueError('Current load not supported')
  b[2]+=l.pl; b[3]+=l.ql; b[4]+=l.yp; b[5]-=l.yq
 for s in c.fixed_shunts:
  if s.status and s.i in ids:buses[ids[s.i]][4]+=s.gl;buses[ids[s.i]][5]+=s.bl
 for s in c.switched_shunts:
  if s.stat and s.i in ids:buses[ids[s.i]][5]+=s.binit
 for g in c.generators:
  if g.i not in ids: continue
  vg=buses[ids[g.i]][7]
  gens.append([ids[g.i],g.pg,g.qg,g.qt,g.qb,vg,g.mbase,g.stat,g.pt,g.pb]+[0]*11)
 def br(i,j,r,x,b=0,rate=0,tap=1,angle=0,status=1,name=''):
  if i not in ids or j not in ids:
   if status: raise ValueError(('missing active endpoint',i,j))
   return
  branches.append([ids[i],ids[j],r,x,b,rate,rate,rate,tap,angle,int(bool(status)),-360,360]);meta.append(name)
 for l in c.branches:
  br(l.i,abs(l.j),l.r,l.x,l.b,l.ratea,status=l.st,name=f'line:{l.i}:{abs(l.j)}:{l.ckt.strip()}')
  if l.st and l.i in ids and abs(l.j) in ids:
   buses[ids[l.i]][4]+=l.gi*B;buses[ids[l.i]][5]+=l.bi*B
   buses[ids[abs(l.j)]][4]+=l.gj*B;buses[ids[abs(l.j)]][5]+=l.bj*B
 tables={s.i:s for s in c.transformer_corrections}; corrections=[]
 def corr(w):
  if not w.tab:return 1.
  tab=tables[w.tab]
  xy=[(getattr(tab,f't{k}'),getattr(tab,f'f{k}')) for k in range(1,12) if getattr(tab,f'f{k}')>0]
  x=w.ang if abs(w.cod)==3 else w.windv
  val=float(np.interp(x,[a for a,b in xy],[b for a,b in xy]));corrections.append({'table':w.tab,'x':x,'factor':val});return val
 for k,t in enumerate(c.transformers):
  p=t.p1;q=t.p2
  assert p.cw==1 and p.cm==1 and p.cz in [1,2]
  if not p.stat:continue
  if p.i in ids:buses[ids[p.i]][4]+=p.mag1*B;buses[ids[p.i]][5]+=p.mag2*B
  z12=complex(q.r12,q.x12)*(1 if p.cz==1 else B/q.sbase12)
  if not p.k:
   z=z12*corr(t.w1)*t.w2.windv**2
   br(p.i,p.j,z.real,z.imag,rate=t.w1.rata,tap=t.w1.windv/t.w2.windv,angle=t.w1.ang,status=p.stat,name=f'trafo:{p.i}:{p.j}:{p.ckt.strip()}')
  else:
   z23=complex(q.r23,q.x23)*(1 if p.cz==1 else B/q.sbase23)
   z31=complex(q.r31,q.x31)*(1 if p.cz==1 else B/q.sbase31)
   zs=[(z12+z31-z23)/2,(z12+z23-z31)/2,(z23+z31-z12)/2]
   star=1000000+k;ids[star]=len(buses);names[star]='synthetic star'
   buses.append([len(buses),1,0,0,0,0,1,q.vmstar,q.anstar,1,1,1.1,.9])
   for n,(i,w,z) in enumerate(zip([p.i,p.j,p.k],[t.w1,t.w2,t.w3],zs),1):
    z*=corr(w)
    active=p.stat==1 or (p.stat==2 and n!=2) or (p.stat==3 and n!=3) or (p.stat==4 and n!=1)
    br(i,star,z.real,z.imag,rate=w.rata,tap=w.windv,angle=w.ang,status=active,name=f'trafo3:{p.i}:{p.j}:{p.k}:{p.ckt.strip()}:{n}')
 bus=np.array(buses);gen=np.array(gens);branch=np.array(branches)
 from scipy.sparse import coo_matrix
 from scipy.sparse.csgraph import connected_components
 active=branch[:,10]>0;ij=branch[active,:2].astype(int)
 adj=coo_matrix((np.ones(len(ij)),(ij[:,0],ij[:,1])),shape=(len(bus),len(bus)))
 ncomp,labels=connected_components(adj,directed=False)
 component_info=[]
 for lab in range(ncomp):
  ix=np.where(labels==lab)[0]
  if len(ix)==1 or not np.any(bus[ix,1]==3):
   if len(ix)>1:raise ValueError(('Island without slack',len(ix)))
   component_info.append({'bus_index':int(ix[0]),'bus_id':next(k for k,v in ids.items() if v==ix[0]),'P_load':float(bus[ix[0],2]),'Q_load':float(bus[ix[0],3])})
   bus[ix,1]=4

 Y,_,_=makeYbus(B,bus,branch);V=bus[:,7]*np.exp(1j*np.deg2rad(bus[:,8]));S=makeSbus(B,bus,gen)
 mismatch=(V*np.conj(Y@V)-S)*B
 hvdc_ids=set()
 for h in c.tt_dc_lines:hvdc_ids.update([h.rectifier.ipr,h.inverter.ipi])
 hvdc_records=[]
 for i in hvdc_ids:
  if i not in ids:continue
  idx=ids[i];mis=mismatch[idx]
  # needed additional network injection is mismatch; negative demand inserts it.
  bus[idx,2]-=mis.real;bus[idx,3]-=mis.imag
  hvdc_records.append({'bus':i,'P_MW':float(mis.real),'Q_Mvar':float(mis.imag),'basis':'inferred from source voltages; not independently validated'})
 # Public RAW contains source-equal voltage buses tied by X=1e-4 pu lines.
 # Report residual summed across these ties separately; individual tie flows are
 # not observable from source rounded voltages. This is a diagnostic, not a gate change.
 tie_edges=[(ids[l.i],ids[abs(l.j)]) for l in c.branches if l.st and abs(l.r)<1e-12 and abs(l.x)<=1.00001e-4 and l.i in ids and abs(l.j) in ids]
 ti=np.array(tie_edges,dtype=int)
 adjtie=coo_matrix((np.ones(len(ti)),(ti[:,0],ti[:,1])),shape=(len(bus),len(bus)))
 ntie,tielabel=connected_components(adjtie,directed=False)
 grouped=[]
 for label in range(ntie):
  ix=np.where(tielabel==label)[0]
  if any(int(i) in [ids[z] for z in hvdc_ids if z in ids] for i in ix):continue
  grouped.append({'buses':[next(k for k,v in ids.items() if v==i) for i in ix], 'P_MW':float(mismatch[ix].real.sum()),'Q_Mvar':float(mismatch[ix].imag.sum()),'all_PQ':bool(np.all(bus[ix,1]==1)),'contains_ref':bool(np.any(bus[ix,1]==3))})
 orig=[ids[b.i] for b in c.buses if b.i in ids and b.i not in hvdc_ids]
 nonref=[x for x in orig if bus[x,1] not in [3,4]];pq=[x for x in orig if bus[x,1]==1]
 j=max(nonref,key=lambda j:abs(mismatch[j].real));rev={v:k for k,v in ids.items()}
 summary={'zero_impedance_tie_count':len(tie_edges),'source_grouped_max_P_MW':max(abs(g['P_MW']) for g in grouped if not g['contains_ref']),'source_grouped_max_PQ_Q_Mvar':max(abs(g['Q_Mvar']) for g in grouped if g['all_PQ']),'excluded_isolated_buses':component_info,'source':path.name,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'original_buses':len(c.buses),'included_original_buses':len(orig)+len(hvdc_records),'star_buses':len(bus)-len(orig)-len(hvdc_records),'active_lines_and_transformer_windings':int(sum(branch[:,10])),'fixed_tap_correction_count':len(corrections),'hvdc_terminal_boundary_injections':hvdc_records,'remote_voltage_control':'held at source local bus Vm, not reproduced','switch_shunt_control':'held at Binit','tap_control':'held at source ratio/phase','FACTS_modes':[f.mode for f in c.facts],'source_residual_nonHVDC_max_P_MW':float(max(abs(mismatch[nonref].real))),'source_residual_nonHVDC_max_PQ_Q_Mvar':float(max(abs(mismatch[pq].imag))),'worst_P_bus':{'id':rev[j],'name':names[rev[j]],'mismatch_MW':float(mismatch[j].real)},'source_residual_nonHVDC_P_MW_percentiles':np.percentile(abs(mismatch[nonref].real),[50,95,99,100]).tolist()}
 ppc={'version':'2','baseMVA':B,'bus':bus,'gen':gen,'branch':branch}
 (ROOT/(path.stem+'_residual_groups.json')).write_text(json.dumps(sorted(grouped,key=lambda g:abs(g['P_MW']),reverse=True),indent=2))
 return ppc,summary,meta,rev

