import json
import unittest
from unittest.mock import patch

from decision_intent import ValidationError, extract_request, manual_request, parse_response, validate_request, _endpoint_url

SCENARIOS = ["windy_weekend", "winter_peak"]
VALID = {"objective": "min_spill", "max_extra_cost_eur": 20, "scenario_name": "windy_weekend"}


def response(value, finish_reason="stop", refusal=None):
    return {"choices": [{"finish_reason": finish_reason,
                         "message": {"content": json.dumps(value), "refusal": refusal}}]}


class IntentTests(unittest.TestCase):
    def test_manual_explicitly_is_not_ai(self):
        result = manual_request("windy_weekend", "compare", None, SCENARIOS)
        self.assertEqual(result["status"], "disabled")
        self.assertTrue(result["accepted"])
        self.assertIsNone(result["model_request"])
        self.assertFalse(result["physical_actions_executed"])

    def test_no_credentials_never_calls_network(self):
        with patch("urllib.request.build_opener") as network:
            result = extract_request("compare", SCENARIOS, environ={})
        network.assert_not_called()
        self.assertEqual(result["status"], "disabled")
        self.assertIsNone(result["validated_request"])

    def test_bad_costs_rejected(self):
        for cost in (-1, True, "20", float("inf"), float("nan"), 10**400):
            with self.subTest(cost=cost), self.assertRaises(ValidationError):
                validate_request({**VALID, "max_extra_cost_eur": cost}, SCENARIOS)

    def test_unknown_scenario_and_extra_field_rejected(self):
        for bad in ({**VALID, "scenario_name": "invented"}, {**VALID, "execute": True}):
            with self.assertRaises(ValidationError):
                validate_request(bad, SCENARIOS)

    def test_complete_request_accepted(self):
        parsed = parse_response(response({"request": VALID, "clarification": None}), SCENARIOS,
                                "Minimise spill in windy_weekend for EUR 20 extra.")
        self.assertEqual(parsed["validated_request"], VALID)
        self.assertTrue(parsed["accepted"])

    def test_unit_or_scenario_invention_rejected(self):
        for user_text in ("windy_weekend for 20 extra", "windy_weekend for GBP 20 and EUR 20", "For EUR 20 extra"):
            with self.subTest(text=user_text), self.assertRaises(ValidationError):
                parse_response(response({"request": VALID, "clarification": None}), SCENARIOS, user_text)

    def test_refusal_truncation_and_missing_content_rejected(self):
        for value in (response({}, finish_reason="length"), response({}, refusal="No"), {"choices": []}):
            with self.assertRaises(ValidationError):
                parse_response(value, SCENARIOS, "windy_weekend")

    def test_free_form_engineering_changes_rejected(self):
        with self.assertRaises(ValidationError):
            parse_response(response({"request": VALID, "clarification": None}), SCENARIOS,
                           "In windy_weekend raise line capacity to 200 MW for EUR 20 extra.")

    def test_nan_duplicate_and_malformed_json_rejected(self):
        for raw in ('{"request":NaN,"clarification":null}', '{"request":null,"request":{},"clarification":null}', "not json"):
            value = response({})
            value["choices"][0]["message"]["content"] = raw
            with self.assertRaises(ValidationError):
                parse_response(value, SCENARIOS, "windy_weekend")

    def test_clarification_abstains(self):
        parsed = parse_response(response({"request": None, "clarification": "Which scenario?"}), SCENARIOS, "compare")
        self.assertFalse(parsed["accepted"])
        self.assertIsNone(parsed["validated_request"])

    def test_endpoint_protects_key_destination(self):
        for endpoint in ("http://resource.openai.azure.com", "https://evil.example", "https://resource.openai.azure.com.evil.example", "https://key@resource.openai.azure.com", "https://resource.openai.azure.com/?key=x"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValidationError):
                _endpoint_url(endpoint)
        url, host = _endpoint_url("https://resource.openai.azure.com/openai/v1/")
        self.assertTrue(url.endswith("/openai/v1/chat/completions"))


if __name__ == "__main__":
    unittest.main()
