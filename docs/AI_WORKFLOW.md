# Microsoft AI workflow — v5

Two workflows share the local Azure adapter. The original AI Analyst investigates allowed model alternatives. The new Offer decisions audit asks which condition would invalidate a fixed nominal offer.

## Counterexample audit

`POST /api/challenge-audit` accepts a validated plan, mode, prompt and a 1–7 record budget. All modes first read the same eight nominal records to select the nominal offer. This fixed overhead is reported separately. There are no hidden full-matrix reads during selection.

Azure may call `test_offer_scenario` with exactly one allowlisted `scenario_id`. The application fixes offer, cost assumptions, physical records and pass rules. Parallel batches, unknown options, duplicate records and extra arguments are rejected. Tool outcomes supply all numerical results; free-form invented numbers are ignored. No market or device API is exposed.

Modes: fixed deterministic order, seeded random order, or Azure. A call reads a precomputed physical result, not a new power flow. The UI's complete offer decision separately inspects all 64 cells; do not present that already-computed decision as an AI discovery.

## Measure fairly

`python evaluation/decision_benchmark.py` records local policy fixtures and rule/random baselines. `--run-live` additionally requests Azure and uses quota. Compare equal maximum record reads, first failing-condition read, number of failing conditions found, rejected calls, total provider latency and token usage. Fewer than the maximum reads are allowed and disclosed.

The provided live benchmark is one small diagnostic plan, not a statistically sufficient model-quality evaluation. There are only seven challenge conditions; a complete rule is cheap. Evidence does not yet support an LLM speed, accuracy or wind-saving advantage. A larger, independently authored held-out scenario/task set would be needed for that claim.

## Connection

Copy `.env.example` to `.env`. Configure endpoint, API key and deployment name for the implemented Azure OpenAI v1 Chat Completions function-calling interface, then restart localhost. The endpoint suffix and transport are checked, keys remain backend-only, and redirects are rejected. If the event provides token-only/Entra authentication or a different API, adapt the provider with those actual details; do not pretend credentials alone prove compatibility.

Scripted provider tests exercise application contracts; they are not Microsoft model calls. Delivery status: **live Azure not run**.
