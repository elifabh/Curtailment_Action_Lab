"""Check local demo readiness. --azure opts into a bounded live Azure audit."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--azure', action='store_true', help='Use the configured Azure connection for a one-record audit (may consume quota).')
    args = parser.parse_args()
    import app_service  # Loads the local .env without printing its contents.
    import decision_service
    import extension_service
    from ai.agent_runner import agent_status
    from ai.challenge_agent import run

    checks = []
    def check(name, fn):
        try:
            ok, detail = fn()
        except Exception as exc:
            ok, detail = False, type(exc).__name__ + ': check installation and complete ZIP extraction.'
        checks.append({'name': name, 'passed': bool(ok), 'detail': detail})
        print(('PASS ' if ok else 'FAIL ') + name + ': ' + detail, flush=True)

    def assets():
        required = ['web/index.html', 'web/app.js', 'web/decision.js', 'web/reporting.js',
                    'web/extension.html', 'web/extension.js',
                    'evidence_v5/results/challenge_matrix.json']
        missing = [f for f in required if not (ROOT/f).is_file()]
        return not missing, 'Required demo files found.' if not missing else 'Missing: ' + ', '.join(missing)
    check('Demo files', assets)
    def decision():
        r = decision_service.analyse(decision_service.default_plan())
        ok = r['status'] == 'retain' and r['nominal']['additional_wind_MW'] == 20.703125
        return ok, f"Default status: {r['status']}; nominal added wind: {r['nominal']['additional_wind_MW']} MW."
    check('Offer decisions', decision)
    def rule():
        r = run({'plan': decision_service.default_plan(), 'budget': 4, 'mode': 'deterministic'})
        return r['status'] == 'completed' and r['record_reads'] == 4, f"{r['record_reads']} recorded conditions inspected."
    check('Rule-based audit', rule)
    for name in extension_service.SAVED:
        def saved(n=name):
            r = extension_service.saved_example(n)['result']
            return bool(r.get('calculation_id')), 'Recorded calculation loaded.'
        check(name, saved)
    check('New-calculation dependencies', lambda: (extension_service.configuration()['available'],
        'Installed; this check does not run a new power flow.' if extension_service.configuration()['available']
        else 'Run INSTALL_IRISH_EXTENSION.bat and restart the server.'))

    ai = agent_status()
    live = {'status': 'not_run', 'reason': 'Use --azure to test live access.'}
    if args.azure and ai['enabled']:
        print('Running a live Azure audit, maximum one recorded condition. No device command. Please wait...', flush=True)
        r = run({'plan': decision_service.default_plan(), 'budget': 1, 'mode': 'azure',
                 'prompt': 'Inspect one allowed recorded condition using test_offer_scenario. Preserve all requirements.'})
        live = {k:r.get(k) for k in ('status','record_reads','provider_calls','provider_http_requests','provider_retries','error','is_live_provider')}
        ok = r['status'] == 'completed' and r['record_reads'] == 1
        checks.append({'name': 'Live Azure audit', 'passed': ok, 'detail': live})
        print(('PASS ' if ok else 'FAIL ') + 'Live Azure audit: ' + json.dumps(live, ensure_ascii=True), flush=True)
    else:
        live['reason'] = ai['message'] if not ai['enabled'] else live['reason']
        print('NOT TESTED Live Azure: ' + live['reason'], flush=True)
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks,
              'local_checks_passed': all(c['passed'] for c in checks if c['name'] != 'Live Azure audit'),
              'azure': live, 'fresh_power_flow_executed': False}
    (ROOT/'DEMO_CHECK_RESULT.json').write_text(json.dumps(report, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')
    print('Saved DEMO_CHECK_RESULT.json. No API keys are included.', flush=True)
    return 0 if all(c['passed'] for c in checks) else 1


if __name__ == '__main__':
    raise SystemExit(main())
