# Archived-weather forecast increment

One fixed additional experiment completed on 2026-09-27. No Flex product files
were changed. Run `python tmp/forecast_candidate/evaluate.py` from the workspace.
Dependencies: numpy, pandas, openpyxl, scikit-learn.

## Scope and provenance

Training: January–June 2026, 8,592 eligible half-hours. Evaluation: August
2026, 1,486 half-hours. July unused. The last source interval is August31
22:30UTC; the 6-hour ranking diagnostic includes only30 complete UTC days.
Republic of Ireland wind dispatch-down target; lagged all-island measurements
are predictive features, not a claim of matching jurisdictions physically.

The same fixed HGB model now has78 features (original46 plus32 archived weather
features). Eight pre-existing representative weather locations are retained.
This is not a capacity-weighted wind-farm map.

Open-Meteo Previous Runs documentation confirms `_previous_day2` represents
forecasts48 hours before their valid time:
https://open-meteo.com/en/docs/previous-runs-api

January–July inputs already existed locally. August was downloaded from the
same endpoint/model/variables. Source URL and SHA256s are in results.json.
No realised future weather or reanalysis was used. Forecast origin is implied
by the API offset, not a recorded historical delivery timestamp. The implied
origin precedes decision time by at least13 hours. Original historical
delivery latency and training-label publication dates are unverified.

## Total dispatch-down result

| Predictor | MAE MW | RMSE MW |
|---|---:|---:|
| Zero |48.684|189.184|
| Training mean |220.968|253.824|
| Shrunk calendar |212.072|251.042|
| Original no-weather HGB |121.361|195.996|
| Weather-only Ridge |78.111|146.287|
| Archived-weather HGB |42.044|99.004|

The augmented model passes the prewritten point-metric gate for total
dispatch-down only. None of the four cause-specific models pass. Relative to
zero, MAE is13.64% lower and RMSE47.67% lower in this evaluation. The paired
3-day block-bootstrap95% interval for model-minus-zero daily MAE is
[-45.38,+19.76]MW, so robust superiority over zero is not established. The
intervals relative to no-weather HGB and weather-only Ridge exclude zero.

At the diagnostic fixed50MW alert threshold, precision50.7%, recall67.9%,
F1=0.581. These are not calibrated probabilities or an operational guarantee.

## Decision diagnostic

Selecting six hours per complete day with the weather HGB coincides with
22,130.5MWh of historical DD, versus22,685.5MWh for the calendar comparator
and25,299.4MWh with perfect foresight. Consequently, the experiment does not
show superior six-hour scheduling value. These numbers are historical
alignment, NOT recovered energy, prevented curtailment or a feasible asset
dispatch schedule.

## Product recommendation

Retain total-DD early warning as a candidate input module. Do not pitch it
as a new proven standalone curtailment-reduction product. Its concrete
demonstrable capability is improved point forecast errors with archived
weather in this exploratory August replay. The next decisive product layer
must compare actionable choices under a validated physical or site model;
these national predictions alone do not establish causal savings.

August had already been inspected in an earlier no-weather screen. These
results are exploratory, not an independent holdout or as-issued live test.
No Microsoft AI service was connected, no automatic plant action executed,
and no field or commercial benefit demonstrated.

