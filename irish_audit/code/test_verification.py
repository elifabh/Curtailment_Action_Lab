"""Mutation checks for materially misleading claims and broken physical records."""
from copy import deepcopy
import json,unittest
import numpy as np
from fixed_case import ROOT,build,direct_check
from raw_equation_check import verify

class VerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.meta=build()
        cls.case=dict(np.load(ROOT/'results/feasible_counterfactual.npz'))
        h=json.loads((ROOT/'results/expanded_tap_experiment.json').read_text())['history']
        cls.taps={c['transformer']:c['new_w1'] for r in h for c in r['changes']}
        cls.off=json.loads((ROOT/'results/feasible_counterfactual_actions.json').read_text())['disconnect_shunts']
    def check_raw(self,case,**kw):
        return verify(case,self.meta,tap_changes=self.taps,shunt_off=self.off,**kw)
    def test_prepared_state_matches_raw_electrical_equations_and_original_bounds(self):
        self.assertTrue(self.check_raw(self.case)['passed'])
        self.assertTrue(direct_check(self.case,self.meta)['passes_implemented_checks'])
    def test_widening_rating_is_detected(self):
        c=deepcopy(self.case);c['branch'][0,5]+=10
        self.assertFalse(self.check_raw(c)['passed'])
    def test_widening_generator_limit_is_detected(self):
        c=deepcopy(self.case);c['gen'][0,3]+=1
        self.assertFalse(self.check_raw(c)['passed'])
    def test_unaccounted_energy_injection_is_detected(self):
        self.assertFalse(self.check_raw(self.case,wind_mw=50)['passed'])
    def test_tampered_voltage_is_detected(self):
        c=deepcopy(self.case);c['bus'][self.meta['source_ids'][1341],7]=1.15
        self.assertFalse(self.check_raw(c)['passed'])
        self.assertFalse(direct_check(c,self.meta)['passes_implemented_checks'])
    def test_numerical_pass_does_not_imply_operational_approval(self):
        self.assertFalse(direct_check(self.case,self.meta)['operationally_validated'])

if __name__=='__main__':unittest.main(verbosity=2)
