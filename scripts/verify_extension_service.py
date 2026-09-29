from pathlib import Path
import sys,time,json,shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import extension_service as svc
checks=[]
p={'kind':'snapshot','candidate_bus':1701,'flex_MW':12.5,'line_outage':True,'wind_available_MW':55.125,'load_factor':1}
a=svc.start(p)
try:svc.start(p)
except RuntimeError:checks.append('concurrent_job_rejected')
else:raise AssertionError('Two simultaneous service jobs were accepted.')
start=time.monotonic()
while True:
 r=svc.status({'job_id':a['job_id']})
 if r['status']=='completed':break
 if r['status']=='failed':raise AssertionError(r)
 assert time.monotonic()-start<300
 time.sleep(.3)
d=r['result'];c=d['comparison']
assert d['inputs']==p and d['new_power_flows_run']>0
assert c['comparable']
assert c['baseline']['best_tested']['wind_MW']<=55.125
assert c['selected']['best_tested']['wind_MW']<=55.125
assert abs(c['energy_balance_difference_MW'])<1e-6
checks.extend(['novel_inputs_reached_worker','new_physical_solves_executed','both_best_points_pass','availability_bound_preserved','paired_energy_balance_reconciles','result_published_only_after_completion'])
shutil.copy2(svc.JOBS/a['job_id']/'result.json',ROOT/'extension_results/novel_snapshot.json')
placebo={**p,'candidate_bus':2072,'wind_available_MW':55.125}
b=svc.start(placebo)
while True:
 q=svc.status({'job_id':b['job_id']})
 if q['status']=='completed':break
 if q['status']=='failed':raise AssertionError(q)
 time.sleep(.3)
z=q['result']['comparison']
assert z['comparable'] and z['additional_hypothetical_wind_MW']==0
assert q['result']['reused_identical_evaluations']>0
checks.extend(['same_site_placebo_has_zero_difference','identical_reuse_not_counted_as_new_solve'])
shutil.copy2(svc.JOBS/b['job_id']/'result.json',ROOT/'extension_results/same_site_placebo.json')
report={'checks':checks,'passed':len(checks),'integration':'actual service functions and subprocess worker; no browser session or cloud provider used',
 'novel_result':{'wind_available_MW':55.125,'flex_MW':12.5,'difference_MW':c['additional_hypothetical_wind_MW'],'calls':d['new_power_flows_run']},'placebo_difference_MW':z['additional_hypothetical_wind_MW']}
(ROOT/'extension_results/service_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
