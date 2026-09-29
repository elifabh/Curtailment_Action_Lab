# Prior work and the defensible product contribution

Reviewed 27 September 2026. This is a targeted comparison with primary sources, not an exhaustive patent or commercial-product search.

| Existing approach | What its published material establishes | Consequence for this project |
|---|---|---|
| Agbonaye et al., Renewable Energy, 2022 | A framework connects flexible demand, local constraints, wind curtailment, customer value and network hosting limits. | Neither consuming excess wind nor checking flexible-load network impact is a new scientific idea. We do not reuse that paper's savings as our results. |
| Piclo Flex | Its E-Distribuzione announcement describes acquiring and dispatching flexibility for local constraints. | A producer/consumer flexibility marketplace is already an established category. We do not claim to replace procurement or settlement. |
| GridBeyond / Microsoft customer story, August 2026 | Azure-based forecasting, asset optimisation, digital twins and energy-market services are deployed commercially. | AI plus forecasting, batteries or industrial flexibility is not by itself a novelty claim. Their reported commercial results are not our benchmark measurements. |
| Power-Flexible AI Data Centers, 2026 preprint | The authors describe grid-responsive computing and geographic workload shifting, with a reported small-cluster experiment. | Data-centre flexibility is plausible in particular implementations; it does not establish that a 20 MW facility exists or is movable at our Irish connection points. |

## What this prototype contributes

A reproducible planning workflow joins a public Irish network model, an explicit load-location decision, separate electrical-equation checks, simple comparator policies, rejection of unsupported cases, and a transparent value calculation. Each result retains its input conditions, failed checks and permitted claim scope. A bounded Azure interface can inspect the evidence when connected.

This is an implemented combination and a product hypothesis. It is **not proven globally unique**, a new power-flow algorithm, or an established commercial advantage. The customer-value hypothesis is less manual effort to screen and explain candidate connection-point flexibility. That human productivity benefit still needs a user study; software runtime alone cannot prove it.

## Comparator design

- Existing location: keep the same hypothetical flexible demand at Cruiserath.
- Nearest connection: choose the candidate with the fewest graph hops to the wind connection. This strong, simple rule may match the full screen.
- Equal allocation: distribute the same 20 MW among the eight declared hypothetical candidates, then run the same electrical checks.
- Location-blind selection: report the range and mean of the checked candidate outcomes. Report failed candidates separately; never count their wind as usable.
- Price-only: no observed, differentiated site tariffs were supplied. A common simultaneous wholesale price supplies no location ranking. No invented price-only performance advantage is claimed.

The exhaustive declared-candidate screen is only a finite reference. It is not a global optimum across all possible locations, capacities, control policies and network states. It also uses more calculations than a one-candidate rule; both call counts are disclosed.

## Sources

1. Agbonaye et al. (2022), DOI 10.1016/j.renene.2022.03.131: https://pure.ulster.ac.uk/en/publications/value-of-demand-flexibility-for-managing-wind-energy-constraint-a/
2. Piclo, E-Distribuzione local flexibility announcement: https://www.piclo.com/press-releases/piclo-to-deliver-italys-first-local-flexibility-market-with-e-distribuzione
3. Microsoft, GridBeyond customer story, 27 August 2026: https://www.microsoft.com/en/customers/story/27136-gridbeyond-azure
4. Williams et al., Power-Flexible AI Data Centers (preprint): https://arxiv.org/abs/2606.25098

Vendor statements establish what is publicly offered or described; we have not independently audited their platforms. Absence of a feature from a public page is not evidence that a competitor lacks it.


## v5 addition — 28 September 2026

The proposed contribution is the integrated offer-to-counterexample-to-withdrawal workflow. Robust optimisation, power-flow screening and LLM-assisted falsification are already prior art. In particular, [Large Language Models as Falsifiers for Cyber-Physical Systems](https://arxiv.org/abs/2609.20752) studies LLM falsification; it does not establish our performance or uniqueness. The eight-offer, seven-challenge catalogue is inexpensive to enumerate, so AI superiority must not be inferred from attaching a tool-calling agent. The live Microsoft comparison is still unrun.
