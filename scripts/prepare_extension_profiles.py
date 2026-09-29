"""Extract a predeclared six-hour planning pilot from public EirGrid sources.

Reads original workbooks without modifying them. The generated JSON separates
observed national values from assumed local wind and asset inputs.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import argparse, hashlib, json, math
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
SYSTEM_HASH='11eec44649426878e850f23949e3cbef9388252313062ab98a719dc405ceb6cc'
DD_HASH='78ea2262da0deff153e49201d0103aeb3ac30b68dbc612ac9096eaf88efc4dbb'

def utc(value,offset):
    if not isinstance(value,datetime):
        value=datetime(1899,12,30)+timedelta(days=float(value))
    value=value.replace(microsecond=0)
    return (value-timedelta(hours=float(offset))).replace(tzinfo=timezone.utc)

def finite(value):
    if not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('A required source cell is missing or non-numeric.')
    return float(value)

def build(folder):
    sysfile=folder/'System-Data-Qtr-Hourly-2025-v12.xlsx'
    ddfile=folder/'DD-HH-2025-v10.xlsx'
    assert hashlib.sha256(sysfile.read_bytes()).hexdigest()==SYSTEM_HASH
    assert hashlib.sha256(ddfile.read_bytes()).hexdigest()==DD_HASH
    wb=load_workbook(sysfile,read_only=True,data_only=True)
    rows=wb['System Data'].iter_rows(values_only=True)
    header=next(rows);ix={x:i for i,x in enumerate(header) if x}
    observed={}
    for r in rows:
        t=utc(r[ix['DateTime']],r[ix['GMT Offset']])
        if t in observed:raise ValueError('Duplicate UTC quarter-hour.')
        observed[t]={k:finite(r[ix[k]]) for k in ['IE Demand','NI Demand','AI Demand','IE Wind Availability','NI Wind Availability','IE Wind Generation']}
    wb.close()
    times=sorted(observed)
    assert len(times)==35040 and times[0]==datetime(2025,1,1,tzinfo=timezone.utc)
    assert times[-1]==datetime(2025,12,31,23,45,tzinfo=timezone.utc)
    assert all(b-a==timedelta(minutes=15) for a,b in zip(times,times[1:]))
    reconcile=max(abs(x['AI Demand']-x['IE Demand']-x['NI Demand']) for x in observed.values())
    discrepancies=[{'timestamp_utc':t.isoformat().replace('+00:00','Z'),
        'AI_demand_MW':x['AI Demand'],'IE_plus_NI_demand_MW':x['IE Demand']+x['NI Demand'],
        'difference_MW':x['AI Demand']-x['IE Demand']-x['NI Demand']}
        for t,x in observed.items() if abs(x['AI Demand']-x['IE Demand']-x['NI Demand'])>=.011]
    peak=max(x['IE Wind Availability'] for x in observed.values())
    wb=load_workbook(ddfile,read_only=True,data_only=True)
    rows=wb['DD HH'].iter_rows(values_only=True)
    header=next(rows);ix={x:i for i,x in enumerate(header) if x}
    dd={}
    for r in rows:
        if r[ix['UT_TYPE']]!='Wind' or r[ix['JURISDICTION']]!='IE':continue
        t=utc(r[ix['HH_TIMESTAMP']],r[ix['GMT_OFFSET']])
        if t in dd:raise ValueError('Duplicate UTC dispatch-down half-hour.')
        dd[t]={'reported_IE_dispatch_down_MWh':finite(r[ix['Sum of DD_MWH']]),
               'reported_IE_constraints_MWh':finite(r[ix['Sum of CONSTRAINTS_MWH']])}
    wb.close()
    ddt=sorted(dd)
    assert len(ddt)==17520 and all(b-a==timedelta(minutes=30) for a,b in zip(ddt,ddt[1:]))
    selected=[]
    start=datetime(2025,1,1,tzinfo=timezone.utc)
    for i in range(12):
        t=start+timedelta(minutes=30*i)
        pair=[observed[t],observed[t+timedelta(minutes=15)]]
        assert all(abs(x['AI Demand']-x['IE Demand']-x['NI Demand'])<.011 for x in pair), 'Pilot demand does not reconcile; do not impute.'
        mean=lambda name:sum(r[name] for r in pair)/2
        selected.append({'timestamp_utc':t.isoformat().replace('+00:00','Z'),'duration_hours':.5,
          'all_island_demand_MW':mean('AI Demand'),'IE_wind_available_MW':mean('IE Wind Availability'),
          'IE_wind_actual_MW':mean('IE Wind Generation'),
          'assumed_local_wind_available_MW':200*mean('IE Wind Availability')/peak,**dd[t]})
    report={'selection':'First six UTC hours of 2025, fixed before model outcomes.',
      'start_utc':'2025-01-01T00:00:00Z','end_utc_exclusive':'2025-01-01T06:00:00Z',
      'national_observations':True,'local_wind_observed':False,'asset_observed':False,
      'local_wind_rule':'200 MW × half-hour mean IE wind availability / maximum 2025 quarter-hour IE wind availability. Historical shape assumption, not a forecast.',
      'normalisation_peak_IE_wind_MW':peak,'half_hour_rule':'Mean of two consecutive quarter-hour MW observations. Reported dispatch-down remains original MWh.',
      'audit':{'system_quarter_hours':len(times),'dispatch_down_half_hours':len(dd),
        'maximum_AI_minus_IE_minus_NI_demand_MW':reconcile,
        'demand_reconciliation_issues':discrepancies,
        'pilot_demand_reconciles':True,'source_values_corrected':False,'utc_gaps':0,'utc_duplicates':0,
        'pilot_half_hours':len(selected)},
      'sources':[{'name':sysfile.name,'sha256':SYSTEM_HASH,'url':'https://cms.eirgrid.ie/sites/default/files/publications/'+sysfile.name},
                 {'name':ddfile.name,'sha256':DD_HASH,'url':'https://cms.eirgrid.ie/sites/default/files/publications/'+ddfile.name}],
      'rows':selected}
    out=ROOT/'extension_data/pilot_2025_01_01.json'
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'saved':str(out),'audit':report['audit'],'wind_peak_MW':peak}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source_folder',type=Path)
    build(p.parse_args().source_folder)
