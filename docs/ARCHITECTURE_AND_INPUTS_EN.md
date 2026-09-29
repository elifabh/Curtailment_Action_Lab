# Architecture and input boundary

## Implemented application

| Layer | Implementation | Boundary |
|---|---|---|
| UI | English HTML/CSS/JavaScript, four tabs, offline bundle | No external assets or secret keys |
| Local API | Python standard-library HTTP server on loopback | Intended for one local demonstrator, not public hosting |
| Irish study | Versioned checked numerical records, strict scenario lookup | No unrecorded result substitution |
| Fresh Irish extension | Separate worker process; bounded new scenarios; twelve-interval profile experiments | Optional dependencies; conditional fixed-control planning model; no annual saving claim |
| Physical reproduction | RAW conversion, PYPOWER AC solution, direct source equations, tie recovery | Conditional steady-state model, not operating clearance |
| Reference engine | Local nine-bus AC OPF and independent checks | Separate public reference experiment |
| Value service | Validated explicit duration/value/cost assumptions | No observed tariffs, chronology or customer profit inferred |
| AI | Azure OpenAI v1 function calling, fixed conditions, allowlisted candidate IDs | Saved-record tools; earlier user-supplied live trace; no new Azure test or automatic call to the fresh Irish extension |
| Observability | Record IDs, source/protocol hashes, rejected calls, checks, JSON exports | No secret logging or claimed production monitoring service |

`GET /api/study` returns the delivered study. `POST /api/value` accepts a recorded `case_id`, `duration_hours`, `wind_value_EUR_MWh`, `activation_premium_EUR_MWh` and `other_event_cost_EUR`. Optional inputs are `flex_energy_limit_MWh` and `displaced_generation_tCO2_MWh`. Booleans, non-finite numbers and unknown fields are rejected. A failed physical comparison cannot be monetised. Changed inputs invalidate the prior displayed value.

The deployment delivered is an extracted local application, not a Terraform-managed production platform. No model training is needed for the main physical study. Azure credentials are optional until the live AI stage. A production adapter would replace file-based scenario inputs while preserving the same checks and result provenance.

## Data actually delivered

| Data | Source or construction | What it establishes |
|---|---|---|
| Winter Peak 2024 electrical network | Public EirGrid TYTFS2024 RAW files, retained hash/disclaimer | Source topology and published numerical parameters |
| Prepared controls | Explicit tap/shunt experiment records | Reproducible mathematical starting assumptions |
| Additional wind | Hypothetical injection at bus 1341 | Controlled availability experiment, not measured wasted wind |
| Flexible demand | Hypothetical amounts at identified network buses | Locational comparison, not actual customer flexibility |
| Price and event duration | User-entered assumptions only | Conditional value, not market history |
| Checks and accepted wind | Actual local calculations and separate equation checks | Scoped model results |

The national forecast appendix remains separate research. It is not used to claim that these hypothetical site loads coincide with observed Irish dispatch-down events.

## Inputs needed for a real use case

The operator must supply a reviewed network state, usable ratings, controller/HVDC settings, permitted actions and required security checks. The customer or aggregator supplies a verified connection ID, time-stamped demand, available power and energy, deadlines/reserve requirements, rebound and activation costs. The producer supplies time-matched available wind and dispatch-down records. Metered baseline and intervention data are needed for a field claim.

A data centre can participate only through a verified flexibility envelope that protects its workload and reserve obligations. A graph node is not evidence that a real 20 MW asset exists there. These are production/pilot inputs, not extra requirements asserted for the hackathon demonstration.
