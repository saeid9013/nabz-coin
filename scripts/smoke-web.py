"""Check static web delivery and same-origin API proxy against a real demo backend."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]

def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

def main():
    api_port, web_port = port(), port()
    processes = []
    with tempfile.TemporaryDirectory(prefix='nabz-web-smoke-') as tmp:
        env = {**os.environ, 'APP_MODE': 'demo', 'DATABASE_PATH': str(Path(tmp) / 'demo.sqlite3')}
        try:
            processes.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'nabz.main:create_app', '--factory', '--host', '127.0.0.1', '--port', str(api_port)], cwd=ROOT / 'services/api', env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            processes.append(subprocess.Popen([sys.executable, str(ROOT / 'scripts/serve-web.py'), '--port', str(web_port), '--api-url', f'http://127.0.0.1:{api_port}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            origin = f'http://127.0.0.1:{web_port}'
            for _ in range(60):
                try:
                    with urllib.request.urlopen(origin + '/api/v1/market', timeout=2) as response:
                        market = json.load(response)
                    break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(.1)
            else:
                raise AssertionError('Web/backend startup failed')
            assert market['mode'] == 'demo' and len(market['items']) == 100
            for resource in ['/', '/app.js', '/ui.js', '/style.css', '/sw.js', '/manifest.webmanifest', '/assets/Vazirmatn-Regular.ttf']:
                with urllib.request.urlopen(origin + resource, timeout=2) as response:
                    assert response.status == 200 and response.read()
            with urllib.request.urlopen(origin + '/api/v1/coins/1/chart?range=7d', timeout=2) as response:
                chart = json.load(response)
                assert len(chart['points']) == 48
            try:
                urllib.request.urlopen(origin + '/api/v1/coins/1/chart?range=invalid', timeout=2)
                raise AssertionError('Invalid range should be rejected')
            except urllib.error.HTTPError as error:
                assert error.code == 422
            print('Web HTTP smoke passed: static assets, real demo backend proxy, chart and 422; temporary processes stopped.')
        finally:
            for process in reversed(processes):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

if __name__ == '__main__':
    main()
