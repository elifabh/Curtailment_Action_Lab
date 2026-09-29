# Reference-network verification protocol

Locked before the three confirmation conditions were calculated, 27 September 2026.

## Scope

Use the public PYPOWER 5.1.19 `case9` data, derived from the MATPOWER/Chow nine-bus example. Keep every published voltage bound, generator P/Q bound, branch RATE_A, impedance and shunt unchanged. Add one explicitly hypothetical unity-power-factor wind generator at bus 6: active injection between zero and available wind; reactive injection fixed to zero. Scale both P and Q consumer demand together, identically for baseline and candidate.

The fixed baseline has line 6–7 unavailable. Candidate topologies are all lines available, or one of the six ring lines unavailable. They are hypothetical alternatives, not evidence that real maintenance tasks are interchangeable or approved. No switching sequence, N−1 security, transient stability, frequency, ramping, commitment or maintenance-resource model is included.

## Objective

AC OPF minimizes published conventional generation polynomial costs plus a synthetic wind-curtailment penalty of 1,000 objective units per MWh. Implement the equivalent negative linear wind coefficient; restore the constant when reporting the objective. These units are **not EUR**. This is a declared dispatch policy, not a proof of global maximum wind or a forecast of market prices.

## Independent verification

1. Solve unmodified source case with PYPOWER Newton AC power flow.
2. Independently implement each branch's complex pi-model current equations and bus shunt injection. Recompute both-end complex branch powers and every bus's complex balance without using PYPOWER's Ybus, branch flows or residual routines.
3. Independently solve PV/PQ equations with SciPy `root`, from flat angles and unit PQ voltages, holding generator active setpoints and controlled-bus voltage magnitudes. Compare voltage magnitude/angle to PYPOWER. This validates the solved AC state, not global optimality or real grid accuracy.
4. For every candidate require: optimizer success; no islands; unchanged P/Q consumer load; finite solution; full-bus P and Q residual ≤0.0001 MW/MVAr; all bus voltage limits within 0.000001 p.u.; both-end branch apparent power ≤RATE_A+0.0001 MVA; every online generator P/Q bound within 0.0001 MW/MVAr; wind availability and zero-Q bounds; angle limits; independent power flow agreement ≤0.00001 p.u. and 0.001 degrees.
5. No failed case contributes a claimed benefit. Report positive, zero and negative comparisons.

## Development conditions already examined

Available wind 100, 160, 200 and 240 MW at demand multiplier 1.0; baseline versus all lines available. A pure wind-only flat OPF objective was numerically unsuccessful. The fixed objective above resolved convergence. These were development, not holdout tests.

## Fixed confirmation conditions

Run all seven permitted topologies for (wind MW, demand multiplier): **(185, 0.90), (215, 1.05), (230, 1.10)**. Do not select only favourable cases. Pass requires the source validation and all 21 candidate verifications to meet the above tolerances; otherwise list failures and restrict claims accordingly. Also run a low-wind 50 MW null case; an islanding topology as a negative connectivity check; and deliberately corrupt the solution's voltage, generation and branch capacity to confirm the checker rejects them.

## Claims and units

Primary result is a snapshot change in accepted and curtailed **MW**, within this constructed reference network. Percentage reduction denominator is baseline curtailed MW at the same wind/load, never Irish total curtailment. If baseline curtailment is below 0.001 MW, percentage reduction is undefined. No MWh, carbon, profit or country-wide extrapolation without separately supplied duration/data. AC feasible here means passing the listed steady-state tests only.

## Primary references

- https://github.com/rwl/PYPOWER/blob/master/pypower/case9.py
- https://github.com/MATPOWER/matpower/blob/master/data/case9.m
- https://matpower.app/manual/matpower/StandardACOPF.html
- https://matpower.app/manual/matpower/ACPowerFlow.html
