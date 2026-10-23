"""Restore the exact locally reviewed Iggy commit, not a moving PR ref."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE = '87528db58f2941e180547b54860dc855c161594b'
HEAD = '672e5ff11df234f1e8999d7a31426ec823ec9588'
TREE = 'efd2b794c511c9ffe7c7962fed3c349339f0779c'
BUNDLE_SHA256 = 'fdc391fa4bed653dac52ec99066af34e7b9fe2e6f77a0741d3524e907bdf8e04'
root = Path(os.environ['GITHUB_WORKSPACE'])
bundle = root / '.github/validation/iggy-4552.bundle'
assert hashlib.sha256(bundle.read_bytes()).hexdigest() == BUNDLE_SHA256
checkout = root / 'iggy'
def git(*args):
    return subprocess.check_output(['git', '-C', str(checkout), *args], text=True).strip()
subprocess.run(['git', 'init', str(checkout)], check=True)
git('remote', 'add', 'origin', 'https://github.com/apache/iggy.git')
git('fetch', '--depth=1', '--no-tags', 'origin', BASE)
git('fetch', '--depth=1', '--no-tags', 'origin', 'c5709f52042477d24c0847e6035bfdcafddc32bc')
git('checkout', '--detach', BASE)
git('bundle', 'verify', str(bundle))
git('fetch', str(bundle), 'refs/heads/fix/node-client-event-review-oct23')
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
