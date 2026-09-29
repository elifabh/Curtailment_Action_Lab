# AI module

The current application uses `agent_runner.py`: an iterative Azure tool-calling agent connected to the deterministic scenario engine. Read `../docs/AI_WORKFLOW.md` for setup, boundaries, interface and evaluation instructions.

Files:

- `agent_runner.py`: bounded agent, deterministic baseline and finite-candidate reference.
- `evaluate_agent.py`: explicit opt-in Azure benchmark. No opt-in means `not_run`.
- `fixtures_agent.json`: authored workflow cases, not measured AI accuracy.
- `../tests/test_agent_runner.py`: scripted provider contract tests.
- `decision_intent.py`: retained legacy intent/explanation helper for compatibility. It is not the v2 investigation agent and is not the source of current benchmark claims.

Missing Azure credentials disable the agent; local manual and deterministic comparisons remain available. No application component sends physical switching commands. The Irish model is available for manual diagnostics; automatic recommendation search is blocked while its reconstruction remains unvalidated.
