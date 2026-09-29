# AI investigation workflow

The implemented agent is a bounded, advisory tool-calling loop. On the default Irish profile it retrieves checked connection-point alternatives. On the separate reference profile it can ask the local grid engine to evaluate permitted topology scenarios, inspect the results, and choose another candidate. It does not operate grid equipment.

The displayed numerical explanation is assembled from engine records in Python. Free-form model prose is not treated as numerical evidence. A result can be ranked only when the model profile allows recommendations, the engine marks the result eligible, and every declared check passes. Passing those declared checks is not an operational safety approval.

## Current evidence

- The Azure tool-calling integration is implemented, but a live Azure evaluation has **not been run** in the delivered package.
- Without Azure configuration, the AI button is disabled. Manual scenarios and the separately labelled **deterministic baseline** work locally.
- `tests/test_agent_runner.py` contains 18 authored contract tests. They exercise application behaviour with scripted provider messages; they do **not** measure AI accuracy, intelligence or physical curtailment reduction.
- `tests/test_agent_integration.py` adds five application integration tests, including actual numerical engine calls. Passing these does not establish AI quality.
- `data/deterministic_search_evaluation.json` is an actual local reference-engine run: at 200 MW available wind and load scale 1.0, a four-call deterministic baseline reaches approximately 200 MW accepted wind. The separately evaluated seven-candidate reference reaches the same value within numerical tolerance. There is no demonstrated AI gain at this operating point.

## Interaction

1. Select the model, available wind and load in Scenario Lab.
2. Enter an investigation request, for example: “Start with outage_6_7, then investigate permitted alternatives that might accept more wind. Keep the selected conditions unchanged.”
3. The selected wind and load stay fixed throughout the action comparison. The agent may change only the permitted action ID.
4. Each tool request is validated locally and then passed to the deterministic engine. Results return to the model using the matching `tool_call_id`.
5. A trace shows the evaluated candidates, engineering checks and rejected requests. The summary identifies the best **tested eligible** candidate, if any.

The default reference actions are seven hypothetical line-availability states. They are not a list of interchangeable approved maintenance or switching decisions. Any real intervention requires additional operational constraints and an authorised engineer.

The request parser conservatively detects explicit conflicts such as “wind to 300 MW” while the selected wind is 200 MW. It requests a control change first. This is not a claim that all natural-language ambiguity is understood. Tool arguments are checked independently of natural-language interpretation.

## Python contract

```python
from ai.agent_runner import run_agent, run_baseline

result = run_agent(prompt, context, evaluate_fn, budget=4)
baseline = run_baseline(context, evaluate_fn, budget=4)
```

`context` is supplied by the application, not by the model:

```json
{
  "profile_id": "reference_9bus",
  "allowed_actions": [{"id": "all_in_service", "name": "All lines available"}],
  "controls": {
    "wind_mw": {"min": 0, "max": 240, "default": 200},
    "load_scale": {"min": 0.85, "max": 1.15, "default": 1}
  },
  "fixed_conditions": {"wind_mw": 200, "load_scale": 1},
  "recommendation_allowed": true,
  "validation_status": "Passed declared reference-model checks"
}
```

`evaluate_fn(candidate)` receives exactly:

```json
{"action_id": "all_in_service", "wind_mw": 200, "load_scale": 1}
```

The callback must return finite `accepted_wind_mw`, a Boolean `eligible`, and a nonempty `checks` list with Boolean `passed` values. Additional evidence can be included. The runner does not turn a failed check into a pass. The original Irish source profile retains `recommendation_allowed: false`, and its superseded calculation is disabled. The separate Irish conditional profile allows comparison within the prepared study only; it does not authorise physical actions. It exposes the eligible alternatives in the eight-point portfolio. Irish tool calls are evidence reads, explicitly counted separately from new solver calls.

Returned fields include `status`, `records`, `rejected`, `best_valid`, `summary`, `solver_calls`, `provider_calls`, `usage` and `elapsed_seconds`. `summary_source` is `deterministic_engine_records`. `physical_actions_executed` is always false.

## Bounded execution

- Budget: 1–8 candidate calls; default 4. One candidate may internally use an optimiser and independent checks, but it is one engine request.
- `parallel_tool_calls` is false. If a provider nevertheless sends a parallel batch, none of that batch is executed.
- Unknown tools/actions, additional physical parameters, out-of-range numbers, Boolean-as-number values, non-finite JSON and duplicate JSON keys are rejected.
- Repeated candidates are not re-evaluated. Provider rounds are also bounded so invalid requests cannot produce an unlimited loop.
- Provider refusals, incomplete responses and timeouts produce explicit statuses. Errors do not create synthetic success results.
- The callback may reuse cached deterministic evaluations. `solver_calls` means candidate requests, not a claim that each request started a fresh numerical optimiser.
- Full electrical safety, security-constrained dispatch, forecast uncertainty, market settlement and field execution are outside this agent's claim.

## Azure setup

The backend reads these variables; never put secrets in the browser or commit them:

```text
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com
AZURE_OPENAI_API_KEY=YOUR-KEY
AZURE_OPENAI_DEPLOYMENT=YOUR-FUNCTION-CALLING-DEPLOYMENT
```

An endpoint ending in `/openai/v1/` is also accepted. A model deployment must support the Chat Completions function-calling and strict tool schema features used here. Actual event-provided deployment capabilities are not yet verified.

The stdlib client posts to `/openai/v1/chat/completions` with `api-key`, a deployment name in `model`, typed function tools, and `parallel_tool_calls: false`. Authentication does not leave the backend. Redirects to other endpoints are rejected. The default per-request network timeout is 35 seconds.

## Evaluation protocol

`ai/fixtures_agent.json` is an authored workflow fixture set. It includes normal investigation requests and two requests that must not execute: a conflicting wind setting and a request to disable engineering checks. It is not a collection of independent real grid incidents.

Both the AI search and the deterministic baseline receive the same maximum candidate-call budget and unchanged wind/load conditions. The baseline evenly covers a sorted list of the declared candidates without looking at results first. A separate exhaustive evaluation of that finite set supplies the reference best value. Its extra calls are reported and are not given to the agent.

Report best eligible accepted wind, regret to that declared-candidate reference, fraction of that reference, rejected physical candidates, invalid requests rejected, engine calls, provider usage and wall time. Missing eligible outcomes remain null. The reference is not a continuous or globally optimal secure-dispatch oracle.

Without opting in, the evaluator only writes a `not_run` record:

```sh
python ai/evaluate_agent.py
```

After configuring Azure, use the application adapter and explicitly opt in to cloud requests:

```sh
python ai/evaluate_agent.py --run-live --engine-adapter app_service --profile reference_9bus --wind 200 --load 1 --budget 4
```

The adapter exposes `get_agent_context(profile_id, wind_mw, load_scale)` and `evaluate_candidate(request)`. `benchmark(context, callback, prompt, budget, run_live=False)` can also be imported for a local baseline/reference comparison without any Azure request.

To reproduce the local contract/integration tests, real-engine baseline, finite-candidate reference and consolidated `evaluation/summary.json` without any Azure call:

```sh
python evaluation/reproduce_agent.py
```

A single live comparison is descriptive. It does not establish general superiority. A small action set can be enumerated directly; AI is useful only if a measured workflow benefit justifies its cost and latency. Cached solver results can affect wall times, so the delivered timing is not a speed claim.

## Official API references

Checked on 27 September 2026:

- Microsoft function-calling guide: https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/function-calling
- Azure OpenAI Chat Completions v1 reference: https://learn.microsoft.com/en-us/rest/api/microsoft-foundry/azureopenai/chat

These references describe the API contract. They do not certify this application or prove any AI performance benefit.

## Default Irish workflow

Use `python evaluation/conditional_agent.py --budget 4` for the recorded-candidate deterministic benchmark without cloud access. Add `--run-live` only after Azure access is available. The same declared candidate set and budget are given to the live agent and baseline. The exhaustive finite-set reference is separately counted. Opening the robustness explorer does not give the agent permission to invent unrecorded wind/load settings.

The extended physical study was produced deterministically before AI use. It can show that a nearer point is not always the best tested location; this is not evidence that an LLM finds the best point more effectively than enumeration. The live experiment must establish any AI workflow advantage.
