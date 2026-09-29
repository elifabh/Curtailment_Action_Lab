"""Bundle the English interface with explicitly recorded demo calculations."""
from pathlib import Path
import json
import re
import sys
import base64
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app_service as app
from study_service import study_data
from decision_service import configuration as decision_configuration


def main():
    config = app.configuration()
    config['mode'] = 'recorded_results'
    config['runtime'] = {'available':False,'message':'Recorded demo. Start the local server to calculate new scenarios.'}
    config['ai'] = {'enabled':False,'status':'disabled','provider':'Azure OpenAI', 'live_evaluation_status':'not_run',
                    'description':'Recorded demo. No live AI is running; use the local server and configure Azure for an actual agent run.'}
    for profile in config['profiles']:
        profile['runtime_available'] = False
    records = app.read_json('data/recorded.json', {})
    decision=decision_configuration()
    decision['ai']=config['ai']
    pdf=ROOT/'presentation/Pitch_EN.pdf'
    if not pdf.is_file() or not pdf.read_bytes().startswith(b'%PDF-'):
        raise SystemExit('A valid presentation/Pitch_EN.pdf is required for the embedded Presentation button.')
    data = {'config':config,'evidence':app.evidence(),'evaluation':app.evaluation(),'study':study_data(),
        'decision':decision,'presentation_pdf_base64':base64.b64encode(pdf.read_bytes()).decode('ascii'),**records}
    html = (ROOT/'web/index.html').read_text(encoding='utf-8')
    css = (ROOT/'web/style.css').read_text(encoding='utf-8')
    js = (ROOT/'web/app.js').read_text(encoding='utf-8')
    study_js = (ROOT/'web/study.js').read_text(encoding='utf-8')
    # Escaping '<' prevents embedded data from ending the script element.
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(',',':')).replace('<','\\u003c')
    html = re.sub(r'<link rel="stylesheet" href="/static/style.css">', lambda _: '<style>'+css+'</style>', html)
    html = html.replace('<script src="/static/app.js"></script>', '<script>window.ACTIONLAB_DATA='+encoded+';</script><script>'+js+'</script>')
    html = html.replace('<script src="/static/study.js"></script>', '<script>'+study_js+'</script>')
    for asset in ('reporting.js','decision-core.js','decision.js','presentation.js'):
        html=html.replace('<script src="/static/'+asset+'"></script>','<script>'+(ROOT/'web'/asset).read_text(encoding='utf-8')+'</script>')
    if any(asset in html for asset in ('/static/app.js','/static/study.js','/static/style.css','/static/decision','/static/presentation.js','/static/reporting.js')):
        raise SystemExit('Could not inline all application assets.')
    (ROOT/'OPEN_DEMO.html').write_text(html, encoding='utf-8')
    print('OPEN_DEMO.html built with recorded results; live AI disabled.')

if __name__ == '__main__':
    main()
