"""Finite offer selection and conditional counterexample audit. No transactions."""
from pathlib import Path
import json,math,time
ROOT=Path(__file__).resolve().parent

def matrix():
    p=ROOT/'evidence_v5/results/challenge_matrix.json'
    if not p.exists():raise RuntimeError('The physical challenge matrix has not been built.')
    return json.loads(p.read_text())

def num(x,name,lo,hi):
    if type(x) not in (int,float) or not math.isfinite(x) or not lo<=x<=hi:raise ValueError(f'{name} must be a finite number from {lo} to {hi}.')
    return float(x)

def validate(payload,data=None):
    d=data or matrix()
    keys={'budget_EUR','duration_hours','wind_value_EUR_MWh','minimum_gain_MW','require_nonnegative_surplus','required_scenarios','offers'}
    if not isinstance(payload,dict) or set(payload)!=keys:raise ValueError('Supply exactly the documented decision fields.')
    p=dict(payload)
    for k,lo,hi in [('budget_EUR',0,1e6),('duration_hours',.01,24),('wind_value_EUR_MWh',-1000,10000),('minimum_gain_MW',.5,200)]:p[k]=num(p[k],k,lo,hi)
    if type(p['require_nonnegative_surplus']) is not bool:raise ValueError('The surplus condition must be boolean.')
    ids=[x['id'] for x in d['scenarios']];req=p['required_scenarios']
    if not isinstance(req,list) or not req or any(not isinstance(x,str) or x not in ids for x in req) or len(set(req))!=len(req) or 'nominal' not in req:raise ValueError('Required conditions must be distinct declared scenario IDs and include nominal.')
    candidates=[x['bus'] for x in d['candidates']];offers=p['offers']
    if not isinstance(offers,list) or len(offers)!=len(candidates):raise ValueError('Supply one offer for each declared candidate.')
    seen=set();clean=[]
    for o in offers:
        if not isinstance(o,dict) or set(o)!={'bus','premium_EUR_MWh','available','energy_MWh'}:raise ValueError('An offer requires bus, premium_EUR_MWh, available and energy_MWh.')
        if type(o['bus']) is not int or o['bus'] not in candidates or o['bus'] in seen or type(o['available']) is not bool:raise ValueError('Offer IDs must be unique declared buses and availability must be boolean.')
        seen.add(o['bus']);clean.append({'bus':o['bus'],'premium_EUR_MWh':num(o['premium_EUR_MWh'],'premium',0,10000),'available':o['available'],'energy_MWh':num(o['energy_MWh'],'energy_MWh',0,1e5)})
    p['offers']=clean
    return p

def default_plan(d=None):
    d=d or matrix()
    return {'budget_EUR':500,'duration_hours':1,'wind_value_EUR_MWh':50,'minimum_gain_MW':.5,'require_nonnegative_surplus':True,'required_scenarios':['nominal','delivery_half','demand_lower'],
        'offers':[{'bus':c['bus'],'premium_EUR_MWh':10,'available':True,'energy_MWh':20} for c in d['candidates']]}

def evaluate_cell(p,bus,sid,d):
    o=next(x for x in p['offers'] if x['bus']==bus);c=next(x for x in d['cells'] if x['bus']==bus and x['scenario_id']==sid)
    s=next(x for x in d['scenarios'] if x['id']==sid);cost=20*p['duration_hours']*o['premium_EUR_MWh'];reasons=[]
    if not o['available']:reasons.append('offer_unavailable')
    if o['energy_MWh']+1e-9<20*p['duration_hours']:reasons.append('insufficient_offered_energy')
    if cost>p['budget_EUR']+1e-9:reasons.append('over_budget')
    gain=c['additional_wind_MW'] if c['comparable'] else None
    energy=gain*p['duration_hours'] if gain is not None else None
    surplus=energy*p['wind_value_EUR_MWh']-cost if energy is not None else None
    if not c['comparable']:reasons.append(c['block_reason'])
    else:
        if gain+1e-9<p['minimum_gain_MW']:reasons.append('below_requested_wind_gain')
        if p['require_nonnegative_surplus'] and surplus< -1e-9:reasons.append('negative_assumed_surplus')
    return {'bus':bus,'scenario_id':sid,'scenario_name':s['name'],'dimension':s['dimension'],'passes':not reasons,'reasons':reasons,
        'additional_wind_MW':gain,'assumed_extra_wind_MWh':energy,'reserved_flex_MWh':20*p['duration_hours'],'scenario_delivered_flex_MWh':s['flex_MW']*p['duration_hours'],
        'assumed_offer_cost_EUR':cost,'assumed_surplus_EUR':surplus,'physical_record':c,'new_power_flows_run':0}

DATA_FIELDS={'wind':('Local wind availability and forecast','Confirm the wind conditions during the proposed event.'),
    'delivery':('Metered flexibility and reserve obligations','Confirm delivered power and energy, deadlines and protected reserve before booking flexibility.'),
    'demand':('Reviewed demand and generation dispatch','Confirm the operating point and redispatch/control scope. A failed fixed-control baseline needs model review.'),
    'network':('Operator-confirmed network state','Confirm the line status, usable ratings and permitted controls.')}

def analyse(payload,data=None):
    started=time.perf_counter();d=data or matrix();p=validate(payload,d)
    allrows=[evaluate_cell(p,o['bus'],s['id'],d) for o in p['offers'] for s in d['scenarios']]
    nominal=sorted([x for x in allrows if x['scenario_id']=='nominal' and x['passes']],key=lambda x:(-x['additional_wind_MW'],x['assumed_offer_cost_EUR'],x['bus']))
    n=nominal[0] if nominal else None;choices=[]
    for o in p['offers']:
        needed=[x for x in allrows if x['bus']==o['bus'] and x['scenario_id'] in p['required_scenarios']]
        if all(x['passes'] for x in needed):choices.append({'bus':o['bus'],'minimum_tested_gain_MW':min(x['additional_wind_MW'] for x in needed),'minimum_assumed_surplus_EUR':min(x['assumed_surplus_EUR'] for x in needed),'assumed_offer_cost_EUR':needed[0]['assumed_offer_cost_EUR'],'required_records':[x['physical_record']['id'] for x in needed]})
    choices.sort(key=lambda x:(-x['minimum_tested_gain_MW'],x['assumed_offer_cost_EUR'],x['bus']));g=choices[0] if choices else None
    status='no_nominal_offer' if n is None else 'withdraw' if g is None else 'retain' if n['bus']==g['bus'] else 'switch'
    audit=[x for x in allrows if n and x['bus']==n['bus']];priorities=[]
    for dim,(field,action) in DATA_FIELDS.items():
        bad=[x for x in audit if x['dimension']==dim and not x['passes']]
        if bad:priorities.append({'dimension':dim,'requested_data':field,'action':action,'affected_required_conditions':sum(x['scenario_id'] in p['required_scenarios'] for x in bad),'counterexample_records':[x['physical_record']['id'] for x in bad],'failed_tested_conditions':len(bad)})
    priorities.sort(key=lambda x:(-x['affected_required_conditions'],-x['failed_tested_conditions'],x['dimension']))
    return {'status':status,'inputs':p,'nominal':n,'guarded':g,'eligible_guarded_choices':choices,'nominal_offer_audit':audit,'all_offer_results':allrows,'data_priorities':priorities,
        'contract_conditions':{'reserved_power_MW':20,'assumed_duration_hours':p['duration_hours'],'required_scenarios':p['required_scenarios'],'operating_permission':False,'execution':'Advisory only. No contract, bid or device command is sent.'},
        'scope':'Conditional selection among eight hypothetical 20 MW offers using checked planning-model records.',
        'limitations':d['limitations']+['Passing all selected tests is not a guarantee outside the finite tested set.','Reservation cost uses all quoted 20 MW even in lower-delivery stress cases.','Priority means observed decision sensitivity, not a measured monetary value of information.'],
        'source_sha256':d['source_sha256'],'protocol_sha256':d['protocol_sha256'],'record_reads':len(allrows),'new_power_flows_run':0,'elapsed_seconds':time.perf_counter()-started,'field_savings':False,'customer_profit_established':False}

def configuration():
    d=matrix()
    return {'matrix':d,'default_plan':default_plan(d),'price_status':'Illustrative editable offers; no customer quotations supplied.'}
