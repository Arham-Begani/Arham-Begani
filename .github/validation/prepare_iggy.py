"""Restore the exact locally reviewed Iggy commit, not a moving PR ref."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE = 'c5709f52042477d24c0847e6035bfdcafddc32bc'
HEAD = 'a3de19bd7923ba57931fadbe3a05b5b293ee3ada'
TREE = '8af1b6ccda2bf7925ea63ce733396dbdc9df677a'
BUNDLE_SHA256 = '221f0ecdc1d678e48c192f3d9d854638faea75d0c9a454a774bea441cab5a9da'
root = Path(os.environ['GITHUB_WORKSPACE'])
bundle = root / '.github/validation/iggy-4552.bundle'
assert hashlib.sha256(bundle.read_bytes()).hexdigest() == BUNDLE_SHA256
checkout = root / 'iggy'
def git(*args):
    return subprocess.check_output(['git', '-C', str(checkout), *args], text=True).strip()
subprocess.run(['git', 'init', str(checkout)], check=True)
git('remote', 'add', 'origin', 'https://github.com/apache/iggy.git')
git('fetch', '--depth=1', '--no-tags', 'origin', BASE)
git('checkout', '--detach', 'FETCH_HEAD')
git('bundle', 'verify', str(bundle))
git('fetch', str(bundle), 'refs/heads/feat/node-client-events')
git('checkout', '--detach', HEAD)
assert git('rev-parse', 'HEAD') == HEAD
assert git('rev-parse', 'HEAD^{tree}') == TREE
assert git('status', '--porcelain') == ''
evidence = Path(os.environ['RUNNER_TEMP']) / 'iggy-results'
evidence.mkdir(exist_ok=True)
(evidence / 'identity.json').write_text(json.dumps({
    'base': BASE, 'head': HEAD, 'tree': TREE, 'bundle_sha256': BUNDLE_SHA256,
    'environment': 'GitHub-hosted Ubuntu validation; separate from the recorded Windows local runs',
}, indent=2) + '\n')
print('Verified exact source:', HEAD, TREE)
