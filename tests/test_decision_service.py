"""Invariants and failure boundaries for an advisory procurement workflow."""
import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import decision_service as ds
from ai.challenge_agent import run

class DecisionTests(unittest.TestCase):
    def setUp(self):self.data=ds.matrix();self.p=ds.default_plan(self.data)
    def test_default_uses_recorded_gain_and_is_not_execution(self):
        r=ds.analyse(self.p);self.assertEqual(r['nominal']['additional_wind_MW'],20.703125)
        self.assertEqual(r['guarded']['minimum_tested_gain_MW'],9.5703125)
        self.assertFalse(r['contract_conditions']['operating_permission']);self.assertFalse(r['field_savings'])
    def test_higher_demand_baseline_blocks_all_candidates(self):
        self.p['required_scenarios']=['nominal','demand_higher'];r=ds.analyse(self.p)
        self.assertEqual(r['status'],'withdraw');self.assertIsNone(r['guarded'])
        self.assertEqual(r['data_priorities'][0]['dimension'],'demand')
    def test_adequate_budget_does_not_rescue_missing_energy(self):
        for o in self.p['offers']:o['energy_MWh']=19.9
        self.assertEqual(ds.analyse(self.p)['status'],'no_nominal_offer')
    def test_zero_budget_rejects_positive_cost(self):
        self.p['budget_EUR']=0;self.assertIsNone(ds.analyse(self.p)['nominal'])
    def test_zero_delivery_has_zero_location_gain(self):
        for c in self.data['cells']:
            if c['scenario_id']=='delivery_zero':self.assertEqual(c['additional_wind_MW'],0)
    def test_lower_delivery_uses_new_physics_and_full_reservation_cost(self):
        r=ds.evaluate_cell(self.p,1701,'delivery_half',self.data)
        self.assertNotEqual(r['additional_wind_MW'],20.703125/2)
        self.assertEqual(r['reserved_flex_MWh'],20);self.assertEqual(r['scenario_delivered_flex_MWh'],10)
        self.assertEqual(r['assumed_offer_cost_EUR'],200)
    def test_guard_can_change_offer_on_economic_counterexample(self):
        prices={1341:5,2072:0,1701:25,5191:7,1571:9,1761:14,1981:12,2870:18}
        for o in self.p['offers']:o['premium_EUR_MWh']=prices[o['bus']]
        r=ds.analyse(self.p)
        self.assertEqual(r['nominal']['bus'],1701);self.assertEqual(r['status'],'switch')
        self.assertNotEqual(r['guarded']['bus'],1701)
        self.assertGreaterEqual(r['guarded']['minimum_assumed_surplus_EUR'],0)
    def test_offer_availability_cannot_be_ignored(self):
        for o in self.p['offers']:o['available']=False
        self.assertIsNone(ds.analyse(self.p)['guarded'])
    def test_negative_wind_value_does_not_create_profit(self):
        self.p['wind_value_EUR_MWh']=-10;self.assertIsNone(ds.analyse(self.p)['nominal'])
    def test_nonfinite_boolean_extra_or_duplicate_fields_rejected(self):
        for k,v in [('budget_EUR',True),('budget_EUR',float('inf')),('duration_hours',0),('minimum_gain_MW',.1)]:
            with self.assertRaises(ValueError):ds.analyse({**self.p,k:v})
        with self.assertRaises(ValueError):ds.analyse({**self.p,'skip_checks':True})
        q=copy.deepcopy(self.p);q['offers'][0]=q['offers'][1]
        with self.assertRaises(ValueError):ds.analyse(q)
    def test_required_scenarios_cannot_skip_nominal(self):
        for req in [[],['delivery_half'],['nominal','unrecorded'],['nominal','nominal']]:
            with self.assertRaises(ValueError):ds.analyse({**self.p,'required_scenarios':req})

class ChallengeAgentTests(unittest.TestCase):
    def setUp(self):self.p=ds.default_plan()
    def message(self,args,name='test_offer_scenario',calls=1):
        import json
        return {'choices':[{'finish_reason':'tool_calls','message':{'tool_calls':[{'id':f'tool_{i}','type':'function','function':{'name':name,'arguments':json.dumps(args)}} for i in range(calls)]}}]}
    def test_rule_audit_is_bounded_and_has_no_provider_calls(self):
        r=run({'plan':self.p,'budget':2,'mode':'deterministic'})
        self.assertEqual(r['record_reads'],2);self.assertEqual(r['provider_calls'],0);self.assertEqual(r['new_power_flows_run'],0)
    def test_audit_has_no_hidden_full_matrix_search(self):
        from unittest.mock import patch
        original=ds.evaluate_cell;seen=[]
        def tracked(p,b,s,d):seen.append((b,s));return original(p,b,s,d)
        with patch.object(ds,'evaluate_cell',side_effect=tracked):r=run({'plan':self.p,'budget':2})
        self.assertEqual(len(seen),10)
        self.assertEqual(sum(s=='nominal' for b,s in seen),8)
        self.assertEqual(r['baseline_lookups_for_offer_selection'],8)
    def test_malformed_provider_payload_fails_closed(self):
        for response in [None,[],{'choices':[None]},{'choices':[{'message':None}]},{'usage':None}]:
            r=run({'plan':self.p,'mode':'azure'},provider=lambda _,v=response:v)
            self.assertEqual(r['status'],'provider_error');self.assertEqual(r['record_reads'],0)
    def test_scripted_provider_cannot_repeat_a_record(self):
        r=run({'plan':self.p,'budget':2,'mode':'azure'},provider=lambda _:self.message({'scenario_id':'wind_25'}))
        self.assertEqual(r['record_reads'],1);self.assertLessEqual(r['provider_calls'],5);self.assertTrue(r['rejected']);self.assertFalse(r['is_live_provider'])
    def test_provider_cannot_override_cost_or_engine_checks(self):
        r=run({'plan':self.p,'budget':1,'mode':'azure'},provider=lambda _:self.message({'scenario_id':'wind_25','skip_checks':True}))
        self.assertEqual(r['record_reads'],0);self.assertTrue(r['rejected'])
    def test_parallel_tool_batch_is_never_executed(self):
        r=run({'plan':self.p,'budget':2,'mode':'azure'},provider=lambda _:self.message({'scenario_id':'wind_25'},calls=2))
        self.assertEqual(r['record_reads'],0);self.assertEqual(r['status'],'invalid_provider_batch')
    def test_refusal_is_not_a_success(self):
        r=run({'plan':self.p,'mode':'azure'},provider=lambda _:{'choices':[{'finish_reason':'stop','message':{'refusal':'No'}}]})
        self.assertEqual(r['status'],'provider_refused');self.assertEqual(r['record_reads'],0)
    def test_invented_success_prose_cannot_supply_numbers(self):
        r=run({'plan':self.p,'mode':'azure'},provider=lambda _:{'choices':[{'finish_reason':'stop','message':{'content':'Guaranteed 9000 MW saved'}}]})
        self.assertEqual(r['record_reads'],0);self.assertEqual(r['status'],'no_tool_calls');self.assertNotIn('9000',r['summary'])
    def test_impossible_budget_rejected(self):
        for b in [True,0,8,float('nan')]:
            with self.assertRaises(ValueError):run({'plan':self.p,'budget':b})

if __name__=='__main__':unittest.main()
