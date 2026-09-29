# Irish-model audit and conditional flexibility experiment

The audit repaired concrete calculation errors and produced a **conditional, numerically checked Irish planning-model experiment**. It did not reproduce every PSS/E control, validate an operational Irish dispatch, or measure avoided curtailment.

## What changed

1. **Source versions were checked.** The official archive contains both V33 and V35 exports. V35 includes solution settings, including `THRSHZ=0.0001`, but its saved state differs from V33: 1,876 voltage magnitudes, 54 generator reactive outputs and 26 switched-shunt states differ. V35 settings therefore cannot certify the V33 solution. V33 has 173 original voltage violations; V35 has 466. No better-looking version was silently substituted.
2. **Fixed-Q generation and Q limits were enforced.** Nineteen fixed-Q buses cease to act as independent voltage controllers; two further buses hit aggregate reactive limits in the baseline. The recalculated baseline has no generator P/Q limit violations under the stated numerical tolerances.
3. **Thermal-rating units were corrected.** The RAW header specifies current expressed as MVA at nominal voltage. The earlier apparent-power/rating calculation did not honor this convention. This audit uses terminal current for lines and the represented physical winding current for transformers. Original numerical ratings are preserved.
4. **Ideal ties were inspected.** Recovering flows gives 144 uniquely determined tree-edge flows. Four edges in cyclic groups use an explicit inverse-reactance allocation. All pass the supplied ratings in the selected states, but the cyclic split is not a unique measured result.
5. **A separate electrical check was implemented.** A direct text parser and winding-side voltage equations reproduce 2,507 converted branch/winding flows and nodal balances without using the legacy converted R/X/tap fields or PYPOWER's admittance builder. The selected states also retain the original bus/generator bounds and branch ratings.

## Original case versus prepared scenario

The original V33 source has voltage violations below 100 kV. Merely converging a solver cannot remove them or establish safety.

An exploratory, explicitly different scenario adjusts 60 two-winding transformer taps within the source's declared discrete settings and disconnects the 25 Mvar capacitor at bus 74564. This capacitor is locked in the source; its disconnection is an **assumed permitted planning action**, not a repaired parser field or an automatic source control. Aghada bus 10470 is the balancing generator. HVDC is an explicitly calibrated fixed boundary. Local generator voltage targets and remaining shunts are fixed.

| Experiment | Original-bus groups with voltage violations |
|---|---:|
| Q-limited source-tap reconstruction | 164 |
| Local tap adjustment targeting violating buses | 28 |
| Including supported remote targets and impedance corrections | 2 |
| Same tap scenario plus capacitor 74564 disconnected | 0 |

The 164 count is for merged model groups; the 173 source count is for original source buses. They have different denominators. The reduction in these counts is **not** a curtailment-reduction percentage.

A broader adjustment-to-all-control-bands experiment also ran and ended with 32 violations, including five at transmission voltage. Its unsuccessful result is retained. The diagnostic sequence was adaptive engineering investigation, not a preregistered statistical holdout.

## Controlled locational comparison

Both alternatives use the same prepared grid, line 1341–1701 unavailable, 200 MW hypothetical wind availability at bus 1341, 7,324.51 MW source consumer demand and a further hypothetical 20 MW flexible load at unity power factor. Only the flexible load's location changes.

| Quantity | Load at bus 2072, Cruiserath | Load at bus 1341, Binbane |
|---|---:|---:|
| Flexible demand served | 20 MW | 20 MW |
| Total consumer demand | 7,344.51 MW | 7,344.51 MW |
| Best tested wind acceptance | 47.65625 MW | 61.71875 MW |
| Hypothetical available wind not accepted | 152.34375 MW | 138.28125 MW |
| Implemented voltage, generator and rated-branch violations | 0 | 0 |

The near-wind alternative admits **14.0625 MW more hypothetical wind** in this experiment. Report this as approximately 14 MW. It is not 14 MWh, a national percentage, an observed dispatch-down event, or a demonstrated customer saving.

The search tested a 25 MW coarse grid over 0–200 MW and refined the last tested feasible interval to at most 0.25 MW. It reports tested passing points, not a global maximum. Some low-wind cases fail the balancing generator's P limit, so feasibility is not assumed to start at zero or to be globally monotonic. All 64 evaluations, including failures, are retained in `results/wind_screen.json`.

The topology-only comparison is much weaker here: 41.796875 versus 42.1875 MW best tested wind acceptance with no extra flexible load. This does not support the old 37 MW Irish claim. The earlier legacy comparison is retired from the application's calculation interface.

## Verification boundary

- Direct RAW checks pass for the selected states. The maximum branch-flow differences are below 1e-6 MVA, and grouped nodal residuals below 1e-4 MVA. Exact values and state hashes are in `results/conditional_flex_study.json`.
- Six mutation/verification tests check a valid state and deliberately corrupted voltage, ratings, generator limits and unaccounted injection. Test passes are software evidence, not additional physical experiments.
- Of 2,458 active retained branches, 92 have zero RATEA and 1,186 have RATEA at least 9,999. These values are preserved and disclosed; they do not establish real equipment capability. No limits were widened to get a pass.
- A separately developed VeraGrid import was attempted. Its fixed-control solve converged but did not reproduce the case and logged unsolved-island/import issues; the enabled-control solve did not converge. Neither is claimed as independent corroboration. Raw-parser comparison normalizes local/remote bus notation; it is distinct from electrical conversion.
- Pypowsybl could not initialize in this sandbox (`graal_create_isolate error: 32`). It supplied no verification result.
- No N-1/security, dynamic stability, protection, switching sequence, site SLA, tariff, temporal flexibility or actual operating permission was established.
- No real 20 MW data-centre or factory flexibility was supplied at either location. These are hypothetical connection-point loads, not invented customer records.

## Product decision

Retain **locational flexibility screening for a grid planner or an aggregator working with a planner** as the strongest newly supported candidate. Its useful question is: *where would a specified, available flexible load help under this network constraint?* A nationwide cheap-hour alert alone cannot answer that question.

The current product is a reproducible planning prototype. The application shows the verified stored pair; supplied scripts reproduce the calculations. The Azure agent can inspect the bounded records when configured. Deterministic inspection of two alternatives already finds the best result. No AI physical advantage is claimed.

A deployable operating product still needs verified asset envelopes and connection points, a reviewed operating network and ratings, approved action/control sets, security studies, and market/settlement treatment. Those are specific missing inputs and validations, not quantities that software can invent.

## Sources

- EirGrid official study: https://cms.eirgrid.ie/all-island-ten-year-transmission-forecast-statement-2024
- Official archive: https://cms.eirgrid.ie/sites/default/files/publications/TYTFS2024_studyfiles.zip
- Official report, transmission-study scope and indicative connection studies: https://cms.eirgrid.ie/sites/default/files/publications/All-Island-Ten-Year-Transmission-Forecast-Statement-2024_1.pdf
- Siemens PSS/E 33.4 Program Operation Manual, sections on rating units, ideal ties and transformer controls; public mirror: https://studylib.net/doc/27755134/pom
- MATPOWER's documented transformer conversion: https://matpower.org/docs/ref/matpower7.1/lib/psse_convert_xfmr.html
- Independent software source: https://veragrid.readthedocs.io/en/latest/_modules/VeraGridEngine/IO/raw/raw_to_veragrid.html

The supplied EirGrid disclaimer applies. Source hashes are in `results/source_audit.json`. Microsoft AI was not connected during this audit.
