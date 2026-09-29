"""Create a portable ZIP and SHA-256 manifest; excludes local secrets/caches."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.env','.venv','__pycache__','scenario_audit','node_modules','browser-qa-results','dom-qa-results','.git','extension_runs','readability-qa-results','DEMO_CHECK_RESULT.json'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT.parent/'Curtailment_Action_Lab.zip')
    args=parser.parse_args()
    output=args.output.resolve()
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and not any(s in EXCLUDED or s.startswith('actionlab_irish_') for s in p.relative_to(ROOT).parts) and p.suffix not in ('.pyc','.tmp') and p.name!='MANIFEST.sha256' and p.resolve()!=output)
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files)
    (ROOT/'MANIFEST.sha256').write_text(manifest,encoding='utf-8')
    files.append(ROOT/'MANIFEST.sha256')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as archive:
        for p in files:
            archive.write(p,'Curtailment_Action_Lab/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output) as archive:
        bad=archive.testzip()
        if bad: raise SystemExit('ZIP integrity failure: '+bad)
    print(json.dumps({'path':str(output),'files':len(files),'bytes':output.stat().st_size,'crc':'passed'}))

if __name__=='__main__':main()
