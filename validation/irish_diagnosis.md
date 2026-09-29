# Irish planning-case reconstruction: diagnosis

**Decision: retain the Irish case as exploratory evidence. Do not present the earlier 37 MW difference as validated curtailment reduction.**

The earlier numerical failure is partly an importer/test problem, rather than evidence that the public model is unusable. Correcting this problem substantially improves reconstruction, but does not establish operational feasibility.

## What was diagnosed and corrected

The winter 2024 RAW export has 148 active non-transformer branches with zero resistance and reactance of at most 0.0001 pu. Every pair of their endpoint buses has exactly equal saved voltage magnitude and angle. These are consistent with PSS/E's ideal bus-tie treatment. The original importer treated them as finite-reactance lines, for which equal endpoint voltage incorrectly implies zero transferred power.

The diagnostic merges these buses, sums their loads and shunts, retains generators and preserves all other impedances, limits, statuses, source tap settings and phase shifts. There are 2,132 internal buses before this operation and 1,986 afterwards, including transformer star points. The merge threshold is an explicit assumption: the source RAW does not supply the PSS/E THRSHZ solution setting.

| Check | Result |
|---|---:|
| Largest source active-power residual before tie merge | 334.812 MW |
| Largest source active-power residual after tie merge | 4.312 MW |
| Largest reactive-power residual at effective PQ buses after merge | 4.922 Mvar |
| Remaining P/Q rows outside a conservative voltage-rounding envelope | 0 / 0 |
| Maximum solved voltage magnitude difference from saved source | 0.000024614 pu |
| Maximum solved angle difference from saved source, reference aligned | 0.031183 degrees |

The remaining largest residuals occur at opposite ends of small, nonzero-impedance branches. The export writes voltage magnitude to five decimal places and angle to four. This precision can amplify into several MW/Mvar when impedance is small.

For each row the diagnostic computes the rigorous complex-power error bound

`|delta S| <= baseMVA * [epsilon |YV| + |V| |Y| epsilon + epsilon |Y| epsilon]`,

where epsilon bounds voltage error from half a last printed digit in magnitude and angle. The diagnostic counts envelope exceedances with a 0.001 MW/Mvar comparison tolerance. **This is a necessary envelope, not proof that one joint solution lies inside every rounding interval.** The solved angle difference is much larger than half a printed digit. Exact PSS/E replication has therefore not been established. No voltage, thermal or generator limit was widened to obtain these results.

## Independent checks and their limits

- Direct CSV-style parsing of the RAW bus section independently confirms all 2,025 source bus records and the same 173 source voltage violations as the library parser.
- Newton, fast-decoupled XB and fast-decoupled BX all converge on the merged model. Their voltage magnitudes agree within approximately 1.6e-11 pu and their angles within approximately 2.1e-8 degrees.
- These are independent numerical algorithms **using the same imported network**. They do not independently validate transformer conversion, the HVDC approximation or the source control behavior. No separate PSS/E or commercial-solver run was performed.

## Physical feasibility remains unresolved

| Unchanged source limits | Result |
|---|---|
| Source bus voltage violations | 173; all below 100 kV |
| Solved merged groups containing original buses with voltage violations | 164 |
| Nonzero-RATEA modeled branch overloads in this baseline | 0; maximum loading approximately 95.50% |
| Active-power generator limit violations | 0 |
| Reactive-power generator limit violations, 0.0001 Mvar tolerance | 22; maximum excess 0.01259 Mvar |
| Reactive-power excesses above 0.02 Mvar | 0 |

The original and merged voltage counts have different denominators because several source buses are merged into a single group. This is **not** a demonstrated removal of nine physical voltage violations.

The Q-limit results above describe an unconstrained power-flow calculation; the diagnostic does not enforce Q limits. The small excess magnitudes are disclosed instead of silently labelling them a pass. Neither absence of a modeled overload nor numerical convergence establishes full grid safety.

## Conversion coverage

- **Transformers:** 109 active three-winding star points and 97 fixed-position impedance correction applications are represented. The star-impedance and partial-winding-status formulas were inspected against MATPOWER's documented importer. This is a formula review, not a full independent conversion run.
- **Multisection lines:** the 32 grouping records do not replace their constituent electrical branches, which remain represented. Group ownership, outage grouping and permission rules are not implemented; an individual branch toggle must not be described as an authorized real maintenance action.
- **HVDC:** two terminal records are present. At the connected modeled boundary, P/Q is inferred from saved voltages (approximately +80.330 MW and -29.836 Mvar at bus 86220). That boundary is excluded from independent residual checks. Converter controls and their response to interventions are not reproduced.
- **FACTS:** the three source devices have mode 0. No active FACTS control is claimed.
- **Controls:** transformer taps and switched shunts are fixed to the saved state; generator local voltage targets use saved local voltages. Remote regulation and control interactions are not reproduced.
- **Loads:** there are no active constant-current or constant-admittance load components in this selected case. The calculation does not validate the legacy importer's behavior on other cases.
- **Ideal ties:** the merge reproduces equal-voltage behavior; internal tie flows and their individual thermal limits are not recovered.

## What would clear the remaining gate

1. Obtain the source solver's settings, control configuration and higher-precision solved outputs; reproduce the base case with a separately verified importer or the source tool.
2. Reproduce HVDC and remote voltage controls, or agree explicit fixed-boundary/fixed-control scope with the model owner.
3. Resolve or explicitly establish the applicability of the source voltage limits at collector and auxiliary buses. Do not delete those limits or call violations safe because they already occur in the source.
4. Recover and check ideal-tie flows; enforce and report generator limits.
5. Validate each proposed action under the applicable contingency/security and operating rules. A static snapshot alone supplies no historical MWh denominator and no national curtailment-reduction percentage.

The reference-network demonstration can validate the application's workflow separately. It cannot transfer its success percentage to Ireland.

## Sources and provenance

- EirGrid public planning-model publication: https://cms.eirgrid.ie/all-island-ten-year-transmission-forecast-statement-2024
- Source archive: https://cms.eirgrid.ie/sites/default/files/publications/TYTFS2024_studyfiles.zip
- Selected file: `TYTFS2024_WP2024_V33.raw`; SHA-256 `006db9ce2ff20a7bf2a67ffbd9988735a1b3d3dc8abbd6309395e7139b66cb24`.
- Electranix, *E-TRAN User's Manual*, printed p. 79 for ideal branches and p. 128 for RAW precision and cancelling residuals: https://www.electranix.com/wp-content/uploads/2024/04/E-TRAN.pdf
- MATPOWER documented transformer importer: https://matpower.org/docs/ref/matpower7.1/lib/psse_convert_xfmr.html
- MATPOWER documented RAW converter: https://matpower.org/docs/ref/matpower7.1/lib/psse_convert.html

## Reproduce

Install `irish_requirements.txt`. Run:

```sh
python irish_reproduce.py --raw /path/to/TYTFS2024_WP2024_V33.raw --output irish_diagnostic_output
```

The script is locked to the selected source file hash. It writes diagnostics and a merged mathematical model into the requested output folder. It does not modify the original RAW file, execute grid controls or authorize any operational action. Use `irish_diagnosis.json` for exact machine-readable values.
