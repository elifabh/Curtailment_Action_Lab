# Curtailment Action Lab

**Find where flexible demand could make room for more wind — and test when the offer stops making sense.**

A planning decision-support prototype developed for Hack the Climate 2026.

## The problem

Network bottlenecks can prevent available wind generation from reaching consumers. The location of flexible demand matters: the same additional demand can produce different outcomes at different connection points.

Curtailment Action Lab compares those locations and makes the assumptions behind a recommendation visible.

## What the application does

- Compares hypothetical flexibility offers using recorded grid-model results.
- Reports KEEP, SWITCH, WITHDRAW, or NO OFFER against declared requirements.
- Uses Microsoft AI to choose recorded conditions to investigate.
- Provides a rule-based audit for comparison at the same maximum record-read budget.
- Runs fresh Irish AC power-flow comparisons through a separate calculation engine.
- Exports readable reports and machine-readable JSON evidence.

The AI chooses which evidence to inspect. Numerical checks and decision rules remain authoritative.

## Run locally

Python 3.11 or newer is required; development testing used Python 3.12.

On Windows, run these files in order, waiting for each installation to finish:

1. `INSTALL_SIMULATOR.bat`
2. `INSTALL_IRISH_EXTENSION.bat`
3. `START_LOCAL.bat`

Open http://127.0.0.1:8765 and keep the server window open.


## Configure Microsoft AI

Copy `.env.example` to `.env` and enter your Azure settings:

```dotenv
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
```

Restart the server after changing these settings. Never commit `.env` or API keys.

Run `CHECK_DEMO.bat` to check the demo files, recorded decisions, calculation dependencies and a live Azure audit. The live check consumes Azure quota; it does not run a fresh power flow.

## Demo workflow

1. Open **Scenario Lab → Offer decisions** and compare the default offers.
2. Inspect the retained offer at **Example site C / bus 1701**.
3. Run **Microsoft AI audit** with a maximum of four recorded conditions.
4. Export the decision JSON before changing assumptions.
5. Make **No flexible load delivered** a required condition and compare again.
6. Open **Fresh Irish calculations**, enter a new scenario and run the calculation.
7. Download its readable report and calculation JSON.

A record budget is an upper limit: the AI may inspect fewer records.

## Example model result

In the prepared planning snapshot, placing the same hypothetical 20 MW demand at the best tested candidate allows **20.703125 MW more wind** than at the reference location.

This is a conditional model comparison, not measured field savings or an estimate of Ireland-wide impact.

## Evidence and limitations

The Irish study uses EirGrid's Winter Peak 2024 planning model, with documented preparation assumptions. Flexibility offers and commercial values are hypothetical.

The AI audit reads saved evidence; it does not run new power flows. Fresh calculations are performed by the separate numerical engine.

MW results describe power in a scenario. Energy and financial estimates depend on declared duration and value assumptions. The application does not purchase flexibility, control equipment, or grant operating permission.

Further details:

- [Irish calculation extension](docs/EXTENSION_EN.md)
- [Recorded study findings](evidence_v5/FINDINGS_EN.md)
- [Validation status](VALIDATION_STATUS_EN.md)

## Reproduce checks

After installing the calculation dependencies:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/verify_decision_records.py
```
