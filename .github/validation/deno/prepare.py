import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

folder = Path(__file__).resolve().parent
manifest = json.loads((folder / 'manifest.json').read_text())
source = Path('deno')
patch = folder / 'fix.patch'
assert hashlib.sha256(patch.read_bytes()).hexdigest() == manifest['patch_sha256']
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == manifest['base']
if '--verify' not in sys.argv:
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=source, check=True)
    subprocess.run(['git', 'apply', '--index', str(patch)], cwd=source, check=True)
for name, expected in manifest['files'].items():
    assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected, name
subprocess.run(['git', 'diff', '--exit-code'], cwd=source, check=True)
results = Path(os.environ['RUNNER_TEMP']) / 'deno-results'
results.mkdir(exist_ok=True)
(results / 'manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
