"""Exploratory import/solve with a separately developed PSS/E converter.

Convergence here is not a validation certificate. Preserve converter warnings
and compare device coverage before using a result as a cross-check.
"""
from pathlib import Path
import argparse, json, time, traceback
import numpy as np
import VeraGridEngine as vg

ROOT = Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser()
ap.add_argument('--version',choices=['33','35'],default='33')
ap.add_argument('--controls',choices=['fixed','enabled'],default='fixed')
args=ap.parse_args()
out=ROOT/'results'/('veragrid_v'+args.version+'_'+args.controls)
out.mkdir(parents=True,exist_ok=True)
report={'package':'VeraGridEngine','version':'6.7.1','raw_version':args.version,
        'controls':args.controls,'status':'EXPLORATORY_COVERAGE_NOT_YET_VALIDATED'}
start=time.perf_counter()
try:
    loader=vg.FileOpen(str(ROOT/f'TYTFS2024_WP2024_V{args.version}.raw'))
    grid=loader.open()
    loader.logger.to_df().to_csv(out/'import_log.csv',index=False)
    report['device_counts']={k:len(getattr(grid,k)) for k in
        ['buses','lines','transformers2w','transformers3w','generators','loads','shunts','hvdc_lines']}
    print('Loaded',report['device_counts'],flush=True)
    enabled=args.controls=='enabled'
    opts=vg.PowerFlowOptions(tolerance=1e-8,max_iter=50,retry_with_other_methods=False,
        control_q=enabled,control_taps_modules=enabled,control_taps_phase=enabled,
        control_remote_voltage=enabled,apply_temperature_correction=False,
        use_stored_guess=True,initialize_angles=False)
    driver=vg.PowerFlowDriver(grid,opts)
    driver.run()
    driver.logger.to_df().to_csv(out/'solve_log.csv',index=False)
    r=driver.results
    report['converged']=bool(r.converged)
    report['error']=float(r.error)
    report['elapsed_s']=time.perf_counter()-start
    vm=np.abs(r.voltage)
    lo=np.array([b.Vmin for b in grid.buses]);hi=np.array([b.Vmax for b in grid.buses])
    active=np.array([b.active for b in grid.buses])
    bad=active&((vm<lo-1e-6)|(vm>hi+1e-6))
    report['voltage_violations']=int(sum(bad))
    report['voltage_violations_ge_100kv']=int(sum(bad & (np.array([b.Vnom for b in grid.buses])>=100)))
    report['max_absolute_loading']=float(np.max(np.abs(r.loading)))
    import pandas as pd
    pd.DataFrame({'code':[b.code for b in grid.buses],'name':[b.name for b in grid.buses],
        'active':active,'Vnom':[b.Vnom for b in grid.buses],'Vm':vm,
        'Va_deg':np.angle(r.voltage,deg=True),'Vmin':lo,'Vmax':hi,
        'source_Vm':[b.Vm0 for b in grid.buses],'source_Va_deg':[np.rad2deg(b.Va0) for b in grid.buses],
        'violation':bad}).to_csv(out/'bus_results.csv',index=False)
    np.savez_compressed(out/'electrical_results.npz',voltage=r.voltage,Sf=r.Sf,St=r.St,loading=r.loading)
except Exception as exc:
    report['exception']=repr(exc)
    (out/'traceback.txt').write_text(traceback.format_exc())
finally:
    report['elapsed_s']=time.perf_counter()-start
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
