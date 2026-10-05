"""Local live stack. Secrets remain in an ignored server-only file."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

def main():
    secret_file = ROOT / '.tools/live/secrets.json'
    if not secret_file.exists():
        raise SystemExit('Server key file is missing: .tools/live/secrets.json')
    key = json.loads(secret_file.read_text(encoding='utf-8-sig'))['CMC_API_KEY']
    env = {**os.environ, 'APP_MODE': 'live', 'CMC_API_KEY': key,
           'DATABASE_PATH': str(ROOT / '.tools/live/market.sqlite3'),
           'CMC_METADATA_ENABLED': 'false', 'CMC_INDICES_ENABLED': 'false',
           'CMC_HISTORY_IDS': '', 'NEWS_FEED_URLS': '', 'TRANSLATION_PROVIDER': 'disabled'}
    processes = []
    try:
        subprocess.run([sys.executable, '-m', 'nabz.scheduler', '--once'], cwd=ROOT / 'services/api', env=env, check=True)
        processes.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'nabz.main:create_app', '--factory', '--host', '127.0.0.1', '--port', '8000'], cwd=ROOT / 'services/api', env=env))
        processes.append(subprocess.Popen([sys.executable, '-m', 'nabz.scheduler'], cwd=ROOT / 'services/api', env=env))
        processes.append(subprocess.Popen([sys.executable, str(ROOT / 'scripts/serve-web.py'), '--port', '8080', '--api-url', 'http://127.0.0.1:8000', '--mode', 'live']))
        print('Live web: http://127.0.0.1:8080 ; Ctrl+C stops this stack.', flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)

if __name__ == '__main__':
    main()
