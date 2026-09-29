"""Application services for Action Lab. All physical quantities come from solvers."""
from __future__ import annotations

import copy
import hashlib
from functools import lru_cache
import importlib.util
import json
import math
import os
from pathlib import Path
import threading
import time

# Small sparse planning cases benefit from bounded BLAS parallelism. Respect a
# user's explicit setting; avoid starting dozens of threads per request.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parent
ENV_KEYS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
SOLVER_LOCK = threading.RLock()
REFERENCE_ID = "reference_9bus"
IRISH_ID = "irish_winter_2024"
CONDITIONAL_ID = "irish_conditional_flex"
REFERENCE_ACTIONS = ["all_in_service", "outage_4_5", "outage_5_6", "outage_6_7", "outage_7_8", "outage_8_9", "outage_9_4"]


def load_local_settings():
    """Read three literal values, without shell evaluation; environment wins."""
    path = ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key in ENV_KEYS and value:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(key, value)


load_local_settings()


def read_json(relative, fallback=None):
    path = ROOT / relative
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else copy.deepcopy(fallback)


def scientific_available():
    return all(importlib.util.find_spec(name) is not None for name in ("numpy", "scipy", "pypower"))


def profile_definitions():
    runtime = scientific_available()
    profiles = [
        {
            "id": REFERENCE_ID, "name": "Reference network · 9 buses",
            "description": "Public benchmark network with a declared hypothetical wind generator. Compare steady-state AC planning scenarios.",
            "status": "Reference validation pending", "validation_status": "pending",
            "available": True, "runtime_available": runtime,
            "actions": [{"id": a, "name": "All lines in service" if a == "all_in_service" else "Outage of line " + a[7:].replace("_", "–"),
                         "description": "Hypothetical topology for comparison. No maintenance approval is implied."} for a in REFERENCE_ACTIONS],
            "limits": {"wind_mw": {"min": 0, "max": 240, "step": 1}, "load_scale": {"min": 0.85, "max": 1.15, "step": 0.05}},
            "default_request": {"profile": REFERENCE_ID, "wind_mw": 200.0, "load_scale": 1.0, "action_id": "all_in_service"},
            "baseline": "Line 6–7 out of service; same wind availability and demand.",
            "provenance": [{"name": "PYPOWER case9", "url": "https://github.com/rwl/PYPOWER/blob/master/pypower/case9.py", "kind": "Public reference network"}],
            "assumptions": ["Hypothetical wind at bus 6, with the same availability in both cases.", "Published case limits remain unchanged. Original demand scales uniformly by the selected load factor.", "The objective includes an explicit synthetic wind-curtailment penalty. It is not an electricity tariff."],
            "limitations": ["Results apply to this benchmark and declared steady-state checks. They do not measure Irish curtailment.", "No full N-1, dynamic stability, protection, switching or maintenance approval is established.", "A converged AC optimum is not a proof of a global optimum."],
        },
        {
            "id": IRISH_ID, "name": "Original Irish case · Source audit",
            "description": "Original EirGrid planning snapshot and archived conversion diagnosis. The legacy comparison has been superseded; use the conditional study for the new checked experiment.",
            "status": "Superseded calculation; source retained", "validation_status": "exploratory", "available": False, "runtime_available": False,
            "actions": [{"id": "line_in_service", "name": "Line 1341–1701 in service"}, {"id": "line_outage", "name": "Line 1341–1701 outage"}],
            "limits": {"wind_mw": {"min": 0, "max": 200, "step": 10}, "load_scale": {"min": 1, "max": 1, "step": 0.05}},
            "default_request": {"profile": IRISH_ID, "wind_mw": 200.0, "load_scale": 1.0, "action_id": "line_in_service"},
            "baseline": "Requested wind injection with line 1341–1701 out of service.",
            "provenance": [{"name": "EirGrid TYTFS2024", "url": "https://cms.eirgrid.ie/all-island-ten-year-transmission-forecast-statement-2024", "kind": "Public planning model"}],
            "assumptions": ["Additional hypothetical wind at Binbane 110 kV; equal active-power reduction at the stated Aghada generator.", "Consumer demand remains 7,324.51 MW. No historical 2026 replay is claimed."],
            "limitations": ["The source itself contains 173 voltage-limit violations below 100 kV. Counterfactuals also contain violations.", "Ideal bus ties, rounded source voltages and simplified controls require careful interpretation. Read the diagnostic report.", "Results are not eligible for an approved-operation or verified-curtailment-saving claim."],
        },
    ]
    status = read_json("validation/reference_summary.json", {})
    if status.get("validated") is True:
        profiles[0].update(status="Declared model checks validated", validation_status="validated_reference")
    from conditional_study import profile as conditional_profile
    profiles.append(conditional_profile())
    return profiles


def configuration():
    profiles = profile_definitions()
    from ai.agent_runner import agent_status
    ai_status = agent_status()
    configured = ai_status["enabled"]
    runtime = scientific_available()
    return {
        "title": "Curtailment Action Lab", "version": "5.0",
        "subtitle": "Compare wind opportunities and inspect the engineering evidence.",
        "profiles": profiles, "default_request": next(p['default_request'] for p in profiles if p['id']==CONDITIONAL_ID),
        "mode": "local_live" if runtime else "recorded_results",
        "runtime": {"available": runtime, "message": "Local numerical solver available." if runtime else "Recorded results are available. Install requirements.txt and restart to run new calculations."},
        "ai": {"enabled": configured, "status": "configured_unverified" if configured else ai_status["status"],
               "provider": "Azure OpenAI", "live_evaluation_status": "not_run",
               "description": "The agent inspects allowed options within a fixed budget, using stored network records or the selected local solver. Run an investigation to check the connection." if configured else ai_status["message"] + " Deterministic comparison and recorded evidence remain available."},
        "sources": [p for x in profiles for p in x["provenance"]],
        "definitions": {"MW": "Power at a snapshot. Energy over time is measured in MWh.", "curtailment_reduction": "Baseline withheld wind minus selected withheld wind, under the same modelled conditions.", "validated_reference": "Passed the stated numerical and steady-state checks. This does not imply field validation."},
    }


def validate_request(payload):
    required = {"profile", "wind_mw", "load_scale", "action_id"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("Supply exactly profile, wind_mw, load_scale and action_id.")
    profile = next((p for p in profile_definitions() if p["id"] == payload["profile"]), None)
    if profile is None:
        raise ValueError("Choose an available model profile.")
    if payload["action_id"] not in [a["id"] for a in profile["actions"]]:
        raise ValueError("Choose an action from this profile's allowed list.")
    normalized = {"profile": profile["id"], "action_id": payload["action_id"]}
    for key in ("wind_mw", "load_scale"):
        value = payload[key]
        limits = profile["limits"][key]
        if type(value) not in (int, float) or not math.isfinite(value) or not limits["min"] <= value <= limits["max"]:
            raise ValueError(f"{key} must be a finite number from {limits['min']} to {limits['max']}.")
        normalized[key] = float(value)
    return normalized, profile


def request_key(request):
    return json.dumps(request, sort_keys=True, separators=(",", ":"))


def recorded_response(endpoint, request):
    recordings = read_json("data/recorded.json", {})
    for entry in recordings.get(endpoint, []):
        if request_key(entry["request"]) == request_key(request):
            result = copy.deepcopy(entry["response"])
            result["mode"] = "recorded_result"
            return result
    raise RuntimeError("This exact request is not recorded. Install requirements.txt and restart the local server to compute it.")


@lru_cache(maxsize=32)
def _irish_candidate(wind_mw, outage):
    from engine.scenario_screen import evaluate as calculate
    return calculate(wind_mw, outage)


def evaluate_irish(request):
    from presentation import live_document
    baseline = copy.deepcopy(_irish_candidate(request["wind_mw"], True))
    selected = copy.deepcopy(_irish_candidate(request["wind_mw"], request["action_id"] == "line_outage"))
    legacy = live_document(request["wind_mw"], request["action_id"] == "line_in_service", baseline, selected)
    legacy.update(status="engineering_review_required", eligible=False,
                  summary="Diagnostic comparison. Unresolved voltage violations prevent a verified curtailment-reduction claim.",
                  metrics=legacy["comparison"]["metrics"], accepted_wind_mw=None,
                  request=request, profile=IRISH_ID, mode="live_irish_diagnostic")
    legacy["baseline"] = baseline
    legacy["selected"] = selected
    legacy["evidence"]["baseline_topology"] = "outage"
    legacy["evidence"]["selected_topology"] = "outage" if request["action_id"] == "line_outage" else "in service"
    for check in legacy["checks"]:
        if check.get("label") == "Original strict source residual gate":
            check["detail"] = "The legacy gate failed. The new diagnosis addresses ideal ties and rounding; source feasibility and complete controls remain unresolved."
    return legacy


def complete_document(result, request, profile, seconds):
    result = copy.deepcopy(result)
    if profile["id"] == REFERENCE_ID:
        baseline = result["baseline"]["metrics"]
        selected = result["selected"]["metrics"]
        fields = [("accepted_wind_mw", "Accepted wind", "MW"),
                  ("curtailed_wind_mw", "Withheld wind", "MW"),
                  ("load_mw", "Demand served", "MW"),
                  ("losses_mw", "Network losses", "MW"),
                  ("max_branch_loading_pct", "Maximum branch loading", "%")]
        result["metrics"] = [{"key": key, "label": label, "unit": unit,
                              "baseline": baseline[key], "selected": selected[key],
                              "delta": selected[key] - baseline[key]}
                             for key, label, unit in fields]
        result["eligible"] = bool(result["comparison"]["eligible_for_claim"])
        delta = result["comparison"]["additional_wind_mw"]
        result["summary"] = (f"The selected reference-network scenario accepts {delta:.2f} MW more wind than the fixed line 6–7 outage baseline, at the same wind availability and demand. "
                             "Both cases pass the declared checks. This is a modelled snapshot, not measured Irish savings.") if result["eligible"] else "A declared check failed. This comparison cannot support a verified wind-acceptance claim."
        # Do not hide a failed baseline behind a passing selected case.
        result["checks"] = [{**check, "id": f"{side}_{check['id']}",
                             "label": f"{side.title()}: {check['label']}",
                             "detail": f"Value: {check.get('value')}; limit: {check.get('limit')} {check.get('unit', '')}."}
                            for side in ("baseline", "selected") for check in result[side]["checks"]]
    result["request"] = request
    result["profile"] = profile["id"]
    result.setdefault("provenance", profile["provenance"])
    result.setdefault("assumptions", profile["assumptions"])
    result.setdefault("limitations", profile["limitations"])
    result.setdefault("metrics", result.get("comparison", {}).get("metrics", []))
    result.setdefault("summary", result.get("message", "Review the comparison and checks."))
    result.setdefault("status", "engineering_review_required")
    result["physical_actions_executed"] = False
    result["elapsed_seconds"] = round(seconds, 6)
    result["run_id"] = hashlib.sha256(json.dumps({"request": request, "metrics": result["metrics"]}, sort_keys=True).encode()).hexdigest()[:16]
    result.setdefault("mode", "live_numerical_comparison")
    return result


def evaluate(payload):
    request, profile = validate_request(payload)
    if request["profile"] == IRISH_ID:
        raise RuntimeError('The legacy Irish comparison is superseded by the revised audit. Select Irish planning study · 20 MW flexibility. The original source remains available in Evidence.')
    if request["profile"] == CONDITIONAL_ID:
        from conditional_study import comparison
        return complete_document(comparison(request),request,profile,0.)
    if not scientific_available():
        return recorded_response("evaluate", request)
    start = time.perf_counter()
    with SOLVER_LOCK:
        if request["profile"] == REFERENCE_ID:
            from engine.reference_engine import evaluate as calculate
            result = calculate(request)
        else:
            result = evaluate_irish(request)
    return complete_document(result, request, profile, time.perf_counter() - start)


def sensitivity(payload):
    request, profile = validate_request(payload)
    if request["profile"] == CONDITIONAL_ID:
        r=evaluate(request);m=r['metrics'][0]
        return {"request":request,"mode":"precomputed_verified_study","rows":[{"wind_mw":200.,
            "baseline":m['baseline'],"selected":m['selected'],"delta":m['delta'],"eligible":r['eligible'],"status":r['status']}],
            "metric_label":"Best tested wind acceptance","unit":"MW",
            "summary":"One fixed study condition is included. This is not a sensitivity curve. The supplied audit scripts reproduce the full wind admission screen.",
            "limitations":profile['limitations']}
    if not scientific_available():
        return recorded_response("sensitivity", request)
    cap = profile["limits"]["wind_mw"]["max"]
    values = sorted(set([0, 50, 100, 150, 200, cap, request["wind_mw"]]))
    rows = []
    for wind in values:
        item = evaluate({**request, "wind_mw": wind})
        metric = next((m for m in item["metrics"] if m.get("key") in ("accepted_wind_mw", "accepted_wind_MW", "wind_accepted") or "accepted" in m.get("label", "").lower()), None)
        if metric is None:
            # The Irish case only evaluates the requested injection. No accepted-wind claim.
            metric = next((m for m in item["metrics"] if "loading" in m.get("label", "").lower()), {})
        before, after = metric.get("baseline"), metric.get("selected")
        rows.append({"wind_mw": wind, "baseline": before, "selected": after,
                     "delta": after - before if type(before) in (int, float) and type(after) in (int, float) else None,
                     "status": item["status"], "eligible": item.get("eligible", False), "run_id": item["run_id"]})
    return {"request": request, "mode": "live_sensitivity", "rows": rows,
            "metric_label": "Accepted wind" if request["profile"] == REFERENCE_ID else "Maximum branch loading",
            "unit": "MW" if request["profile"] == REFERENCE_ID else "%",
            "summary": "Only wind availability changes across these rows. Demand and the selected topology remain fixed.",
            "limitations": profile["limitations"]}


def search_context(payload):
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    allowed = {"profile", "wind_mw", "load_scale", "budget", "prompt", "action_id"}
    if set(payload) - allowed:
        raise ValueError("Unsupported search fields.")
    profile_id = payload.get("profile", REFERENCE_ID)
    profile = next((p for p in profile_definitions() if p["id"] == profile_id), None)
    if profile is None:
        raise ValueError("Choose an available model profile.")
    defaults = profile["default_request"]
    request, profile = validate_request({"profile": profile_id,
        "wind_mw": payload.get("wind_mw", defaults["wind_mw"]),
        "load_scale": payload.get("load_scale", defaults["load_scale"]),
        "action_id": payload.get("action_id", defaults["action_id"])})
    budget = payload.get("budget", 4)
    if type(budget) is not int or not 1 <= budget <= 8:
        raise ValueError("Budget must be an integer from 1 to 8 candidate calls.")
    context = {"profile_id": profile_id, "allowed_actions": [{"id": a["id"], "label": a["name"]} for a in profile["actions"]],
               "controls": {k: {**profile["limits"][k], "default": request[k]} for k in ("wind_mw", "load_scale")},
               "fixed_conditions": {"wind_mw": request["wind_mw"], "load_scale": request["load_scale"]},
               "validation_status": profile["validation_status"],
               "recommendation_allowed": (profile_id == REFERENCE_ID and profile["validation_status"] == "validated_reference") or profile_id==CONDITIONAL_ID,
               "limitations": profile["limitations"], "assumptions": profile["assumptions"],
               "candidate_evaluation_mode": "precomputed_verified_study" if profile_id==CONDITIONAL_ID else "local_solver"}
    return request, profile, budget, context


def candidate_callback(profile_id):
    def run(candidate):
        request, _ = validate_request({"profile": profile_id, **candidate})
        with SOLVER_LOCK:
            if profile_id == CONDITIONAL_ID:
                from conditional_study import candidate as conditional_candidate
                return conditional_candidate(request)
            if profile_id == REFERENCE_ID:
                from engine.reference_engine import evaluate_candidate
                result = evaluate_candidate(request)
                result["accepted_wind_mw"] = result["metrics"]["accepted_wind_mw"]
                return result
            result = evaluate_irish(request)
            return {"eligible": False, "accepted_wind_mw": None, "checks": result["checks"], "status": result["status"], "evidence": result}
    return run


def normalize_agent(result, request, budget):
    result = copy.deepcopy(result)
    result["request"] = request
    result["budget"] = budget
    result["used_calls"] = result.get("budget_used", 0)
    result["tool_trace"] = [{"tool": "evaluate_candidate", "arguments": row.get("candidate", {}),
                             "result": row.get("result", {}), "status": "completed",
                             "duration_ms": row.get("elapsed_seconds", 0) * 1000} for row in result.get("records", [])]
    result["errors"] = result.get("rejected", [])
    best = result.get("best_valid")
    if best:
        result["best_request"] = {"profile": request["profile"], **best.get("candidate", {})}
        result["best_result"] = best.get("result")
    result["physical_actions_executed"] = False
    return result


def run_search(payload, use_ai=False):
    request, profile, budget, context = search_context(payload)
    if request["profile"] == IRISH_ID:
        return {"status": "blocked_model_validation", "summary": "The original Irish source profile is diagnostic and its legacy comparison is retired. Use Evidence to inspect the source audit, or select the separate conditional study or reference network.",
                "tool_trace": [], "used_calls": 0, "budget": budget, "physical_actions_executed": False}
    if use_ai:
        prompt = payload.get("prompt", "")
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 4000:
            raise ValueError("Enter a request of 1–4,000 characters.")
    if not scientific_available() and request['profile']!=CONDITIONAL_ID:
        if use_ai:
            return {"status": "disabled", "summary": "Install the numerical solver before running the AI agent.", "tool_trace": [], "used_calls": 0, "budget": budget}
        return recorded_response("search", {"profile": request["profile"], "wind_mw": request["wind_mw"], "load_scale": request["load_scale"], "budget": budget})
    from ai.agent_runner import run_agent, run_baseline
    callback = candidate_callback(request["profile"])
    result = run_agent(prompt, context, callback, budget=budget) if use_ai else run_baseline(context, callback, budget=budget)
    normalized=normalize_agent(result, request, budget)
    if request['profile']==CONDITIONAL_ID:
        normalized['precomputed_evidence_reads']=normalized['used_calls']
        normalized['solver_calls']=0
        normalized['summary']='Verified stored-study lookup; no new power flow was run by this request. '+normalized['summary']
        normalized['candidate_evaluation_mode']='precomputed_verified_study'
    return normalized


def get_agent_context(profile_id, wind_mw, load_scale):
    return search_context({"profile": profile_id, "wind_mw": wind_mw, "load_scale": load_scale})[3]


def evaluate_candidate(request):
    request = dict(request)
    profile_id = request.pop("profile_id", request.pop("profile", REFERENCE_ID))
    return candidate_callback(profile_id)(request)


def evidence():
    from study_service import study_data
    extended=study_data()
    decision=read_json('evaluation/decision_benchmark.json',{})
    challenge=read_json('evidence_v5/results/challenge_matrix.json',{})
    return {
        "title": "Evidence and model boundaries", "profiles": profile_definitions(),
        "reference": read_json("validation/reference_summary.json", {"status": "pending"}),
        "irish": read_json("validation/irish_summary.json", {"status": "exploratory", "source_voltage_violations_below_100kV": 173}),
        "irish_conditional": read_json("validation/irish_conditional_summary.json", {}),
        "extended_study":extended,
        "offer_decisions":{
            "title":"Offer decisions and counterexamples · v5",
            "status":"conditional_model_evidence",
            "summary":"Eight hypothetical 20 MW offers are compared against budget, delivery, energy and selected network conditions. Recommendations can be retained, changed or withdrawn.",
            "scope":"64 site–condition cells: 56 comparable and 8 blocked; 288 new power flows. Commercial inputs are editable assumptions.",
            "findings":[
                {"label":"Authored decision cases","detail":str(decision.get('cases')),"status":"reported"},
                {"label":"Nominal offers failing an extra required test","detail":str(decision.get('nominal_offers_violating_required_tests')),"status":"reported"},
                {"label":"Meaning of the guard","detail":"A decision rule on a finite test set, not predictive AI accuracy or a field-saving score.","status":"reported"},
                {"label":"Experiment record","detail":"evidence_v5/PROTOCOL.json; evidence_v5/results/challenge_matrix.json; evaluation/decision_benchmark.json","status":"reported"}],
            "claim_not_allowed":"Real customer quotations, field curtailment savings, a guaranteed operating schedule or measured live AI advantage.",
            "source_sha256":challenge.get('source_sha256'),"protocol_sha256":challenge.get('protocol_sha256')},
        "robustness":{"title":"Robustness, baselines and conditional value","status":extended.get('status','not_ready'),
            "summary":"Recorded variations, simple-policy comparisons, actual calculation timings and a value calculator with explicit duration and price assumptions.",
            "scope":"One prepared public Irish network. All outcomes and stress-test failures are retained.",
            "claim_not_allowed":"Field energy savings, a unique new algorithm, a proven business return, or a measured AI advantage.",
            "findings":[{"label":k.replace('_',' '),"detail":str(v),"status":"reported"} for k,v in extended.get('primary_summary',{}).items()]},
        "verification": read_json("validation/package_checks.json", {}),
        "sources": configuration()["sources"],
        "limitations": ["Reference-network results and Irish planning diagnostics are separate experiments.", "A completed live AI connection test does not establish comparative AI performance.", "No model output executes a physical action or claims a verified national avoided-energy total."],
    }


def evaluation():
    report=read_json("evaluation/summary.json", {"status": "pending", "summary": "Numerical and agent evaluation results are being prepared.", "live_ai_status": "not_run"})
    current=read_json("evaluation/conditional_agent_results.json", {})
    baseline=current.get('baseline_metrics',{})
    report['conditional_study']={
        'profile_id':CONDITIONAL_ID,
        'status':'baseline_completed_ai_'+current.get('live_ai_benchmark_status','not_run'),
        'summary':'Irish stored-study benchmark: compare the deterministic candidate budget with the complete declared-candidate reference. This lookup runs no new power flows. Live AI performance is unmeasured.',
        'live_ai_status':current.get('live_ai_benchmark_status','not_run'),
        'metrics':[
            {'label':'Best recorded acceptance','value':baseline.get('best_valid_accepted_wind_mw'),'unit':'MW'},
            {'label':'Stored candidates inspected','value':baseline.get('candidate_calls'),'unit':'records'},
            {'label':'New power flows in this lookup','value':0,'unit':'calls'},
            {'label':'Live AI result','value':current.get('agent_metrics',{}).get('best_valid_accepted_wind_mw'),'unit':'MW; unmeasured if blank'}],
        'limitations':['Conditional prepared model; actual operating approval and field savings are not established.',
                        'Candidate lookup alone does not establish an AI optimisation advantage.'],
        'evidence_file':'evaluation/conditional_agent_results.json'}
    return report
