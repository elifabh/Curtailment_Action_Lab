"""Local asynchronous fresh-calculation jobs. No cloud or device actions."""
from pathlib import Path
import importlib.util
import json
import re
import subprocess
import sys
import threading
import time
import uuid
from extension_engine import validate, schema, dump, LIMITATIONS

ROOT=Path(__file__).resolve().parent
JOBS=ROOT/'extension_runs'
LOCK=threading.Lock()
PROCESSES={}
SAVED={'snapshot_example':'One scenario: reproduced headline',
       'pilot_fixed_demand':'Six hours: wind profile, fixed demand',
       'pilot_observed_demand':'Six hours: demand profile, assumed redispatch'}

def configuration():
    missing=[x for x in ('numpy','scipy','pypower','grg_pssedata') if importlib.util.find_spec(x) is None]
    return {'available':not missing,'missing_dependencies':missing,'candidates':schema(),
            'baseline_bus':2072,'limits':{'wind_MW':[0,200],'flex_MW':[0,40],'load_factor':[.99,1.01]},
            'pilot_period':'1 January 2025, 00:00–06:00 UTC',
            'default':{'kind':'snapshot','candidate_bus':1701,'flex_MW':20.,'line_outage':True,
                       'wind_available_MW':200.,'load_factor':1.},
            'example_available':(ROOT/'extension_results/snapshot_example.json').is_file(),
            'saved_examples':[{'id':name,'label':label,'recorded_elapsed_seconds':json.loads((ROOT/'extension_results'/f'{name}.json').read_text()).get('elapsed_seconds')} for name,label in SAVED.items() if (ROOT/'extension_results'/f'{name}.json').is_file()],
            'limitations':LIMITATIONS,'ai_invokes_fresh_engine':False,
            'install_instructions':'Close the local server, run INSTALL_IRISH_EXTENSION.bat on Windows or bash INSTALL_IRISH_EXTENSION.sh on macOS/Linux, then start the server again.'}

def start(payload):
    p=validate(payload)
    if not configuration()['available']:
        raise RuntimeError('Install the Irish extension dependencies and restart the server. The saved demonstration remains available.')
    with LOCK:
        if any(v['process'].poll() is None for v in PROCESSES.values()):
            raise RuntimeError('A fresh calculation is already running. Wait for its result before starting another.')
        job=uuid.uuid4().hex
        path=JOBS/job
        path.mkdir(parents=True)
        dump(path/'request.json',p)
        dump(path/'progress.json',{'status':'starting','stage':'preparing','new_power_flows_run':0})
        log=(path/'worker.log').open('wb')
        process=subprocess.Popen([sys.executable,str(ROOT/'extension_engine.py'),
            '--request',str(path/'request.json'),'--output',str(path/'result.json'),
            '--progress',str(path/'progress.json')],cwd=ROOT,stdin=subprocess.DEVNULL,
            stdout=log,stderr=log)
        log.close()
        PROCESSES[job]={'process':process,'started':time.monotonic(),'kind':p['kind']}
        return {'job_id':job,'status':'starting','mode':'fresh_irish_planning_calculation'}

def status(payload):
    if not isinstance(payload,dict) or set(payload)!={'job_id'} or not isinstance(payload['job_id'],str) or not re.fullmatch('[a-f0-9]{32}',payload['job_id']):
        raise ValueError('Supply one valid calculation identifier.')
    job=payload['job_id'];path=JOBS/job
    if not (path/'request.json').is_file():raise ValueError('Calculation not found.')
    if job in PROCESSES:
        item=PROCESSES[job];p=item['process']
        maximum=1800 if item['kind']=='pilot' else 300
        if p.poll() is None and time.monotonic()-item['started']>maximum:
            p.terminate()
            dump(path/'progress.json',{'status':'failed','error':'Calculation time limit reached. No partial result is presented as a complete result.'})
        elif p.poll() is not None:
            prior=json.loads((path/'progress.json').read_text())
            if prior.get('status') not in ('failed','completed'):
                dump(path/'progress.json',{'status':'failed','error':'Calculation stopped before completion. Review the installation and model inputs.'})
    r=json.loads((path/'progress.json').read_text())
    if job not in PROCESSES and r.get('status') not in ('failed','completed'):
        request=json.loads((path/'request.json').read_text())
        maximum=1800 if request.get('kind')=='pilot' else 300
        if time.time()-(path/'progress.json').stat().st_mtime>maximum:
            r={'status':'failed','error':'No calculation progress was received after the server restarted. Start a new calculation.'}
            dump(path/'progress.json',r)
    result={'job_id':job,**r}
    if r['status']=='completed':
        if not (path/'result.json').is_file():
            return {'job_id':job,'status':'failed','error':'The completed calculation record is missing. Start a new calculation.'}
        result['result']=json.loads((path/'result.json').read_text())
    return result

def saved_example(name='snapshot_example'):
    if name not in SAVED:raise ValueError('Unknown recorded experiment.')
    f=ROOT/'extension_results'/f'{name}.json'
    if not f.exists():raise RuntimeError('No saved extension example is included.')
    return {'status':'completed','mode':'saved_extension_example','result':json.loads(f.read_text())}
