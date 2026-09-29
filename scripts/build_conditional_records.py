"""Refresh the conditional-study evidence and exact offline records."""
from pathlib import Path
import sys,json,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import app_service as app

def main():
    source=ROOT/'irish_audit/results/conditional_flex_study.json'
    if source.exists():shutil.copyfile(source,ROOT/'validation/conditional_flex_study.json')
    s=app.read_json('validation/conditional_flex_study.json')
    if not s:raise RuntimeError('Run the audit and finalize_study.py first.')
    summary={'title':'Irish conditional flexibility study','status':'conditional_snapshot_checked',
        'summary':f"Same 20 MW load and line outage: the near-wind location admits {s['additional_wind_MW']:.2f} MW more hypothetical wind than the distant location in the checked prepared model.",
        'scope':'Public Irish planning network, hypothetical wind and flexible load, declared preparatory tap and shunt changes. Snapshot MW only.',
        'independent_method':'Separate RAW text parser and winding-side electrical equations; original numerical ratings and voltage/generator bounds retained.',
        'claim_not_allowed':'Measured avoided Irish curtailment, national percentages, profit, operating approval or demonstrated AI optimisation advantage.',
        'findings':[{'label':'Original source status','status':'blocked','detail':'The unmodified V33 file has 173 voltage violations; V35 has a different stored operating point. Neither is silently replaced or declared a passed source.'},
            {'label':'Prepared numerical scenario','status':'passed_scoped','detail':'Source-bounded tap changes and one explicitly hypothetical capacitor disconnection produce a starting state passing the implemented static checks.'},
            {'label':'Equal-demand location comparison','status':'passed_scoped','detail':f"Bus 2072: {s['baseline_wind_MW']:.2f} MW; bus 1341: {s['selected_wind_MW']:.2f} MW best tested wind acceptance. Both serve 7,344.51 MW consumer demand."},
            {'label':'Real asset access and operational scope','status':'blocked','detail':'Site flexibility, actual ratings, tariffs, control permissions and security studies remain unverified.'}]}
    (ROOT/'validation/irish_conditional_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    rec=app.read_json('data/recorded.json',{})
    for endpoint in ['evaluate','sensitivity','search']:
        rec[endpoint]=[x for x in rec.get(endpoint,[]) if x.get('request',{}).get('profile') not in [app.CONDITIONAL_ID,app.IRISH_ID]]
    from conditional_study import actions
    for action in [a['id'] for a in actions()]:
        req={'profile':app.CONDITIONAL_ID,'wind_mw':200.,'load_scale':1.,'action_id':action}
        rec['evaluate'].append({'request':req,'response':app.evaluate(req)})
        rec['sensitivity'].append({'request':req,'response':app.sensitivity(req)})
    for budget in (1,2,4,8):
        req={'profile':app.CONDITIONAL_ID,'wind_mw':200.,'load_scale':1.,'budget':budget}
        rec['search'].append({'request':req,'response':app.run_search(req)})
    (ROOT/'data/recorded.json').write_text(json.dumps(rec,indent=2,allow_nan=False)+'\n')
    print('Conditional study and exact recorded requests updated.')
if __name__=='__main__':main()
