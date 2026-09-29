# Reproduce the extended conditional study

`PROTOCOL.json` was written before the new scenario outcomes. `results/evaluations.jsonl` retains every actual power-flow evaluation, including failed checks. `results/report.json` is the full result; `study_summary.json` is the app-facing summary. `FINDINGS_EN.md` explains the outcomes and limits.

The experiment reuses the v3 prepared Irish model. It does not widen electrical limits or infer actual asset flexibility. Candidate selection is recorded before candidate outcomes in `results/candidate_selection.json`.

## Run in a separate copy

Use Python 3.12 and install `irish_audit/requirements.txt` from the project root. The delivered run used Linux with `OPENBLAS_NUM_THREADS=1`. Keep the delivered results intact; make a separate project copy, move its `evidence_v4/results` directory to a clearly named archive, and create an empty results directory for an explicit rerun. The script refuses to overwrite full or partial results.

```sh
python -m pip install -r irish_audit/requirements.txt
python evidence_v4/code/run_study.py
python evidence_v4/code/build_summary.py
python evaluation/conditional_agent.py --budget 4
python scripts/build_conditional_records.py
python scripts/build_offline.py
```

The numerical study is substantially slower than the recorded UI. It makes no Azure calls and sends no physical commands. Check dependency versions and record any changed environment. Do not silently combine outcomes from different input files or protocols.

## Design and interpretation

- Five flexible-demand sizes × six wind ceilings × two line states produce 60 paired conditions. The same-demand requirement is checked. Curves are reused under different availability ceilings; these are not 60 independent field trials.
- The coarse wind grid is 0–200 MW in 25 MW increments. The interval above the highest passing coarse point is refined to at most 0.25 MW. These are best tested points, not globally optimal or monotonic-feasibility certificates.
- Eight connection candidates are chosen before outcomes using the in-service electrical graph, voltage level and source-ID tie breaks. No real commercial asset is assigned to a bus by this selection rule.
- The fixed source-demand stress factors are 0.99 and 1.01. A failed paired comparison does not prove the real grid cannot operate with different generation or controls.
- A material difference is greater than 0.5 MW in magnitude, fixed before the experiment. The scenario grid is deterministic; no population success probability or bootstrap confidence interval is invented.
- A complete eight-candidate screen uses more calculation effort than the nearest-node rule. Any benefit relative to that rule is not described as equal-budget AI superiority.
- Optional MWh/EUR figures require explicit user assumptions. No hourly historical curtailment series, actual customer schedule or market tariff is used by this study.

The original model source and independent verification are documented in `irish_audit/`. The complete numerical source, licences/disclaimer and previous unsuccessful diagnostics are retained.
