"""Strict reader for verified, precomputed Irish connection-point alternatives."""
from pathlib import Path
import copy,json
ROOT=Path(__file__).resolve().parent
PROFILE_ID='irish_conditional_flex'
ACTIONS={'flex_at_2072':'baseline','flex_at_1341':'selected'}

def study():return json.loads((ROOT/'validation/conditional_flex_study.json').read_text())

def portfolio():
    path=ROOT/'evidence_v4/study_summary.json'
    if not path.exists():return []
    return json.loads(path.read_text()).get('portfolio',[])

def actions():
    rows=portfolio()
    if rows:return [{'id':f"flex_at_{r['bus']}",'name':f"20 MW at {r['name'].title()} (bus {r['bus']})"}
                    for r in rows if r['eligible_in_study']]
    return [{'id':'flex_at_2072','name':'20 MW at Cruiserath, Dublin (bus 2072)'},
            {'id':'flex_at_1341','name':'20 MW at Binbane, near wind (bus 1341)'}]

def profile():
    s=study()
    return {'id':PROFILE_ID,'name':'Irish planning study · 20 MW flexibility',
        'description':'Same demand and network outage, different connection points for hypothetical 20 MW flexible demand. Verified stored snapshots; use Robustness & value for other tested conditions.',
        'status':'Conditional snapshot checks passed','validation_status':'conditional_snapshot_checked',
        'available':True,'runtime_available':False,'result_mode':'precomputed_verified_study',
        'actions':actions(),
        'limits':{'wind_mw':{'min':200,'max':200,'step':1},'load_scale':{'min':1,'max':1,'step':1}},
        'default_request':{'profile':PROFILE_ID,'wind_mw':200.,'load_scale':1.,'action_id':'flex_at_1341'},
        'baseline':'20 MW flexible demand at bus 2072; same total demand, wind availability, outage and prepared controls.',
        'assumptions':s['assumptions'], 'limitations':s['limitations'],
        'provenance':[{'name':'EirGrid TYTFS2024 official planning files',
            'url':'https://cms.eirgrid.ie/all-island-ten-year-transmission-forecast-statement-2024',
            'kind':'Public Irish network model; additional wind and flexible load are hypothetical'}]}

def candidate(request):
    if request.get('action_id') not in [a['id'] for a in actions()] or request.get('wind_mw')!=200 or request.get('load_scale')!=1:
        raise ValueError('This profile supports exactly 200 MW available wind, load scale 1, and the checked 20 MW connection-point alternatives. Use the recorded study explorer or audit code for other conditions.')
    s=study();rows=portfolio();checks=[]
    if rows:
        r=next(x['best_state'] for x in rows if f"flex_at_{x['bus']}"==request['action_id'])
        ch={**r,'direct_branch_flow_difference_MVA':r['direct_flow_difference_MVA']}
    else:r=s[ACTIONS[request['action_id']]];ch=r['checks']
    for key,n in ch['violations'].items():
        checks.append({'id':key,'label':key.replace('_',' ').capitalize(),'passed':n==0,'value':n,'limit':0,'detail':f'{n} violations under the declared model limits.'})
    for key,bound in [('direct_balance_max_MVA',1e-4),('direct_branch_flow_difference_MVA',1e-6)]:
        v=ch[key];checks.append({'id':key,'label':key.replace('_',' ').capitalize(),'passed':v<=bound,'value':v,'limit':bound,'detail':f'{v:.3g} MVA; tolerance {bound:g} MVA.'})
    checks.append({'id':'raw_source_crosscheck','label':'Independent RAW electrical equations and unchanged source limits',
        'passed':r['raw_equations']['passed'],'detail':'Separate direct-text parsing and winding-voltage equations reproduce the solved state. HVDC remains a declared fixed boundary.'})
    if rows:
        t=r['ideal_ties']
        checks.append({'id':'ideal_tie_recovery','label':'Recovered ideal-tie flows under declared allocation',
            'passed':t['max_nodal_balance_residual_MVA']<1e-4 and t['tree_overloads']==0 and t['cyclic_allocation_overloads']==0,
            'detail':'Tree tie flows are unique. Four cyclic tie edges use the declared inverse-reactance allocation; alternative cycle-flow splits are not certified.'})
    return {'eligible':all(c['passed'] for c in checks),'accepted_wind_mw':r['wind_MW'],
        'status':'conditional_snapshot_checked','mode':'precomputed_verified_study','checks':checks,
        'summary':'Verified stored mathematical scenario. Eligibility applies only to comparison within the declared study; it grants no operating permission.',
        'assumptions':s['assumptions'],'preparation':s['preparation'],
        'limitations':s['limitations'],'evidence':r,'operationally_validated':False,'physical_actions_executed':False}

def comparison(request):
    s=study();a=candidate({**request,'action_id':'flex_at_2072'});b=candidate(request)
    delta=b['accepted_wind_mw']-a['accepted_wind_mw']
    data=[('accepted_wind_mw','Best tested wind acceptance','MW',a['accepted_wind_mw'],b['accepted_wind_mw']),
        ('withheld_wind_mw','Hypothetical available wind not accepted','MW',200-a['accepted_wind_mw'],200-b['accepted_wind_mw']),
        ('flexible_demand_mw','Flexible demand served','MW',20.,20.),
        ('total_demand_mw','Total consumer demand','MW',s['total_consumer_demand_MW'],s['total_consumer_demand_MW'])]
    metrics=[{'key':k,'label':l,'unit':u,'baseline':x,'selected':y,'delta':y-x} for k,l,u,x,y in data]
    return {'title':s['title'],'status':'conditional_snapshot_checked','eligible':a['eligible'] and b['eligible'],
        'mode':'precomputed_verified_study',
        'summary':f'The selected connection point accepts {delta:.2f} MW more hypothetical wind than Cruiserath in this prepared Irish planning-model scenario. Both alternatives serve the same 20 MW flexible load. These are precomputed snapshot results, not field savings or an approved dispatch.',
        'baseline':a,'selected':b,'metrics':metrics,
        'comparison':{'additional_wind_mw':delta,'eligible_for_claim':a['eligible'] and b['eligible'],
            'claim_scope':'Conditional mathematical snapshot only'},
        'checks':[{**c,'id':side+'_'+c['id'],'label':side.title()+': '+c['label']}
                  for side,r in [('baseline',a),('selected',b)] for c in r['checks']],
        'assumptions':s['assumptions'],'limitations':s['limitations'],
        'evidence':{'conditions_held_equal':s['conditions_held_equal'],'preparation':s['preparation'],
            'source_sha256':s['source_sha256'],'operationally_validated':False,'field_savings_MWh':None},
        'operationally_validated':False,'physical_actions_executed':False}
