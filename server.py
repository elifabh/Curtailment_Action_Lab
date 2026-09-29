"""Local Curtailment Action Lab. No commands are sent to physical equipment."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import app_service as service

ROOT = Path(__file__).resolve().parent


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON fields are unsupported.')
        result[key] = value
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = 'ActionLab/6.0'

    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def send_bytes(self, status, content, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, status, value):
        self.send_bytes(status, json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), 'application/json; charset=utf-8')

    def do_GET(self):
        if not self.valid_host():
            return self.send_json(403, {'error': 'Use the local URL printed by the server.'})
        path = urlsplit(self.path).path
        from study_service import study_data
        import decision_service
        import extension_service
        from ai.agent_runner import agent_status
        endpoints = {'/api/config': service.configuration, '/api/evidence': service.evidence, '/api/evaluation': service.evaluation, '/api/study':study_data, '/api/decision-config':lambda:{**decision_service.configuration(),'ai':agent_status()}, '/api/extension-config':extension_service.configuration, '/api/extension-example':extension_service.saved_example}
        endpoints['/api/extension-pilot-fixed']=lambda:extension_service.saved_example('pilot_fixed_demand')
        endpoints['/api/extension-pilot-demand']=lambda:extension_service.saved_example('pilot_observed_demand')
        if path == '/api/health':
            return self.send_json(200, {'status': 'ok', 'version': '6.0', 'physical_actions_executed': False})
        if path in endpoints:
            try:
                return self.send_json(200, endpoints[path]())
            except RuntimeError as exc:
                return self.send_json(503, {'error': str(exc)})
            except (OSError, ValueError, KeyError, TypeError):
                return self.send_json(503, {'error': 'A required demo record could not be loaded. Extract the complete ZIP, then restart the server.'})
        routes = {'/': ('web/index.html', 'text/html; charset=utf-8'),
                  '/extension':('web/extension.html','text/html; charset=utf-8'),
                  '/static/extension.css':('web/extension.css','text/css; charset=utf-8'),
                  '/static/extension.js':('web/extension.js','application/javascript; charset=utf-8'),
                  '/static/style.css': ('web/style.css', 'text/css; charset=utf-8'),
                  '/static/app.js': ('web/app.js', 'application/javascript; charset=utf-8'),
                  '/static/reporting.js': ('web/reporting.js', 'application/javascript; charset=utf-8'),
                  '/static/study.js': ('web/study.js', 'application/javascript; charset=utf-8'),
                  '/static/decision-core.js':('web/decision-core.js','application/javascript; charset=utf-8'),
                  '/static/decision.js':('web/decision.js','application/javascript; charset=utf-8'),
                  '/static/presentation.js':('web/presentation.js','application/javascript; charset=utf-8'),
                  '/presentation/Pitch_EN.pdf':('presentation/Pitch_EN.pdf','application/pdf')}
        if path not in routes:
            return self.send_json(404, {'error': 'Not found.'})
        name, kind = routes[path]
        source = ROOT / name
        if not source.is_file():
            return self.send_json(503, {'error': 'A required interface file is missing. Extract the complete ZIP.'})
        return self.send_bytes(200, source.read_bytes(), kind)

    def do_POST(self):
        if not self.valid_host():
            return self.send_json(403, {'error': 'Invalid local host.'})
        origin = self.headers.get('Origin')
        port = self.server.server_port
        if origin is not None and origin not in (f'http://localhost:{port}', f'http://127.0.0.1:{port}'):
            return self.send_json(403, {'error': 'Only local same-origin requests are allowed.'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.send_json(415, {'error': 'Send application/json.'})
        from study_service import estimate_value
        from decision_service import analyse
        from ai.challenge_agent import run as challenge_run
        from extension_service import start as extension_start, status as extension_status
        routes = {'/api/extension-start':extension_start,'/api/extension-status':extension_status,'/api/decision':analyse,'/api/challenge-audit':challenge_run,'/api/value':estimate_value,'/api/evaluate': service.evaluate, '/api/sensitivity': service.sensitivity,
                  '/api/search': service.run_search, '/api/agent': lambda p: service.run_search(p, use_ai=True)}
        path = urlsplit(self.path).path
        if path not in routes:
            return self.send_json(404, {'error': 'Not found.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16000:
                raise ValueError('Request must contain 1–16,000 bytes.')
            payload = json.loads(self.rfile.read(length), object_pairs_hook=unique_object,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON is unsupported.')))
            if not isinstance(payload, dict):
                raise ValueError('Expected a JSON object.')
            return self.send_json(200, routes[path](payload))
        except (ValueError, TypeError, UnicodeError, OverflowError) as exc:
            return self.send_json(400, {'error': str(exc)})
        except RuntimeError as exc:
            return self.send_json(422, {'error': str(exc)})
        except Exception as exc:
            # Do not expose environment variables, provider responses or local paths.
            sys.stderr.write(f'Calculation error: {type(exc).__name__}\n')
            return self.send_json(500, {'error': 'The calculation could not complete. Check installation and try a recorded default scenario.'})

    def log_message(self, fmt, *args):
        sys.stderr.write('%s %s\n' % (self.address_string(), fmt % args))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Choose a port from 1024 to 65535.')
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError as exc:
        raise SystemExit(f'Could not start the server ({type(exc).__name__}). Try --port 8766.')
    runtime = 'Live local solver' if service.scientific_available() else 'Recorded results (install requirements.txt for new calculations)'
    print(f'\nCurtailment Action Lab v6\nOpen http://127.0.0.1:{args.port}\nFresh Irish experiments: http://127.0.0.1:{args.port}/extension\n{runtime}\nPress Ctrl+C to stop.\n', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
