"""Physical eligibility and conservative value-accounting contracts."""
from pathlib import Path
import sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import study_service as service

class ValueTests(unittest.TestCase):
    def setUp(self):
        self.pair={'id':'controlled','comparable':True,'flex_MW':20.,'additional_wind_MW':14.,'other_generation_reduction_MW':13.,'reason':None}
        self.request={'case_id':'controlled','duration_hours':2.,'wind_value_EUR_MWh':50.,'activation_premium_EUR_MWh':10.,'other_event_cost_EUR':0.}
        self.mock=patch.object(service,'get_pair',return_value=self.pair);self.mock.start();self.addCleanup(self.mock.stop)
    def test_zero_duration_has_zero_energy_and_no_unit_price_division(self):
        r=service.estimate_value({**self.request,'duration_hours':0})
        self.assertEqual(r['extra_wind_MWh'],0)
        self.assertIsNone(r['break_even_premium_EUR_per_flexible_MWh'])
    def test_negative_wind_value_is_not_turned_into_profit(self):
        r=service.estimate_value({**self.request,'wind_value_EUR_MWh':-10})
        self.assertLess(r['scenario_surplus_EUR'],0)
    def test_energy_envelope_blocks_unavailable_flexibility(self):
        r=service.estimate_value({**self.request,'flex_energy_limit_MWh':39.})
        self.assertEqual(r['status'],'blocked_energy_envelope');self.assertIsNone(r['extra_wind_MWh'])
    def test_failed_physics_cannot_be_monetised(self):
        self.pair.update(comparable=False,reason='No checked pair')
        r=service.estimate_value(self.request)
        self.assertEqual(r['status'],'blocked_physical_comparison');self.assertIsNone(r['scenario_surplus_EUR'])
    def test_zero_wind_gain_does_not_hide_activation_cost(self):
        self.pair['additional_wind_MW']=0
        r=service.estimate_value(self.request)
        self.assertLess(r['scenario_surplus_EUR'],0)
    def test_emissions_use_other_generation_displacement_and_require_factor(self):
        self.assertIsNone(service.estimate_value(self.request)['assumed_avoided_tCO2'])
        r=service.estimate_value({**self.request,'displaced_generation_tCO2_MWh':.4})
        self.assertAlmostEqual(r['assumed_avoided_tCO2'],10.4)
        self.assertFalse(r['customer_profit_established']);self.assertFalse(r['field_savings'])
    def test_nonfinite_boolean_and_unsupported_inputs_rejected(self):
        for change in [{'duration_hours':float('nan')},{'duration_hours':True},{'duration_hours':-1},{'wind_MW':99}]:
            with self.assertRaises(ValueError):service.estimate_value({**self.request,**change})

if __name__=='__main__':unittest.main()
