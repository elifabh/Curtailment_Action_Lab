"""Reproduce the preregistered reference-network verification suite."""
from pathlib import Path
import json
import platform
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.reference_engine import ACTIONS, evaluate, evaluate_candidate, validate_source, SOURCE_SHA256


def main():
    conditions = [(185., .90), (215., 1.05), (230., 1.10)]
    cases = []
    for wind, scale in conditions:
        for action in ACTIONS:
            result = evaluate_candidate({'wind_mw': wind, 'load_scale': scale, 'action_id': action})
            cases.append(result)
            print(f'{wind} MW / {scale} / {action}: {result["status"]}', flush=True)
    source = validate_source()
    comparisons = [evaluate({'wind_mw': w, 'load_scale': s}) for w, s in conditions]
    demo = evaluate({})
    null = evaluate({'wind_mw': 50})
    output = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256': SOURCE_SHA256,
        'protocol': 'validation/reference_protocol.md',
        'python_version': platform.python_version(),
        'summary': {'source_passed': source['passed'], 'confirmed_cases': len(cases),
                    'passed_cases': sum(c['eligible'] for c in cases),
                    'failed_cases': sum(not c['eligible'] for c in cases),
                    'checks_per_case': len(cases[0]['checks']),
                    'null_additional_wind_mw': null['comparison']['additional_wind_mw'],
                    'all_confirmation_passed': source['passed'] and all(c['eligible'] for c in cases)},
        'source_validation': source, 'default_comparison': demo,
        'confirmation_comparisons': comparisons, 'confirmation_cases': cases,
        'low_wind_null_comparison': null,
    }
    target = ROOT / 'validation' / 'reference_validation_results.json'
    target.write_text(json.dumps(output, indent=2, allow_nan=False) + '\n')
    (ROOT / 'data' / 'reference_default_comparison.json').write_text(json.dumps(demo, indent=2, allow_nan=False) + '\n')
    print(json.dumps(output['summary'], indent=2))
    return output


if __name__ == '__main__':
    main()
