"""Recompute finite demo records. Does not use Azure or invent unrecorded results."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app_service as app


def main():
    if not app.scientific_available():
        raise SystemExit('Install requirements.txt before generating recordings.')
    records = {'evaluate': [], 'sensitivity': [], 'search': []}
    default = app.configuration()['default_request']
    requests = [{**default, 'action_id': a} for a in app.REFERENCE_ACTIONS]
    requests += [{**default, 'wind_mw': w} for w in (0., 50., 100., 150., 240.)]
    requests += [{**default, 'wind_mw': w, 'load_scale': load} for w, load in [(185., .9), (215., 1.05), (230., 1.10)]]
    requests += [{'profile': app.IRISH_ID, 'wind_mw': w, 'load_scale': 1., 'action_id': action}
                 for w in (0., 100., 200.) for action in ('line_in_service', 'line_outage')]
    for request in requests:
        request, _ = app.validate_request(request)
        records['evaluate'].append({'request': request, 'response': app.evaluate(request)})
    for request in [default, {**default, 'wind_mw': 50.}, {**default, 'action_id': 'outage_6_7'}]:
        records['sensitivity'].append({'request': request, 'response': app.sensitivity(request)})
    for budget in (2, 4, 7):
        request = {k: default[k] for k in ('profile', 'wind_mw', 'load_scale')}
        request['budget'] = budget
        records['search'].append({'request': request, 'response': app.run_search(request)})
    (ROOT/'data/recorded.json').write_text(json.dumps(records, ensure_ascii=False, allow_nan=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key:len(value) for key,value in records.items()}))

if __name__ == '__main__':
    main()
