# Extension verification

## Completed numerical runs

| Experiment | Result | New power-flow calls |
| --- | --- | ---: |
| Reproduce the 20 MW location comparison | B = 47.65625 MW, C = 68.359375 MW; difference **20.703125 MW**. Both selected points pass. | 32 |
| New availability and service amount | 55.125 MW available wind and 12.5 MW load at each location; difference **9.61718750 MW**. Both selected points pass. | 15 |
| Same-location control | Zero difference for the same feasible connection; exact reuse counted separately. | See same_site_placebo.json |
| First six hours of 2025: wind shape, fixed source demand | **12/12** comparable intervals; **124.21875 MWh** more hypothetical wind accepted at C than B. Demand, other controls and the assumed outage remain fixed. | 50 |
| Same six hours: observed national demand and assumed headroom redispatch | **0/12** comparable intervals. Full-period energy result is **not established**, not zero. | 146 |

The fixed-demand result is not a replay of actual Irish operations. National wind shapes an assumed local 200 MW profile. Both locations serve the same 20 MW scheduled load for six hours: 120 MWh of load at each site. This is not battery charging, load shifting or an annual model.

The observed-demand mode encounters source voltage-limit violations and generator-P violations. The programme retains them and blocks the energy comparison. Fixed peak-case controls and the simple dispatch assumption do not establish those low-demand operating states. No limit was loosened to produce a favourable result. This does not show that the real Irish grid cannot operate at the observed demand.

## Completed software checks

- 70 existing Python regression tests passed, including recorded comparisons, offer decisions, exports and local API contracts.
- 13 extension unit/route tests passed: strict inputs, signed integration, null totals for failed coverage, dependency failure, permitted routes and same-origin enforcement.
- 9 service checks passed using actual worker subprocesses: new inputs, actual new solves, availability bounds, balance reconciliation, simultaneous-job rejection and a feasible same-site control.
- 14 DOM component checks passed for loading, the displayed numbers, stale inputs, new/saved labels, profile rows, blocked totals, report/JSON exports, escaped text and error recovery. Transport was mocked in these DOM checks.

These are separate checks with different purposes. They do not mean that every possible model state, device or browser is validated. No Windows execution, visual browser test or new live Azure call was performed for this extension.

## Practical scope

The package provides an optional fresh-calculation page, a numerical engine, the two completed profile experiments, English result reports and a Turkish private setup guide. Existing Azure tools still inspect saved evidence; they do not call this new numerical branch.

Annual avoided-curtailment energy and national percentages remain null. Extending the observed-demand study requires reviewed control/dispatch modelling, time-coupled operational assumptions, generator technology/availability data and reconciliation of the flagged source-data discrepancy.

Exact request files, every returned coarse/refined point and calculation provenance accompany the results. `EXTENSION_PROTOCOL.json` records the choices fixed before extension outcomes.
