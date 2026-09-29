# Curtailment Action Lab — v4

A local decision-support prototype for a grid planner, or an aggregator working with one: **where would the same flexible demand allow more wind, under the stated network conditions, and what activation premium could the assumed benefit support?**

## Open the product

Extract the whole ZIP and open **`OPEN_DEMO.html`**. No account, installation or internet is needed. This is a replay of checked numerical records, with a local conditional-value calculator. It makes no AI calls or new power-flow calculations.

The default model is the Irish conditional planning study. In **Scenario Lab**, use **Single comparison** for the original pair or **Robustness & value** for the extended experiment. Personal Turkish instructions: `START_HERE_TR.md`. All product content is English.

For the local HTTP application, use Python 3.12 and `START_LOCAL.bat` on Windows or `bash START_LOCAL.sh` on macOS/Linux. Open http://127.0.0.1:8765. The recorded Irish study, economic calculator and optional Azure adapter need only standard-library Python. To calculate new nine-bus reference scenarios, first run `INSTALL_SIMULATOR.bat` or `bash INSTALL_SIMULATOR.sh`; installation downloads the pinned scientific dependencies.

## What v4 adds

- **60 paired conditions:** six available-wind ceilings, five flexible-load sizes and two line states. Both locations serve the same total demand within each pair. Cases reuse checked curve points; they are not 60 field trials or independent operating days.
- **Eight connection points:** selected by a declared network-graph rule before their outcomes. Compared with the existing location, the nearest-location rule and equal allocation across the candidates.
- **Demand stress checks:** the prepared model is also tested at ±1% source demand. Unsupported comparisons stay visible.
- **Conditional commercial calculation:** enter duration, extra wind value, activation premium and costs. Negative results remain negative; an insufficient entered energy envelope blocks the illustration. No real prices are invented.
- **Measured calculation workload:** actual power-flow count, end-to-end time, evaluation timing and memory, separated from fast stored-result retrieval.
- **An explicit novelty review:** prior papers and existing commercial products are distinguished from this prototype's contribution.
- **Expanded evidence and export:** source/protocol hashes, all scenario outcomes, failures, assumptions and comparison data.

Exact results are in `evidence_v4/FINDINGS_EN.md` and `evidence_v4/study_summary.json`. Current completion status: `VALIDATION_STATUS_EN.md` and `docs/CRITERIA_STATUS_EN.md`.

## Read the headline correctly

At the default point, the same hypothetical 20 MW load is compared at Cruiserath (bus 2072) and Binbane (bus 1341). Best tested wind acceptance rises from **47.65625 to 61.71875 MW**, a **14.0625 MW** difference in the prepared model. The eight-candidate screen also finds CATH_FALL (bus 1701) at **68.359375 MW**, or **20.703125 MW** above Cruiserath. This is **6.640625 MW** above the nearest-point rule. Use **Inspect best checked location** to open that pair. The broader study tests when the location effect holds and when it does not.

The public source is EirGrid's Winter Peak 2024 planning network. Additional wind and flexible assets are scenario assumptions. Preparation includes **60 source-bounded tap adjustments and one hypothetical disconnection of a locked 25 Mvar capacitor**. The original file remains a diagnostic; it is not silently declared a verified operating state. Source limits are not widened. Some source ratings are zero or placeholder-like, controls/HVDC are simplified, and operating permissions are unconfirmed.

**MW is snapshot power.** MWh and EUR appear only when you enter explicit duration and commercial assumptions. The calculator does not prove a continuous feasible schedule, battery SoC, data-centre SLA, measured avoided curtailment, annual savings or customer profit. The controlled experiment does not establish nationwide Irish savings. No device or switching command is executed.

## Four tabs

| Tab | Purpose |
|---|---|
| Overview | Product purpose, available model profiles and scope. |
| Scenario Lab | Single paired comparison, extended conditions, location baselines and conditional economics. |
| AI Analyst | Bounded Azure tool use when connected; separately labelled deterministic record search without Azure. |
| Evidence | Sources, preparation, checks, complete outcomes and downloadable records. |

The separate public nine-bus reference profile supports local AC optimisation. Its approximately 60 MW line-availability effect is a different constructed experiment; it is not an Irish result. Reference source validation and 21 confirmation scenarios are retained.

## Microsoft AI: connect after access arrives

1. Copy `.env.example` to `.env`.
2. Enter the Azure resource endpoint, API key and deployed model name. The deployment must support the implemented Azure OpenAI v1 Chat Completions function-calling contract.
3. Restart the local server and run a small request in AI Analyst.
4. Inspect the actual tool trace and run the live comparison:

```sh
python evaluation/conditional_agent.py --run-live --budget 4
```

This command consumes Azure quota. Keys stay on the local backend and are excluded from the packaged ZIP. No live Azure evaluation has been run in this delivery. Fixture tests check our integration rules, not model quality. Event-provided authentication/model details may require adapter configuration.

For the Irish profile, AI retrieves verified stored alternatives. It does not rerun the Irish solver. The benchmark compares the same allowed candidate-call budget with a deterministic rule and a separately enumerated finite reference. **No AI improvement in physical wind acceptance is established.** The proposed AI benefit is guided investigation with inspectable evidence. See `docs/AI_WORKFLOW.md`.

## Reproduce

```sh
# Main application contracts (scientific reference dependencies required)
python -m unittest discover -s tests -p 'test_*.py' -v
# Stored Irish candidate baseline; no Azure request
python evaluation/conditional_agent.py --budget 4
# Regenerate recorded candidate views and the standalone page
python scripts/build_conditional_records.py
python scripts/build_offline.py
```

For the physical v4 study, install `irish_audit/requirements.txt` and follow `evidence_v4/README.md`. Preserve the delivered results before an explicit new run. The complete study takes substantially longer than opening a stored result. The original numerical diagnosis and six corruption/verification checks remain in `irish_audit/`.

DOM/HTTP/offline flow checks are supplied in `tests/dom_smoke.js`; details are in `docs/BROWSER_QA.md`. Real rendered-browser verification could not run in this preparation environment. DOM success is not a visual-rendering claim. Launchers have not been executed on Windows or macOS.

## Scope and architecture

Vanilla HTML/CSS/JavaScript → localhost Python API → checked Irish record reader or nine-bus AC engine. The optional Azure agent uses the same strict candidate interface. `study_service.py` handles conditional economics. No external CDN, cloud database, training job or device-control integration is required for the demo.

Sources, versions and retained notices: `docs/THIRD_PARTY_NOTICES_EN.md`. Input contracts and future integration: `docs/ARCHITECTURE_AND_INPUTS_EN.md`. Commercial hypothesis and production inputs: `docs/VALUE_AND_ADOPTION_EN.md`.

**The external slide deck, PDF, pitch script and judge Q&A are retained from v2 and have not been updated for v4.** They are not current evidence. Presentation preparation is deferred as requested. The in-app three-step view uses the selected comparison.

This package completes a public-data conditional planning demonstration. Live Microsoft AI verification and current presentation preparation are deferred. A production deployment or field-saving claim requires separately verified network and customer inputs; those are not represented as hackathon prerequisites.
