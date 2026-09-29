"""Deterministic policy fixtures and an optional equal-read-budget AI audit."""
from pathlib import Path
import sys,json,itertools,copy,time,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import decision_service as ds
from ai.challenge_agent import run

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-live',action='store_true');args=ap.parse_args()
    d=ds.matrix();prices={1341:5,2072:0,1701:25,5191:7,1571:9,1761:14,1981:12,2870:18}
    rows=[];parity=[];start=time.perf_counter()
    for budget,hours,value,floor,required,profile in itertools.product([100,500,1000],[1,4],[0,50,100],[.5,10],[['nominal'],['nominal','delivery_half'],['nominal','wind_50'],['nominal','demand_higher']],['uniform','different']):
        p=ds.default_plan(d);p.update(budget_EUR=budget,duration_hours=hours,wind_value_EUR_MWh=value,minimum_gain_MW=floor,required_scenarios=required)
        for o in p['offers']:o['energy_MWh']=20*hours;o['premium_EUR_MWh']=10 if profile=='uniform' else prices[o['bus']]
        r=ds.analyse(p,d);n=r['nominal'];g=r['guarded'];bad=bool(n and any(not x['passes'] for x in r['nominal_offer_audit'] if x['scenario_id'] in required))
        if g:assert all(x['passes'] for x in r['all_offer_results'] if x['bus']==g['bus'] and x['scenario_id'] in required)
        rows.append({'id':len(rows)+1,'status':r['status'],'nominal_bus':n['bus'] if n else None,'guarded_bus':g['bus'] if g else None,'nominal_violates_required_condition':bad,'guarded_minimum_gain_MW':g['minimum_tested_gain_MW'] if g else None,'inputs':p})
        q=copy.deepcopy(r);q.pop('elapsed_seconds');parity.append({'input':p,'expected':q})
    plan=ds.default_plan(d)
    report={'status':'completed','scope':'Authored decision grid with actual physical records and synthetic prices; not independent customer/field trials. Guard success is an enforced decision property, not an AI accuracy score.',
        'cases':len(rows),'outcomes':{s:sum(x['status']==s for x in rows) for s in ['retain','switch','withdraw','no_nominal_offer']},
        'nominal_offers_violating_required_tests':sum(x['nominal_violates_required_condition'] for x in rows),
        'guarded_offers_violating_required_tests':0,'rows':rows,'elapsed_seconds':time.perf_counter()-start,
        'audit_baselines':{m:run({'plan':plan,'budget':4,'mode':m},data=d) for m in ['deterministic','random']},
        'azure':run({'plan':plan,'budget':4,'mode':'azure'},data=d) if args.run_live else {'status':'not_run','reason':'No live Azure evaluation in this delivery. Scripted-provider tests measure application contracts only.'}}
    (ROOT/'evaluation/decision_benchmark.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (ROOT/'evaluation/decision_parity_fixtures.json').write_text(json.dumps({'matrix':d,'cases':parity},separators=(',',':'),allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ['cases','outcomes','nominal_offers_violating_required_tests','guarded_offers_violating_required_tests','elapsed_seconds']},indent=2))
if __name__=='__main__':main()
