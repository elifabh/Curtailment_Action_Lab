"""Authored provider contract tests. Passing these is not AI performance evidence."""
from __future__ import annotations
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.agent_runner import (run_agent, run_baseline, validate_candidate, validate_context,
                             agent_status, AzureProvider, AgentError)
from ai.evaluate_agent import benchmark


def context():
    return {"profile_id": "test_fixture_not_a_grid", "allowed_actions": [
        {"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}],
        "controls": {"wind_mw": {"min": 0, "max": 500, "default": 200},
                     "load_scale": {"min": .5, "max": 1.5, "default": 1}},
        "fixed_conditions": {"wind_mw": 200, "load_scale": 1},
        "recommendation_allowed": True, "validation_status": "authored test fixture"}


def request(action="a", **kw):
    return {"action_id": action, "wind_mw": 200, "load_scale": 1, **kw}


def call(action="a", id="call_1", args=None, name="evaluate_candidate", **kw):
    return {"id": id, "type": "function", "function": {
        "name": name, "arguments": json.dumps(request(action, **kw)) if args is None else args}}


def response(*calls, finish=None, refusal=None):
    return {"choices": [{"finish_reason": finish or ("tool_calls" if calls else "stop"),
                         "message": {"role": "assistant", "tool_calls": list(calls),
                                     "content": "Made-up model numbers must not be presented: 99999 MW.",
                                     "refusal": refusal}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15}}


class ScriptedProvider:
    label = "authored contract fixture, not AI"

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, payload):
        self.requests.append(copy.deepcopy(payload))
        return self.responses.pop(0) if self.responses else response()


class EngineFixture:
    def __init__(self):
        self.calls = []

    def __call__(self, candidate):
        self.calls.append(copy.deepcopy(candidate))
        values = {"a": 100, "b": 150, "c": 180, "d": 190}
        okay = candidate["action_id"] != "d"
        return {"accepted_wind_mw": values[candidate["action_id"]], "eligible": okay,
                "checks": [{"label": "authored fixture check", "passed": okay}]}


class AgentContractTests(unittest.TestCase):
    def test_disabled_without_credentials_never_calls_engine(self):
        engine = EngineFixture()
        result = run_agent("Compare actions", context(), engine, env={})
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(engine.calls, [])
        self.assertFalse(agent_status({})["enabled"])

    def test_iterative_protocol_has_tool_id_and_returns_new_evidence(self):
        provider = ScriptedProvider([response(call("a")), response(call("b", id="call_2")), response()])
        result = run_agent("Compare actions", context(), EngineFixture(), 3, provider)
        self.assertEqual(result["best_valid"]["candidate"]["action_id"], "b")
        messages = provider.requests[1]["messages"]
        self.assertEqual(messages[-1]["role"], "tool")
        self.assertEqual(messages[-1]["tool_call_id"], "call_1")
        self.assertEqual(messages[-2]["tool_calls"][0]["id"], "call_1")
        self.assertFalse(provider.requests[0]["parallel_tool_calls"])
        self.assertNotIn("99999", result["summary"])
        self.assertEqual(result["usage"]["total_tokens"], 45)

    def test_budget_is_hard_bound(self):
        provider = ScriptedProvider([response(call("a")), response(call("b", id="call_2")),
                                     response(call("c", id="call_3"))])
        engine = EngineFixture()
        result = run_agent("Compare", context(), engine, 2, provider)
        self.assertEqual(len(engine.calls), 2)
        self.assertEqual(len(provider.requests), 2)
        self.assertEqual(result["solver_calls"], 2)

    def test_unknown_tool_never_executes(self):
        engine = EngineFixture()
        provider = ScriptedProvider([response(call(name="switch_physical_line")), response()])
        result = run_agent("Compare", context(), engine, provider=provider)
        self.assertFalse(engine.calls)
        self.assertEqual(len(result["rejected"]), 1)

    def test_extra_parameter_cannot_override_limit(self):
        engine = EngineFixture()
        provider = ScriptedProvider([response(call(args=json.dumps({**request(), "rating": 99999}))), response()])
        result = run_agent("Compare", context(), engine, provider=provider)
        self.assertFalse(engine.calls)
        self.assertEqual(result["invalid_requests_rejected"], 1)

    def test_nonfinite_duplicate_and_bool_arguments_rejected(self):
        for args in ('{"action_id":"a","wind_mw":NaN,"load_scale":1}',
                     '{"action_id":"a","wind_mw":200,"wind_mw":100,"load_scale":1}',
                     '{"action_id":"a","wind_mw":true,"load_scale":1}'):
            with self.subTest(args=args):
                engine = EngineFixture()
                result = run_agent("Compare", context(), engine,
                                   provider=ScriptedProvider([response(call(args=args)), response()]))
                self.assertFalse(engine.calls)
                self.assertEqual(result["invalid_requests_rejected"], 1)

    def test_fixed_conditions_cannot_be_changed(self):
        engine = EngineFixture()
        result = run_agent("Compare", context(), engine,
                           provider=ScriptedProvider([response(call(load_scale=1.1)), response()]))
        self.assertFalse(engine.calls)
        self.assertEqual(result["invalid_requests_rejected"], 1)

    def test_explicit_prompt_conflict_requires_clarification(self):
        engine, provider = EngineFixture(), ScriptedProvider([])
        result = run_agent("Set wind to 300 MW", context(), engine, provider=provider)
        self.assertEqual(result["status"], "clarification_required")
        self.assertFalse(engine.calls)
        self.assertFalse(provider.requests)

    def test_parallel_batch_rejected_even_if_provider_ignores_flag(self):
        engine = EngineFixture()
        provider = ScriptedProvider([response(call("a"), call("b", id="call_2")), response()])
        result = run_agent("Compare", context(), engine, provider=provider)
        self.assertFalse(engine.calls)
        self.assertEqual(len(result["rejected"]), 2)
        self.assertEqual([m["tool_call_id"] for m in provider.requests[1]["messages"] if m["role"] == "tool"],
                         ["call_1", "call_2"])

    def test_failed_checks_never_best_even_if_engine_eligible_true(self):
        def engine(_):
            return {"accepted_wind_mw": 190, "eligible": True,
                    "checks": [{"label": "voltage", "passed": False}]}
        result = run_agent("Compare", context(), engine, 1, ScriptedProvider([response(call())]))
        self.assertIsNone(result["best_valid"])
        self.assertEqual(result["violations_rejected"], 1)

    def test_unvalidated_profile_never_recommended(self):
        ctx = context()
        ctx["recommendation_allowed"] = False
        result = run_baseline(ctx, EngineFixture(), 4)
        self.assertIsNone(result["best_valid"])

    def test_engine_exception_is_sanitized_and_counts_budget(self):
        def engine(_):
            raise RuntimeError("secret credential must never appear")
        result = run_agent("Compare", context(), engine, 1, ScriptedProvider([response(call())]))
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(result["solver_calls"], 1)
        self.assertFalse(result["records"])

    def test_refusal_and_truncated_call_do_not_execute(self):
        for provider_response in (response(refusal="declined"), response(call(), finish="length")):
            engine = EngineFixture()
            result = run_agent("Compare", context(), engine, provider=ScriptedProvider([provider_response]))
            self.assertFalse(engine.calls)
            self.assertIn(result["status"], ("refused", "error"))

    def test_duplicate_candidate_is_not_evaluated_again(self):
        engine = EngineFixture()
        result = run_agent("Compare", context(), engine, 3,
            ScriptedProvider([response(call()), response(call(id="call_2")), response()]))
        self.assertEqual(len(engine.calls), 1)
        self.assertEqual(result["invalid_requests_rejected"], 1)

    def test_timeout_is_reported_without_fake_result(self):
        def provider(_):
            raise TimeoutError()
        result = run_agent("Compare", context(), EngineFixture(), provider=provider)
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["records"])

    def test_baseline_is_not_ai_and_uses_same_cap(self):
        result = run_baseline(context(), EngineFixture(), 2)
        self.assertEqual(result["mode"], "deterministic_baseline")
        self.assertEqual(result["solver_calls"], 2)
        self.assertEqual(result["provider_calls"], 0)

    def test_benchmark_oracle_calls_separate_and_test_provider_not_live(self):
        result = benchmark(context(), EngineFixture(), "Compare", 2, run_live=True,
                           provider=ScriptedProvider([response(call("a")), response(call("b", id="call_2"))]))
        self.assertEqual(result["baseline_metrics"]["candidate_calls"], 2)
        self.assertEqual(result["agent_metrics"]["candidate_calls"], 2)
        self.assertEqual(result["oracle"]["separate_candidate_calls"], 4)
        self.assertEqual(result["oracle"]["best_valid_accepted_wind_mw"], 180)
        self.assertEqual(result["agent_metrics"]["regret_to_declared_candidate_oracle_mw"], 30)
        self.assertEqual(result["benchmark_provider_kind"], "injected_test")
        self.assertEqual(result["live_ai_benchmark_status"], "not_run")

    def test_azure_endpoint_must_not_leak_key_to_arbitrary_host(self):
        env = {"AZURE_OPENAI_API_KEY": "test-only", "AZURE_OPENAI_DEPLOYMENT": "test-only"}
        for endpoint in ("http://sample.openai.azure.com", "https://example.com/openai/v1",
                         "https://sample.openai.azure.com.evil.example", "https://sample.openai.azure.com/?key=x"):
            with self.subTest(endpoint=endpoint), self.assertRaises(AgentError):
                AzureProvider({**env, "AZURE_OPENAI_ENDPOINT": endpoint})


if __name__ == "__main__":
    unittest.main()
