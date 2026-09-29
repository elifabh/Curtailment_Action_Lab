# Irish-model audit, revision 3

This is a diagnosis and validation exercise. It does not claim avoided Irish curtailment.

## Questions

1. Which missing settings can be recovered from another official export in the same archive?
2. Can the electrical conversion and source-state reconstruction be checked independently?
3. Which source or solved violations remain under unmodified published limits?
4. Is any comparison suitable for transmission pre-feasibility, and what prevents an operational or avoided-energy claim?

## Fixed safeguards

- Preserve source files and SHA-256 hashes. Never increase ratings or voltage limits to obtain a pass.
- Use the V35 companion to recover settings only after checking common records against V33.
- Report source reconstruction, numerical solution and engineering feasibility separately.
- Preserve all failures. Independent packages are not assumed correct merely because they are external.
- Any deliberate control change is a new scenario, not a repair of the recorded source operating point.
- Do not change generation/load records to force an independent importer to match without recording the transformation.
- A transfer-headroom result is not measured curtailment reduction. MW is not MWh.
- Maintenance optimisation requires a declared job set, durations, allowed windows, electrical actions and security constraints. No operator-approved schedule has been supplied.

## Numerical verification

For recomputed states, target maximum bus power-balance residual <= 1e-4 MVA. Compare direct branch-current equations against the solver's branch flow outputs and check original bus/generator/branch bounds. The original source may have a different declared solution tolerance and printed-data rounding; report these separately, without interpreting a source-fit tolerance as a safety margin.

Independent import and solver experiments are exploratory until their model coverage is audited. Differences must be attributed before results are interchangeable.

## Claim levels

- Source inventory checked.
- Electrical transformation independently checked within stated device coverage.
- Power flow numerically converged.
- Declared steady-state limits passed.
- Operational action validated (requires further security/control/permission evidence; not implied by earlier levels).
