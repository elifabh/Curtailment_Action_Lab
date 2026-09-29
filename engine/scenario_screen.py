"""Exploratory fixed-control transmission screening; NOT all-network safe dispatch."""
import sys,json,copy
from pathlib import Path
import numpy as np
ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT.parent/'research_deps'))
from pypower.runpf import runpf
from pypower.ppoption import ppoption
from pypower.makeYbus import makeYbus
from pypower.makeSbus import makeSbus
from pypower.ext2int import ext2int
# Actual served constant-power load from source RAW, independently audited in network_inventory.json.
A=np.load(ROOT/'TYTFS2024_WP2024_V33_model.npz');base={k:A[k] for k in ['bus','gen','branch']};base.update(baseMVA=float(A['baseMVA']),version='2')
src=A['source_ids'];names=A['branch_names'];wind_idx=int(np.where(src==1341)[0][0]);gidx=int(np.where((src[base['gen'][:,0].astype(int)]==10470)&(base['gen'][:,7]>0))[0][0]);line_idx=int(np.where(names=='line:1341:1701:1')[0][0])
opts=ppoption(VERBOSE=0,OUT_ALL=0,PF_TOL=1e-8,PF_MAX_IT=25)
def evaluate(mw,outage):
 if not np.isfinite(mw) or mw<0 or mw>234:raise ValueError('Added wind must be finite and between0 and234MW for this fixed Aghada redispatch rule.')
 if not isinstance(outage,(bool,np.bool_)):raise ValueError('outage must be boolean')
 p=copy.deepcopy(base);p['bus'][wind_idx,2]-=mw;p['gen'][gidx,1]-=mw;p['branch'][line_idx,10]=int(not outage)
 q_clamped=[]
 for qiter in range(20):
  o,ok=runpf(p,opts)
  if not ok:break
  g=o['gen'];bad=np.where((g[:,7]>0)&((g[:,2]<g[:,4]-.02)|(g[:,2]>g[:,3]+.02)))[0]
  if not len(bad):break
  p['bus'][:,7:9]=o['bus'][:,7:9]
  changed=False
  for j in bad:
   bi=int(g[j,0])
   if p['bus'][bi,1]==3:continue # leave slack violation explicit
   p['gen'][j,2]=np.clip(g[j,2],g[j,4],g[j,3]);p['bus'][bi,1]=1
   q_clamped.append(int(j));changed=True
  if not changed:break
 if not ok:return {'added_wind_MW':mw,'outage':outage,'converged':False,'screen_pass':False,'overall_status':'REJECTED_NONCONVERGENCE','operational_recommendation':False}
 b=o['bus'];g=o['gen'];br=o['branch'];thermal=np.maximum(np.hypot(br[:,13],br[:,14]),np.hypot(br[:,15],br[:,16]));ld=np.divide(thermal,br[:,5],out=np.zeros(len(br)),where=br[:,5]>0);valid=(src<1000000)&(b[:,1]!=4);trans=valid&(b[:,9]>=100);low=valid&~trans
 pv=(g[:,7]>0)&((g[:,1]<g[:,9]-1e-4)|(g[:,1]>g[:,8]+1e-4));qv=(g[:,7]>0)&((g[:,2]<g[:,4]-.02)|(g[:,2]>g[:,3]+.02));vv=(b[:,7]>b[:,11]+1e-5)|(b[:,7]<b[:,12]-1e-5)
 pi=ext2int(o);Y,*_=makeYbus(pi['baseMVA'],pi['bus'],pi['branch']);V=pi['bus'][:,7]*np.exp(1j*np.deg2rad(pi['bus'][:,8]));mis=(V*np.conj(Y@V)-makeSbus(pi['baseMVA'],pi['bus'],pi['gen']))*pi['baseMVA'];err=float(max(abs(mis)))
 j=int(np.argmax(ld))
 audit_dir=ROOT/'scenario_audit';audit_dir.mkdir(exist_ok=True)
 np.savez(audit_dir/f"wind_{mw}_outage_{int(outage)}.npz",baseMVA=p['baseMVA'],bus=o['bus'],gen=o['gen'],branch=o['branch'],source_ids=src,branch_names=names,loading_ratio=ld,bus_voltage_violations=vv,q_clamped=np.array(q_clamped))
 return {'added_wind_MW':mw,'outage':outage,'converged':bool(ok),'overall_status':'ENGINEERING_REVIEW_REQUIRED','operational_recommendation':False,'max_collector_voltage_pu':float(max(b[low,7])),'max_collector_voltage_limit_exceedance_pu':float(max(np.maximum(b[low,7]-b[low,11],b[low,12]-b[low,7]))),'screen_pass':bool(max(ld)<=1+1e-6 and not any(vv&trans) and not any(pv) and not any(qv)),'max_loading_pct':float(100*max(ld)),'limiting_branch':str(names[j]),'max_transmission_voltage_pu':float(max(b[trans,7])),'min_transmission_voltage_pu':float(min(b[trans,7])),'thermal_violations':int(sum(ld>1+1e-6)),'transmission_voltage_violations':int(sum(vv&trans)),'collector_voltage_violations':int(sum(vv&low)),'generator_P_violations':int(sum(pv)),'generator_Q_violations':int(sum(qv)),'Q_clamped_generator_count':len(set(q_clamped)),'AC_balance_residual_MVA':err,'balancing_generator_MW':float(g[gidx,1]),'total_served_demand_MW':7324.51,'net_bus_demand_including_fixed_HVDC_MW':float(sum(base['bus'][:,2])),'losses_MW':float(sum(br[:,13]+br[:,15]))}
if __name__=='__main__':
 rows=[]
 for outage in [False,True]:
  for mw in [0,100,150,175,200,225]:
   r=evaluate(mw,outage);rows.append(r);print(json.dumps(r),flush=True)
 (ROOT/'scenario_screen.json').write_text(json.dumps({'status':'exploratory; not validated operational recommendation','source_case':'TYTFS2024_WP2024_V33.raw','hypothesis':'Additional unity-power-factor wind injection at Binbane110kV, displacing equal MW at Aghada generator10470. Compare in-service vs hypothetical outage of1341–1701 circuit1. No actual forecast or outage claim.','thermal_basis':'RAW RATEA; do not relax ratings','screen':'Checks all modeled branch RATEA thermal limits,>=100kV voltage limits,onlinegenerator P and Q limits (0.02Mvar Q tolerance), with PV-to-PQ conversion at violated Q boundaries. Collector voltage violations are separately disclosed and NOT cleared.','validation_gate':'Original strict snapshot gate remains FAIL; close voltage reconstruction only.','rows':rows},indent=2))
