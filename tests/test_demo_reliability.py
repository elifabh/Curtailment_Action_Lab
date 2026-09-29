"""Regression tests for interrupted demo runs; no live Azure calls."""
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
import urllib.error
from unittest.mock import Mock, patch

import decision_service as ds
import extension_service as extension
from ai.agent_runner import AzureProvider, ProviderError
from ai.challenge_agent import run


def tool(sid, cid='call_1'):
    return {'choices': [{'finish_reason': 'tool_calls', 'message': {'tool_calls': [
        {'id': cid, 'type': 'function', 'function': {'name': 'test_offer_scenario',
          'arguments': json.dumps({'scenario_id': sid})}}
    ]}}]}


class AuditRecovery(unittest.TestCase):
    def setUp(self):
        self.payload = {'plan': ds.default_plan(), 'mode': 'azure', 'budget': 4}

    def test_three_good_reads_then_timeout_preserves_checks_and_counts_failed_call(self):
        provider = Mock(side_effect=[tool('delivery_half'), tool('demand_lower'),
                                    tool('delivery_zero'), TimeoutError()])
        r = run(self.payload, provider=provider)
        self.assertEqual(r['status'], 'provider_error')
        self.assertTrue(r['partial'])
        self.assertEqual(r['record_reads'], 3)
        self.assertEqual(r['provider_calls'], 4)
        self.assertEqual(r['counterexamples_found'], 1)
        self.assertEqual([x['additional_wind_MW'] for x in r['records']], [9.5703125, 15.4296875, 0])
        self.assertEqual(r['error']['code'], 'connection_error')
        self.assertEqual(r['new_power_flows_run'], 0)

    def test_round_limit_is_not_success(self):
        r = run(self.payload, provider=lambda _: tool('wind_25'))
        self.assertEqual(r['status'], 'provider_stalled')
        self.assertTrue(r['partial'])
        self.assertEqual(r['record_reads'], 1)

    def test_already_inspected_records_are_removed_from_next_schema(self):
        requests = []
        def provider(payload):
            requests.append(payload)
            return tool(['delivery_half', 'demand_lower'][len(requests)-1])
        r = run({**self.payload, 'budget': 2}, provider=provider)
        enum = requests[1]['tools'][0]['function']['parameters']['properties']['scenario_id']['enum']
        self.assertNotIn('delivery_half', enum)
        self.assertEqual(r['status'], 'completed')
        self.assertEqual(r['record_reads'], 2)

    def test_provider_may_finish_early_without_inventing_missing_reads(self):
        provider = Mock(side_effect=[tool('delivery_zero'), {'choices': [{'finish_reason': 'stop', 'message': {'content': 'Done'}}]}])
        r = run(self.payload, provider=provider)
        self.assertEqual(r['status'], 'completed')
        self.assertEqual(r['stop_reason'], 'provider_finished')
        self.assertEqual(r['record_reads'], 1)
        self.assertEqual(r['uninspected_conditions'], 6)

    def test_budget_met_on_last_retry_round_is_completed(self):
        provider=Mock(side_effect=[tool('delivery_half')]*4+[tool('demand_lower')])
        r=run({**self.payload,'budget':2},provider=provider)
        self.assertEqual(r['status'],'completed')
        self.assertEqual(r['record_reads'],2)
        self.assertEqual(r['provider_calls'],5)

    def test_http_failure_keeps_actionable_code_and_no_provider_body(self):
        r = run(self.payload, provider=Mock(side_effect=ProviderError('Azure rate limit reached.', 'azure_http_429', http_status=429)))
        self.assertEqual(r['error']['http_status'], 429)
        self.assertEqual(r['provider_calls'], 1)
        self.assertEqual(r['record_reads'], 0)

    def test_disabled_configuration_makes_no_provider_request(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(AzureProvider, '__init__', side_effect=AssertionError('Must not initialise Azure')) as provider:
            r = run(self.payload)
        provider.assert_not_called()
        self.assertEqual(r['status'], 'disabled')
        self.assertEqual(r['provider_calls'], 0)


class AzureTransport(unittest.TestCase):
    def provider(self, **kwargs):
        return AzureProvider({'AZURE_OPENAI_ENDPOINT': 'https://demo.openai.azure.com',
                              'AZURE_OPENAI_API_KEY': 'test-secret', 'AZURE_OPENAI_DEPLOYMENT': 'test-only'}, **kwargs)

    @staticmethod
    def response():
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"choices": []}'
        return response

    def test_429_retries_respect_retry_after_and_count_transport_attempts(self):
        fail = urllib.error.HTTPError('https://example.invalid', 429, 'secret response', {'retry-after-ms': '2000'}, io.BytesIO(b'secret'))
        opener = Mock();opener.open.side_effect = [fail, self.response()]
        p = self.provider()
        with patch('urllib.request.build_opener', return_value=opener), patch('ai.agent_runner.time.sleep') as sleep:
            p({'messages': []})
        sleep.assert_called_once_with(2)
        self.assertEqual(p.http_requests, 2)
        self.assertEqual(p.retry_count, 1)

    def test_authentication_failure_is_not_retried_or_exposed(self):
        fail = urllib.error.HTTPError('https://example.invalid', 401, 'test-secret', {}, io.BytesIO(b'test-secret'))
        opener = Mock();opener.open.side_effect = fail
        p = self.provider()
        with patch('urllib.request.build_opener', return_value=opener), self.assertRaises(ProviderError) as caught:
            p({'messages': []})
        self.assertEqual(p.http_requests, 1)
        self.assertEqual(p.retry_count, 0)
        self.assertNotIn('test-secret', str(caught.exception))
        self.assertEqual(caught.exception.http_status, 401)

    def test_timeout_retries_are_bounded(self):
        opener = Mock();opener.open.side_effect = TimeoutError()
        p = self.provider()
        with patch('urllib.request.build_opener', return_value=opener), patch('ai.agent_runner.time.sleep'), self.assertRaises(ProviderError):
            p({'messages': []})
        self.assertEqual(p.http_requests, 3)
        self.assertEqual(p.retry_count, 2)

    def test_long_retry_after_is_not_ignored(self):
        fail = urllib.error.HTTPError('https://example.invalid', 429, '', {'Retry-After': '120'}, None)
        opener = Mock();opener.open.side_effect = fail
        p = self.provider()
        with patch('urllib.request.build_opener', return_value=opener), patch('ai.agent_runner.time.sleep') as sleep, self.assertRaises(ProviderError):
            p({'messages': []})
        sleep.assert_not_called()
        self.assertEqual(p.http_requests, 1)


class CalculationRecovery(unittest.TestCase):
    def job(self, root, status='running'):
        job = 'a'*32;path = Path(root)/job;path.mkdir()
        (path/'request.json').write_text('{"kind":"snapshot"}')
        (path/'progress.json').write_text(json.dumps({'status': status}))
        return job, path

    def test_worker_exit_without_result_is_not_polled_forever(self):
        with tempfile.TemporaryDirectory() as root:
            job, _ = self.job(root)
            process = Mock();process.poll.return_value = 0
            with patch.object(extension, 'JOBS', Path(root)), patch.dict(extension.PROCESSES, {job: {'process': process, 'started': time.monotonic(), 'kind': 'snapshot'}}, clear=True):
                r = extension.status({'job_id': job})
            self.assertEqual(r['status'], 'failed')

    def test_stale_job_after_restart_has_a_terminal_state(self):
        with tempfile.TemporaryDirectory() as root:
            job, path = self.job(root)
            os.utime(path/'progress.json', (time.time()-400,)*2)
            with patch.object(extension, 'JOBS', Path(root)), patch.dict(extension.PROCESSES, {}, clear=True):
                r = extension.status({'job_id': job})
            self.assertEqual(r['status'], 'failed')

    def test_missing_completed_file_is_a_structured_error(self):
        with tempfile.TemporaryDirectory() as root:
            job, _ = self.job(root, 'completed')
            with patch.object(extension, 'JOBS', Path(root)):
                r = extension.status({'job_id': job})
            self.assertEqual(r['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
