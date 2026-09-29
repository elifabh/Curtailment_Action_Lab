"""Reproduce local agent contract checks and deterministic baseline evidence.

No Azure request is made. This script is not a live AI quality benchmark.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app_service
from ai.evaluate_agent import benchmark


def write_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    log = io.StringIO()
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_agent*.py")
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(tests)
    (ROOT / "evaluation" / "agent_test_results.txt").write_text(log.getvalue(), encoding="utf-8")
    contract = {
        "scope": "Application contracts and real-engine integration; no live AI performance measurement.",
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "all_passed": result.wasSuccessful() and not result.skipped,
        "log": "evaluation/agent_test_results.txt",
    }
    write_json(ROOT / "evaluation" / "agent_contract_results.json", contract)
    context = app_service.get_agent_context("reference_9bus", 200., 1.)
    callback = lambda candidate: app_service.evaluate_candidate({"profile_id": "reference_9bus", **candidate})
    report = benchmark(context, callback,
        "Compare allowed topology scenarios at the selected conditions.", budget=4, run_live=False)
    write_json(ROOT / "data" / "deterministic_search_evaluation.json", report)
    live_record = {
        "live_ai_benchmark_status": "not_run", "status": "not_run",
        "reason": "This reproduction runs local tests and numerical comparisons only; no Azure request was made.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "accuracy": None, "ai_gain": None,
        "next_step": "Configure Azure and explicitly opt in with python ai/evaluate_agent.py --run-live.",
    }
    write_json(ROOT / "data" / "agent_evaluation.json", live_record)
    baseline = report["baseline_metrics"]
    regret = baseline["regret_to_declared_candidate_oracle_mw"]
    tolerance = 1e-6
    matches = regret is not None and regret <= tolerance
    source_paths = ["data/deterministic_search_evaluation.json", "data/agent_evaluation.json",
                    "evaluation/agent_contract_results.json", "ai/agent_runner.py", "ai/evaluate_agent.py"]
    sources = [{"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
               for path in source_paths]
    summary = {
        "status": "completed" if contract["all_passed"] and report["oracle"]["complete"] else "review_required",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": ("The four-call deterministic baseline matches the best eligible result in the seven-candidate "
                    "reference set at the selected default conditions. Live Microsoft AI performance is unmeasured."
                    if matches else "Review the measured deterministic comparison; live Microsoft AI performance is unmeasured."),
        "live_ai_status": "not_run", "ai_improvement_measured": False, "ai_accuracy": None,
        "profile_id": "reference_9bus", "fixed_conditions": {"wind_mw": 200., "load_scale": 1.},
        "baseline_metrics": baseline, "agent_metrics": report["agent_metrics"], "oracle": report["oracle"],
        "baseline_matches_reference_within_tolerance": matches,
        "comparison_tolerance_mw": tolerance, "contract_tests": contract,
        "metrics": [
            {"label": "Baseline accepted wind", "value": baseline["best_valid_accepted_wind_mw"], "unit": "MW"},
            {"label": "Declared-candidate reference", "value": report["oracle"]["best_valid_accepted_wind_mw"], "unit": "MW"},
            {"label": "Baseline candidate calls", "value": baseline["candidate_calls"], "unit": "calls"},
            {"label": "Separate reference calls", "value": report["oracle"]["separate_candidate_calls"], "unit": "calls"},
            {"label": "Live AI improvement", "value": None, "unit": "not measured"},
        ],
        "sources": sources,
        "limitations": report["limitations"] + [
            "Passing authored provider tests does not establish AI reasoning quality or grounding accuracy.",
            "The original Irish source profile remains blocked. The separate conditional Irish study inspects verified stored connection-point alternatives; these are not approved operating actions.",
        ],
    }
    write_json(ROOT / "evaluation" / "summary.json", summary)
    print(json.dumps({"status": summary["status"], "tests": contract,
                      "baseline_matches_reference": matches, "live_ai_status": "not_run"}, indent=2))
    return 0 if summary["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
