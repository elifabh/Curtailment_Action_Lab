"""Fresh, bounded Irish planning experiments. Never an operating instruction.

The original source conversion, AC solver, RAW-equation check and ideal-tie
checks are reused without widening a limit. Each job runs in its own process
and temporary audit directory; stored demonstration records are never edited.
"""
from __future__ import annotations
from pathlib import Path
import contextlib
import hashlib
import importlib.util
import io
import json
import math
import shutil
import sys
import tempfile
import time
from copy import deepcopy

ROOT = Path(__file__).resolve().parent
SOURCE_HASH = '006db9ce2ff20a7bf2a67ffbd9988735a1b3d3dc8abbd6309395e7139b66cb24'
LIMITATIONS = [
    'Prepared 2024/25 Irish planning snapshot; hypothetical wind and flexible load.',
    'Best tested passing point, not a global optimum or a monotonicity certificate.',
    'Source taps, shunts, local voltage targets and inferred HVDC boundary remain fixed.',
    'Missing and placeholder-like ratings remain; passing checks is not full network certification.',
    'Ideal-cycle tie flows use the original declared allocation; other loop-flow splits are not certified.',
    'No N-1, transient stability, SNSP, inertia or RoCoF clearance, and no operating permission.',
    'No field savings, customer profitability, market order or physical device action is established.'
]

def dump(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(path)

def schema():
    matrix = json.loads((ROOT/'evidence_v5/results/challenge_matrix.json').read_text())
    return [{'bus':c['bus'], 'name':c['name']} for c in matrix['candidates']]

def number(value, name, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be a finite number from {low} to {high}.')
    return float(value)

def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError('Expected a JSON object.')
    kind = payload.get('kind')
    common = {'kind', 'candidate_bus', 'flex_MW', 'line_outage'}
    required = common | ({'wind_available_MW', 'load_factor'} if kind == 'snapshot' else {'profile_mode'} if kind == 'pilot' else set())
    if kind not in ('snapshot', 'pilot') or set(payload) != required:
        raise ValueError('Supply exactly the documented snapshot or pilot inputs.')
    p = dict(payload)
    allowed = {c['bus'] for c in schema()}
    if type(p['candidate_bus']) is not int or p['candidate_bus'] not in allowed:
        raise ValueError('Select one of the eight declared connection points.')
    if type(p['line_outage']) is not bool:
        raise ValueError('line_outage must be a boolean.')
    p['flex_MW'] = number(p['flex_MW'], 'Flexible demand', 0, 40)
    if kind == 'snapshot':
        p['wind_available_MW'] = number(p['wind_available_MW'], 'Available wind', 0, 200)
        p['load_factor'] = number(p['load_factor'], 'Demand multiplier', .99, 1.01)
    elif p['profile_mode'] not in ('wind_shape_fixed_demand', 'observed_demand_assumed_redispatch'):
        raise ValueError('Select a declared profile mode.')
    return p

class FreshStudy:
    def __init__(self, workdir, progress):
        import numpy as np
        self.np = np
        self.progress = progress
        self.workdir = Path(workdir)
        audit = self.workdir/'irish_audit'
        (audit/'results').mkdir(parents=True)
        shutil.copytree(ROOT/'irish_audit/code', audit/'code', ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('TYTFS2024_WP2024_V33.raw',):
            shutil.copy2(ROOT/'irish_audit'/name, audit/name)
        for name in ('feasible_counterfactual.npz', 'expanded_tap_experiment.json', 'feasible_counterfactual_actions.json'):
            shutil.copy2(ROOT/'irish_audit/results'/name, audit/'results'/name)
        self.outdir = self.workdir/'results'
        self.outdir.mkdir()
        sys.path.insert(0, str(audit/'code'))
        # Preload the isolated modules: the legacy study inserts its own code
        # directory, so import precedence alone would otherwise modify its logs.
        import wind_screen, fixed_case, raw_equation_check, source_audit
        spec = importlib.util.spec_from_file_location('fresh_physical_study', ROOT/'evidence_v4/code/run_study.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m.ROOT = self.workdir
        m.OUT = self.outdir
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.study = m.Study()
        self.source_ppc = deepcopy(self.study.ppc)
        self.source_pg = self.source_ppc['gen'][:,1].copy()
        self.online = self.source_ppc['gen'][:,7] > 0
        self.source_pg_total = float(self.source_pg[self.online].sum())
        self.reused = 0
        self.cache = {}

    def redispatch(self, target):
        """Declared headroom participation, not economic or historical dispatch.

        Redispatch all source-online generators within unchanged P limits.
        The original slack handles residual losses. Status/limits are unchanged.
        No generator technology classification is inferred from the RAW file.
        """
        np = self.np
        g = self.source_ppc['gen']
        active = self.online
        low, high = g[active,9], g[active,8]
        if target < float(low.sum())-1e-7 or target > float(high.sum())+1e-7:
            raise ValueError('Aggregate source-online generator bounds cannot meet the assumed balance.')
        start = np.clip(self.source_pg[active], low, high)
        difference = target-float(start.sum())
        headroom = high-start if difference >= 0 else start-low
        if abs(difference) > 1e-8 and float(headroom.sum()) <= 0:
            raise ValueError('No generator headroom for the assumed redispatch.')
        values = start + (difference * headroom / headroom.sum() if abs(difference)>1e-8 else 0)
        assert np.all(values >= low-1e-7) and np.all(values <= high+1e-7)
        return values

    def evaluate(self, wind, p, factor, policy, phase):
        key = (float(wind), p['candidate_bus'], p['flex_MW'], p['line_outage'], float(factor), policy)
        if key in self.cache:
            self.reused += 1
            return deepcopy(self.cache[key])
        self.study.ppc = deepcopy(self.source_ppc)
        dispatch = {'policy':policy, 'source_generator_status_unchanged':True, 'source_limits_unchanged':True}
        if policy == 'assumed_headroom_redispatch':
            target = self.source_pg_total + self.study.source_demand*(factor-1) + p['flex_MW'] - wind
            dispatch['scheduled_generation_MW'] = target
            try:
                self.study.ppc['gen'][self.online,1] = self.redispatch(target)
            except ValueError as exc:
                r = {'id':f'dispatch_block_{len(self.cache)+1}', 'wind_MW':wind,
                     'passes_declared_snapshot_checks':False, 'solver_converged':False,
                     'block_reason':str(exc), 'dispatch':dispatch, 'phase':phase}
                self.cache[key] = r
                return deepcopy(r)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            r, out = self.study.evaluate(wind, p['line_outage'], {p['candidate_bus']:p['flex_MW']}, factor, phase)
        r['dispatch'] = dispatch
        if r['passes_declared_snapshot_checks']:
            state_file = self.outdir/f"{r['id']}.npz"
            self.np.savez_compressed(state_file, **{k:out[k] for k in ('baseMVA','bus','gen','branch')})
            r['solved_state_sha256'] = hashlib.sha256(state_file.read_bytes()).hexdigest()
        self.cache[key] = r
        self.progress({'stage':'calculating', 'new_power_flows_run':self.study.calls,
                       'last_point':{'wind_MW':wind, 'candidate_bus':p['candidate_bus'],
                                     'passed':r['passes_declared_snapshot_checks']}})
        return deepcopy(r)

    def curve(self, p, factor=1., policy='fixed_dispatch'):
        ceiling = p['wind_available_MW']
        grid = sorted(set([0., ceiling] + [float(x) for x in range(25,201,25) if x < ceiling]))
        points = [self.evaluate(w,p,factor,policy,'coarse') for w in grid]
        passing = [r for r in points if r['passes_declared_snapshot_checks']]
        best = max(passing,key=lambda r:r['wind_MW']) if passing else None
        if best and best['wind_MW'] < ceiling:
            low = best['wind_MW']
            high = min(x for x in grid if x>low)
            while high-low > .25:
                w = (high+low)/2
                r = self.evaluate(w,p,factor,policy,'local_refinement')
                points.append(r)
                if r['passes_declared_snapshot_checks']:
                    best=r;low=w
                else: high=w
        return {'best_tested':best, 'tested_points':points,
                'search_resolution_MW':.25,
                'global_optimum_certified':False,
                'input':{**p,'load_factor':factor,'dispatch_policy':policy}}

    def compare(self, p, factor=1., policy='fixed_dispatch'):
        a = self.curve({**p, 'candidate_bus':2072}, factor, policy)
        b = self.curve(p, factor, policy)
        aa,bb = a['best_tested'],b['best_tested']
        comparable = bool(aa and bb and abs(aa['total_consumer_demand_MW']-bb['total_consumer_demand_MW'])<1e-6)
        delta = bb['wind_MW']-aa['wind_MW'] if comparable else None
        losses = bb['network_losses_MW']-aa['network_losses_MW'] if comparable else None
        other = bb['other_generation_MW']-aa['other_generation_MW'] if comparable else None
        return {'baseline':a,'selected':b,'comparable':comparable,
                'additional_hypothetical_wind_MW':delta,
                'change_other_generation_MW':other,'change_network_losses_MW':losses,
                'energy_balance_difference_MW':delta+other-losses if comparable else None,
                'block_reason':None if comparable else 'No passing tested point for one or both alternatives; no saving is assigned.',
                'baseline_bus':2072,'candidate_bus':p['candidate_bus'],
                'new_power_flows_run':self.study.calls}

def integrate(rows):
    """Signed interval integration. Missing results must never become zero."""
    good = [r for r in rows if r['comparison']['comparable']]
    hours = sum(r['duration_hours'] for r in rows)
    covered = sum(r['duration_hours'] for r in good)
    subtotal = sum(r['comparison']['additional_hypothetical_wind_MW']*r['duration_hours'] for r in good) if good else None
    full = len(good)==len(rows) and bool(rows)
    return {'intervals':len(rows),'comparable_intervals':len(good),'blocked_intervals':len(rows)-len(good),
            'period_hours':hours,'covered_hours':covered,'coverage_fraction':covered/hours if hours else 0,
            'comparable_intervals_subtotal_MWh':subtotal,
            'full_period_change_MWh':subtotal if full else None,
            'full_period_result_available':full,
            'adverse_intervals':sum(r['comparison']['additional_hypothetical_wind_MW']<-.000001 for r in good),
            'change_other_generation_MWh':sum(r['comparison']['change_other_generation_MW']*r['duration_hours'] for r in good) if good else None,
            'change_network_losses_MWh':sum(r['comparison']['change_network_losses_MW']*r['duration_hours'] for r in good) if good else None,
            'annual_avoided_curtailment_MWh':None,'national_reduction_percent':None}

def run(payload, output_path, progress_path):
    p = validate(payload)
    start=time.perf_counter()
    output_path=Path(output_path)
    latest={}
    def progress(details):
        latest.update(details)
        dump(progress_path, {'status':'running', **latest,'elapsed_seconds':time.perf_counter()-start})
    progress({'stage':'preparing'})
    with tempfile.TemporaryDirectory(prefix='actionlab_irish_',dir=output_path.parent) as temp:
        engine=FreshStudy(temp,progress)
        result={'inputs':p,'mode':'fresh_irish_planning_calculation','source_sha256':SOURCE_HASH,
                'source_model':'EirGrid TYTFS2024 Winter Peak 2024/25',
                'limitations':LIMITATIONS,'operationally_validated':False,
                'physical_actions_executed':False,'field_savings_MWh':None,
                'search_protocol':'Fixed 25 MW coarse grid plus exact availability; locally refine the highest passing point to 0.25 MW. No global optimum claim.'}
        result['preparation']={'tap_changes':engine.study.taps,'disconnected_shunt_buses':engine.study.shunts,
                               'source_consumer_demand_MW':engine.study.source_demand,
                               'slack_bus':10470,'wind_bus':1341}
        result['implementation_hashes']={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in [ROOT/'extension_engine.py',ROOT/'evidence_v4/code/run_study.py',
                      ROOT/'irish_audit/code/fixed_case.py',ROOT/'irish_audit/code/raw_equation_check.py']}
        if p['kind']=='snapshot':
            result['comparison']=engine.compare(p,p['load_factor'])
        else:
            profile=json.loads((ROOT/'extension_data/pilot_2025_01_01.json').read_text())
            result['profile']=profile
            result['interval_results']=[]
            result['limitations']=LIMITATIONS+[
                'Local hypothetical wind is assumed to follow the country aggregate shape, scaled to a 200 MW annual observed-peak equivalent; no local wind history is available.',
                'The first six UTC hours of 2025 were selected before reviewing model outcomes; no favourable interval selection.',
                'Both locations serve the same constant scheduled load at every interval, with identical total energy. No shifting, battery, rebound or profit claim.',
                'Time-varying generator ramp limits and commitment are not modelled; intervals are linked by the declared equal-service schedule only.',
                'Assumed redispatch, when selected, uses all source-online units within unchanged P limits. Fuel types and renewable availability of that fleet are unverified; incremental hypothetical wind is not net national wind savings.',
                'Reported Irish dispatch-down is contextual and is not treated as recoverable energy or used to infer a particular local network state.'
            ]
            fixed=p['profile_mode']=='wind_shape_fixed_demand'
            progress({'stage':'pilot','completed_intervals':0,'total_intervals':len(profile['rows'])})
            for i,r in enumerate(profile['rows']):
                factor=1. if fixed else r['all_island_demand_MW']/engine.study.source_demand
                request={**p,'wind_available_MW':r['assumed_local_wind_available_MW']}
                comparison=engine.compare(request,factor,'fixed_dispatch' if fixed else 'assumed_headroom_redispatch')
                result['interval_results'].append({'timestamp_utc':r['timestamp_utc'],'duration_hours':r['duration_hours'],
                    'observed_all_island_demand_MW':r['all_island_demand_MW'],
                    'source_load_factor':factor,'assumed_local_wind_available_MW':r['assumed_local_wind_available_MW'],
                    'comparison':comparison})
                progress({'stage':'pilot','completed_intervals':i+1,'total_intervals':len(profile['rows']),
                          'new_power_flows_run':engine.study.calls})
            result['summary']=integrate(result['interval_results'])
            result['service']={'power_MW':p['flex_MW'],'duration_hours':result['summary']['period_hours'],
                'energy_each_alternative_MWh':p['flex_MW']*result['summary']['period_hours'],
                'deadline':'2025-01-01T06:00:00Z','schedule':'Same constant load in both alternatives throughout the six-hour window.',
                'power_limit_MW':40,'deadline_energy_met':True,'real_asset_verified':False}
        result.update(new_power_flows_run=engine.study.calls,reused_identical_evaluations=engine.reused,
                      elapsed_seconds=time.perf_counter()-start)
        result['calculation_id']='fresh_'+hashlib.sha256(json.dumps(result,sort_keys=True,allow_nan=False).encode()).hexdigest()[:16]
        dump(output_path,result)
    dump(progress_path,{'status':'completed','new_power_flows_run':result['new_power_flows_run'],
                        'elapsed_seconds':result['elapsed_seconds'],'calculation_id':result['calculation_id']})
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--progress',required=True,type=Path)
    args=parser.parse_args()
    try:
        run(json.loads(args.request.read_text()),args.output,args.progress)
    except Exception as exc:
        dump(args.progress,{'status':'failed','error':'Fresh calculation failed. Review the installation or the model inputs.',
                            'error_type':type(exc).__name__})
        raise
