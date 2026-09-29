"""Compare optional Azure tool use against the verified stored study alternatives.

Default: no Azure request. This measures retrieval/selection, not new power-flow
optimisation. Physical wind-acceptance values come from the prior offline study.
"""
from pathlib import Path
import sys,json,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import app_service
from ai.evaluate_agent import benchmark

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-live',action='store_true',help='Call the configured Azure deployment; consumes its quota.')
    p.add_argument('--budget',type=int,default=4,choices=range(1,9))
    a=p.parse_args()
    context=app_service.get_agent_context('irish_conditional_flex',200.,1.)
    callback=app_service.candidate_callback('irish_conditional_flex')
    report=benchmark(context,callback,
        'Compare the allowed hypothetical locations of the same 20 MW load. Use the stored verified study, preserve its assumptions, and do not claim actual Irish savings or operating approval.',
        budget=a.budget,run_live=a.run_live)
    report['evaluation_scope']=__doc__
    report['new_power_flows_run']=0
    report['physical_AI_improvement_claimed']=False
    for key in ('baseline','agent'):
        if isinstance(report.get(key),dict):
            report[key]['solver_calls']=0
            report[key]['precomputed_evidence_reads']=report[key].get('budget_used',0)
            report[key]['candidate_evaluation_mode']='precomputed_verified_study'
    (ROOT/'evaluation/conditional_agent_results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'live_requested':a.run_live,'scope':'Stored evidence retrieval/selection only',
        'baseline_metrics':report['baseline_metrics'],'agent_metrics':report['agent_metrics']},indent=2))
if __name__=='__main__':main()
