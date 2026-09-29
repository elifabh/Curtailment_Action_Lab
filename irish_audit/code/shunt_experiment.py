"""Enumerate explicit hypothetical capacitor disconnections after tap adjustment.

The two named devices are locked in the source. Changing their state is a new
planning scenario with an assumed permission, NOT a reconstruction fix.
Select the passing alternative with the fewest disconnections, then bus ID.
"""
import json,numpy as np
from copy import deepcopy
from fixed_case import ROOT,build,solve,direct_check,recover_tie_flows

def main():
    p,m=build();b=dict(np.load(ROOT/'results/expanded_tap_experiment_solution.npz'))
    b['version']='2';b['baseMVA']=float(b['baseMVA']);b['branch']=b['branch'][:,:13]
    rows=[];chosen=False
    for disconnect in [[],[74561],[74564],[74561,74564]]:
        work=deepcopy(b);mm=deepcopy(m)
        for bid in disconnect:
            shunts=[s for s in m['source'].switched_shunts if s.i==bid]
            assert len(shunts)==1 and shunts[0].stat==1 and shunts[0].binit==25
            work['bus'][m['source_ids'][bid],5]-=25.
            for ix,rawid in mm['reverse_ids'].items():
                if rawid==bid:mm['full']['bus'][ix,5]-=25.
        o,s=solve(work);ch=direct_check(o,m);ties=recover_tie_flows(o,mm)
        row={'disconnected_shunt_buses':disconnect,'scope':__doc__,'solver':s,'checks':ch,
            'tie_recovery':{k:v for k,v in ties.items() if k!='flows'}}
        rows.append(row);print(disconnect,ch['violations'],flush=True)
        if ch['passes_implemented_checks'] and not chosen:
            chosen=True
            np.savez_compressed(ROOT/'results/feasible_counterfactual.npz',**{k:o[k] for k in ['baseMVA','bus','gen','branch']})
            (ROOT/'results/feasible_counterfactual_actions.json').write_text(json.dumps({'disconnect_shunts':disconnect,'scope':__doc__},indent=2)+'\n')
    (ROOT/'results/shunt_counterfactuals.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':main()
