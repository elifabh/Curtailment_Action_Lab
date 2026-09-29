"""Recheck selected states with the latest direct RAW verifier and create UI evidence."""
from pathlib import Path
import hashlib,json,copy
import numpy as np
from fixed_case import ROOT,build,direct_check,recover_tie_flows
from raw_equation_check import verify

def main():
    _,meta=build();report=json.loads((ROOT/'results/wind_screen.json').read_text())
    taps=report['preparation']['tap_changes'];off=report['preparation']['disconnected_shunt_buses']
    for name,r in report['best_tested'].items():
        state=dict(np.load(ROOT/f'results/wind_{name}_best.npz'))
        check=verify(state,meta,tap_changes=taps,shunt_off=off,branch_off=['line:1341:1701:1'] if r['line_outage'] else [],
            wind_mw=r['wind_MW'],extra_load=r['extra_load_MW'])
        assert check['passed'],check
        r['raw_equations']=check
        mm=copy.deepcopy(meta)
        raw_index={bus:i for i,bus in mm['reverse_ids'].items()}
        mm['full']['bus'][raw_index[1341],2]-=r['wind_MW']
        for bus,p in r['extra_load_MW'].items():mm['full']['bus'][raw_index[int(bus)],2]+=p
        for bus in off:mm['full']['bus'][raw_index[bus],5]-=25.
        tie=recover_tie_flows(state,mm)
        assert tie['max_nodal_balance_residual_MVA']<1e-4 and tie['tree_overloads']==0 and tie['cyclic_allocation_overloads']==0
        r['ideal_ties']={k:v for k,v in tie.items() if k!='flows'}
        r['state_sha256']=hashlib.sha256((ROOT/f'results/wind_{name}_best.npz').read_bytes()).hexdigest()
    (ROOT/'results/wind_screen.json').write_text(json.dumps(report,indent=2)+'\n')
    near=report['best_tested']['outage_flex_at_1341'];far=report['best_tested']['outage_flex_at_2072']
    delta=near['wind_MW']-far['wind_MW']
    study={'id':'irish_conditional_flex','title':'Irish planning study: where flexibility is used matters',
        'status':'conditional_snapshot_checks_passed','additional_wind_MW':delta,
        'baseline_wind_MW':far['wind_MW'],'selected_wind_MW':near['wind_MW'],
        'hypothetical_available_wind_MW':200,'flexible_demand_MW':20,
        'total_consumer_demand_MW':7324.51+20,
        'baseline_flex_bus':2072,'selected_flex_bus':1341,
        'conditions_held_equal':['200 MW hypothetical wind availability','20 MW hypothetical flexible demand at unity power factor',
            '7,324.51 MW source consumer demand','Line 1341–1701 out of service',
            'Prepared taps, disconnected capacitor, local voltage targets and fixed HVDC boundary'],
        'preparation':report['preparation'],
        'assumptions':['Hypothetical controllable loads at the two named buses. No real data-centre capacity or permission was supplied.',
            'Both alternatives use a derived planning case with declared tap changes and a capacitor disconnection. The original RAW case is not feasible under all its own limits.',
            'The source file is a public transmission planning model, not a measured dispatch-down time series.',
            'Aghada bus 10470 balances changes. HVDC import remains a calibrated fixed boundary; source local voltage targets are held fixed.'],
        'limitations':['This is a conditional model experiment, not measured Irish savings or an instruction to move a real load.',
            'Best tested points within 0–200 MW; search is not certified globally optimal. Refinement interval is at most 0.25 MW.',
            'The original ratings are preserved, including zero and very large placeholder-like ratings. Actual equipment capability still needs confirmation.',
            '144 ideal tree-tie flows pass the recovery check; four cyclic tie flows use an explicit inverse-reactance allocation, not a unique measured split.',
            'No N-1, dynamics, inertia/SNSP, protection, switching permission, tariff, site SLA or intertemporal device feasibility was established.',
            'The snapshot cannot establish avoided MWh, profit, or a percentage of Ireland-wide curtailment.',
            'AI did not produce this result. Deterministic calculations and verification produced it. Live Microsoft AI remains untested.'],
        'baseline':far,'selected':near,'operationally_validated':False,'field_savings_MWh':None,
        'interpretation':'A controlled locational comparison: same added demand, different connection point, same network outage.',
        'source_sha256':meta['source_import']['source_sha256']}
    (ROOT/'results/conditional_flex_study.json').write_text(json.dumps(study,indent=2)+'\n')
    print(json.dumps({k:v for k,v in study.items() if k in ['additional_wind_MW','baseline_wind_MW','selected_wind_MW','total_consumer_demand_MW']}))
if __name__=='__main__':main()
