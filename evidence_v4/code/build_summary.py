"""Summarise actual study outputs for the app; never substitute missing results."""
from pathlib import Path
import json,hashlib,statistics
ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/'evidence_v4'

def main():
    p=DIR/'results/report.json'
    if not p.exists():raise SystemExit('Run the complete physical study first.')
    r=json.loads(p.read_text());proto=json.loads((DIR/'PROTOCOL.json').read_text())
    assert hashlib.sha256((DIR/'PROTOCOL.json').read_bytes()).hexdigest()==r['protocol_sha256']
    pairs=[]
    for n,x in enumerate(r['primary_pairs'],1):
        a,b=x['baseline'],x['selected']
        if x['comparable']:
            assert a['passes_declared_snapshot_checks'] and b['passes_declared_snapshot_checks']
            assert abs(a['total_consumer_demand_MW']-b['total_consumer_demand_MW'])<1e-6
            if x['flex_MW']==0:assert abs(x['additional_wind_MW'])<1e-8
        pairs.append({'id':f'case_{n:02d}',**{k:v for k,v in x.items() if k not in ('baseline','selected')},
            'baseline_wind_MW':a['wind_MW'] if a else None,'selected_wind_MW':b['wind_MW'] if b else None,
            'baseline_record_id':a['id'] if a else None,'selected_record_id':b['id'] if b else None,
            'baseline_other_generation_MW':a['other_generation_MW'] if a else None,
            'selected_other_generation_MW':b['other_generation_MW'] if b else None,
            'total_demand_MW':a['total_consumer_demand_MW'] if a else b['total_consumer_demand_MW'] if b else None,
            'model_scope':'conditional_prepared_network','field_savings_MWh':None})
    portfolio=[]
    for x in r['portfolio']:
        c=x['curve'];b=c['best_tested']
        portfolio.append({k:v for k,v in x.items() if k!='curve'}|{
            'best_tested_wind_MW':b['wind_MW'] if b else None,
            'eligible_in_study':b is not None,'record_id':b['id'] if b else None,
            'measured_original_curve_calls':c['calls'],'measured_original_curve_seconds':c['elapsed_seconds'],
            'reused_exact_inputs_in_portfolio_phase':c['reused_exact_inputs'],
            'best_state':b})
    valid=[x for x in portfolio if x['eligible_in_study']]
    best=max(valid,key=lambda x:x['best_tested_wind_MW']) if valid else None
    other=[x for x in valid if x['bus']!=1341]
    best_other=max(other,key=lambda x:x['best_tested_wind_MW']) if other else None
    nearest=min(portfolio,key=lambda x:(x['graph_hops_to_wind'],x['bus']))
    existing=next(x for x in portfolio if x['bus']==2072)
    portfolio_pairs=[]
    for x in portfolio:
        a=existing['best_state'];b=x['best_state'];ok=a is not None and b is not None
        if ok:assert abs(a['total_consumer_demand_MW']-b['total_consumer_demand_MW'])<1e-6
        delta=b['wind_MW']-a['wind_MW'] if ok else None
        portfolio_pairs.append({'id':f"portfolio_{x['bus']}",'selected_bus':x['bus'],'selected_location_name':x['name'],
            'flex_MW':20,'line_outage':True,'source_load_factor':1.,'wind_available_MW':200,
            'comparable':ok,'additional_wind_MW':delta,
            'other_generation_reduction_MW':a['other_generation_MW']-b['other_generation_MW'] if ok else None,
            'interpretation':'positive' if ok and delta>.5 else 'negative' if ok and delta<-.5 else 'neutral' if ok else 'blocked',
            'reason':None if ok else 'No checked pair for this portfolio comparison.',
            'baseline_wind_MW':a['wind_MW'] if a else None,'selected_wind_MW':b['wind_MW'] if b else None,
            'baseline_record_id':a['id'] if a else None,'selected_record_id':b['id'] if b else None,
            'total_demand_MW':a['total_consumer_demand_MW'] if a else None,
            'model_scope':'conditional_prepared_network','field_savings_MWh':None})
    uniform=r['uniform_allocation']['best_tested']
    compare=[{'method':'Existing location: Cruiserath','accepted_wind_MW':existing['best_tested_wind_MW'],'candidate_curves':1},
        {'method':'Nearest connection rule','accepted_wind_MW':nearest['best_tested_wind_MW'],'candidate_curves':1},
        {'method':'Equal allocation across eight candidates','accepted_wind_MW':uniform['wind_MW'] if uniform else None,'candidate_curves':1},
        {'method':'Best of eight checked candidates','accepted_wind_MW':best['best_tested_wind_MW'] if best else None,'candidate_curves':8}]
    flows=[json.loads(line) for line in (DIR/'results/evaluations.jsonl').read_text().splitlines()]
    assert len(flows)==r['new_power_flows']
    duration=[x['elapsed_seconds'] for x in flows]
    default=next(x for x in pairs if x['wind_available_MW']==200 and x['flex_MW']==20 and x['line_outage'])
    summary={'status':'completed','scope':r['scope'],'primary_summary':r['primary_summary'],
        'pairs':pairs,'default_case_id':default['id'],'stress_pairs':r['stress_pairs'],
        'portfolio':portfolio,'portfolio_pairs':portfolio_pairs,'baseline_comparison':compare,'best_candidate_bus':best['bus'] if best else None,
        'best_non_colocated_candidate':best_other,
        'nearest_rule_gap_to_best_MW':best['best_tested_wind_MW']-nearest['best_tested_wind_MW'] if best and nearest['eligible_in_study'] else None,
        'location_blind':{'eligible_candidates':len(valid),'total_candidates':len(portfolio),
            'mean_accepted_among_eligible_MW':statistics.mean(x['best_tested_wind_MW'] for x in valid) if valid else None,
            'minimum_accepted_among_eligible_MW':min(x['best_tested_wind_MW'] for x in valid) if valid else None,
            'maximum_accepted_among_eligible_MW':max(x['best_tested_wind_MW'] for x in valid) if valid else None,
            'note':'No model of customer selection probabilities or differing site prices. Failed candidates are not counted as usable output.'},
        'runtime':{'power_flows':len(flows),'passing_power_flows':r['passing_power_flows'],
            'elapsed_seconds':r['total_elapsed_seconds'],'setup_seconds':r['setup_seconds'],
            'median_checked_evaluation_seconds':statistics.median(duration),
            'p95_checked_evaluation_seconds':sorted(duration)[min(len(duration)-1,int(.95*len(duration)))],
            'single_machine_single_run':True,'environment':r['runtime'],
            'interpretation':'Real calculation timings, including verification where passed. UI requests read stored results and are not counted as new power flows.'},
        'source_sha256':r['source_sha256'],'protocol_sha256':r['protocol_sha256'],
        'assumptions':[proto['preparation'],'Hypothetical flexible assets; no real facility or operating permission was supplied.',
            'Same consumer demand and network state within each pair; only the additional flexible-load location changes.',
            'Best tested points under an availability ceiling, not a global optimum or historical dispatch simulation.'],
        'limitations':['One prepared public planning network; findings do not establish all operating states or other grids.',
            'Original zero and placeholder-like ratings remain. Full operational security and control permissions are not established.',
            'Stress-test failures and non-beneficial scenarios remain in the report.',
            'Conditional MWh/value calculations require explicit duration and price assumptions; no measured annual saving.',
            'An exhaustive screen uses more calculations than a simple one-candidate rule; no unfair equal-budget superiority claim.',
            'Live Microsoft AI is not run; the numerical outcome is produced by deterministic physics calculations.'],
        'sources':[{'name':'EirGrid public TYTFS2024 planning study','url':'https://cms.eirgrid.ie/all-island-ten-year-transmission-forecast-statement-2024'},
            {'name':'Prior work and comparator review','file':'docs/NOVELTY_AND_COMPARATORS_EN.md'}]}
    (DIR/'study_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'summary':summary['primary_summary'],'best_candidate_bus':summary['best_candidate_bus'],
        'best_non_colocated_bus':best_other['bus'] if best_other else None,
        'baselines':compare,'runtime':summary['runtime']},indent=2))

if __name__=='__main__':main()
