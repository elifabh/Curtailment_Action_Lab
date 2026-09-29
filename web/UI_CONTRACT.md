# Frontend contract

The UI is vanilla HTML/CSS/JavaScript, English, with no external fonts, CDNs or package manager dependencies. The server serves `/static/style.css` `/static/app.js` and `/static/study.js`.

## Pages and controls

- Overview: public/reference profiles and workflow.
- Scenario Lab: paired calculation, comparison metrics, engineering checks, wind sensitivity, assumptions and limits.
- AI Analyst: optional Azure agent and separately labelled deterministic search; fixed wind/demand conditions, budget, returned tool trail, errors and evidence.
- Evidence: sources, model profiles, assumptions, limitations and complete JSON export.
- Present: three slides generated from the current returned result; no hard-coded result values.

Model changes synchronize between Scenario Lab and AI Analyst. Changed inputs mark previous results stale. Requests are finite values within configured bounds and allowed action IDs; backend remains authoritative. All API strings are inserted with `textContent`, not interpreted as HTML. Only HTTP(S) source links are enabled.

## Endpoints

`GET /api/config`:

```json
{
  "profiles": [{
    "id": "reference_9bus", "name": "Reference network", "description": "…",
    "available": true, "validation_status": "pending",
    "actions": [{"id": "all_in_service", "name": "All lines in service", "description": "…"}],
    "limits": {"wind_mw": {"min": 0, "max": 240, "step": 10}, "load_scale": {"min": 0.85, "max": 1.15, "step": 0.05}},
    "default_request": {"profile": "reference_9bus", "wind_mw": 200, "load_scale": 1, "action_id": "all_in_service"},
    "assumptions": [], "limitations": [], "provenance": []
  }],
  "default_request": {}, "sources": [],
  "ai": {"enabled": false, "status": "not_configured", "description": "…"},
  "runtime": {"available": true, "message": "…"}
}
```

`POST /api/evaluate` and `/api/sensitivity` send exactly `profile`, `wind_mw`, `load_scale`, `action_id`.

Evaluate response:

```json
{
  "request": {}, "summary": "…", "status": "…",
  "metrics": [{"key":"accepted_wind_mw","label":"Accepted wind","baseline":null,"selected":null,"delta":null,"unit":"MW"}],
  "checks": [{"id":"…","label":"…","passed":null,"detail":"…"}],
  "assumptions": [], "limitations": [], "provenance": []
}
```

Numbers above are deliberately omitted; actual figures come only from the calculator. Missing values render as `Not reported`.

Sensitivity response: `{rows:[{wind_mw,baseline,selected,delta,status}],metric_label,unit,summary}`. The UI renders an SVG line chart and an exact-value table. It does not interpolate new solver results or extrapolate.

`POST /api/agent` and `/api/search` send `{profile,wind_mw,load_scale,action_id,prompt,budget}`. Budget is an integer 1–8. The UI never treats deterministic search as an AI run. AI is disabled unless `config.ai.enabled` is true or its status is `configured`, `ready` or `available`, and never enabled in offline mode.

Response: `{summary,status,tool_trace:[{tool,arguments,result,status,duration_ms}],budget,used_calls,best_request,best_result,errors}`. A candidate-only `best_result` is not a paired comparison; inspecting it starts a separately requested paired `/api/evaluate`.

`GET /api/evidence` and `GET /api/evaluation` populate readable panels and full downloadable payloads. The UI shows no AI-superiority claim from merely configured credentials.

## Recorded offline mode

Before this script, define `window.ACTIONLAB_DATA` containing `{config,evidence,evaluation,evaluate,sensitivity,search}`. The last three fields are arrays of `{request,response}`. Matching uses profile, wind, demand and action (plus budget for search), ignoring prompt text for deterministic search. Missing recordings produce an explicit message; there is no fabricated fallback or AI run. The page persistently displays `Recorded demo mode`.

## Keyboard and small screens

Tab keys and arrow/Home/End keys navigate the tablist. The modal supports left/right arrows and Escape; buttons support keyboard activation. Profile and scenario controls use native form validation. Responsive CSS covers narrow mobile layouts; diagrams and bars have textual counterparts. Reduced motion is respected.

## Validation performed by frontend owner

`node --check web/app.js` passed. Rendering and end-to-end checks are owned by the integration/QA task; do not infer pixel validation from syntax checks.

## Extended recorded study (v4)

Scenario Lab has two subviews within the same main tab: Single comparison and Robustness & value. `GET /api/study` supplies 60 exact paired conditions, the eight-candidate portfolio, explicit baselines and runtime. Unrecorded settings are not interpolated into numerical claims. The best-candidate button loads the exact permitted single-comparison request.

`POST /api/value` uses the recorded case ID plus explicit duration and commercial assumptions. Required and optional fields are documented in `docs/ARCHITECTURE_AND_INPUTS_EN.md`. Failed physical pairs and insufficient energy envelopes are blocked. Negative values remain negative. Changed selections or value inputs invalidate the displayed calculation; late responses for obsolete inputs are ignored.

Offline data adds a `study` field and uses the same documented value arithmetic. This calculation is labelled a conditional illustration and never a new power flow or observed customer saving.

The study comparison selector also exposes the eight portfolio pairs at fixed 200 MW wind / 20 MW flexibility / stated outage. Each value calculation uses that selected pair, rather than reusing the default Binbane difference. Portfolio selection disables unavailable wind/load settings.
