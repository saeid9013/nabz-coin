"""Capture real Android screenshots as binary PNG; no synthetic fallback."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--adb', default='adb')
parser.add_argument('--device', required=True)
parser.add_argument('--name', required=True, help='For example market-dark-360-text2')
args = parser.parse_args()
if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in args.name):
    raise SystemExit('Screenshot name must use lowercase letters, digits, dash or underscore')
root = Path(__file__).resolve().parents[1]
out = root / 'docs/screenshots' / (args.name + '.png')
if out.exists():
    raise SystemExit('Existing screenshot preserved; choose a new name')
result = subprocess.run([args.adb, '-s', args.device, 'exec-out', 'screencap', '-p'],
    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
if not result.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
    raise SystemExit('Device did not return PNG; no screenshot saved')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(result.stdout)
print(out)
