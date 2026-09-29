# Archived-weather forecast increment: fixed exploratory protocol

Written 2026-09-27 before evaluating this weather-augmented model. The earlier
August no-weather results have been seen; August is not an untouched holdout.

- Reproduce the previous issue time and measured-feature eligibility: issue at
  12:00 UTC preceding the target UTC day; measurements no later than 11:00 UTC.
- Train January–June 2026; July unused; evaluate August 2026. No tuning, target
  selection, threshold optimization or change of loss after viewing results.
- Candidate: same fixed HistGradientBoostingRegressor as the earlier screen,
  adding 32 features from the existing eight coordinates: ECMWF IFS 0.25-degree
  100-m wind speed, cube of speed, sine and cosine of direction.
- Input is Open-Meteo Previous Runs `_previous_day2`, documented as forecast
  48 hours before valid time. Hourly values repeat for both half-hours. A
  minimum 12-hour interval between implied forecast origin and decision time
  is required. Actual delivery timestamps and historical training-label
  availability have NOT been audited: no as-issued operational claim.
- Compare same test intervals against zero, training mean, shrunk calendar,
  original no-weather HGB, and one simple weather-only standardized Ridge
  (alpha=100, fixed in advance). All predictions clipped at zero.
- Primary metrics: MAE and RMSE in MW for the five original targets. A target
  passes only if the weather HGB beats every comparator on both metrics.
- Paired daily MAE differences: 3-day circular block bootstrap, 2,000 draws,
  seed42, 95% interval. Exploratory, no multiplicity-adjusted significance.
- Diagnostic only: fixed alert threshold50 MW; precision, recall and F1.
  Do not use diagnostic metrics to rescue a failed primary gate.
- Diagnostic ranking only: each complete day select 12 half-hour intervals
  (6hours) using predicted total dispatch-down; compare historical DD energy
  in those intervals to fixed00:00–06:00UTC and training calendar selections.
  This is time alignment only, not avoided MWh or an executable asset plan.
- If API download is unavailable, stop and report the data gap. Do not fill
  future weather from realised observations or reanalysis.

