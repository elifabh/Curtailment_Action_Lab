# Reproduce the v5 challenge study

The protocol was written before the new numerical runs. `PROTOCOL.json` records fixed scenarios, inputs and decision rules. Do not silently change it when interpreting the delivered results.

1. Install `irish_audit/requirements.txt` in a local Python 3.12 environment.
2. Preserve the delivered evidence, then run `python evidence_v5/code/run_challenges.py` from the project root.
3. Run `python evaluation/decision_benchmark.py` and `node tests/decision_parity.js`.
4. Run `python scripts/build_offline.py` to refresh the standalone interface.

The new physical run reuses exactly matching v4 curves with qualified file-and-record references. Eighteen missing curves are solved afresh; 10 MW delivery is not interpolated from 20 MW. The numerical source and preparation come from the retained Irish audit. The demand-higher baseline fails the declared conditions, so no candidate benefit is claimed for it.

`results/challenge_matrix.json` is the site–condition join. `results/evaluations.jsonl` and the NPZ files contain the fresh physical evaluations. Commercial cases in `evaluation/decision_benchmark.json` use synthetic assumptions and are a distinct experiment. The standalone application reads these physical records; it does not execute the rebuild.

Rebuilding results may vary in elapsed time by machine and library environment. No runtime number is a scaling guarantee. Live Azure is optional, separate, and requires `--run-live`.
