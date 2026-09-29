"""Application/engine integration tests; no live Azure calls or AI-quality claim."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app_service
from ai.agent_runner import run_agent

SCIENCE_READY = all(importlib.util.find_spec(name) is not None for name in ("pypower", "numpy", "scipy"))


@unittest.skipUnless(SCIENCE_READY, "Install numerical dependencies to run real-engine integration tests.")
class AgentIntegrationTests(unittest.TestCase):
    def test_application_disables_ai_without_credentials_and_returns_no_fake_trace(self):
        with patch.dict("os.environ", {}, clear=True):
            result = app_service.run_search({"profile": "reference_9bus", "wind_mw": 200,
                "load_scale": 1, "budget": 2, "prompt": "Compare allowed scenarios."}, use_ai=True)
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["used_calls"], 0)
        self.assertEqual(result["tool_trace"], [])

    def test_real_baseline_respects_budget_and_fixed_conditions(self):
        result = app_service.run_search({"profile": "reference_9bus", "wind_mw": 185,
                                         "load_scale": 1, "budget": 2})
        self.assertEqual(result["mode"], "deterministic_baseline")
        self.assertEqual(result["used_calls"], 2)
        self.assertEqual(len(result["tool_trace"]), 2)
        for row in result["tool_trace"]:
            self.assertEqual(row["arguments"]["wind_mw"], 185)
            self.assertEqual(row["arguments"]["load_scale"], 1)
            self.assertIn("accepted_wind_mw", row["result"])
            if row["result"]["eligible"]:
                self.assertTrue(all(check["passed"] for check in row["result"]["checks"]))

    def test_cli_adapter_connects_to_same_physical_engine(self):
        context = app_service.get_agent_context("reference_9bus", 200, 1)
        self.assertEqual(context["fixed_conditions"], {"wind_mw": 200., "load_scale": 1.})
        self.assertTrue(context["recommendation_allowed"])
        result = app_service.evaluate_candidate({"profile_id": "reference_9bus", "action_id": "all_in_service",
                                                  "wind_mw": 200, "load_scale": 1})
        self.assertTrue(result["eligible"])
        self.assertAlmostEqual(result["accepted_wind_mw"], 200, places=4)

    def test_scripted_tool_request_uses_real_engine_not_scripted_engine_results(self):
        context = app_service.get_agent_context("reference_9bus", 200, 1)
        calls = []
        def provider(payload):
            return {"choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": "scripted_integration_fixture", "type": "function", "function": {
                    "name": "evaluate_candidate", "arguments": json.dumps({"action_id": "all_in_service",
                                                                             "wind_mw": 200, "load_scale": 1})}}]}}]}
        def callback(candidate):
            calls.append(candidate)
            return app_service.evaluate_candidate({"profile_id": "reference_9bus", **candidate})
        result = run_agent("Compare at current conditions", context, callback, budget=1, provider=provider)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["solver_calls"], 1)
        self.assertTrue(result["best_valid"]["result"]["eligible"])
        self.assertFalse(result["is_live_provider"])

    def test_irish_automatic_search_is_blocked_before_model_or_engine(self):
        profile = app_service.IRISH_ID
        with patch("app_service.candidate_callback") as callback:
            result = app_service.run_search({"profile": profile, "prompt": "Find a safe action."}, use_ai=True)
        self.assertEqual(result["status"], "blocked_model_validation")
        callback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
