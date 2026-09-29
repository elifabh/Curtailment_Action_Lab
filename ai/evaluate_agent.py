"""Opt-in live Azure agent comparison against fixed-budget deterministic search.

No --run-live: records not_run; never substitutes mock responses as live results.
The adapter must supply get_agent_context(profile_id, wind_mw, load_scale)
and evaluate_candidate(request), where request also includes profile_id.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ai.agent_runner import agent_status, run_agent, run_baseline, exhaustive_reference


def _best_mw(run):
    best = run.get("best_valid")
    return best["result"]["accepted_wind_mw"] if best else None


def _metrics(run, oracle_mw):
    best = _best_mw(run)
    return {
        "status": run["status"], "best_valid_accepted_wind_mw": best,
        "regret_to_declared_candidate_oracle_mw": (max(0., oracle_mw - best)
            if oracle_mw is not None and best is not None else None),
        "fraction_of_declared_candidate_oracle": (best / oracle_mw
            if oracle_mw is not None and oracle_mw > 0 and best is not None else None),
        "candidate_calls": run.get("solver_calls", 0),
        "declared_budget": run.get("budget"),
        "violations_rejected": run.get("violations_rejected", 0),
        "invalid_requests_rejected": run.get("invalid_requests_rejected", 0),
        "wall_seconds": run.get("elapsed_seconds"),
        "provider_calls": run.get("provider_calls", 0), "provider_usage": run.get("usage", {}),
    }


def benchmark(context, evaluate_fn, prompt, budget=4, *, run_live=False, provider=None):
    """Same upper bound on candidate calls; oracle computation is separate and visible."""
    baseline = run_baseline(context, evaluate_fn, budget)
    if run_live:
        agent = run_agent(prompt, context, evaluate_fn, budget, provider=provider)
    else:
        agent = {"status": "not_run", "mode": "azure_agent", "budget": budget,
                 "message": "Live Azure benchmark was not requested.", "best_valid": None,
                 "records": [], "solver_calls": 0}
    # Run the oracle after the searches. Its outcomes are not exposed to the agent.
    oracle = exhaustive_reference(context, evaluate_fn)
    oracle_complete = not oracle["rejected"]
    oracle_mw = _best_mw(oracle) if oracle_complete else None
    is_live = bool(agent.get("is_live_provider"))
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "profile_id": context.get("profile_id"),
        "fixed_conditions": context.get("fixed_conditions"),
        "budget_per_search": budget,
        "live_ai_benchmark_status": (agent["status"] if is_live else "not_run"),
        "benchmark_provider_kind": "live_azure" if is_live else "injected_test" if provider else "none",
        "performance_claim": "No superiority claim. A live run is a single descriptive comparison, not a statistical guarantee.",
        "baseline_metrics": _metrics(baseline, oracle_mw),
        "agent_metrics": _metrics(agent, oracle_mw),
        "oracle": {"definition": "Best eligible result in the finite declared candidate set only.",
                   "complete": oracle_complete, "best_valid_accepted_wind_mw": oracle_mw,
                   "separate_candidate_calls": oracle["solver_calls"]},
        "limitations": [
            "Model snapshot comparisons, not measured field curtailment or Ireland-wide percentages.",
            "Both search methods have the same maximum candidate-call budget; early stops are reported.",
            "The oracle's extra calls are for evaluation only and are not part of either search budget.",
            "Accepted wind is compared only under fixed available wind and load conditions.",
            "Wall times include provider latency and may be affected by engine caching; no speed superiority claim.",
            "The deterministic baseline can match exhaustive search when the budget covers the action set.",
        ],
        "agent": agent, "baseline": baseline, "oracle_records": oracle["records"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-live", action="store_true", help="Opt in to paid Azure API requests using configured credentials.")
    parser.add_argument("--engine-adapter", default="app_service", help="Module with get_agent_context and evaluate_candidate.")
    parser.add_argument("--profile", default="reference_9bus")
    parser.add_argument("--wind", type=float, default=200.)
    parser.add_argument("--load", type=float, default=1.)
    parser.add_argument("--budget", type=int, choices=range(1, 9), default=4)
    parser.add_argument("--prompt", default="Compare allowed topology scenarios at the selected conditions. Find the best eligible accepted wind within budget.")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "agent_evaluation.json")
    args = parser.parse_args()
    if not args.run_live:
        result = {"live_ai_benchmark_status": "not_run", "status": "not_run",
                  "reason": "No --run-live opt-in. No Azure or solver calls were made.",
                  "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                  "accuracy": None, "ai_gain": None,
                  "next_step": "Configure Azure, then run the documented --run-live command."}
    elif not agent_status()["enabled"]:
        result = {"live_ai_benchmark_status": "not_run", "status": "disabled",
                  "reason": agent_status()["message"], "accuracy": None, "ai_gain": None}
    else:
        try:
            adapter = importlib.import_module(args.engine_adapter)
            context = adapter.get_agent_context(args.profile, args.wind, args.load)
            callback = lambda candidate: adapter.evaluate_candidate({"profile_id": args.profile, **candidate})
            result = benchmark(context, callback, args.prompt, args.budget, run_live=True)
        except Exception as exc:
            result = {"live_ai_benchmark_status": "not_run", "status": "adapter_error",
                      "reason": f"Engine adapter could not be used ({type(exc).__name__}). Check the documented API.",
                      "accuracy": None, "ai_gain": None}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": result.get("live_ai_benchmark_status")}, indent=2))


if __name__ == "__main__":
    main()
