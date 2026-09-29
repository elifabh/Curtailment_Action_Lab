"""New physical counterexamples using unchanged v4 equations and limits."""
from pathlib import Path
import json,time,hashlib,sys,importlib.util
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'evidence_v5';OUT=D/'results'
spec=importlib.util.spec_from_file_location('physical_v4',ROOT/'evidence_v4/code/run_study.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.OUT=OUT

def key(alloc,outage,factor):return json.dumps([sorted((int(k),float(v)) for k,v in alloc.items() if v),bool(outage),float(factor)])
def origin(curve,path):
    curve['origin_file']=str(path.relative_to(ROOT))
    return curve

def main():
    if (OUT/'evaluations.jsonl').exists() or (OUT/'challenge_matrix.json').exists():raise SystemExit('Preserve prior or partial results before a separate explicit run.')
    start=time.perf_counter();p=json.loads((D/'PROTOCOL.json').read_text());s=m.Study()
    for f in sorted((ROOT/'evidence_v4/results').glob('*.json')):
        c=json.loads(f.read_text())
        if isinstance(c,dict) and 'points' in c and 'flex_allocation_MW' in c:
            s.curves[key(c['flex_allocation_MW'],c['line_outage'],c['source_load_factor'])]=origin(c,f)
    # Generate all new curve families before reviewing offer-policy outcomes.
    for family in p['new_curve_families']:
        for bus in p['candidate_buses']:
            alloc={bus:float(family['flex_MW'])}
            k=key(alloc,family['line_outage'],family['source_load_factor'])
            if k not in s.curves:
                name=f"{family['id']}_{bus}"
                c=s.curve(name,alloc,family['line_outage'],family['source_load_factor'])
                s.curves[k]=origin(c,OUT/f'{name}.json')
    cells=[]
    for scenario in p['scenarios']:
        f=scenario['flex_MW']; factor=scenario['source_load_factor']; outage=scenario['line_outage']
        base=s.curves[key({2072:f} if f else {},outage,factor)]
        a=m.select(base,scenario['wind_available_MW'])
        for bus in p['candidate_buses']:
            k=key({bus:f} if f else {},outage,factor);c=s.curves.get(k)
            b=m.select(c,scenario['wind_available_MW']) if c else None
            good=a is not None and b is not None
            if good:assert abs(a['total_consumer_demand_MW']-b['total_consumer_demand_MW'])<1e-6
            cells.append({'id':f"{scenario['id']}__{bus}",'scenario_id':scenario['id'],'bus':bus,'comparable':good,
                'additional_wind_MW':b['wind_MW']-a['wind_MW'] if good else None,
                'baseline_wind_MW':a['wind_MW'] if a else None,'selected_wind_MW':b['wind_MW'] if b else None,
                'baseline_ref':{'file':base['origin_file'],'record_id':a['id']} if a else None,
                'selected_ref':{'file':c['origin_file'],'record_id':b['id']} if b else None,
                'total_demand_MW':a['total_consumer_demand_MW'] if a else None,
                'block_reason':None if good else 'equal_demand_baseline_unverified' if a is None else 'selected_point_unverified',
                'source':'actual_calculation_records','operationally_validated':False})
    old=json.loads((ROOT/'evidence_v4/study_summary.json').read_text())
    report={'status':'completed','protocol_sha256':hashlib.sha256((D/'PROTOCOL.json').read_bytes()).hexdigest(),
        'source_sha256':old['source_sha256'],'scenarios':p['scenarios'],'candidates':[{k:v for k,v in x.items() if k in ['bus','name','graph_hops_to_wind']} for x in old['portfolio']],
        'cells':cells,'new_power_flows':s.calls,'new_passing_points':sum(x['passes_declared_snapshot_checks'] for x in s.records),
        'elapsed_seconds':time.perf_counter()-start,'all_new_evaluations':'evidence_v5/results/evaluations.jsonl',
        'limitations':['Prepared public planning model with v4 control/rating limitations.','Finite tested conditions; no probability or operational safety guarantee.','Costs and duration are user assumptions.','No chronological task, battery, rebound or SLA verification.','A blocked baseline is an unresolved comparison, not proof that the real grid cannot operate.']}
    m.dump(OUT/'challenge_matrix.json',report)
    print('COMPLETE',json.dumps({'new_power_flows':s.calls,'cells':len(cells),'comparable':sum(x['comparable'] for x in cells),'seconds':report['elapsed_seconds']}),flush=True)

if __name__=='__main__':main()
