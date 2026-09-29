"""Read checked study records and calculate explicitly conditional event value."""
from pathlib import Path
import json,math

ROOT=Path(__file__).resolve().parent

def study_data():
    path=ROOT/'evidence_v4/study_summary.json'
    if not path.exists():return {'status':'not_ready','summary':'The extended study has not been built.'}
    return json.loads(path.read_text())

def get_pair(case_id):
    data=study_data()
    for pair in data.get('pairs',[])+data.get('portfolio_pairs',[]):
        if pair['id']==case_id:return pair
    raise ValueError('Select a case from the recorded study.')

def _number(payload,key,low,high,optional=False):
    v=payload.get(key)
    if optional and v is None:return None
    if type(v) not in (int,float) or not math.isfinite(v) or not low<=v<=high:
        raise ValueError(f'{key} must be a finite number from {low} to {high}.')
    return float(v)

def estimate_value(payload):
    required={'case_id','duration_hours','wind_value_EUR_MWh','activation_premium_EUR_MWh','other_event_cost_EUR'}
    allowed=required|{'flex_energy_limit_MWh','displaced_generation_tCO2_MWh'}
    if not isinstance(payload,dict) or not required<=set(payload) or set(payload)-allowed:
        raise ValueError('Supply the case, duration, wind value, activation premium and other event cost; only the two documented optional inputs are supported.')
    p=get_pair(payload['case_id'])
    hours=_number(payload,'duration_hours',0,24)
    value=_number(payload,'wind_value_EUR_MWh',-1000,10000)
    premium=_number(payload,'activation_premium_EUR_MWh',-1000,10000)
    other=_number(payload,'other_event_cost_EUR',0,1_000_000)
    energy_limit=_number(payload,'flex_energy_limit_MWh',0,100_000,optional=True)
    emissions=_number(payload,'displaced_generation_tCO2_MWh',0,2,optional=True)
    base={'case_id':p['id'],'inputs':dict(payload),'mode':'conditional_event_illustration',
        'field_savings':False,'customer_profit_established':False,'new_power_flows_run':0}
    if not p['comparable']:
        return {**base,'status':'blocked_physical_comparison','reason':p['reason'],'extra_wind_MWh':None,'scenario_surplus_EUR':None}
    flex_energy=p['flex_MW']*hours
    if energy_limit is not None and flex_energy>energy_limit+1e-9:
        return {**base,'status':'blocked_energy_envelope','reason':'The requested event exceeds the entered flexible-energy envelope.',
            'required_flexible_energy_MWh':flex_energy,'extra_wind_MWh':None,'scenario_surplus_EUR':None}
    energy=p['additional_wind_MW']*hours
    displacement=p['other_generation_reduction_MW']*hours
    gross=energy*value;activation=flex_energy*premium;surplus=gross-activation-other
    return {**base,'status':'conditional_calculation','extra_wind_MWh':energy,
        'flexible_energy_MWh':flex_energy,'other_generation_reduction_MWh':displacement,
        'assumed_avoided_tCO2':displacement*emissions if emissions is not None else None,
        'gross_scenario_value_EUR':gross,'extra_activation_cost_EUR':activation,
        'scenario_surplus_EUR':surplus,
        'break_even_premium_EUR_per_flexible_MWh':(gross-other)/flex_energy if flex_energy>0 else None,
        'energy_envelope_status':'within_entered_limit' if energy_limit is not None else 'not_supplied',
        'commercial_signal':'positive_under_entered_assumptions' if surplus>1e-8 else 'negative_under_entered_assumptions' if surplus< -1e-8 else 'zero_under_entered_assumptions',
        'limitations':['Duration and values are scenario assumptions, not observed event data or market prices.',
            'Network and asset conditions are assumed to persist throughout the event; no chronological dispatch, rebound, SoC or SLA model is run.',
            'This is combined scenario value before unentered costs and contractual allocation, not measured customer profit.',
            'No annualisation or national curtailment percentage is supported.']}
