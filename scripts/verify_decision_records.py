"""Check the decision matrix against its independently read physical records."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]

def main():
    d=json.loads((ROOT/'evidence_v5/results/challenge_matrix.json').read_text())
    assert d['protocol_sha256']==hashlib.sha256((ROOT/'evidence_v5/PROTOCOL.json').read_bytes()).hexdigest()
    assert d['source_sha256']==hashlib.sha256((ROOT/'irish_audit/TYTFS2024_WP2024_V33.raw').read_bytes()).hexdigest()
    refs=0;blocked=0;paired=0
    for c in d['cells']:
        s=next(x for x in d['scenarios'] if x['id']==c['scenario_id'])
        points={}
        for side,bus in [('baseline',2072),('selected',c['bus'])]:
            r=c[side+'_ref']
            if r is None:continue
            path=ROOT/r['file'];assert path.resolve().is_relative_to(ROOT.resolve())
            curve=json.loads(path.read_text());matches=[x for x in curve['points'] if x['id']==r['record_id']]
            assert len(matches)==1;pt=matches[0];refs+=1;points[side]=pt
            assert pt['passes_declared_snapshot_checks'] and pt['raw_equations']['passed']
            assert pt['source_load_factor']==s['source_load_factor'] and pt['line_outage']==s['line_outage']
            alloc={int(k):v for k,v in pt['flex_allocation_MW'].items() if v}
            assert alloc==({bus:s['flex_MW']} if s['flex_MW'] else {})
            valid=[x['wind_MW'] for x in curve['points'] if x['passes_declared_snapshot_checks'] and x['wind_MW']<=s['wind_available_MW']+1e-9]
            assert pt['wind_MW']==max(valid)==c[side+'_wind_MW']
        if c['comparable']:
            a,b=points['baseline'],points['selected'];paired+=1
            assert abs(a['total_consumer_demand_MW']-b['total_consumer_demand_MW'])<1e-6
            assert c['additional_wind_MW']==b['wind_MW']-a['wind_MW']
        else:
            blocked+=1;assert c['additional_wind_MW'] is None and c['block_reason']
    result={'passed':True,'paired_cells_checked':paired,'blocked_cells_preserved':blocked,'qualified_physical_references_checked':refs,'protocol_hash_matches':True,'raw_source_hash_matches':True,'meaning':'Record mapping and declared physical-check integrity; not operating approval.'}
    (ROOT/'validation/decision_record_integrity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
