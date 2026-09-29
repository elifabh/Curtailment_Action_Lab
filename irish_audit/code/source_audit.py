"""Direct-text audit of official companion PSS/E exports; no solver dependencies."""
from pathlib import Path
import csv, re, json, hashlib
ROOT=Path(__file__).resolve().parents[1]

def rows(path):
    lines=path.read_text(encoding='utf-8-sig').splitlines()
    version=int(next(csv.reader([next(x for x in lines if x.strip() and not x.startswith('@!'))],quotechar="'",skipinitialspace=True))[2])
    section='HEADER' if version>=35 else 'BUS'
    out={};start=0 if version>=35 else 3
    for line in lines[start:]:
        if line.startswith('@!') or not line.strip():continue
        marker=re.search(r'BEGIN (.+?) DATA',line)
        if line.lstrip().startswith('0 /'):
            section=marker.group(1) if marker else 'END';continue
        if line.lstrip().startswith('/') or line.strip()=='Q':continue
        out.setdefault(section,[]).append(next(csv.reader([line],quotechar="'",skipinitialspace=True)))
    return version,out

def main():
    paths=[ROOT/'TYTFS2024_WP2024_V33.raw',ROOT/'TYTFS2024_WP2024_V35.raw']
    parsed=[rows(p)[1] for p in paths]
    bus=[{int(r[0]):r for r in d['BUS']} for d in parsed]
    diffs=[]
    numeric_max={}
    for k in sorted(set(bus[0])|set(bus[1])):
        a,b=bus[0].get(k),bus[1].get(k)
        if a!=b:diffs.append({'bus':k,'v33':a,'v35':b})
    common=sorted(set(bus[0])&set(bus[1]))
    active=[k for k in common if int(bus[0][k][3])!=4]
    import statistics
    phase_shift=statistics.median(float(bus[1][k][8])-float(bus[0][k][8]) for k in active)
    phase_error=max(abs(float(bus[1][k][8])-float(bus[0][k][8])-phase_shift) for k in active)
    for j in [2,3,4,5,6,7,9,10,11,12]:
        numeric_max[str(j)]=max(abs(float(bus[1][k][j])-float(bus[0][k][j])) for k in common)
    header='\n'.join(paths[1].read_text().splitlines()[:23])
    settings={}
    for line in header.splitlines():
        if '=' in line:
            group=line.split(',')[0]
            settings[group]={k:v for k,v in re.findall(r'(\w+)=([^, ]+)',line)}
            if group=='SOLVER':settings[group]['algorithm']=line.split(',')[1].strip()
    bad=[]
    for k,r in bus[0].items():
        if int(r[3])!=4 and not float(r[10])-1e-9<=float(r[7])<=float(r[9])+1e-9:
            bad.append({'id':k,'name':r[1].strip(),'base_kv':float(r[2]),'vm':float(r[7]),'vmin':float(r[10]),'vmax':float(r[9])})
    all_bad={}
    for version,bs in zip((33,35),bus):
        records=[{'id':k,'name':r[1].strip(),'base_kv':float(r[2]),'vm':float(r[7]),'vmin':float(r[10]),'vmax':float(r[9])}
            for k,r in bs.items() if int(r[3])!=4 and not float(r[10])-1e-9<=float(r[7])<=float(r[9])+1e-9]
        all_bad[str(version)]={'total':len(records),'ge_100kv':sum(x['base_kv']>=100 for x in records),'records':records}
    d={'sources':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],
       'bus_counts':[len(x) for x in bus],'bus_record_difference_count':len(diffs),'common_bus_records_identical':not diffs,
       'common_bus_numeric_field_max_differences':numeric_max,
       'active_bus_uniform_phase_rotation_deg':phase_shift,
       'max_angle_difference_after_rotation_deg':phase_error,
       'bus_data_equivalent_up_to_angle_reference_and_printed_precision':all(v==0 for v in numeric_max.values()) and phase_error<=0.000100001,
       'v35_solution_settings':settings,'source_voltage_violations':bad,
       'source_voltage_violation_count':len(bad),'source_voltage_violations_ge_100kv':sum(x['base_kv']>=100 for x in bad),
       'voltage_violations_by_export':all_bad,
       'data_classification':{'official_files':'Irish transmission planning models, not live or historical dispatch measurements','additional_wind':'Hypothetical injection in the earlier comparison','reference_60mw':'Separate synthetic nine-bus experiment, not obtained from these Irish exports'},
       'correction_to_v2':'The V33 export omits system solution settings; its official V35 companion includes them. THRSHZ=0.0001 is documented for V35. The saved states differ; V35 settings cannot certify the V33 reconstruction.',
       'export_interchangeable':False}
    (ROOT/'results/source_audit.json').write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps({k:v for k,v in d.items() if k not in ('source_voltage_violations','voltage_violations_by_export')},indent=2))
if __name__=='__main__':main()
