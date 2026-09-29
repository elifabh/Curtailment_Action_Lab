# User value, assumptions and adoption

## The decision

The initial user is a network planner, or an aggregator working with a network planner. Before procuring or studying flexible demand, the user asks: **which available connection-point loads would help this wind constraint, by how much in the checked model, and at what maximum additional activation cost under stated values?**

This supports a planning or procurement decision. The demo does not relocate a physical factory, schedule a real data centre, settle a market trade or send switching instructions. The two-location comparison represents two alternative portfolios with equal total hypothetical flexible demand. Eight-location screening tests that same total requirement at several connection points.

## Inputs and outputs

| Input | Responsible source | Demo status |
|---|---|---|
| Network snapshot, component limits and allowed controls | Network owner / operator | Public EirGrid planning case with explicit prepared-state assumptions |
| Connection-point identifier | Network owner and facility | Real network identifiers; hypothetical flexible assets |
| Flexible power, event energy, deadlines and service constraints | Facility or aggregator | Scenario inputs; no actual customer envelope supplied |
| Wind availability and expected duration | Generator / forecasting process | Declared wind levels and user-entered event duration |
| Additional energy value and activation premium | Commercial owner / contractual terms | Explicit scenario values, not sourced Irish tariffs |

The output is a comparison record with accepted wind, equal-demand checks, failure reasons, conditional energy equivalents and a break-even activation premium. An engineer can export the record and reproduce its network calculation before using it in a reviewed study.

## Value calculation

For a checked pair, let dW be the extra accepted wind in MW, F the equal flexible load in MW, h the assumed hours, v the assumed value per additional MWh of wind, and c the extra activation cost per MWh of flexible demand relative to the baseline.

- Conditional extra wind energy = dW × h.
- Flexible energy used in either alternative = F × h.
- Gross scenario value = dW × h × v.
- Extra activation cost = F × h × c.
- Combined scenario surplus = gross value − extra activation cost − other entered event costs.
- Break-even premium = (gross value − other entered event costs) / (F × h), when that denominator is positive.

A negative value is retained and displayed. More wind acceptance does not guarantee a positive commercial outcome. Values are exogenous assumptions: the calculation does not predict how additional wind changes market prices. Revenue ownership, settlement, compensation for curtailed generation, taxes and unentered operating/capital costs are not established. Combined scenario surplus is **not booked customer profit**.

If an event-energy envelope is supplied, the calculator rejects a duration requiring more flexible energy than that envelope. This simple block-energy check does not model battery state of charge, cooling temperature, job deadlines, rebound, ramps or an entire operating day. The MW result becomes a conditional MWh illustration only while the assumed network, wind and facility conditions persist. It is never multiplied into a claimed annual saving without time-indexed evidence.

Other-generator displacement is available separately from extra wind; it accounts for the calculated change in losses. An optional emissions factor is a user assumption about that displaced generation, not a measured Irish marginal emissions factor.

## Data-centre example

A suitable facility would supply metered load, its network connection, deferrable job power and deadlines, service-level restrictions, cooling limits and any battery reserve policy. Only its genuinely available flexible portion belongs in the power envelope. The demo does not assume that a UPS can be freely emptied or that peak cooling demand can be deferred. The same input contract can describe an appropriately qualified industrial or storage asset.

## Commercial proposition to test

An initial offering would be a reproducible connection-point screening study or a planning-software module. The proposed buyer is a network planning/flexibility procurement team, potentially with an aggregator partner. This identifies a buyer and a decision; it does not establish willingness to pay, sales, savings or a signed pilot.

Real deployment additionally requires a reviewed current network, actual ratings and controls, verified asset envelopes, required contingency/stability studies, settlement treatment and a metered baseline. Those are deployment inputs outside this public-data hackathon demonstration. They are not silently labelled complete.
