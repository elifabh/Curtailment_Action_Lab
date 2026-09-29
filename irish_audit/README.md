# Reproduce the Irish audit

Read `docs/FINDINGS_EN.md` for the result, the unsuccessful attempts and the limits on interpretation.

Python 3.12 was used. From this folder, create an environment and install:

```sh
python -m venv .venv
# Activate it using the command appropriate for your operating system.
python -m pip install -r requirements.txt
python code/source_audit.py
python code/fixed_case.py
python code/tap_experiment.py --policy expanded_supported_controls
python code/shunt_experiment.py
python code/raw_equation_check.py
python code/wind_screen.py
python code/finalize_study.py
python code/test_verification.py
```

These scripts run locally and make no AI or device-control requests. The wind screen may take several minutes. Its output is a bounded scenario study, not a global optimisation certificate. Do not change thresholds and then describe the rerun as the same experiment.

`results/conditional_flex_study.json` contains the checked pair and all key assumptions. The other results preserve the diagnostic sequence. The original RAW files remain unchanged. `code/source_audit.py` needs only the standard library; numerical scripts use the pinned requirements below.

The optional independent-import attempt requires a **separate** environment with `VeraGridEngine==6.7.1` and `pulp==3.3.0`. Run `code/compare_exports.py` and `code/independent_veragrid.py --version 33 --controls fixed` or `--controls enabled`. Its failure/differences are recorded; reproducing that experiment is not necessary to run the checked demo.

The broader tap-policy failures can be reproduced with `--policy control_bands` and `--policy violating_buses_only`. The delivered expanded experiment includes impedance-correction updates and positive downstream remote targets; it does not model load-drop compensation or every PSS/E control.

To refresh the application after a numerical rerun, return to the project root and run `python scripts/build_conditional_records.py`, then `python scripts/build_offline.py`.
