# UI checks and rendered-browser verification

The local interface is tested separately from the power-system calculations. The v5 retained DOM/HTTP run passed 40 flow checks, including the Irish portfolio, 60-condition explorer, positive/negative conditional value, energy blocking, exports and offline replay. See `validation/ui_checks.json` for the actual result and its scope. An additional 38 offer/PDF DOM flows passed, recorded in `validation/decision_dom_report.json`. All 288 Python/JavaScript decision fixtures agreed. Visual rendering remains unverified in this environment.

## Run the optional browser test

From the extracted project directory, with Python and Node.js installed:

```sh
python -m pip install -r requirements.txt
npm install --no-save playwright
npx playwright install chromium
node tests/browser_smoke.js
```

The test starts and stops its own local Python server on port 8877. It does not call Azure. It intentionally clears Azure credentials in the child server so the unavailable-AI state is tested.

It exercises the four tabs, comparison, invalid wind input, sensitivity, deterministic search, evidence export, presentation mode, offline HTML, and desktop/mobile page overflow. The `browser-qa-results` directory receives screenshots, exported JSON, and `browser_report.json`. Inspect the screenshots before presenting.

Optional environment variables: `PYTHON` selects the Python executable, `QA_PORT` changes the port, and `QA_OUTPUT_DIR` changes the output directory.

## What the build environment could verify

The build environment could execute JavaScript in a DOM implementation and call the real local HTTP API. Such checks verify application behavior and returned data. They do **not** establish browser rendering, visual appearance, responsive layout, or native dialog/download behavior.

The installed Playwright library was found. An official Chrome for Testing executable was downloaded and its ZIP integrity checked, but rendering terminated with `SIGTRAP` before a page opened. This Linux execution environment does not expose `/proc/self/exe` or `/proc/self/status`. No rendered screenshot or successful real-browser test is claimed from that environment.

DOM testing emulates the dialog API and captures export blobs. A successful DOM report must not be described as a successful Playwright run.

## Reproduce the DOM-only checks

With Node.js and the Python simulator installed, run `npm install --no-save jsdom@30.1.1` and `node tests/dom_smoke.js`, then `node tests/decision_dom.js`. This is a separate non-visual check. The Python launcher can be selected through `PYTHON`.


The updated optional Playwright script covers the offer view and withdrawal on desktop/offline plus mobile overflow. It has not been executed successfully here; inspect the real page during rehearsal. The inherited Chromium launch failure is in `validation/browser_environment.json`.


Readability update: 16 additional DOM/HTTP checks cover example labels, chart numbers, all readable report types, selected-profile benchmark exports, stale results, model switching and HTML escaping. Captured Azure replies are test fixtures. These tests make no live provider calls and do not verify real browser rendering. See `validation/readable_reports.json`.
