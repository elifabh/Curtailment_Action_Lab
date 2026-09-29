"""Critical extension contracts: bounded inputs, signed energy, failure gates."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from io import BytesIO
import extension_engine as engine
import extension_service as service

class ExtensionContracts(unittest.TestCase):
    def setUp(self):
        self.p={'kind':'snapshot','candidate_bus':1701,'flex_MW':20.,'line_outage':True,'wind_available_MW':200.,'load_factor':1.}

    def test_valid_snapshot_retains_exact_requested_inputs(self):
        self.assertEqual(engine.validate(self.p),self.p)

    def test_unknown_inputs_and_unbounded_values_are_rejected(self):
        cases=[{**self.p,'cost':0},{**self.p,'wind_available_MW':float('nan')},
               {**self.p,'wind_available_MW':201},{**self.p,'load_factor':.5},
               {**self.p,'flex_MW':True},{**self.p,'line_outage':'true'},
               {**self.p,'candidate_bus':999999}]
        for p in cases:
            with self.subTest(p=p),self.assertRaises(ValueError):engine.validate(p)

    def test_pilot_cannot_claim_an_unimplemented_dispatch_mode(self):
        p={'kind':'pilot','candidate_bus':1701,'flex_MW':20.,'line_outage':True,'profile_mode':'economic_optimisation'}
        with self.assertRaises(ValueError):engine.validate(p)

    @staticmethod
    def row(delta,good=True):
        return {'duration_hours':.5,'comparison':{'comparable':good,
          'additional_hypothetical_wind_MW':delta,'change_other_generation_MW':-delta if good else None,
          'change_network_losses_MW':0 if good else None}}

    def test_signed_energy_retains_adverse_intervals(self):
        r=engine.integrate([self.row(2),self.row(-4)])
        self.assertEqual(r['full_period_change_MWh'],-1)
        self.assertEqual(r['adverse_intervals'],1)
        self.assertIsNone(r['annual_avoided_curtailment_MWh'])
        self.assertIsNone(r['national_reduction_percent'])

    def test_one_failed_comparison_blocks_full_period_total(self):
        r=engine.integrate([self.row(2),self.row(None,False)])
        self.assertEqual(r['comparable_intervals_subtotal_MWh'],1)
        self.assertEqual(r['coverage_fraction'],.5)
        self.assertIsNone(r['full_period_change_MWh'])
        self.assertFalse(r['full_period_result_available'])

    def test_no_passing_interval_is_not_zero_saving(self):
        r=engine.integrate([self.row(None,False)])
        self.assertIsNone(r['comparable_intervals_subtotal_MWh'])
        self.assertIsNone(r['full_period_change_MWh'])

    def test_job_identifier_cannot_select_arbitrary_files(self):
        for value in ['../server.py','x'*32,'',True]:
            with self.assertRaises(ValueError):service.status({'job_id':value})

    def test_missing_dependencies_cannot_silently_return_recorded_result(self):
        with patch.object(service,'configuration',return_value={'available':False}):
            with self.assertRaises(RuntimeError):service.start(self.p)

    def test_profile_keeps_real_and_assumed_values_separate(self):
        p=json.loads((engine.ROOT/'extension_data/pilot_2025_01_01.json').read_text())
        self.assertEqual(len(p['rows']),12)
        self.assertEqual(sum(x['duration_hours'] for x in p['rows']),6)
        self.assertFalse(p['local_wind_observed'])
        self.assertFalse(p['asset_observed'])
        self.assertTrue(p['audit']['pilot_demand_reconciles'])
        self.assertEqual(p['rows'][0]['timestamp_utc'],'2025-01-01T00:00:00Z')
        self.assertEqual(p['rows'][-1]['timestamp_utc'],'2025-01-01T05:30:00Z')
        for r in p['rows']:
            self.assertAlmostEqual(r['assumed_local_wind_available_MW'],200*r['IE_wind_available_MW']/p['normalisation_peak_IE_wind_MW'])

class ExtensionRoutes(unittest.TestCase):
    def handler(self,path,body=None,origin=None):
        from server import Handler
        h=object.__new__(Handler)
        h.path=path;h.server=SimpleNamespace(server_port=8765)
        encoded=json.dumps(body or {}).encode()
        h.headers={'Host':'127.0.0.1:8765','Content-Type':'application/json','Content-Length':str(len(encoded))}
        if origin:h.headers['Origin']=origin
        h.rfile=BytesIO(encoded);h.response=None
        h.send_json=lambda code,value:setattr(h,'response',(code,value))
        h.send_bytes=lambda code,value,kind:setattr(h,'response',(code,value,kind))
        return h

    def test_fresh_page_and_javascript_routes_exist(self):
        for path,needle in [('/extension',b'Run fresh calculation'),('/static/extension.js',b'/api/extension-start')]:
            h=self.handler(path);h.do_GET()
            self.assertEqual(h.response[0],200);self.assertIn(needle,h.response[1])

    def test_config_and_saved_example_are_distinct_from_new_calculation(self):
        h=self.handler('/api/extension-config');h.do_GET()
        self.assertEqual(h.response[0],200);self.assertFalse(h.response[1]['ai_invokes_fresh_engine'])
        h=self.handler('/api/extension-example');h.do_GET()
        self.assertEqual(h.response[1]['mode'],'saved_extension_example')

    def test_same_origin_request_calls_fresh_service(self):
        payload={'kind':'snapshot','candidate_bus':1701,'flex_MW':20.,'line_outage':True,'wind_available_MW':200.,'load_factor':1.}
        with patch.object(service,'start',return_value={'job_id':'a'*32,'status':'starting'}) as mock:
            h=self.handler('/api/extension-start',payload,'http://127.0.0.1:8765');h.do_POST()
            self.assertEqual(h.response[0],200);mock.assert_called_once_with(payload)

    def test_cross_origin_cannot_start_fresh_calculation(self):
        with patch.object(service,'start') as mock:
            h=self.handler('/api/extension-start',{},'https://other.invalid');h.do_POST()
            self.assertEqual(h.response[0],403);mock.assert_not_called()

if __name__=='__main__':unittest.main()
