"""Physical invariants and deliberate counterexamples, not solver-output snapshots."""
from copy import deepcopy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pypower.api import runpf, ppoption
from engine.reference_engine import (source_case, validate_source, check_solution,
                                    evaluate, evaluate_candidate, normalize_request)


class ReferenceEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = source_case()
        cls.solved, _ = runpf(deepcopy(cls.source), ppoption(VERBOSE=0, OUT_ALL=0, PF_TOL=1e-10))

    def test_unmodified_source_matches_independent_solver(self):
        result = validate_source()
        self.assertTrue(result['passed'])
        self.assertLess(result['audit']['independent_power_flow']['max_voltage_difference_pu'], 1e-5)

    def test_voltage_corruption_is_rejected(self):
        corrupted = deepcopy(self.solved)
        corrupted['bus'][4, 7] = 1.2
        audit = check_solution(corrupted, self.source, independent=False)
        self.assertFalse(audit['passed'])
        self.assertFalse(next(x for x in audit['checks'] if x['id'] == 'voltage')['passed'])

    def test_generator_p_and_q_violations_are_rejected(self):
        for column, value, check in [(1, 500., 'generator_p'), (2, 400., 'generator_q')]:
            corrupted = deepcopy(self.solved)
            corrupted['gen'][0, column] = value
            audit = check_solution(corrupted, self.source, independent=False)
            self.assertFalse(next(x for x in audit['checks'] if x['id'] == check)['passed'])

    def test_rating_tampering_and_overload_are_rejected(self):
        corrupted = deepcopy(self.solved)
        corrupted['branch'][0, 5] = 1
        audit = check_solution(corrupted, self.source, independent=False)
        self.assertFalse(next(x for x in audit['checks'] if x['id'] == 'limits_unchanged')['passed'])
        self.assertFalse(next(x for x in audit['checks'] if x['id'] == 'thermal')['passed'])

    def test_hidden_load_shedding_is_rejected(self):
        corrupted = deepcopy(self.solved)
        corrupted['bus'][4, 2] -= 10
        audit = check_solution(corrupted, self.source, independent=False)
        self.assertFalse(next(x for x in audit['checks'] if x['id'] == 'load_unchanged')['passed'])

    def test_island_is_rejected(self):
        island = deepcopy(self.source)
        island['branch'][0, 10] = 0  # Disconnects generator bus 1.
        audit = check_solution(self.solved, island, independent=False)
        self.assertFalse(next(x for x in audit['checks'] if x['id'] == 'connected')['passed'])

    def test_low_wind_no_material_benefit(self):
        result = evaluate({'wind_mw': 50})
        self.assertTrue(result['comparison']['eligible_for_claim'])
        self.assertLess(abs(result['comparison']['additional_wind_mw']), .001)
        self.assertIsNone(result['comparison']['curtailment_reduction_pct'])

    def test_same_action_has_exactly_zero_benefit(self):
        result = evaluate({'action_id': 'outage_6_7'})
        self.assertEqual(result['comparison']['additional_wind_mw'], 0)
        self.assertEqual(result['baseline']['metrics']['load_mw'], result['selected']['metrics']['load_mw'])

    def test_no_available_wind_cannot_produce_wind(self):
        result = evaluate_candidate({'wind_mw': 0})
        self.assertTrue(result['eligible'])
        self.assertEqual(result['metrics']['accepted_wind_mw'], 0)

    def test_default_benefit_respects_all_limits(self):
        result = evaluate({})
        self.assertTrue(result['baseline']['eligible'])
        self.assertTrue(result['selected']['eligible'])
        self.assertGreater(result['comparison']['additional_wind_mw'], 59.9)
        self.assertLess(result['comparison']['additional_wind_mw'], 60.1)
        for side in ('baseline', 'selected'):
            self.assertTrue(all(c['passed'] for c in result[side]['checks']))
            self.assertEqual(result[side]['metrics']['load_mw'], 315.)

    def test_invalid_requests_rejected_before_solver(self):
        for request in [{'wind_mw': math.nan}, {'wind_mw': True}, {'wind_mw': 1000},
                        {'load_scale': 0.5}, {'action_id': '__import__'},
                        {'profile': 'Irish grid'}, {'wind_mw': '200'}]:
            with self.subTest(request=request), self.assertRaises(ValueError):
                normalize_request(request)


if __name__ == '__main__':
    unittest.main()
