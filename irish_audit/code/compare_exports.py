"""Compare named common PSS/E device fields using VeraGrid's RAW parser."""
from pathlib import Path
import json,csv
from VeraGridEngine.IO.raw.raw_parser_writer import read_raw
from VeraGridEngine.basic_structures import Logger
ROOT=Path(__file__).resolve().parents[1]
cases=[]
for version in (33,35):
    log=Logger()
    cases.append(read_raw(str(ROOT/f'TYTFS2024_WP2024_V{version}.raw'),logger=log))
    log.to_df().to_csv(ROOT/f'results/raw_parser_v{version}_log.csv',index=False)
specs={
 'buses':(['I'],['VM','VA','IDE','NVHI','NVLO','BASKV']),
 'loads':(['I','ID'],['STATUS','PL','QL','IP','IQ','YP','YQ']),
 'generators':(['I','ID'],['PG','QG','QT','QB','VS','IREG','STAT','PT','PB','WMOD','WPF']),
 'branches':(['I','J','CKT'],['R','X','B','ST','GI','BI','GJ','BJ','RATEA']),
 'transformers':(['I','J','K','CKT'],['STAT','CW','CZ','CM','R1_2','X1_2','SBASE1_2','R2_3','X2_3','R3_1','X3_1','MAG1','MAG2']+
     [f'{x}{w}' for w in (1,2,3) for x in ['WINDV','ANG','COD','CONT','RMA','RMI','VMA','VMI','NTP','TAB']]),
 'switched_shunts':(['I'],['STAT','MODSW','BINIT','VSWHI','VSWLO','REGULATION_BUS','RMPCT']),
 'fixed_shunts':(['I','ID'],['STATUS','GL','BL'])}
report={}; details=[]
for section,(keys,fields) in specs.items():
    a,b=[{tuple(str(getattr(x,k)).strip() for k in keys):x for x in getattr(c,section)} for c in cases]
    changes={};missing=[]
    for field in fields:
        values=[]
        for key in a.keys() & b.keys():
            fa='SWREM' if field=='REGULATION_BUS' else field
            fb='SWREG' if field=='REGULATION_BUS' else field
            if not hasattr(a[key],fa) or not hasattr(b[key],fb):
                missing.append(field);break
            av,bv=getattr(a[key],fa),getattr(b[key],fb)
            if field in ('IREG','REGULATION_BUS'):
                av=av or a[key].I;bv=bv or b[key].I
            if av!=bv:
                delta=abs(av-bv) if isinstance(av,(int,float)) and isinstance(bv,(int,float)) else None
                values.append(delta)
                details.append({'section':section,'device':'/'.join(key),'field':field,'v33':av,'v35':bv,'abs_delta':delta})
        if values:changes[field]={'changed_count':len(values),'max_abs_delta':max((v for v in values if v is not None),default=None)}
    report[section]={'counts':[len(a),len(b)],'only_v33':[list(x) for x in a.keys()-b.keys()],
        'only_v35':[list(x) for x in b.keys()-a.keys()],'changed_fields':changes,'unavailable_fields':missing}
with (ROOT/'results/export_field_changes.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['section','device','field','v33','v35','abs_delta']);w.writeheader();w.writerows(details)
(ROOT/'results/export_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
