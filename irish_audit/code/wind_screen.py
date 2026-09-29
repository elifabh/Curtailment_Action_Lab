"""Conditional Irish planning-model comparison, with identical prepared controls.

The additional wind and optional geographically movable 20 MW load are synthetic.
This estimates tested snapshot acceptance, not historical curtailed MWh, a global
optimum, security-certified capacity, or an approved operational action.
"""
import json,time
from copy import deepcopy
import numpy as np
from fixed_case import ROOT,build,solve,direct_check
from raw_equation_check import verify

def setup():
    ppc,meta=build()
    prepared=dict(np.load(ROOT/'results/feasible_counterfactual.npz'))
    ppc['branch']=prepared['branch'][:,:13].copy()
    ppc['bus'][:,5]=prepared['bus'][:,5]
    ppc['bus'][:,7:9]=prepared['bus'][:,7:9]
    # Declare the balancing generator, instead of relying on solver fallback
    # when the source's nominal slack machines are out of service.
    ppc['bus'][ppc['bus'][:,1]==3,1]=1
    ppc['bus'][meta['source_ids'][10470],1]=3
    history=json.loads((ROOT/'results/expanded_tap_experiment.json').read_text())['history']
    taps={c['transformer']:c['new_w1'] for row in history for c in row['changes']}
    shunts=json.loads((ROOT/'results/feasible_counterfactual_actions.json').read_text())['disconnect_shunts']
    return ppc,meta,taps,shunts

def calculate(ppc,meta,taps,shunts,wind,outage,extra_load=None):
    case=deepcopy(ppc);case['bus'][meta['source_ids'][1341],2]-=wind
    name='line:1341:1701:1';ix=meta['branch_names'].index(name)
    if outage:case['branch'][ix,10]=0
    if extra_load:
        for bus,p in extra_load.items():case['bus'][meta['source_ids'][bus],2]+=p
    start=time.perf_counter();out,status=solve(case);ch=direct_check(out,meta)
    raw=None
    if status['converged'] and ch['passes_implemented_checks']:
        # Direct RAW verification accepts extra signed demand injections too.
        raw=verify(out,meta,tap_changes=taps,shunt_off=shunts,branch_off=[name] if outage else [],wind_mw=wind,extra_load=extra_load)
    passed=bool(status['converged'] and ch['passes_implemented_checks'] and raw and raw['passed'])
    return out,{'wind_MW':float(wind),'line_outage':outage,'extra_load_MW':extra_load or {},
        'passes_declared_snapshot_checks':passed,'solver':status,'checks':ch,'raw_equations':raw,'elapsed_s':time.perf_counter()-start}

def main():
    ppc,meta,taps,shunts=setup();rows=[];best={}
    scenarios=[('outage',True,None),('line_available',False,None),
        ('outage_flex_at_1341',True,{1341:20.}),('outage_flex_at_2072',True,{2072:20.})]
    for name,outage,load in scenarios:
        coarse=[]
        for wind in range(0,201,25):
            out,r=calculate(ppc,meta,taps,shunts,wind,outage,load);r['scenario']=name;rows.append(r);coarse.append(r)
            print(name,wind,r['passes_declared_snapshot_checks'],r['checks']['violations'],flush=True)
            if r['passes_declared_snapshot_checks']:
                best[name]=r
                np.savez_compressed(ROOT/f'results/wind_{name}_best.npz',**{k:out[k] for k in ['baseMVA','bus','gen','branch']})
        if name not in best:continue
        low=best[name]['wind_MW'];high=min(low+25.,200.)
        while high-low>0.25:
            wind=(low+high)/2;out,r=calculate(ppc,meta,taps,shunts,wind,outage,load);r['scenario']=name;rows.append(r)
            if r['passes_declared_snapshot_checks']:
                low=wind;best[name]=r
                np.savez_compressed(ROOT/f'results/wind_{name}_best.npz',**{k:out[k] for k in ['baseMVA','bus','gen','branch']})
            else:high=wind
    report={'scope':__doc__,'source':'TYTFS2024_WP2024_V33.raw','available_hypothetical_wind_MW':200,
        'wind_bus':1341,'balance_bus':10470,'preparation':{'tap_changes':taps,'disconnected_shunt_buses':shunts},
        'interpretation':'Best tested passing point in [0,200] MW with a fixed coarse grid and local bisection; no global or monotonicity certificate.',
        'best_tested':best,'evaluations':rows,'operationally_validated':False,'field_curtailment_reduction':None}
    (ROOT/'results/wind_screen.json').write_text(json.dumps(report,indent=2)+'\n')
    print('BEST',json.dumps({k:v['wind_MW'] for k,v in best.items()}))
if __name__=='__main__':main()
