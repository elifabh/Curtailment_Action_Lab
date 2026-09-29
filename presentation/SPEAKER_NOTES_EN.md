# Current English speaker notes — v5

## Slide 1

Our buyer is a grid planning team, or an aggregator working with one. We ask where a specified flexible demand could allow more wind, and which conditions would invalidate buying it. This is a public-data conditional planning prototype, not a deployed market or measured Irish saving.

## Slide 2

The prototype compares eight hypothetical offers reserving 20 MW, located at actual bus IDs in the public EirGrid planning model. A different location means selecting different eligible flexibility, not constructing a private wind cable or physically moving a business. Customer prices and availability are editable assumptions. Source: evidence_v4/results/candidate_selection.json; evidence_v5/PROTOCOL.json.

## Slide 3

Exact values: Cruiserath bus 2072: 47.65625 MW; Binbane bus 1341: 61.71875 MW; CATH_FALL bus 1701: 68.359375 MW. This is a best tested finite screen, not a global optimum or national curtailment percentage. Wind availability is 200 MW and the nominated line is out. Both members of each pair serve equal demand and pass the declared checks. Preparation assumes 60 source-bounded tap changes and one locked-capacitor disconnection; real ratings and operating permissions remain unverified. Sources: evidence_v4/study_summary.json; EirGrid TYTFS2024 Winter Peak RAW, https://cms.eirgrid.ie/all-island-ten-year-transmission-forecast-statement-2024.

## Slide 4

The 64-cell matrix covers eight sites and eight conditions: 56 comparable pairs and 8 blocked. Demand-higher cells are blocked because the baseline does not have a passing tested operating point under the fixed control scope. This is not proof that the actual Irish grid cannot operate at that demand. Eighteen new physical curves required 288 power flows in this run. Source: evidence_v5/results/challenge_matrix.json.

## Slide 5

Default illustration: EUR500 budget; 1 hour; EUR50/MWh value of extra wind; all premiums EUR10 per flexible MWh; 20 MWh offered energy; nominal, half delivery and lower demand required. CATH_FALL remains selected; minimum gain across required tests is 9.5703125 MW. Cost is a full 20 MW reservation even for partial delivery. Add the higher-demand test to show withdrawal. Use the differentiated-price example in DEMO_SCRIPT_EN.md to show switching. Energy-times-price is a constant-snapshot illustration, not a verified one-hour schedule or customer profit.

## Slide 6

Of all 288 cases: 48 retain, 13 switch, 67 withdraw, 160 have no eligible nominal offer. Of the 74 cases where the nominal offer violates a required condition, seven switch and 67 withdraw. Six other switches come from maximising the worst tested gain rather than nominal gain. No retained selected offer violates its chosen requirements in these fixtures; that is an enforced property, not independent predictive success. Sources: evaluation/decision_benchmark.json, evaluation/decision_parity_fixtures.json.

## Slide 7

We make no claim that AI beats the fixed rule or creates more wind acceptance. The user request is interpreted through an allowlisted tool test_offer_scenario. The provider cannot send a physical action or override the numerical record. An identical eight-record nominal selection precedes each search; audit budgets count subsequent condition reads. Once credentials arrive, run python evaluation/decision_benchmark.py --run-live and inspect the actual trace. Sources: ai/challenge_agent.py; evaluation/decision_benchmark.py.

## Slide 8

Fit hypotheses, not partner commitments: ESB Networks can assess location-sensitive flexibility; SSE and other asset owners can evaluate flexible assets against constraints; Hitachi Energy can see an evidence-export planning workflow alongside existing market/network tooling; Microsoft can evaluate bounded tool use; WindEurope and Wind Energy Ireland can review repeatability. Existing commercial software already does power-flow, curtailment and flexibility modelling. Our proposed differentiation is the integrated offer, counterexample, withdrawal and data-priority workflow; no first-ever algorithm claim. Actual production needs current reviewed network data, permitted controls and N-1/dynamic checks, customer telemetry/SLA/SoC and verified commercial terms. Sources: docs/NOVELTY_AND_COMPARATORS_EN.md; docs/SPONSOR_FIT_EN.md.
