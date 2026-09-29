# Reference network: verified result and exact scope

The nine-bus reference example passes the implemented steady-state checks. This is **not** validation of the Irish planning-model conversion or of a real operational intervention.

## Fixed default comparison

| Quantity | Line 6–7 unavailable | All lines available |
|---|---:|---:|
| Hypothetical available wind at bus 6 | 200 MW | 200 MW |
| Consumer demand | 315 MW | 315 MW |
| Accepted wind | 139.999984 MW | 200.000000 MW |
| Curtailed wind | 60.000016 MW | approximately 0 MW |
| Additional accepted wind | — | **60.000016 MW** |

This eliminates approximately 60 MW of curtailment in this constructed snapshot. It is neither 60 MWh nor a share of Ireland's total curtailment. Consumer load and original physical limits are identical. Total active line losses decrease by 2.321269 MW, so the difference is not additional wind consumed by larger transmission losses.

Why this example binds: with line 6–7 unavailable, wind at bus 6 and the generator connected through bus 3 must export through the 150 MVA line 5–6. The existing generator has an unchanged 10 MW minimum. Restoring the other path permits the extra injection in the calculated steady state. This is an illustrative grid mechanism; it does not prove that a scheduled maintenance outage may actually be cancelled or moved.

## Independent numerical evidence

The unmodified source case first passed PYPOWER Newton power flow and an independent flat-start SciPy root solve. Its source data are an unsolved input file, so initial slack output zero is not mistaken for a solved operating point.

For the actual candidate states, a separate implementation computes each branch's complex pi-model currents, both terminal powers, and every bus's active/reactive balance directly. It does not use PYPOWER's admittance matrix or reported flow residual routines. A second flat-start solve holds the candidate's active generation and voltage-control setpoints and recovers the candidate's voltage profile. This checks AC consistency, not optimization global optimality.

- All **21 of 21** predeclared confirmation cases passed the **13 implemented checks**.
- Three fixed wind/load conditions, each with seven topologies: 185 MW / 0.90; 215 MW / 1.05; 230 MW / 1.10.
- Largest independent bus power residual across the 21: **0.0000761 MW or MVAr**, below the declared 0.0001 tolerance.
- Largest independent solver voltage difference: **0.0000000172 p.u.**, below 0.00001.
- Largest independent solver angle difference: **0.00000354 degrees**, below 0.001.
- Default all-in-service advantage at the three confirmation conditions: **45.000012, 75.000019 and 90.000022 MW**, respectively.
- A low-wind 50 MW condition gives approximately zero advantage (difference 0.00000000916 MW), as expected. Percentage reduction is undefined when baseline curtailment is effectively zero.
- **11 meaningful software tests passed**, including deliberate voltage, P/Q generation, thermal-rating, consumer-load and connectivity faults. The tests are not 11 trials of a real intervention.

No statistical population inference is claimed from three constructed conditions. These are numerical verification cases, not historical out-of-sample operational evidence.

## What was held unchanged

The machine-readable `reference_bounds_certificate.json` records equal published bus voltage bounds, conventional generator P/Q bounds, branch ratings, impedances and shunts. Case9 specifies a relatively broad **0.9–1.1 p.u. voltage interval**. That interval was not relaxed for this experiment, and must not be represented as an Irish operating standard.

Only declared scenario inputs vary: added synthetic wind availability, common load scaling, and the one unavailable ring line (or no unavailable line). The added wind generator has Pmin=0, Pmax=available wind and Q=0. All conventional generators remain online and dispatch within their published P/Q bounds.

## Optimization policy and commercial interpretation

The objective uses the case's published conventional quadratic generation costs plus an explicitly assumed curtailment penalty of 1,000 objective units per MWh. This is a dispatch preference, not a claimed real price. The solver minimizes it as a nonlinear AC optimization. It is not a certificate of global maximum wind. No EUR savings or profit should be inferred from the objective values.

All seven topology candidates receive the same objective and physical constraints. AI, if available, may select which candidates to calculate and explain the evidence; the numerical solver and checker supply the numbers. A fixed enumeration is the essential baseline. No AI advantage has been established by these electrical tests.

## Not covered

N−1 security, dynamic/transient stability, frequency limits, inertia, fault levels, protection coordination, ramping, unit commitment, operational permissions, maintenance work windows/resources, real wind availability and Irish operational-state validation. Passing the listed checks does not authorize a real switching operation.

## Reproduce

From the project directory, after installing its dependencies:

```sh
python evaluation/reference_reproduce.py
python -m unittest discover -s tests -p test_reference_engine.py -v
```

Results: `reference_validation_results.json`; thresholds and the confirmation design: `reference_protocol.md`; original source data: `../data/reference_case9.json`.

## Sources

- PYPOWER case9: https://github.com/rwl/PYPOWER/blob/master/pypower/case9.py
- MATPOWER case9: https://github.com/MATPOWER/matpower/blob/master/data/case9.m
- AC OPF definition and constraints: https://matpower.app/manual/matpower/StandardACOPF.html
- Power-flow scope: https://matpower.app/manual/matpower/ACPowerFlow.html

`reference_case9.json` is derived from the PYPOWER reference data. The source copyright and BSD terms are retained in `../data/reference_PYPOWER_LICENSE.txt`.
