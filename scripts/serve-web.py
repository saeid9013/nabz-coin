"""Serve the web app locally; optionally proxy read-only API requests to one backend."""
import argparse
import json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import urllib.request
import urllib.error
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / 'apps' / 'web'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--api-url', default='')
    parser.add_argument('--mode', choices=['demo', 'live'], default='demo')
    args = parser.parse_args()
    if args.api_url:
        target = urlsplit(args.api_url)
        if target.scheme not in {'http', 'https'} or not target.hostname or target.username or target.password or target.query or target.fragment or target.path not in {'', '/'}:
            parser.error('--api-url must be an HTTP(S) backend origin without credentials or path')

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT), **kw)

        def end_headers(self):
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
            super().end_headers()

        def do_GET(self):
            if self.path == '/web-config.json':
                body = json.dumps({'mode': args.mode}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path.startswith('/api/v1/'):
                if not args.api_url:
                    self.send_error(503, 'Backend proxy not configured')
                    return
                # Only fixed-origin public API GETs; never forward cookies, secrets or auth.
                request = urllib.request.Request(args.api_url.rstrip('/') + self.path, headers={'Accept': 'application/json'})
                class NoRedirect(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self, *a, **kw):
                        return None
                try:
                    with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as response:
                        body = response.read(4 * 1024 * 1024 + 1)
                        if len(body) > 4 * 1024 * 1024:
                            self.send_error(502, 'API response too large')
                            return
                        self.send_response(response.status)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_header('Content-Length', str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                except urllib.error.HTTPError as error:
                    self.send_error(error.code, 'Backend request failed')
                except (urllib.error.URLError, TimeoutError):
                    self.send_error(503, 'Backend unavailable')
                return
            super().do_GET()

    print(f'Nabz web: http://127.0.0.1:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()

if __name__ == '__main__':
    main()
