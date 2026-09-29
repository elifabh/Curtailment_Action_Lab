"""Auditable AC reference-network scenario comparison, with independent checks.

This is a synthetic research network, not an Irish operational model.
PYPOWER supplies the nonlinear optimizer. The verification equations below do
not call its admittance/flow routines. No safety claim beyond listed checks.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import time
import warnings

import numpy as np
from scipy.optimize import root
from pypower.api import ppoption, runopf, runpf

ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = ROOT / 'data' / 'reference_case9.json'
SOURCE_SHA256 = '44a26bfc866bdb7cf4501ce3700e863d9ff6a901c6571ab5a91fe49dec677ba4'
ACTIONS = {
    'all_in_service': ('All lines available', None),
    'outage_4_5': ('Line 4–5 unavailable', (4, 5)),
    'outage_5_6': ('Line 5–6 unavailable', (5, 6)),
    'outage_6_7': ('Line 6–7 unavailable · baseline', (6, 7)),
    'outage_7_8': ('Line 7–8 unavailable', (7, 8)),
    'outage_8_9': ('Line 8–9 unavailable', (8, 9)),
    'outage_9_4': ('Line 9–4 unavailable', (9, 4)),
}
BASELINE_ID = 'outage_6_7'
TOLERANCES = {'power_mw_mvar': 1e-4, 'voltage_pu': 1e-6,
              'thermal_mva': 1e-4, 'generator_mw_mvar': 1e-4,
              'independent_voltage_pu': 1e-5, 'independent_angle_deg': 1e-3}
LIMITATIONS = [
    'Synthetic wind in the public nine-bus reference network; not Irish operational data.',
    'Steady-state AC feasibility only; no N−1, transient, frequency, ramping or maintenance scheduling checks.',
    'Topology alternatives are hypothetical availability states, not approved switching instructions.',
    'The declared dispatch policy is an AC OPF local solution, not a certified global optimum.',
    'Objective units are synthetic cost units, not EUR; no profit or CO₂ claim.',
    'Snapshot MW, not MWh or a share of Irish annual curtailment.',
]


def source_case():
    raw = CASE_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise RuntimeError('Reference source data checksum mismatch')
    data = json.loads(raw)
    for key in ('bus', 'gen', 'branch', 'gencost', 'areas'):
        data[key] = np.asarray(data[key], dtype=float)
    return data


def configuration():
    return {
        'id': 'reference_9bus', 'name': 'Validated nine-bus reference network',
        'description': 'Synthetic wind at bus 6. Compare line availability at unchanged consumer demand.',
        'source': 'PYPOWER 5.1.19 case9 / MATPOWER nine-bus example',
        'wind_bus': 6, 'base_load_mw': 315.0,
        'ranges': {'wind_mw': {'min': 0.0, 'max': 240.0, 'default': 200.0},
                   'load_scale': {'min': 0.85, 'max': 1.15, 'default': 1.0}},
        'baseline_action_id': BASELINE_ID,
        'actions': [{'id': k, 'name': v[0], 'description':
                     ('All original lines in service.' if v[1] is None else
                      f'Only line {v[1][0]}–{v[1][1]} is unavailable; every other line is in service.')}
                    for k, v in ACTIONS.items()],
        'limitations': LIMITATIONS,
        'sources': [
            {'label': 'Original reference network', 'url': 'https://github.com/rwl/PYPOWER/blob/master/pypower/case9.py'},
            {'label': 'AC OPF formulation', 'url': 'https://matpower.app/manual/matpower/StandardACOPF.html'},
        ],
    }


def _number(value, name, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a finite number')
    value = float(value)
    if not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f'{name} must be between {lo} and {hi}')
    return value


def normalize_request(request):
    if not isinstance(request, dict):
        raise ValueError('Request must be an object')
    if request.get('profile', 'reference_9bus') != 'reference_9bus':
        raise ValueError('Unknown reference profile')
    action = request.get('action_id', 'all_in_service')
    if not isinstance(action, str) or action not in ACTIONS:
        raise ValueError('Unknown action_id')
    return {'profile': 'reference_9bus',
            'wind_mw': _number(request.get('wind_mw', 200.0), 'wind_mw', 0, 240),
            'load_scale': _number(request.get('load_scale', 1.0), 'load_scale', .85, 1.15),
            'action_id': action}


def make_case(wind_mw, load_scale, action_id):
    case = source_case()
    case['bus'][:, 2:4] *= load_scale
    outage = ACTIONS[action_id][1]
    if outage:
        hits = np.where((case['branch'][:, 0] == outage[0]) & (case['branch'][:, 1] == outage[1]))[0]
        if len(hits) != 1:
            raise RuntimeError('Ambiguous topology action')
        case['branch'][hits[0], 10] = 0
    wind = np.zeros(21, dtype=float)
    wind[:10] = [6, min(wind_mw, 50), 0, 0, 0, 1, 100, 1 if wind_mw > 0 else 0, wind_mw, 0]
    case['gen'] = np.vstack([case['gen'], wind])
    case['gencost'] = np.vstack([case['gencost'], [2, 0, 0, 3, 0, -1000, 0]])
    return case


def _complex_flows(case, voltage):
    """Direct pi-model branch currents, including taps, shifts and shunts."""
    bus, branch, base = case['bus'], case['branch'], case['baseMVA']
    index = {int(row[0]): i for i, row in enumerate(bus)}
    currents = np.zeros(len(bus), complex)
    from_s, to_s = np.zeros(len(branch), complex), np.zeros(len(branch), complex)
    for j, row in enumerate(branch):
        if row[10] <= 0:
            continue
        f, t = index[int(row[0])], index[int(row[1])]
        y = 1 / complex(row[2], row[3])
        charging = 0.5j * row[4]
        tap = (row[8] if row[8] != 0 else 1.0) * np.exp(1j * math.radians(row[9]))
        current_f = (y + charging) / (abs(tap) ** 2) * voltage[f] - y / np.conj(tap) * voltage[t]
        current_t = (y + charging) * voltage[t] - y / tap * voltage[f]
        currents[f] += current_f
        currents[t] += current_t
        from_s[j] = voltage[f] * np.conj(current_f) * base
        to_s[j] = voltage[t] * np.conj(current_t) * base
    currents += (bus[:, 4] + 1j * bus[:, 5]) / base * voltage
    injection = voltage * np.conj(currents) * base
    return injection, from_s, to_s


def _net_generation(case):
    index = {int(row[0]): i for i, row in enumerate(case['bus'])}
    generation = np.zeros(len(index), complex)
    for row in case['gen']:
        if row[7] > 0:
            generation[index[int(row[0])]] += complex(row[1], row[2])
    return generation


def _components(case):
    neighbours = {int(row[0]): set() for row in case['bus']}
    for row in case['branch']:
        if row[10] > 0:
            f, t = int(row[0]), int(row[1])
            neighbours[f].add(t); neighbours[t].add(f)
    unseen, count = set(neighbours), 0
    while unseen:
        count += 1
        stack = [unseen.pop()]
        while stack:
            for neighbour in neighbours[stack.pop()]:
                if neighbour in unseen:
                    unseen.remove(neighbour); stack.append(neighbour)
    return count


def independent_power_flow(case):
    """Solve standard PV/PQ balances from a flat start, independently of PYPOWER.

    OPF voltage setpoints and active generation become fixed PF inputs. A wind
    generator with Qmin=Qmax=0 stays at a PQ bus, because it has no AVR.
    """
    bus = case['bus']
    ref = int(np.flatnonzero(bus[:, 1] == 3)[0])
    angle_nodes = np.array([i for i in range(len(bus)) if i != ref])
    controlled = {ref}
    index = {int(row[0]): i for i, row in enumerate(bus)}
    for row in case['gen']:
        if row[7] > 0 and row[3] - row[4] > 1e-9:
            controlled.add(index[int(row[0])])
    pq = np.array([i for i in range(len(bus)) if i not in controlled], dtype=int)
    expected = _net_generation(case) - bus[:, 2] - 1j * bus[:, 3]
    fixed_vm = bus[:, 7].copy()
    ref_angle = math.radians(bus[ref, 8])

    def unpack(x):
        angles = np.full(len(bus), ref_angle)
        angles[angle_nodes] = x[:len(angle_nodes)]
        vm = fixed_vm.copy(); vm[pq] = x[len(angle_nodes):]
        return vm * np.exp(1j * angles)

    def residual(x):
        difference = (_complex_flows(case, unpack(x))[0] - expected) / case['baseMVA']
        return np.r_[difference.real[angle_nodes], difference.imag[pq]]

    start = np.r_[np.full(len(angle_nodes), ref_angle), np.ones(len(pq))]
    solved = root(residual, start, method='hybr', options={'xtol': 1e-10})
    voltage = unpack(solved.x)
    original = bus[:, 7] * np.exp(1j * np.deg2rad(bus[:, 8]))
    angle_diff = np.rad2deg(np.angle(voltage / original))
    max_residual = float(np.max(np.abs(residual(solved.x))) * case['baseMVA'])
    vm_diff = float(np.max(np.abs(np.abs(voltage) - np.abs(original))))
    angle_max = float(np.max(np.abs(angle_diff)))
    passed = (bool(solved.success) and max_residual <= TOLERANCES['power_mw_mvar'] and
              vm_diff <= TOLERANCES['independent_voltage_pu'] and
              angle_max <= TOLERANCES['independent_angle_deg'])
    return {'passed': passed, 'solver_success': bool(solved.success),
            'method': 'SciPy root/hybr with separately implemented branch-current equations; flat start',
            'max_solved_equation_residual_mw_mvar': max_residual,
            'max_voltage_difference_pu': vm_diff, 'max_angle_difference_deg': angle_max,
            'function_evaluations': int(solved.nfev)}


def check_solution(case, expected_case, solver_success=True, independent=True):
    """All physical buses, both branch ends, all P/Q generator bounds; no omissions."""
    bus, gen, branch = case['bus'], case['gen'], case['branch']
    checks = []
    def add(key, label, passed, value=None, limit=None, unit=None):
        checks.append({'id': key, 'label': label, 'passed': bool(passed),
                       'value': value, 'limit': limit, 'unit': unit})
    finite = all(np.isfinite(case[k]).all() for k in ('bus', 'gen', 'branch'))
    add('finite', 'Finite solution values', finite)
    add('converged', 'AC solver converged', solver_success)
    components = _components(expected_case)
    add('connected', 'One connected network; no islands', components == 1, components, 1)
    same_load = np.array_equal(bus[:, 2:4], expected_case['bus'][:, 2:4])
    add('load_unchanged', 'Consumer active and reactive demand unchanged', same_load)
    bounds_same = (np.array_equal(bus[:, 11:13], expected_case['bus'][:, 11:13]) and
                   np.array_equal(gen[:, [3, 4, 8, 9]], expected_case['gen'][:, [3, 4, 8, 9]]) and
                   np.array_equal(branch[:, 5], expected_case['branch'][:, 5]))
    add('limits_unchanged', 'Declared network and generator limits unchanged', bounds_same)
    voltage = bus[:, 7] * np.exp(1j * np.deg2rad(bus[:, 8]))
    injection, fs, ts = _complex_flows(case, voltage)
    residual = _net_generation(case) - bus[:, 2] - 1j * bus[:, 3] - injection
    p_res, q_res = float(np.max(abs(residual.real))), float(np.max(abs(residual.imag)))
    add('p_balance', 'Independent active-power balance at all buses', p_res <= 1e-4, p_res, 1e-4, 'MW')
    add('q_balance', 'Independent reactive-power balance at all buses', q_res <= 1e-4, q_res, 1e-4, 'MVAr')
    v_violation = float(max(0.0, np.max(bus[:, 7] - bus[:, 11]), np.max(bus[:, 12] - bus[:, 7])))
    add('voltage', 'All bus voltage bounds', v_violation <= 1e-6, v_violation, 1e-6, 'p.u. violation')
    rated = (branch[:, 10] > 0) & (branch[:, 5] > 0)
    thermal_violation = float(max(0.0, np.max(np.maximum(abs(fs[rated]), abs(ts[rated])) - branch[rated, 5])))
    add('thermal', 'Apparent power at both ends of every rated line', thermal_violation <= 1e-4,
        thermal_violation, 1e-4, 'MVA violation')
    on = gen[:, 7] > 0
    p_violation = float(max(0.0, np.max(gen[on, 1] - gen[on, 8]), np.max(gen[on, 9] - gen[on, 1])))
    q_violation = float(max(0.0, np.max(gen[on, 2] - gen[on, 3]), np.max(gen[on, 4] - gen[on, 2])))
    add('generator_p', 'Every online generator active-power bound', p_violation <= 1e-4, p_violation, 1e-4, 'MW violation')
    add('generator_q', 'Every online generator reactive-power bound', q_violation <= 1e-4, q_violation, 1e-4, 'MVAr violation')
    index = {int(row[0]): i for i, row in enumerate(bus)}
    angle_violation = 0.0
    for row in branch:
        if row[10] <= 0: continue
        delta = bus[index[int(row[0])], 8] - bus[index[int(row[1])], 8]
        if row[11] > -360: angle_violation = max(angle_violation, row[11] - delta)
        if row[12] < 360: angle_violation = max(angle_violation, delta - row[12])
    add('angle', 'Declared branch angle limits', angle_violation <= 1e-6, float(angle_violation), 1e-6, 'degrees violation')
    external = independent_power_flow(case) if independent and finite and components == 1 else {'passed': False, 'reason': 'Not run'}
    if independent:
        add('independent_pf', 'Independent flat-start AC power-flow agreement', external['passed'],
            external.get('max_voltage_difference_pu'), 1e-5, 'p.u. difference')
    return {'passed': all(x['passed'] for x in checks), 'checks': checks,
            'independent_power_flow': external, 'residual_mw': residual.real.tolist(),
            'residual_mvar': residual.imag.tolist(), 'flows_from_mva': abs(fs).tolist(),
            'flows_to_mva': abs(ts).tolist(), 'active_losses_mw': float((fs + ts).real.sum()),
            'max_branch_loading_pct': float(np.max(np.maximum(abs(fs[rated]), abs(ts[rated])) / branch[rated, 5]) * 100)}


@lru_cache(maxsize=256)
def _run_candidate(wind_mw, load_scale, action_id):
    original = make_case(wind_mw, load_scale, action_id)
    start = time.perf_counter()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        solved = runopf(deepcopy(original), ppoption(VERBOSE=0, OUT_ALL=0, OPF_FLOW_LIM=0,
                        OPF_VIOLATION=1e-6, PDIPM_FEASTOL=1e-7, PDIPM_MAX_IT=200))
    audit = check_solution(solved, original, bool(solved.get('success')))
    elapsed = time.perf_counter() - start
    accepted = float(solved['gen'][-1, 1])
    curtailed = float(max(0, wind_mw - accepted))
    thermal_cost = sum(float(np.polyval(original['gencost'][i, 4:7], solved['gen'][i, 1])) for i in range(3))
    metrics = {'available_wind_mw': wind_mw, 'accepted_wind_mw': accepted,
               'curtailed_wind_mw': curtailed, 'load_mw': float(original['bus'][:, 2].sum()),
               'load_mvar': float(original['bus'][:, 3].sum()),
               'losses_mw': audit['active_losses_mw'],
               'thermal_generation_mw': float(solved['gen'][:3, 1].sum()),
               'max_branch_loading_pct': audit['max_branch_loading_pct'],
               'min_voltage_pu': float(solved['bus'][:, 7].min()),
               'max_voltage_pu': float(solved['bus'][:, 7].max()),
               'thermal_dispatch_cost_units_per_hour': thermal_cost,
               'objective_units': thermal_cost + 1000 * curtailed}
    result = {
        'id': action_id, 'action_id': action_id, 'label': ACTIONS[action_id][0],
        'profile': 'reference_9bus', 'status': 'verified' if audit['passed'] else 'failed',
        'eligible': audit['passed'], 'metrics': metrics,
        'checks': audit['checks'], 'independent_validation': audit['independent_power_flow'],
        'balance_residuals': {'p_mw': audit['residual_mw'], 'q_mvar': audit['residual_mvar']},
        'buses': [{'bus': int(row[0]), 'voltage_pu': float(row[7]), 'angle_deg': float(row[8]),
                   'load_mw': float(row[2]), 'load_mvar': float(row[3]),
                   'vmin_pu': float(row[12]), 'vmax_pu': float(row[11])} for row in solved['bus']],
        'branches': [{'from': int(row[0]), 'to': int(row[1]), 'in_service': bool(row[10]),
                      'rating_mva': float(row[5]), 'from_mva': audit['flows_from_mva'][j],
                      'to_mva': audit['flows_to_mva'][j],
                      'loading_pct': float(max(audit['flows_from_mva'][j], audit['flows_to_mva'][j]) / row[5] * 100) if row[5] else None}
                     for j, row in enumerate(solved['branch'])],
        'generators': [{'bus': int(row[0]), 'kind': 'synthetic wind' if i == 3 else 'reference conventional generator',
                        'p_mw': float(row[1]), 'q_mvar': float(row[2]), 'pmin_mw': float(row[9]), 'pmax_mw': float(row[8]),
                        'qmin_mvar': float(row[4]), 'qmax_mvar': float(row[3])} for i, row in enumerate(solved['gen'])],
        'solver': {'name': 'PYPOWER AC OPF / PIPS', 'success': bool(solved.get('success')),
                   'elapsed_seconds': elapsed, 'message': str(solved.get('raw', {}).get('output', {}).get('message', ''))},
        'limitations': LIMITATIONS,
    }
    return result


def evaluate_candidate(request):
    request = normalize_request(request)
    result = deepcopy(_run_candidate(request['wind_mw'], request['load_scale'], request['action_id']))
    result['request'] = request
    result['trace'] = [
        {'step': 'load_source', 'detail': f'case9 SHA256 {SOURCE_SHA256}'},
        {'step': 'declare_scenario', 'detail': request},
        {'step': 'solve', 'detail': 'AC OPF with unchanged published limits and synthetic wind-curtailment objective'},
        {'step': 'independent_check', 'detail': 'Direct branch-current equations and flat-start SciPy root'},
    ]
    return result


def evaluate(request):
    request = normalize_request(request)
    baseline = evaluate_candidate({**request, 'action_id': BASELINE_ID})
    selected = evaluate_candidate(request)
    bm, sm = baseline['metrics'], selected['metrics']
    eligible = baseline['eligible'] and selected['eligible']
    difference = sm['accepted_wind_mw'] - bm['accepted_wind_mw']
    percent = 100 * difference / bm['curtailed_wind_mw'] if bm['curtailed_wind_mw'] >= .001 else None
    comparison = {
        'eligible_for_claim': eligible,
        'additional_wind_mw': difference if eligible else None,
        'curtailment_reduction_pct': percent if eligible else None,
        'percentage_denominator': 'Baseline curtailed MW in this synthetic reference snapshot',
        'loss_change_mw': sm['losses_mw'] - bm['losses_mw'],
        'thermal_cost_change_units_per_hour': sm['thermal_dispatch_cost_units_per_hour'] - bm['thermal_dispatch_cost_units_per_hour'],
        'not_irish_impact': True,
    }
    return {'request': request, 'status': 'verified_reference_comparison' if eligible else 'rejected_comparison',
            'metrics': comparison, 'comparison': comparison, 'baseline': baseline, 'selected': selected,
            'checks': selected['checks'], 'trace': selected['trace'],
            'evidence': {'source_sha256': SOURCE_SHA256, 'protocol': 'validation/reference_protocol.md',
                         'scope': 'Synthetic reference-network steady-state scenario; not real Irish curtailment',
                         'limitations': LIMITATIONS}}


def sensitivity(request):
    """A fixed, disclosed wind sweep with the same load and selected action."""
    request = normalize_request(request)
    rows = []
    for wind in [0.0, 50.0, 100.0, 150.0, 200.0, 240.0]:
        comparison = evaluate({**request, 'wind_mw': wind})
        rows.append({'available_wind_mw': wind,
                     'baseline_accepted_mw': comparison['baseline']['metrics']['accepted_wind_mw'],
                     'selected_accepted_mw': comparison['selected']['metrics']['accepted_wind_mw'],
                     'baseline_curtailed_mw': comparison['baseline']['metrics']['curtailed_wind_mw'],
                     'selected_curtailed_mw': comparison['selected']['metrics']['curtailed_wind_mw'],
                     'additional_wind_mw': comparison['comparison']['additional_wind_mw'],
                     'eligible': comparison['comparison']['eligible_for_claim']})
    return {'request': request, 'rows': rows, 'limitations': LIMITATIONS,
            'scope': 'Synthetic wind sensitivity; not a weather forecast or time series'}


def validate_source():
    case = source_case()
    solved, success = runpf(deepcopy(case), ppoption(VERBOSE=0, OUT_ALL=0, PF_TOL=1e-10))
    audit = check_solution(solved, case, bool(success))
    return {'case': 'Unmodified PYPOWER case9', 'source_sha256': SOURCE_SHA256,
            'passed': audit['passed'], 'audit': audit,
            'source_data_note': 'Published case is unsolved input, so validate solved PF rather than its initial Pg=0 slack entry.',
            'solved_voltage_pu': solved['bus'][:, 7].tolist(),
            'solved_angle_deg': solved['bus'][:, 8].tolist(),
            'solved_generation_mw': solved['gen'][:, 1].tolist()}


if __name__ == '__main__':
    print(json.dumps({'source': validate_source(), 'comparison': evaluate({})}, indent=2, allow_nan=False))
