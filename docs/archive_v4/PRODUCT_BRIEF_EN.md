# Curtailment Action Lab: where flexibility can help

A low price or national high-wind signal cannot establish that a particular customer's consumption relieves a particular network limit. This prototype supports a more specific decision: **which of the available connection points could accept flexible demand and permit more wind, and what extra activation premium could that conditional benefit support?**

## User and output

The intended user is a grid planner or an aggregator working with one. The output is a checked comparison and an inspectable event-value illustration, not a device command or electricity transaction. No direct private-wire connection is added or assumed. The customer's position in the network still matters.

The public Irish planning-model study compares equal flexible demand at different connections. It covers 60 paired conditions, eight connection candidates, simple location/allocation baselines and source-demand stress checks. Exact findings are in `evidence_v4/FINDINGS_EN.md`. Hypothetical assets do not imply that an actual factory or data centre has that flexibility.

## Why this prototype is useful to investigate

The workflow joins a numerical network outcome to the user's next decision. It shows when location matters, when the tested effect is negligible, when the model cannot support a comparison, and when entered commercial costs exceed the assumed benefit. Each result carries its inputs and checks. The contribution is the implemented, reproducible decision workflow; the underlying flexibility and power-system methods are established.

The prepared network uses declared tap/shunt changes and simplified controls. Existing equipment-rating limitations remain visible. All results are conditional snapshots. They do not certify switching actions, national savings or a chronological customer schedule.

## Commercial hypothesis

A first offer could be a fixed-scope flexibility-screening study or a software module within a planner/aggregator's existing workflow. A verified site envelope and an operator-reviewed model would replace the illustrative inputs. Willingness to pay and procurement adoption remain untested. The conditional value calculator does not substitute for a contract, tariff or metered pilot.

Microsoft AI is an optional investigation interface over bounded tools and recorded evidence. The calculations are deterministic. Live AI reliability and workflow value must be measured after credentials arrive; no physical optimisation advantage is claimed.

See `docs/VALUE_AND_ADOPTION_EN.md` for formulas and customer data, `docs/NOVELTY_AND_COMPARATORS_EN.md` for prior work, and `docs/ARCHITECTURE_AND_INPUTS_EN.md` for integration boundaries.
