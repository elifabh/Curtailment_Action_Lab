# Curtailment Action Lab: presentation script

Use slides 1–7 for the pitch. Slide 8 is a technical appendix for questions. The target duration is about 6 minutes 20 seconds including a 75-second software demonstration. Rehearse against the event's final presentation instructions.

## Slide 1 — Curtailment Action Lab (0:00–0:35)

“A grid planner has available wind, a network restriction and several possible actions. Which option is worth investigating, and what evidence supports it?

Curtailment Action Lab compares permitted network scenarios and records the checks behind each result. Today I will show a reproducible reference-network example and distinguish it clearly from our Irish planning-model diagnostic.”

## Slide 2 — The planning decision (0:35–1:15)

“Our user is a transmission planning or outage-planning engineer. We hold available wind, consumer demand and equipment limits constant, then compare network configurations.

The operator must decide which alternatives are actually permitted. Our software does not authorise switching or assume that maintenance can simply disappear.

Topology optimisation already exists. Our contribution is a working workflow that connects requested comparisons to numerical calculations and visible verification evidence.”

## Slide 3 — Controlled reference-network comparison (1:15–2:10)

“This example uses a public nine-bus reference network. We add a hypothetical 200-megawatt wind source and keep consumer demand at 315 megawatts.

With line 6–7 unavailable, the model accepts about 140 megawatts of wind and curtails about 60. With every line available, it accepts approximately 200 megawatts.

That is about 60 megawatts more accepted wind in this constructed snapshot. Both solutions pass the declared numerical checks. We preserve the source equipment limits and account for power balance and losses.

This is a reference-network result. It is not a measurement of Irish curtailment, a national percentage or an approved switching instruction.”

## Slide 4 — Working interface and demo (2:10–3:25)

Say: “Here is the calculation in the application.”

1. Open **Scenario Lab** with the **Reference network** profile.
2. Keep available wind at **200 MW**, demand multiplier **1.0**, and select **All lines available**.
3. Run the comparison. Point to accepted and curtailed wind, then the numerical checks.
4. Change available wind to **50 MW** and rerun. Explain: “Here the two options give essentially the same wind acceptance. The tool does not claim a benefit in every condition.”
5. Open **Evidence**. Show source information and the verification report.
6. If time permits, select the **Irish planning diagnostic** profile. Say: “This profile has unresolved model issues. The application keeps that status visible and does not label its apparent opportunity as a validated Irish saving.”
7. Return to the presentation.

Use the endpoint and controls supplied in the final package. If a run displays a stored replay rather than a fresh computation, say so. Do not describe a screenshot or stored replay as a live calculation.

## Slide 5 — AI proposes the next calculation (3:25–4:15)

“The AI interface gives the model a restricted tool: evaluate an allowed candidate. The numerical engine computes the physical result, and a separate verifier checks it.

The runner records tool calls and rejects malformed, unknown or duplicate requests. Numerical summaries come from the calculation records.

The Azure integration is implemented. We had no Azure credentials for this delivery, so live AI benefit remains unmeasured. The offline deterministic search is labelled explicitly.

Our measured four-call deterministic baseline already matches exhaustive search at the default condition. AI could support natural-language investigation, but additional physical benefit is not demonstrated. We will compare it at the same candidate-evaluation budget.”

If you have subsequently run Azure successfully, replace this paragraph only with the exact verified outcome and dated evaluation report. An API connection alone does not demonstrate better search performance.

## Slide 6 — Evidence and scope (4:15–5:05)

“We separated model verification from interface success.

All 21 predefined reference confirmation cases passed the 13 listed checks per case. The checker independently reconstructs branch powers and bus balances. A separate power-flow solution agrees with the computed state.

The low-wind control gives essentially zero benefit, as expected. The package includes negative controls as well as favourable cases.

The Irish planning reconstruction remains diagnostic. Neither the reference result nor numerical convergence establishes N−1 security, dynamic stability or field performance.”

## Slide 7 — Bounded operator pilot (5:05–6:20)

“The next adoption step is a bounded study on one verified network area.

The operator supplies the network case, permitted alternatives, wind and load assumptions, and required security checks. We compare accepted wind against the existing plan and report failed alternatives. We also measure engineering review time and whether AI improves the workflow.

A scoped planning study or software pilot is a possible commercial offer. We have not yet validated willingness to pay.

The deliverable is an auditable comparison that a planner can reproduce and challenge. Today's demonstrated outcome is a verified constructed scenario, with a clear path to testing the same workflow on an operator's data.”

## Exact numerical record

Source: `validation/reference_validation_results.json`, `default_comparison`.

| Quantity | Line 6–7 unavailable | All lines available |
|---|---:|---:|
| Available hypothetical wind | 200 MW | 200 MW |
| Consumer demand | 315 MW | 315 MW |
| Accepted wind | 139.9999838224 MW | 199.9999999903 MW |
| Curtailed wind | 60.0000161776 MW | Approximately 0 MW |

The rounded difference is **60.0 MW**. It concerns this snapshot. It does not establish MWh, annual savings, euros, carbon savings or a share of Irish curtailment.

## Before presenting

- Start the application and reproduce the default reference calculation.
- Open the low-wind control and Evidence page once, so that the sequence is familiar.
- Confirm whether Azure is connected. Keep the delivered disclosure if it is not.
- Keep the PPTX/PDF available as a fallback and show only tested functionality.
- Do not use the earlier Irish “37 MW” as a validated impact claim.

## Sources

- Numerical protocol and report in the package's `validation` directory.
- Public source network: https://github.com/rwl/PYPOWER/blob/master/pypower/case9.py
- AC optimisation: https://matpower.app/manual/matpower/StandardACOPF.html
- Existing topology work: https://www.neso.energy/about/innovation/our-innovation-projects/network-topology-optimisation
- Irish planning study: https://cms.eirgrid.ie/all-island-ten-year-transmission-forecast-statement-2024
- Azure function calling: https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/function-calling
