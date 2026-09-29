"""New scenario: discrete voltage-control taps, using source control bands.

Not source reconstruction and not a claim of operator-authorised tap changes.
Only explicit two-winding COD=+1, positive downstream CONT, no load-drop
compensation and valid discrete bounds are eligible. The expanded policy also
supports remote downstream targets and source impedance-correction tables.
"""
from copy import deepcopy
import json,argparse
import numpy as np
from fixed_case import ROOT,build,solve,direct_check

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--policy',choices=['control_bands','violating_buses_only','expanded_supported_controls'],default='control_bands')
    args=ap.parse_args()
    ppc,meta=build();source=meta['source'];ids=meta['source_ids']
    indices={n:k for k,n in enumerate(meta['branch_names'])}
    eligible=[];excluded={}
    tables={x.i:x for x in source.transformer_corrections}
    def correction(table,value):
        if not table:return 1.
        obj=tables[table]
        xy=[(getattr(obj,f't{k}'),getattr(obj,f'f{k}')) for k in range(1,12) if getattr(obj,f'f{k}')>0]
        return float(np.interp(value,[x[0] for x in xy],[x[1] for x in xy]))
    for t in source.transformers:
        p,w=t.p1,t.w1
        if not p.stat or p.k or w.cod!=1:continue
        reason=None
        if w.cont<=0:reason='no explicit downstream controlled bus'
        elif w.cont not in ids:reason='controlled bus not present'
        elif w.cr or w.cx:reason='load-drop compensation not supported in this experiment'
        elif w.tab and args.policy!='expanded_supported_controls':reason='impedance correction excluded from first experiment'
        elif w.rma<=w.rmi or w.vma<=w.vmi or w.ntp<2:reason='invalid adjustment bounds'
        if reason:excluded[reason]=excluded.get(reason,0)+1;continue
        name=f'trafo:{p.i}:{p.j}:{p.ckt.strip()}'
        if name not in indices:continue
        k=indices[name];j=ids[w.cont]
        # Restrict to regulation on its immediate downstream merged bus.
        if j!=ids[p.j] and args.policy!='expanded_supported_controls':
            excluded['remote regulation excluded']=excluded.get('remote regulation excluded',0)+1;continue
        eligible.append({'name':name,'branch':k,'bus':j,'rmi':w.rmi,'rma':w.rma,
            'step':(w.rma-w.rmi)/(w.ntp-1),'ntp':w.ntp,'vmi':w.vmi,'vma':w.vma,
            'w2':t.w2.windv,'source_w1':w.windv,'correction_table':w.tab,
            'source_correction_factor':correction(w.tab,w.windv)})
    work=deepcopy(ppc);history=[];seen=set();stop='iteration budget'
    for iteration in range(30):
        out,status=solve(work)
        if not status['converged']:stop='power flow failed';break
        check=direct_check(out,meta)
        row={'iteration':iteration,'checks':{k:v for k,v in check.items() if k!='voltage_violation_group_indices'},'changes':[]}
        history.append(row)
        print('iteration',iteration,check['violations'],flush=True)
        state=tuple(work['branch'][a['branch'],8] for a in eligible)
        if state in seen:stop='repeated discrete tap state';break
        seen.add(state)
        for a in eligible:
            v=out['bus'][a['bus'],7]
            if args.policy!='control_bands' and ppc['bus'][a['bus'],12]<=v<=ppc['bus'][a['bus'],11]:continue
            if a['vmi']<=v<=a['vma']:continue
            k=a['branch'];old=work['branch'][k,8]*a['w2']
            target=(a['vmi']+a['vma'])/2
            desired=old*v/target
            pos=np.clip(round((desired-a['rmi'])/a['step']),0,a['ntp']-1)
            new=a['rmi']+pos*a['step']
            if abs(new-old)<1e-10:continue
            work['branch'][k,8]=new/a['w2']
            factor=correction(a['correction_table'],new)/a['source_correction_factor']
            work['branch'][k,2:4]=ppc['branch'][k,2:4]*factor
            row['changes'].append({'transformer':a['name'],'old_w1':old,'new_w1':float(new),'controlled_voltage':float(v)})
        if not row['changes']:stop='no further eligible tap changes';break
        work['bus'][:,7:9]=out['bus'][:,7:9]
    report={'scope':__doc__,'policy':args.policy,'eligible_controls':len(eligible),'excluded_controls':excluded,
        'stop_reason':stop,'history':history,'eligible_devices':eligible}
    stem={'control_bands':'tap_experiment','violating_buses_only':'targeted_tap_experiment',
        'expanded_supported_controls':'expanded_tap_experiment'}[args.policy]
    (ROOT/f'results/{stem}.json').write_text(json.dumps(report,indent=2)+'\n')
    np.savez_compressed(ROOT/f'results/{stem}_solution.npz',**{k:out[k] for k in ['baseMVA','bus','gen','branch']})
    print(json.dumps({'eligible_controls':len(eligible),'excluded':excluded,'stop':stop,
        'initial':history[0]['checks'],'final':history[-1]['checks']},indent=2))
if __name__=='__main__':main()
