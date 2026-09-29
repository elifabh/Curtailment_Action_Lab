"""New conditional-study contract and non-misleading evidence boundaries."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app_service as app

class ConditionalStudyTests(unittest.TestCase):
    def request(self,**kwargs):
        return {'profile':'irish_conditional_flex','wind_mw':200.,'load_scale':1.,'action_id':'flex_at_1341',**kwargs}
    def test_pair_keeps_demand_equal_and_labels_its_scope(self):
        r=app.evaluate(self.request())
        self.assertEqual(r['mode'],'precomputed_verified_study')
        self.assertAlmostEqual(r['comparison']['additional_wind_mw'],14.0625)
        self.assertTrue(all(c['passed'] for c in r['checks']))
        demand=next(m for m in r['metrics'] if m['key']=='total_demand_mw')
        self.assertEqual(demand['baseline'],demand['selected'])
        self.assertFalse(r['operationally_validated'])
        self.assertIsNone(r['evidence']['field_savings_MWh'])
    def test_unrecorded_conditions_are_rejected(self):
        for request in [self.request(wind_mw=50),self.request(action_id='somewhere_else')]:
            with self.assertRaises(ValueError):app.evaluate(request)
    def test_same_location_is_a_zero_difference_control(self):
        r=app.evaluate(self.request(action_id='flex_at_2072'))
        self.assertEqual(r['comparison']['additional_wind_mw'],0.)
    def test_search_selects_best_inspected_record_without_claiming_new_solver_calls(self):
        r=app.run_search({'profile':'irish_conditional_flex','wind_mw':200.,'load_scale':1.,'budget':2})
        self.assertEqual(r['solver_calls'],0)
        self.assertEqual(r['precomputed_evidence_reads'],2)
        inspected=[x['result']['accepted_wind_mw'] for x in r['records'] if x.get('result',{}).get('eligible')]
        self.assertEqual(r['best_valid']['result']['accepted_wind_mw'],max(inspected))
    def test_superseded_legacy_calculation_cannot_be_run(self):
        with self.assertRaises(RuntimeError):app.evaluate({'profile':app.IRISH_ID,'wind_mw':200.,'load_scale':1.,'action_id':'line_in_service'})

if __name__=='__main__':unittest.main(verbosity=2)
