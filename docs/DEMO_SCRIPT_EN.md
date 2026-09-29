# Rehearsal path — v5

## Retain (about 45 seconds)

Open `OPEN_DEMO.html` → Scenario Lab → Offer decisions. Keep defaults and run. Explain: “We compare hypothetical offers at eight actual network locations. The best nominal site adds 20.70 MW in the prepared model. Requiring half delivery and slightly lower demand reduces the minimum tested gain to 9.57 MW.” Costs and duration are assumptions.

## Switch (about 45 seconds)

Keep default budget, duration, wind value and required tests. Enter these illustrative premiums, in EUR/flexible MWh:

| Bus | Premium |
|---|---:|
| 1341 | 5 |
| 2072 | 0 |
| 1701 | 25 |
| 5191 | 7 |
| 1571 | 9 |
| 1761 | 14 |
| 1981 | 12 |
| 2870 | 18 |

Run again. Nominal choice: 1701. After the required tests: **2870**, with minimum tested gain **9.5703125 MW** and assumed minimum surplus **EUR118.515625**. Bus 1701 no longer meets the nonnegative surplus requirement under half delivery. None of these premiums are real quotations.

## Withdraw (about 30 seconds)

Select the `Source demand 1% higher` condition as required. Run again. The prepared fixed-control baseline is unverified, so all candidate comparisons for that condition are blocked. The recommendation is withdrawn and demand/dispatch review becomes a priority. Do not call this a forecast of real grid failure.

## Show evidence (about 30 seconds)

Open the all-offer table or export JSON. Point to source hashes and physical record IDs. The physical study has 64 cells; the policy benchmark has 288 authored input cases; the fresh physical rebuild used 288 power-flow evaluations. These are three distinct counts.

## AI and slides

Without credentials show the labelled rule-based audit. With working Azure use the Microsoft AI audit, then inspect actual records. Do not describe a deterministic result as an AI run. Presentation opens the current PDF. Use `presentation/DESIGN_BRIEF_EN.md` to redesign it elsewhere without changing the claims.
