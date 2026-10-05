"""Start and stop only our own temporary localhost API process for an HTTP smoke test."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

root = Path(__file__).resolve().parents[1]
qa = root / '.tools' / 'qa'
qa.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, APP_MODE='demo', DATABASE_PATH=str(qa / 'smoke-demo.sqlite3'))
with (qa / 'api-smoke.log').open('w', encoding='utf-8') as log:
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'nabz.main:create_app', '--factory',
        '--host', '127.0.0.1', '--port', '18080'], cwd=root / 'services/api', env=env, stdout=log, stderr=log)
    try:
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError('API exited; see .tools/qa/api-smoke.log')
            try:
                with urllib.request.urlopen('http://127.0.0.1:18080/health', timeout=1) as response:
                    health = json.load(response)
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError('API did not become ready')
        with urllib.request.urlopen('http://127.0.0.1:18080/api/v1/market', timeout=3) as response:
            market = json.load(response)
        assert health['mode'] == 'demo' and market['mode'] == 'demo' and len(market['items']) == 100
        print('HTTP smoke passed: health=ok, market=100 demo coins; server process stopped afterward')
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
