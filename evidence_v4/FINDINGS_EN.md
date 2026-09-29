# Extended study findings — v4

The preregistered study completed **457 actual power-flow evaluations** on the same prepared public Irish planning model. It compares hypothetical flexible demand at identified network connections. These are reproducible conditional snapshots, not measured Irish dispatch-down events or approved operations.

## Main result

For 200 MW hypothetical available wind, the stated line outage and the same 20 MW flexible demand, the best of the eight tested connection points is **CATH_FALL (bus 1701): 68.359375 MW** accepted wind. The existing Cruiserath comparison accepts **47.65625 MW**. The difference is **20.703125 MW** in this model.

The wind-connection/nearest-point rule at Binbane gives **61.71875 MW**. The full screen finds **6.640625 MW** more than that rule. Equal distribution of the 20 MW across all eight points gives **62.6953125 MW**. The whole-screen comparison uses more calculations than a single-location rule; it is not an equal-budget AI advantage or a global optimality result.

The best point is a different network node from the wind injection. No new private-wire connection is added. This supports testing network location instead of assuming only a colocated load could help. It does not establish that an actual 20 MW flexible asset exists at CATH_FALL or any other candidate.

| Candidate | In-service graph hops from wind | Best tested wind (MW) | Difference from Cruiserath (MW) |
|---|---:|---:|---:|
| BINBANE (1341) | 0 | 61.71875 | 14.06250 |
| CRUISERATH (2072) | 9 | 47.65625 | 0.00000 |
| CATH_FALL (1701) | 1 | 68.35938 | 20.70312 |
| TIEVEBRACK (5191) | 1 | 63.28125 | 15.62500 |
| ARDNAGAPPARY (1571) | 2 | 64.84375 | 17.18750 |
| CLIFF (1761) | 2 | 67.57812 | 19.92188 |
| CORRACLASSY (1981) | 2 | 64.84375 | 17.18750 |
| CLOGHER (2870) | 2 | 67.96875 | 20.31250 |

The candidate-selection graph is the prepared in-service network, as preregistered; the evaluated portfolio uses the stated 1341–1701 outage. Graph hop count is an input heuristic, not distance in kilometres or proof of electrical benefit.

## Primary robustness grid

Five flexible-demand sizes, six wind ceilings and two line states give **60 paired conditions**. With the preregistered 0.5 MW material-difference threshold:

- **38 positive**, **20 neutral**, **0 negative**, **2 blocked**.
- The comparable nonzero-flexibility differences range from **0 to 22.265625 MW**. The maximum uses 30 MW flexible demand and is not the same case as the 20 MW portfolio result.
- Zero flexible demand yields exactly zero location effect. At low available wind the two alternatives can accept the same wind, so extra benefit is not guaranteed.
- The two blocked cases have 30 MW flexibility and 25 MW wind availability, one in each line state. No checked point under that wind ceiling was found for one alternative under the fixed controls. This is not proof of physical impossibility with different generation or controls.

Several availability ceilings reuse the same calculated point. These are **not 60 independent trials, historical days or a probabilistic success rate**. A deterministic scenario grid does not justify a confidence interval for all future Irish operation.

## Additional source-demand stress

At source demand factor **0.99**, the paired difference is **15.8203125 MW**. At **1.01**, the existing-location curve has no passing tested point; the pair is blocked even though the other location has a passing point. It receives no reduction or monetary claim.

Small demand changes can expose the limits of fixed controls and fixed non-balancing dispatch. Do not describe this as a fully adaptive operating model. No limits were relaxed to rescue these cases.

## Numerical scope and rejected points

Of 457 evaluated wind points, **141 passed every implemented snapshot gate** and **316 were excluded**. Searching deliberately includes high-wind points beyond model limits. These counts are not a field-success percentage.

Rejected-point categories overlap: 279 evaluated points had original-bus voltage violations, 40 had generator active-power violations, and 27 had rated-branch thermal violations. All evaluated points converged in this run; convergence alone was not enough for eligibility. Records remain in `results/evaluations.jsonl`.

Passing states were checked against directly parsed RAW branch equations and original numerical bounds, plus ideal-tie recovery. The 144 tree ties have unique recovered flows; four cyclic edges use a declared allocation, not a certificate of every possible physical cycle-flow split. Zero and placeholder-like source ratings remain a scope limit.

The prepared scenario retains the declared **60 source-bounded tap changes and capacitor 74564 disconnected**, fixed local generator voltage controls, fixed calibrated HVDC boundary, and the chosen balancing generator. Original source limits were not widened. These controls are assumptions, not authorised field actions.

## Measured workload

- Full study: **31.32 minutes** including setup and checks.
- Median evaluation: **4.247 seconds**; P95: **5.273 seconds**.
- Peak process resident memory: **189.63 MiB**.
- Environment: Linux, Python 3.12.14, NumPy 2.3.5, pinned dependencies, OPENBLAS_NUM_THREADS=1.

This is one recorded preparation run, not a controlled cross-system speed benchmark or a real-time operating guarantee. UI retrieval and value arithmetic use stored data and are not counted as new power flows. A repeated curve with exactly identical inputs is explicitly marked as reused.

## Commercial and AI interpretation

The value calculator can use either a primary-grid pair or any recorded portfolio pair. It multiplies the selected model's MW difference by an **entered assumed duration** and prices it using **entered assumptions**. Extra activation and other event costs are subtracted. Insufficient entered energy blocks the illustration; absent energy data remains visibly unverified. The model does not establish a sustained feasible event or actual market profit.

The four-record deterministic candidate search already reaches the best of the eight recorded alternatives. Live Azure AI was not run. The physical advantage relative to the nearest-point rule belongs to the checked deterministic comparison; it is not an AI performance claim. After access arrives, the separate agent benchmark can measure actual tool use against the same budget.

## Reproduction and provenance

- Protocol hash: `d2599b7e1dbb257dcee449888df57960d705385b30cc9ad1a754b3180392cd56`.
- Original RAW source hash: `006db9ce2ff20a7bf2a67ffbd9988735a1b3d3dc8abbd6309395e7139b66cb24`.
- `PROTOCOL.json`: decisions recorded before new outcomes.
- `results/candidate_selection.json`: connections selected before candidate results.
- `results/report.json`: complete comparison data, reuse and runtime.
- `results/evaluations.jsonl`: every actual evaluated point and check outcome.
- `results/*_best.npz`: saved best tested numerical states.
- `study_summary.json`: exact app-facing values and paired IDs.

See `README.md` in this folder for an explicit separate-copy rerun. No annual MWh, national reduction percentage, customer savings, market price forecast, willingness to pay or operational security certificate is derived from these snapshots.
