"""Real local HTTP checks for the delivered application contract."""
import json
from pathlib import Path
import sys
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from http.server import ThreadingHTTPServer
from server import Handler

class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def post(self,path,body):
        return urlopen(Request(self.url+path,data=body.encode(),headers={'Content-Type':'application/json'}),timeout=30)
    def test_roundtrip_comparison_returns_both_sets_of_checks(self):
        with urlopen(self.url+'/api/config') as response:
            config=json.load(response)
        request=next(p['default_request'] for p in config['profiles'] if p['id']=='reference_9bus')
        with self.post('/api/evaluate',json.dumps(request)) as response:
            result=json.load(response)
        self.assertTrue(result['eligible'])
        self.assertEqual(len(result['checks']),26)
        self.assertTrue(all(x['passed'] for x in result['checks']))
        wind=next(m for m in result['metrics'] if m['key']=='accepted_wind_mw')
        self.assertAlmostEqual(wind['delta'],60,places=3)
        self.assertFalse(result['physical_actions_executed'])
    def test_nonfinite_and_duplicate_request_values_are_rejected(self):
        for body in ('{"wind_mw":NaN}', '{"profile":"reference_9bus","profile":"other"}'):
            with self.assertRaises(HTTPError) as error:
                self.post('/api/evaluate',body)
            self.assertEqual(error.exception.code,400)
    def test_secrets_and_arbitrary_files_are_not_http_routes(self):
        for path in ('/.env','/../app_service.py'):
            with self.assertRaises(HTTPError) as error:
                urlopen(self.url+path)
            self.assertEqual(error.exception.code,404)
    def test_hosted_cross_origin_calculation_is_rejected(self):
        request=Request(self.url+'/api/evaluate',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://example.org'})
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code,403)

if __name__=='__main__':
    unittest.main()
