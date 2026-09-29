# Judge questions and concise answers

## What have you demonstrated?

A reproducible comparison on a public reference network with an explicitly hypothetical wind source. The numerical evidence concerns the stated scenario and the listed steady-state checks. The result does not establish a national or field saving. Use the exact numbers in the delivered numerical report and presentation.

## Why should a grid operator care?

The proposed workflow keeps candidate calculations, failed checks and source assumptions together for engineering review. An operator pilot must measure whether that reduces review effort or identifies useful options compared with the existing process. We have not yet measured that business benefit.

## Is topology optimisation new?

No. Established tools and research already investigate it. This prototype combines a restricted AI tool interface, a numerical comparison engine and inspectable evidence. We claim implementation and test results, not first invention of topology optimisation.

## Why is AI needed when there are only seven options?

It is not necessary to use AI to exhaust seven options. At the default condition, the measured four-call deterministic baseline already matches the best accepted wind across all seven allowed options within numerical tolerance. The AI can translate an engineer's request into allowed tool calls, but any search advantage needs measurement under the same evaluation budget. We will not claim superiority without those results.

## Is the AI really connected to Microsoft?

The code implements an Azure OpenAI tool-calling integration. Credentials were absent during delivery, so the package has no live Azure benchmark result. Offline manual search is explicitly labelled. Once the event provides an eligible deployment, the supplied evaluation can test the real connection and compare its results.

## Can the AI invent a line rating or a more favourable result?

The tool schema and deterministic checks restrict candidate identifiers and preserve selected wind/load conditions. The solver computes physical quantities. The application forms its numerical summary from tool-returned records. Unknown, duplicate and malformed tool requests are rejected. These controls limit the interface. They do not prove a language model can never make a misleading statement elsewhere.

## How do you know the solver result is correct?

The independent checker reconstructs branch complex powers and bus balances, then checks source limits and generator bounds. A second implementation solves the power-flow equations and compares voltage magnitude and angle. The package records tolerances and case-by-case results. Agreement validates the numerical model under these equations, not the real network or global optimality.

## Why does the Irish model remain diagnostic?

The public planning case includes control and conversion details that the present reconstruction does not fully reproduce. The delivery includes the diagnosis and failed checks. We do not label its apparent additional wind as validated curtailment savings.

## How much Irish curtailment does this remove?

We do not know. The constructed reference-network comparison cannot establish that percentage. An Irish claim needs a verified model, corresponding operating conditions and approved actions, followed by appropriate validation.

## Why not simply leave every line in service?

Real maintenance and fault recovery can make that impossible. The all-lines-available case is a useful reference. The alternative outage cases are hypothetical allowed comparisons, not evidence that maintenance activities are interchangeable. An operator must define realistic availability windows and restrictions.

## Does your result prove the action is safe?

It proves only that the numerical state meets the checks recorded for that run. N−1 security, transient and frequency stability, protection coordination, switching sequences and operator approval are outside this prototype's validation.

## Is the result in MW or MWh?

MW, because the main comparison is a snapshot. A duration or time series is required to calculate MWh. Neither annual energy savings nor revenue follows from the snapshot alone.

## Is your optimisation cost a euro saving?

No. The reference model uses its conventional generator cost coefficients plus a synthetic curtailment preference. We report these as objective units. A commercial calculation needs real tariffs, settlements, switching and maintenance costs.

## Can you deploy it today?

The local prototype runs as software. Operational deployment needs a verified operator model, approved candidate actions, additional security assessments, data integration, cybersecurity review and pilot evaluation. The tool currently supports planning analysis and does not control equipment.

## What would you ask a sponsor to provide?

A verified anonymised network area, permitted candidate configurations, wind and load conditions, relevant equipment limits and the required operational checks. For AI evaluation, an Azure deployment and evaluation budget. The pilot should also include the current planning baseline and a way to measure engineering review time.

## What is the commercial model?

A scoped planning study or software pilot is a proposed first offer. A subscription or integration licence would depend on pilot value and the customer's procurement requirements. Willingness to pay has not been tested.

## Does this eliminate all curtailment?

No. It addresses the network limitation represented in the chosen model. System-wide stability limits, market curtailment and other causes need different data and controls.
