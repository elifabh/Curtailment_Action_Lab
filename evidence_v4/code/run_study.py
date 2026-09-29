"""Reproduce the preregistered, conditional flexibility experiment.

No market, device or AI requests. Every candidate is a hypothetical connection
point load. This is a snapshot planning study, not field curtailment evidence.
"""
from pathlib import Path
import sys,json,time,hashlib,platform
try:
    import resource
except ImportError:
    resource=None
from copy import deepcopy
from collections import deque,defaultdict
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'irish_audit/code'))
from wind_screen import setup
from fixed_case import solve,direct_check,recover_tie_flows
from raw_equation_check import verify
from source_audit import rows

OUT=ROOT/'evidence_v4/results'
PROTO=ROOT/'evidence_v4/PROTOCOL.json'

def dump(path,obj):
    path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def peak_rss_mib():
    if resource is None:return None
    divisor=1024*1024 if sys.platform=='darwin' else 1024
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/divisor

class Study:
    def __init__(self):
        t=time.perf_counter()
        self.ppc,self.meta,self.taps,self.shunts=setup()
        _,self.raw=rows(ROOT/'irish_audit/TYTFS2024_WP2024_V33.raw')
        self.source_load=defaultdict(complex)
        for r in self.raw['LOAD']:
            if int(r[2]) and int(r[0]) in self.meta['source_ids']:
                self.source_load[int(r[0])]+=complex(float(r[5]),float(r[6]))
        self.source_demand=float(sum(v.real for v in self.source_load.values()))
        self.bybus={int(r[0]):r for r in self.raw['BUS']}
        self.original_index={v:k for k,v in self.meta['reverse_ids'].items()}
        self.line_ix=self.meta['branch_names'].index('line:1341:1701:1')
        self.records=[];self.curves={};self.calls=0
        self.setup_seconds=time.perf_counter()-t
        self.candidates=self.select_candidates()
        dump(OUT/'candidate_selection.json',{
            'selection_before_outcomes':True,'method':'Fixed in-service unweighted electrical-graph hops; source ID breaks ties.',
            'candidates':self.candidates,'actual_site_flexibility_verified':False})

    def select_candidates(self):
        graph=defaultdict(set)
        for b in self.ppc['branch']:
            if b[10]>0:
                a,z=map(int,b[:2]);graph[a].add(z);graph[z].add(a)
        origin=self.meta['source_ids'][1341];distance={origin:0};q=deque([origin])
        while q:
            a=q.popleft()
            for z in sorted(graph[a]):
                if z not in distance:distance[z]=distance[a]+1;q.append(z)
        def info(bus):
            r=self.bybus[bus]
            return {'bus':bus,'name':r[1].strip(),'nominal_kV':float(r[2]),
                'graph_hops_to_wind':distance.get(self.meta['source_ids'][bus]),
                'assumed_flex_MW':20.,'real_asset_data':False}
        extras=[b for b,r in self.bybus.items() if b not in (1341,2072)
            and float(r[2])>=100 and int(r[3])!=4 and b in self.meta['source_ids']
            and self.meta['source_ids'][b] in distance]
        extras.sort(key=lambda b:(distance[self.meta['source_ids'][b]],b))
        # Distinct electrical nodes: ideal-tied aliases are not extra assets.
        selected=[1341,2072];seen={self.meta['source_ids'][b] for b in selected}
        for b in extras:
            if self.meta['source_ids'][b] not in seen:
                selected.append(b);seen.add(self.meta['source_ids'][b])
            if len(selected)==8:break
        return [info(b) for b in selected]

    def evaluate(self,wind,outage,alloc,load_factor=1.,phase='coarse'):
        start=time.perf_counter();case=deepcopy(self.ppc)
        injections={b:(load_factor-1)*s for b,s in self.source_load.items() if load_factor!=1}
        for b,p in alloc.items():injections[b]=injections.get(b,0j)+p
        for b,s in injections.items():
            i=self.meta['source_ids'][b];case['bus'][i,2]+=s.real;case['bus'][i,3]+=s.imag
        case['bus'][self.meta['source_ids'][1341],2]-=wind
        case['branch'][self.line_ix,10]=0 if outage else self.ppc['branch'][self.line_ix,10]
        out,status=solve(case);solved=time.perf_counter()
        ch=direct_check(out,self.meta);direct_done=time.perf_counter()
        raw=None;tie=None
        if status['converged'] and ch['passes_implemented_checks']:
            raw=verify(out,self.meta,tap_changes=self.taps,shunt_off=self.shunts,
                branch_off=['line:1341:1701:1'] if outage else [],wind_mw=wind,extra_load=injections)
            if raw['passed']:
                mm={**self.meta,'full':deepcopy(self.meta['full'])}
                mm['full']['bus'][self.original_index[1341],2]-=wind
                for b,s in injections.items():
                    i=self.original_index[b];mm['full']['bus'][i,2]+=s.real;mm['full']['bus'][i,3]+=s.imag
                for b in self.shunts:mm['full']['bus'][self.original_index[b],5]-=25.
                t=recover_tie_flows(out,mm)
                tie={k:v for k,v in t.items() if k!='flows'}
        passed=bool(status['converged'] and ch['passes_implemented_checks'] and raw and raw['passed']
            and tie and tie['max_nodal_balance_residual_MVA']<1e-4
            and tie['tree_overloads']==0 and tie['cyclic_allocation_overloads']==0)
        other=float(out['gen'][out['gen'][:,7]>0,1].sum())
        source_injection=sum(x['P_MW'] for x in self.meta['source_import']['hvdc_terminal_boundary_injections'])
        total_demand=self.source_demand*load_factor+sum(alloc.values())
        losses=other+wind+source_injection-total_demand
        self.calls+=1
        r={'id':f'pf_{self.calls:04d}','wind_MW':float(wind),'line_outage':bool(outage),
            'flex_allocation_MW':{str(b):float(p) for b,p in alloc.items()},'source_load_factor':load_factor,
            'total_consumer_demand_MW':total_demand,'other_generation_MW':other,'network_losses_MW':losses,
            'passes_declared_snapshot_checks':passed,'solver_converged':bool(status['converged']),
            'violations':ch['violations'],'max_rated_branch_loading':ch['max_rated_branch_loading'],
            'direct_balance_max_MVA':ch['direct_balance_max_MVA'],
            'direct_flow_difference_MVA':ch['direct_branch_flow_difference_MVA'],
            'raw_equations':{k:v for k,v in raw.items() if k not in ('method','fixed_boundary_caveat')} if raw else None,
            'ideal_ties':tie,'elapsed_seconds':time.perf_counter()-start,
            'solver_seconds':solved-start,'direct_check_seconds':direct_done-solved,
            'verification_seconds':time.perf_counter()-direct_done,'phase':phase,
            'operationally_validated':False}
        self.records.append(r)
        with (OUT/'evaluations.jsonl').open('a') as f:f.write(json.dumps(r,allow_nan=False)+'\n')
        return r,out

    def curve(self,name,alloc,outage=True,load_factor=1.):
        # Reuse only identical physical inputs; never count reuse as a solver call.
        key=json.dumps([sorted(alloc.items()),bool(outage),load_factor])
        if key in self.curves:
            r=deepcopy(self.curves[key]);r['name']=name;r['reused_exact_inputs']=True
            return r
        start=time.perf_counter();points=[];best=None;beststate=None;calls0=self.calls
        for wind in range(0,201,25):
            r,out=self.evaluate(wind,outage,alloc,load_factor);points.append(r)
            if r['passes_declared_snapshot_checks']:best=r;beststate=out
        if best is not None:
            low=best['wind_MW'];high=min(low+25.,200.)
            while high-low>0.25:
                wind=(low+high)/2;r,out=self.evaluate(wind,outage,alloc,load_factor,'refinement');points.append(r)
                if r['passes_declared_snapshot_checks']:low=wind;best=r;beststate=out
                else:high=wind
        r={'name':name,'flex_allocation_MW':alloc,'line_outage':outage,'source_load_factor':load_factor,
            'points':points,'best_tested':best,'calls':self.calls-calls0,
            'elapsed_seconds':time.perf_counter()-start,'reused_exact_inputs':False}
        if best is not None:
            path=OUT/f'{name}_best.npz'
            np.savez_compressed(path,**{k:beststate[k] for k in ['baseMVA','bus','gen','branch']})
            r['state_file']=path.name;r['state_sha256']=sha(path)
        self.curves[key]=deepcopy(r)
        dump(OUT/f'{name}.json',r)
        print(json.dumps({'curve':name,'best_tested_wind_MW':best['wind_MW'] if best else None,
            'new_power_flows':r['calls'],'seconds':round(r['elapsed_seconds'],2)}),flush=True)
        return r

def select(curve,availability):
    p=[r for r in curve['points'] if r['passes_declared_snapshot_checks'] and r['wind_MW']<=availability]
    return max(p,key=lambda r:r['wind_MW']) if p else None

def pair(near,far,availability):
    a=select(far,availability);b=select(near,availability)
    equal=a is not None and b is not None and abs(a['total_consumer_demand_MW']-b['total_consumer_demand_MW'])<1e-6
    delta=b['wind_MW']-a['wind_MW'] if equal else None
    return {'wind_available_MW':availability,'baseline':a,'selected':b,'comparable':equal,
        'additional_wind_MW':delta,
        'other_generation_reduction_MW':a['other_generation_MW']-b['other_generation_MW'] if equal else None,
        'interpretation':'positive' if delta is not None and delta>0.5 else 'negative' if delta is not None and delta<-.5 else 'neutral' if equal else 'blocked',
        'reason':None if equal else 'No checked point under the available-wind bound for at least one alternative. This is a limit of the fixed-control study, not a proof that the real grid cannot operate.'}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'report.json').exists():raise SystemExit('A report already exists. Preserve it; use a new experiment directory for a new run.')
    if (OUT/'evaluations.jsonl').exists():raise SystemExit('Partial evaluations exist. Preserve them before an explicit new run.')
    start=time.perf_counter();s=Study();protocol=json.loads(PROTO.read_text())
    primary=[];curves=[]
    for outage in [True,False]:
        for flex in protocol['flex_capacities_MW']:
            far=s.curve(f'pair_{int(outage)}_{flex}_far',{2072:float(flex)} if flex else {},outage)
            near=s.curve(f'pair_{int(outage)}_{flex}_near',{1341:float(flex)} if flex else {},outage)
            curves.extend([far,near])
            for available in protocol['wind_availability_MW']:
                primary.append({'flex_MW':flex,'line_outage':outage,'source_load_factor':1.,**pair(near,far,available)})
            dump(OUT/'primary_checkpoint.json',primary)
    stress=[]
    for factor in protocol['additional_stress_load_factors']:
        far=s.curve(f'stress_{factor}_far',{2072:20.},True,factor)
        near=s.curve(f'stress_{factor}_near',{1341:20.},True,factor)
        curves.extend([far,near]);stress.append({'source_load_factor':factor,'flex_MW':20.,'line_outage':True,**pair(near,far,200)})
    portfolio=[]
    for c in s.candidates:
        curve=s.curve(f'portfolio_{c["bus"]}',{c['bus']:20.},True)
        curves.append(curve);portfolio.append({**c,'curve':curve})
    uniform=s.curve('portfolio_uniform',{c['bus']:20./len(s.candidates) for c in s.candidates},True)
    curves.append(uniform)
    summary={label:sum(x['interpretation']==label for x in primary) for label in ['positive','neutral','negative','blocked']}
    summary.update(total_pairs=len(primary),comparable_pairs=sum(x['comparable'] for x in primary))
    valid=[x['additional_wind_MW'] for x in primary if x['comparable'] and x['flex_MW']>0]
    report={'protocol_sha256':sha(PROTO),'source_sha256':protocol['source_sha256'],
        'scope':'Conditional prepared-network snapshot experiment, not an operational capability certification or field curtailment trial.',
        'primary_summary':summary,'primary_pairs':primary,'stress_pairs':stress,
        'portfolio':portfolio,'uniform_allocation':uniform,
        'curves':[{k:v for k,v in c.items() if k!='points'} for c in curves],
        'setup_seconds':s.setup_seconds,'total_elapsed_seconds':time.perf_counter()-start,
        'new_power_flows':s.calls,'passing_power_flows':sum(r['passes_declared_snapshot_checks'] for r in s.records),
        'runtime':{'python':platform.python_version(),'numpy':np.__version__,'platform':platform.system(),
            'peak_rss_MiB':peak_rss_mib(),
            'single_run_timing_not_speed_benchmark':True},
        'primary_nonzero_flex_delta_range_MW':[min(valid),max(valid)] if valid else None,
        'all_failures_retained_in':'evaluations.jsonl','operationally_validated':False,'field_savings_MWh':None,
        'assumptions':protocol['preparation']}
    dump(OUT/'report.json',report)
    print('COMPLETE',json.dumps({'summary':summary,'calls':s.calls,'seconds':report['total_elapsed_seconds']}),flush=True)

if __name__=='__main__':main()
