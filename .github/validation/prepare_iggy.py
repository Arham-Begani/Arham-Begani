"""Restore the exact locally reviewed Iggy commit, not a moving PR ref."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE = 'af99cd9f74680495280aa69ad3e71152c7b20e8e'
HEAD = '4f0b105e9420010ebcc90cf246a231da10b2a53b'
TREE = '7d5b1e2b4812894d8e3a45fd4e0df154b77c668f'
BUNDLE_SHA256 = '5e9a4b65103fe5282902b7545df8899603d178450cfb57c03f6a9459db992c76'
root = Path(os.environ['GITHUB_WORKSPACE'])
bundle = root / '.github/validation/iggy-4552.bundle'
assert hashlib.sha256(bundle.read_bytes()).hexdigest() == BUNDLE_SHA256
checkout = root / 'iggy'
def git(*args):
    return subprocess.check_output(['git', '-C', str(checkout), *args], text=True).strip()
subprocess.run(['git', 'init', str(checkout)], check=True)
git('remote', 'add', 'origin', 'https://github.com/apache/iggy.git')
git('fetch', '--depth=1', '--no-tags', 'origin', BASE)
git('fetch', '--depth=1', '--no-tags', 'origin', '87528db58f2941e180547b54860dc855c161594b')
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
