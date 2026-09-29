# Fresh Irish planning calculations

The optional extension runs a new numerical comparison in a separate worker process. It supports eight declared model connection points, 0–200 MW of hypothetical wind, 0–40 MW of equal additional demand, source-demand multipliers from 0.99 to 1.01, and the declared line outage or in-service condition. These are bounded research inputs, not a capability or security envelope for actual assets.

## Use

1. Install `requirements-irish-extension.txt` using the supplied Windows or macOS/Linux installer. The installer uses the same Python selection as the local launcher.
2. Restart `START_LOCAL.bat` or `START_LOCAL.sh`.
3. Open **Scenario Lab → Fresh Irish calculations**.
4. Choose a new scenario, select a hypothetical connection and run the calculation. Progress shows actual new solver calls. One calculation is accepted at a time.
5. Review both alternatives, the declared checks and failed search points. Download the complete JSON or a readable HTML report; use the print action for a PDF.

Included saved extension calculations are labelled as saved. They remain readable without installing the numerical dependencies. They are not substituted for a failed fresh request. The standalone `OPEN_DEMO.html` continues to provide the recorded main demonstration; the extension itself requires the local server.

## Numerical method

The worker copies the existing source audit into a temporary working directory. It reuses the source conversion, fixed-control AC solver, separate RAW electrical equations and declared ideal-tie recovery. Source thermal, voltage, P and Q limits are unchanged. Each alternative serves the same additional demand.

For each availability bound, the search tests 0 MW, the exact bound and 25 MW increments inside the bound. It locally refines the highest passing point to a bracket no wider than 0.25 MW. This yields a best tested passing point, not a global optimum or a proof of monotonicity. Every selected point must pass the existing checks. Failed points and a missing passing baseline remain visible.

The existing prepared source assumes 60 tap adjustments, one capacitor disconnection, local rather than fully reproduced remote controls, and a fixed inferred HVDC boundary. Missing or placeholder ratings and ideal-cycle allocation ambiguity remain. No dynamic security, SNSP, RoCoF, inertia or general contingency certificate is added.

Reports include source/model hashes, implementation hashes, exact inputs, calculation IDs, passing-point evidence, numerical residuals and the count of actual new solves. Identical cached evaluations within one run are counted separately from new solves. Azure credentials are not used by this module. The existing AI workflow continues to inspect saved records.

## Six-hour experiment

The period was specified before reviewing outputs: **1 January 2025, 00:00–06:00 UTC**, twelve consecutive half-hours. The programme does not select favourable intervals after running the model.

- National observations come from EirGrid's 2025 system and dispatch-down workbooks.
- The source system file uses quarter-hour average MW. Two successive quarters are averaged to create half-hour MW inputs.
- Dispatch-down columns are already MWh and are retained unchanged as context. They are not treated as locally recoverable energy.
- Local wind is a scenario assumption: a 200 MW equivalent profile proportional to national IE wind availability, normalised by its observed 2025 quarter-hour maximum. This is a historical profile-shape experiment, not a forecast or a measured local wind series.
- Both locations serve the same constant scheduled load throughout the period. At 20 MW each receives 120 MWh over six hours. No battery, shifting or rebound is represented.

Two modelling modes are distinguished:

1. **Wind profile; fixed source demand.** The hypothetical local wind availability varies. Demand and other dispatch remain at the prepared operating point, apart from the balancing generator. These are dated wind-profile inputs imposed on a fixed planning snapshot.
2. **Observed demand; assumed redispatch.** All-island demand scales source nodal load shares. Source-online generators are redistributed using headroom within their existing P limits; the original slack balances residual losses. This is an assumed dispatch rule, not a production-cost optimisation or a reconstruction of actual unit dispatch. Technology-specific renewable availability, ramps and commitment are unverified. A blocked result indicates the model does not establish that comparison.

The model integrates signed differences as `sum((selected wind MW - baseline wind MW) × 0.5 h)`. Negative effects are retained. Network-loss and other-generation changes are reported separately. If any comparison is blocked, the full-period total is null; only a clearly labelled subtotal over comparable intervals can be returned. No result is annualised.

## Source audit

The extraction checked 35,040 unique consecutive UTC quarters for the system data and 17,520 consecutive UTC half-hours for IE wind dispatch-down. It also found one system-demand inconsistency outside the pilot: at **2025-10-08 09:45 UTC**, the published all-island value is 7,140.585 MW while IE plus NI is 5,244.872 MW. The 1,895.713 MW discrepancy is retained and flagged, not silently corrected. The twelve pilot half-hours reconcile.

This new finding is a reason to resolve the source series before an annual demand-profile study. It does not change the previously calculated January–July 2026 dispatch-down composition.

Sources and file hashes are retained in `extension_data/pilot_2025_01_01.json`:

- https://cms.eirgrid.ie/sites/default/files/publications/System-Data-Qtr-Hourly-2025-v12.xlsx
- https://cms.eirgrid.ie/sites/default/files/publications/DD-HH-2025-v10.xlsx
- https://cms.eirgrid.ie/all-island-ten-year-transmission-forecast-statement-2024

## Reproduction

After installing the numerical dependencies:

```sh
python extension_engine.py --request extension_results/snapshot_request.json --output extension_results/my_snapshot.json --progress extension_results/my_progress.json
python -m unittest discover -s tests -p test_extension.py -v
python scripts/verify_extension_service.py
```

The service verification performs real new calculations and a feasible same-site placebo. It takes longer than the unit tests. To rebuild the profile excerpt, install `openpyxl`, download the two exact source workbooks and pass their containing directory to `python scripts/prepare_extension_profiles.py SOURCE_FOLDER`.

## Validation boundary

See `extension_results/VERIFICATION_EN.md` for measured results and completed checks. Python and numerical verification took place in the supplied Linux environment. UI behaviour was checked with a DOM harness; this is not visual browser or Windows execution testing. No new live Azure call was made. Public output and exports remain English.
