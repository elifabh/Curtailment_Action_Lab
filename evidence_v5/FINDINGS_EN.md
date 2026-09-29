# Findings — v5

There are 64 site–condition cells: 56 comparable and 8 blocked. The new physical rebuild required 288 power flows and 411.019 seconds in this environment; it is separate from rapid record queries. Existing exactly matching v4 records are reused with qualified references.

The nominal best tested candidate is bus 1701, with 20.703125 MW added wind relative to the existing location. Under half delivery, the paired result is 9.5703125 MW, not half the nominal number. At 50 MW available wind it is 2.34375 MW; at 25 MW and zero delivery it is zero. With −1% base demand it is 15.4296875 MW, and with the nominated line in service it is 16.2109375 MW. The +1% demand baseline is unverified, so that benefit is not calculated.

Default hypothetical economics (one hour, EUR50/MWh extra-wind value, EUR10/flexible MWh reservation premium, EUR500 budget) retain bus 1701 for nominal, half-delivery and lower-demand tests. Changing to the documented differentiated premiums switches to bus 2870. Requiring the unverified higher-demand condition withdraws the recommendation.

The separate 288-case authored decision grid yields 48 retain, 13 switch, 67 withdraw and 160 no-nominal-offer results. Of 74 nominal offers failing an extra required test, seven switch and 67 withdraw. Selected guarded offers have zero violations of their selected tests by construction. This is not a field/AI accuracy measure. Python and JavaScript parity is tested separately.

Limits: prepared static model, fixed controls and boundary assumptions, incomplete operational ratings/security, hypothetical offers, no probabilities or continuous schedule. Selection is among finite tested points; sub-0.5 MW ranking differences should not be presented as a robust physical advantage. No first-ever method, field saving, annual MWh, customer profit or live AI advantage is demonstrated.
