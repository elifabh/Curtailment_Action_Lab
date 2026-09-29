"""Bounded advisory Azure tool-calling workflow. No physical device commands.

The callback, never the language model, supplies all engineering values.
Only the Python standard library is required by this module.
"""
from __future__ import annotations

import copy
import email.utils
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping

MAX_BUDGET = 8
ENV_KEYS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")


class AgentError(ValueError):
    """Public error with no secret-bearing provider response."""


class ProviderError(AgentError):
    """Safe, actionable transport diagnostic; never the provider response body."""
    def __init__(self, message, code, *, http_status=None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def provider_diagnostic(exc):
    if isinstance(exc, ProviderError):
        return {'code': exc.code, 'message': str(exc), 'http_status': exc.http_status}
    if isinstance(exc, AgentError):
        return {'code': 'invalid_provider_response', 'message': str(exc)}
    return {'code': 'connection_error', 'message': 'The AI connection failed or timed out. Inspected records are retained; retry the AI audit or run the rule-based audit.'}


def strict_json(text: str):
    def reject_constant(_):
        raise AgentError("Non-finite JSON numbers are not accepted.")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise AgentError("Duplicate JSON fields are not accepted.")
            result[key] = value
        return result

    try:
        return json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique)
    except (json.JSONDecodeError, UnicodeError):
        raise AgentError("Malformed JSON arguments.") from None


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def validate_context(context: Mapping) -> dict:
    if not isinstance(context, Mapping):
        raise AgentError("A current model profile is required.")
    result = copy.deepcopy(dict(context))
    actions = result.get("allowed_actions", [])
    if not isinstance(actions, list) or not 1 <= len(actions) <= 100:
        raise AgentError("The profile must contain 1–100 allowed actions.")
    ids = []
    for action in actions:
        if not isinstance(action, dict) or not isinstance(action.get("id"), str):
            raise AgentError("Each allowed action requires an ID.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", action["id"]):
            raise AgentError("Invalid action ID.")
        ids.append(action["id"])
    if len(set(ids)) != len(ids):
        raise AgentError("Action IDs must be unique.")
    controls = result.get("controls", {})
    for key in ("wind_mw", "load_scale"):
        bounds = controls.get(key, {})
        if (not isinstance(bounds, dict)
                or any(not _number(bounds.get(k)) for k in ("min", "max", "default"))
                or not 0 <= bounds["min"] <= bounds["default"] <= bounds["max"]):
            raise AgentError("The profile must declare finite nonnegative control bounds.")
    fixed = result.get("fixed_conditions", {})
    if not isinstance(fixed, dict) or set(fixed) - {"wind_mw", "load_scale"}:
        raise AgentError("Invalid fixed comparison conditions.")
    for key, value in fixed.items():
        if not _number(value) or not controls[key]["min"] <= value <= controls[key]["max"]:
            raise AgentError("Fixed conditions must be inside profile bounds.")
    for key in ("wind_mw", "load_scale"):
        fixed.setdefault(key, controls[key]["default"])
    result["fixed_conditions"] = fixed
    if result.get("recommendation_allowed") is not None and type(result.get("recommendation_allowed")) is not bool:
        raise AgentError("recommendation_allowed must be a boolean.")
    return result


def validate_candidate(candidate: object, context: Mapping) -> dict:
    if not isinstance(candidate, dict) or set(candidate) != {"action_id", "wind_mw", "load_scale"}:
        raise AgentError("Expected exactly action_id, wind_mw and load_scale.")
    if candidate["action_id"] not in [a["id"] for a in context["allowed_actions"]]:
        raise AgentError("The action is not in this profile's allowed actions.")
    for key in ("wind_mw", "load_scale"):
        value = candidate[key]
        bounds = context["controls"][key]
        if not _number(value) or not bounds["min"] <= value <= bounds["max"]:
            raise AgentError(f"{key} is outside the profile's finite permitted range.")
        if key in context.get("fixed_conditions", {}) and value != context["fixed_conditions"][key]:
            raise AgentError(f"{key} must stay fixed for this comparison.")
    return {"action_id": candidate["action_id"], "wind_mw": float(candidate["wind_mw"]),
            "load_scale": float(candidate["load_scale"])}


def tool_schema(context):
    properties = {"action_id": {"type": "string", "enum": [a["id"] for a in context["allowed_actions"]]}}
    # Bounds are enforced in local code; some Azure strict-schema subsets omit minimum/maximum.
    for key in ("wind_mw", "load_scale"):
        bounds = context["controls"][key]
        properties[key] = {"type": "number", "description": (
            f"Allowed range {bounds['min']} to {bounds['max']}. "
            f"Fixed comparison value: {context.get('fixed_conditions', {}).get(key, 'not fixed')}.")}
    return {"type": "function", "function": {
        "name": "evaluate_candidate", "description": (
            "Run one approved advisory grid scenario. Returns deterministic engineering checks; "
            "does not send physical commands. Keep wind and load fixed when comparing actions."),
        "strict": True, "parameters": {"type": "object", "properties": properties,
            "required": ["action_id", "wind_mw", "load_scale"], "additionalProperties": False}}}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AgentError("Azure redirected the request. Check the endpoint configuration.")


class AzureProvider:
    """Callable provider using Azure OpenAI v1 Chat Completions."""
    label = "Azure OpenAI"

    def __init__(self, env=None, timeout=35, max_retries=2, total_timeout=150):
        env = os.environ if env is None else env
        if not all(env.get(key, "").strip() for key in ENV_KEYS):
            raise AgentError("Azure credentials are not configured.")
        self.deployment = env[ENV_KEYS[2]].strip()
        self._api_key = env[ENV_KEYS[1]].strip()
        try:
            p = urllib.parse.urlsplit(env[ENV_KEYS[0]].strip())
            hostname = p.hostname or ""
            valid = (p.scheme == "https" and not p.username and not p.password and not p.query
                     and not p.fragment and p.port in (None, 443)
                     and p.path.rstrip("/") in ("", "/openai/v1")
                     and any(hostname.endswith(suffix) for suffix in
                             (".openai.azure.com", ".services.ai.azure.com")))
        except ValueError:
            valid = False
        if not valid:
            raise AgentError("Configure an HTTPS Azure OpenAI or Foundry resource endpoint.")
        self.url = f"https://{hostname}/openai/v1/chat/completions"
        self.timeout = min(60, max(1, float(timeout)))
        self.max_retries = min(2, max(0, int(max_retries)))
        self.deadline = time.monotonic() + min(150, max(1, float(total_timeout)))
        self.http_requests = 0
        self.retry_count = 0

    @staticmethod
    def _retry_delay(headers, attempt):
        for key, scale in (('retry-after-ms', .001), ('Retry-After', 1)):
            value = headers.get(key) if headers else None
            if value is None:
                continue
            try:
                delay = float(value) * scale
                if math.isfinite(delay):
                    return max(0, delay)
            except (ValueError, TypeError):
                if key == 'Retry-After':
                    try:
                        return max(0, email.utils.parsedate_to_datetime(value).timestamp() - time.time())
                    except (ValueError, TypeError, OverflowError):
                        pass
        return float(2 ** attempt)

    @staticmethod
    def _http_error(code):
        messages = {
            400: 'Azure rejected the request (HTTP 400). Check that the deployment supports v1 Chat Completions and function calling.',
            401: 'Azure authentication failed (HTTP 401). Check the API key for this resource, then restart the local server.',
            403: 'Azure denied access (HTTP 403). Check resource permissions and network access.',
            404: 'Azure could not find the endpoint or deployment (HTTP 404). Check the resource URL and deployed model name.',
            408: 'Azure timed out (HTTP 408). Retry the audit.',
            429: 'Azure rate limit or quota reached (HTTP 429). Wait and retry; check deployment quota if it persists.',
        }
        message = messages.get(code, f'Azure returned HTTP {code}. Retry the audit; check Azure service availability if it persists.')
        return ProviderError(message, f'azure_http_{code}', http_status=code)

    def __call__(self, payload):
        body = {**payload, "model": self.deployment, "max_completion_tokens": 1600}
        request = urllib.request.Request(self.url, json.dumps(body, allow_nan=False).encode(),
            {"Content-Type": "application/json", "api-key": self._api_key}, method="POST")
        for attempt in range(self.max_retries + 1):
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderError('The AI time limit was reached. Inspected records are retained; retry or reduce the record budget.', 'time_limit')
            self.http_requests += 1
            try:
                with urllib.request.build_opener(_NoRedirect()).open(request, timeout=min(self.timeout, remaining)) as response:
                    raw = response.read(300_001)
                if len(raw) > 300_000:
                    raise AgentError('Azure response exceeded the permitted size.')
                return strict_json(raw.decode('utf-8'))
            except urllib.error.HTTPError as exc:
                error = self._http_error(exc.code)
                retryable = exc.code in (408, 429, 500, 502, 503, 504)
                delay = self._retry_delay(exc.headers, attempt)
                exc.close()
            except (TimeoutError, urllib.error.URLError, OSError):
                error = ProviderError('Azure could not be reached or timed out. Check the connection and retry. Inspected records are retained.', 'connection_error')
                retryable, delay = True, float(2 ** attempt)
            # Do not retry configuration failures, exceed the session deadline,
            # or retry sooner than Azure's declared Retry-After interval.
            if not retryable or attempt >= self.max_retries or delay > 10 or time.monotonic() + delay >= self.deadline:
                raise error from None
            self.retry_count += 1
            time.sleep(delay)


def agent_status(env=None):
    env = os.environ if env is None else env
    configured = all(env.get(key, "").strip() for key in ENV_KEYS)
    if configured:
        try:
            AzureProvider(env)
        except (AgentError, ValueError):
            return {"status": "configuration_error", "enabled": False,
                    "message": "Azure endpoint configuration is invalid.", "live_tested": False}
    return {"status": "configured" if configured else "disabled", "enabled": configured,
            "message": ("Azure is configured; connectivity and model support are not yet verified."
                        if configured else "Set the three Azure environment variables to enable the AI agent."),
            "live_tested": False}


def _normalise_result(raw, candidate, context):
    if not isinstance(raw, dict):
        raise AgentError("The deterministic engine returned no structured result.")
    # Ensure every value returned to a provider or browser is valid JSON.
    try:
        result = json.loads(json.dumps(raw, allow_nan=False))
    except (TypeError, ValueError, OverflowError):
        raise AgentError("The deterministic engine returned invalid result data.") from None
    accepted = result.get("accepted_wind_mw")
    if not _number(accepted) or not 0 <= accepted <= candidate["wind_mw"] + 1e-6:
        raise AgentError("The engine must return bounded accepted_wind_mw.")
    checks = result.get("checks")
    complete = (isinstance(checks, list) and bool(checks)
                and all(isinstance(c, dict) and c.get("passed") is True for c in checks))
    eligible = (context.get("recommendation_allowed") is True
                and result.get("eligible") is True and complete)
    result["eligible"] = eligible
    result["eligibility_note"] = ("Passed the declared model checks; not an operational safety approval."
        if eligible else "Not eligible for recommendation: the model or one or more declared checks are unverified or failed.")
    return result


def _best(records):
    valid = [r for r in records if r.get("result", {}).get("eligible") is True]
    if not valid:
        return None
    return max(valid, key=lambda r: r["result"]["accepted_wind_mw"])


def _finish(output, start):
    output["elapsed_seconds"] = round(time.monotonic() - start, 6)
    output["best_valid"] = _best(output["records"])
    output["violations_rejected"] = sum(not r["result"]["eligible"] for r in output["records"])
    output["invalid_requests_rejected"] = len(output["rejected"])
    output["solver_calls"] = output["budget_used"]
    output["physical_actions_executed"] = False
    best = output["best_valid"]
    if best:
        output["summary"] = (
            f"Evaluated {len(output['records'])} scenario(s). Among the evaluated scenarios, "
            f"{best['candidate']['action_id']} accepted {best['result']['accepted_wind_mw']:.2f} MW "
            "and passed the declared model checks. This is a model result, not a field result or an operational approval.")
    elif output["records"]:
        output["summary"] = (f"Evaluated {len(output['records'])} scenario(s). None is eligible for "
                              "recommendation under all declared checks. Review the evidence.")
    else:
        output["summary"] = output.get("message", "No scenario was evaluated.")
    return output


def _output(mode, budget):
    return {"status": "completed", "mode": mode, "budget": budget, "budget_used": 0,
            "records": [], "rejected": [], "provider_calls": 0, "usage": {},
            "live_ai_benchmark": False, "summary_source": "deterministic_engine_records"}


def _budget(value):
    if type(value) is not int or not 1 <= value <= MAX_BUDGET:
        raise AgentError("The evaluation budget must be an integer from 1 to 8.")
    return value


def _public_context(context):
    # Allowlist what can leave the process. No arbitrary application context or credentials.
    return {key: context[key] for key in (
        "profile_id", "profile_name", "allowed_actions", "controls", "fixed_conditions",
        "validation_status", "recommendation_allowed", "limitations", "assumptions", "candidate_evaluation_mode") if key in context}


def _request_conflict(prompt, context):
    """Conservative check for explicit conflicting wind/load conditions, not an NLP claim."""
    number = r"([0-9]+(?:\.[0-9]+)?)"
    patterns = ((r"\bwind\b.{0,24}?" + number + r"\s*MW\b", "wind_mw", 1),
                (number + r"\s*MW\s+(?:of\s+)?(?:available\s+)?wind\b", "wind_mw", 1),
                (r"\bload\s*(?:scale|multiplier)\s*(?:of|to|=|:)?\s*" + number, "load_scale", 1),
                (r"\bload\s*(?:of|at|to|=|:)?\s*" + number + r"\s*%", "load_scale", .01))
    for pattern, key, scale in patterns:
        for match in re.finditer(pattern, prompt, re.I):
            requested = float(match.group(1)) * scale
            if not math.isclose(requested, context["fixed_conditions"][key], abs_tol=1e-8):
                return (f"The request conflicts with the selected {key}. Change the Scenario Lab controls "
                        "first; agent comparisons keep the selected wind and load fixed.")
    if re.search(r"\b(?:ignore|disable|remove|bypass)\b.{0,35}\b(?:checks|limits|constraints|voltage|safety)\b", prompt, re.I):
        return "Declared engineering checks cannot be disabled by an AI request."
    if re.search(r"\b(?:increase|raise|double|set|change)\b.{0,35}\b(?:ratings|rating|thermal limit|line capacity|reactance)\b", prompt, re.I):
        return "The agent cannot modify engineering ratings or physical network parameters."
    return None


def run_agent(prompt, context, evaluate_fn: Callable, budget=4, provider=None, *, env=None):
    """Iterate tool calls against an injected deterministic engine callback.

    provider is a callable(payload)->Chat-Completions-shaped dict, reserved for
    AzureProvider in the UI and scripted providers in contract tests.
    No provider / missing environment means disabled, not an offline AI imitation.
    """
    start = time.monotonic()
    output = _output("azure_agent", budget)
    try:
        budget = _budget(budget)
        context = validate_context(context)
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 6000:
            raise AgentError("Enter a request of 1–6000 characters.")
        conflict = _request_conflict(prompt, context)
        if conflict:
            output.update(status="clarification_required", message=conflict)
            return _finish(output, start)
        if provider is None:
            available = agent_status(env)
            if not available["enabled"]:
                output.update(status=available["status"], message=available["message"])
                return _finish(output, start)
            provider = AzureProvider(env)
        output["provider"] = getattr(provider, "label", "injected test provider")
        output["is_live_provider"] = isinstance(provider, AzureProvider)
        messages = [
            {"role": "system", "content": (
                "You are an advisory scenario investigator, not a grid controller. Use only evaluate_candidate. "
                "Compare permitted actions using its deterministic checks and accepted wind. Never invent numerical "
                "results or modify ratings, demand, topology, bus IDs or controls outside the provided profile. "
                "Keep fixed comparison conditions unchanged. A candidate is usable only if its returned eligible "
                "flag is true. Prefer distinct informative candidates and stop when the budget is used. "
                "If a requested change is unsupported, do not simulate a different change as if it fulfilled it. "
                "All results are model scenarios, not actual saved energy or operational approvals. "
                f"You may use at most {budget} engine evaluations. Current trusted profile:\n"
                + json.dumps(_public_context(context), allow_nan=False))},
            {"role": "user", "content": prompt.strip()}]
        seen = set()
        # Bounded even when the provider repeatedly returns invalid/duplicate requests.
        for _round in range(budget + 2):
            if output["budget_used"] >= budget:
                output["stop_reason"] = "evaluation_budget_exhausted"
                break
            payload = {"messages": copy.deepcopy(messages), "tools": [tool_schema(context)],
                       "tool_choice": "auto", "parallel_tool_calls": False}
            output["provider_calls"] += 1
            response = provider(payload)
            if not isinstance(response, dict):
                raise AgentError("The provider returned an invalid response.")
            usage = response.get("usage") or {}
            if isinstance(usage, dict):
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    value = usage.get(key)
                    if type(value) is int and value >= 0:
                        output["usage"][key] = output["usage"].get(key, 0) + value
            try:
                choice = response["choices"][0]
                message = choice["message"]
            except (KeyError, IndexError, TypeError):
                raise AgentError("The provider returned no complete assistant message.") from None
            if not isinstance(message, dict):
                raise AgentError("The provider returned an invalid assistant message.")
            if message.get("refusal") or choice.get("finish_reason") == "content_filter":
                output.update(status="refused", stop_reason="provider_refusal",
                              message="The provider declined the request. Use manual comparison.")
                break
            if choice.get("finish_reason") not in ("stop", "tool_calls"):
                raise AgentError("The provider response was incomplete; no partial tool call was executed.")
            calls = message.get("tool_calls") or []
            if not isinstance(calls, list) or len(calls) > 16:
                raise AgentError("The provider returned an invalid tool-call list.")
            if not calls:
                # Unverified model prose is deliberately not presented as engineering evidence.
                output["stop_reason"] = "provider_finished"
                output["message"] = "No additional scenario was requested by the model. Use manual controls for unsupported requests."
                break
            ids = [c.get("id") if isinstance(c, dict) else None for c in calls]
            if (any(not isinstance(i, str) or not i or len(i) > 200 for i in ids)
                    or len(set(ids)) != len(ids)):
                raise AgentError("The provider returned missing or duplicate tool-call IDs.")
            messages.append({"role": "assistant", "content": None, "tool_calls": calls})
            for call in calls:
                tool_result = None
                try:
                    if len(calls) != 1:
                        raise AgentError("Parallel calls are disabled. Request one candidate at a time.")
                    function = call.get("function", {})
                    if call.get("type") != "function" or function.get("name") != "evaluate_candidate":
                        raise AgentError("The requested tool is not allowed.")
                    args = function.get("arguments")
                    if not isinstance(args, str) or len(args) > 4000:
                        raise AgentError("Tool arguments must be a bounded JSON string.")
                    candidate = validate_candidate(strict_json(args), context)
                    key = json.dumps(candidate, sort_keys=True)
                    if key in seen:
                        raise AgentError("This candidate was already evaluated; choose another permitted action.")
                    seen.add(key)
                    if output["budget_used"] >= budget:
                        raise AgentError("The evaluation budget is exhausted.")
                    output["budget_used"] += 1
                    try:
                        raw = evaluate_fn(copy.deepcopy(candidate))
                    except Exception:
                        raise AgentError("The engine could not evaluate this candidate; no result is asserted.") from None
                    result = _normalise_result(raw, candidate, context)
                    record = {"id": f"evaluation_{len(output['records']) + 1}", "tool_call_id": call["id"],
                              "candidate": candidate, "result": result}
                    output["records"].append(record)
                    tool_result = {"record_id": record["id"], "candidate": candidate, "result": result,
                                   "remaining_evaluations": budget - output["budget_used"]}
                except AgentError as exc:
                    output["rejected"].append({"tool_call_id": call["id"], "reason": str(exc)})
                    tool_result = {"error": str(exc), "remaining_evaluations": budget - output["budget_used"]}
                messages.append({"role": "tool", "tool_call_id": call["id"], "name": "evaluate_candidate",
                                 "content": json.dumps(tool_result, allow_nan=False)})
            if output['budget_used'] >= budget:
                output['stop_reason'] = 'evaluation_budget_exhausted'
                break
        else:
            output.update(status="incomplete", stop_reason="provider_round_limit",
                          message="The AI reached its request-attempt limit. Only the displayed candidates were evaluated.")
        if output['status']=='completed' and not output['records']:
            output.update(status='no_tool_calls', message='The AI did not return any checked candidate. Run again or use deterministic search.')
    except (AgentError, TimeoutError, urllib.error.URLError) as exc:
        output.update(status="error", message=str(exc) if isinstance(exc, AgentError)
                      else "The provider timed out or could not be reached.")
    except Exception:
        output.update(status="error", message="The agent could not finish. Manual comparison remains available.")
    if isinstance(provider, AzureProvider):
        output['provider_http_requests'] = provider.http_requests
        output['provider_retries'] = provider.retry_count
    return _finish(output, start)


def candidate_universe(context):
    """The finite comparison set, not a continuous optimum or a secure-dispatch oracle."""
    context = validate_context(context)
    if "candidates" in context:
        candidates = context["candidates"]
        if not isinstance(candidates, list) or not 1 <= len(candidates) <= 500:
            raise AgentError("The declared candidate set must contain 1–500 entries.")
    else:
        fixed = context.get("fixed_conditions", {})
        candidates = [{"action_id": a["id"],
            "wind_mw": fixed.get("wind_mw", context["controls"]["wind_mw"]["default"]),
            "load_scale": fixed.get("load_scale", context["controls"]["load_scale"]["default"])}
            for a in context["allowed_actions"]]
    unique = {json.dumps(validate_candidate(c, context), sort_keys=True): validate_candidate(c, context)
              for c in candidates}
    return [unique[k] for k in sorted(unique)]


def run_baseline(context, evaluate_fn: Callable, budget=4):
    """Deterministic declared-order coverage; explicitly not AI."""
    start = time.monotonic()
    output = _output("deterministic_baseline", budget)
    try:
        _budget(budget)
        context = validate_context(context)
        candidates = candidate_universe(context)
        # Evenly cover the sorted declared universe; no result-informed selection.
        if len(candidates) > budget:
            indices = [round(i * (len(candidates) - 1) / (budget - 1)) for i in range(budget)] if budget > 1 else [0]
            candidates = [candidates[i] for i in indices]
        for candidate in candidates:
            output["budget_used"] += 1
            try:
                result = _normalise_result(evaluate_fn(copy.deepcopy(candidate)), candidate, context)
                output["records"].append({"id": f"evaluation_{len(output['records']) + 1}",
                                          "candidate": candidate, "result": result})
            except Exception:
                output["rejected"].append({"candidate": candidate, "reason": "Engine evaluation failed."})
    except AgentError as exc:
        output.update(status="error", message=str(exc))
    return _finish(output, start)


def exhaustive_reference(context, evaluate_fn):
    """Evaluate the finite declared action set; no continuous or field-optimal claim."""
    start = time.monotonic()
    context = validate_context(context)
    candidates = candidate_universe(context)
    output = _output("exhaustive_declared_candidates", len(candidates))
    for candidate in candidates:
        output["budget_used"] += 1
        try:
            result = _normalise_result(evaluate_fn(copy.deepcopy(candidate)), candidate, context)
            output["records"].append({"id": f"evaluation_{len(output['records']) + 1}",
                                      "candidate": candidate, "result": result})
        except Exception:
            output["rejected"].append({"candidate": candidate, "reason": "Engine evaluation failed."})
    return _finish(output, start)
