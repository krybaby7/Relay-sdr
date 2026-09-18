"""Run bounded, fixture-only checks and write truthful durable results.

Dependencies and Chromium are installed by the branch-restricted workflow.
The caller publishes these results even on failure. This is not a release gate
substitute and does not test live model quality, telephony, or production data.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification' / 'preservation-2026-09-18'
OUT.mkdir(parents=True, exist_ok=True)
results = {
    'run_id': os.environ.get('GITHUB_RUN_ID'),
    'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'scope': 'Recovered native checkpoint. Mocked model/provider tests and loopback fictional browser fixture only. Not a completed release.',
    'checks': [],
}


def check(name, command, cwd, timeout=180):
    started = time.monotonic()
    try:
        run = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, errors='replace', timeout=timeout)
        code, output = run.returncode, run.stdout
    except subprocess.TimeoutExpired as exc:
        code = 124
        output = exc.stdout or ''
        if isinstance(output, bytes):
            output = output.decode('utf-8', 'replace')
        output += '\nVERIFICATION COMMAND TIMED OUT. This check did not pass.\n'
    except OSError as exc:
        code, output = 127, str(exc)
    (OUT / (name + '.txt')).write_text(output)
    result = {'name': name, 'command': command, 'cwd': str(cwd.relative_to(ROOT)) or '.',
              'exit_code': code, 'seconds': round(time.monotonic() - started, 2)}
    results['checks'].append(result)
    print(name, 'exit', code, '\n', output[-6000:], flush=True)
    return code == 0


check('recovery-integrity', [sys.executable, 'recovery/ai-leads-workspace-v2/verify_github_checkpoint.py'], ROOT)
check('backend', [sys.executable, '-m', 'pytest', 'tests', '-q'], ROOT)
frontend = ROOT / 'frontend'
check('typecheck', ['npm', 'run', 'typecheck'], frontend)
check('lint', ['npm', 'run', 'lint'], frontend)
build = check('build', ['npm', 'run', 'build'], frontend)
if build:
    check('browser', ['npm', 'run', 'test:e2e'], frontend, timeout=420)
else:
    results['checks'].append({'name': 'browser', 'status': 'not_run', 'reason': 'Build failed; do not test an old compiled bundle.'})
results['all_executed_checks_passed'] = all(item.get('exit_code') == 0 for item in results['checks'])
(OUT / 'RESULTS.json').write_text(json.dumps(results, indent=2) + '\n')
# Keep useful failure contexts native. No raw real data is used by these tests.
for path in (frontend / 'test-results').rglob('error-context.md'):
    (OUT / (path.parent.name + '-error-context.md')).write_text(path.read_text())
if (frontend / 'test-results' / 'results.json').exists():
    (OUT / 'browser-results.json').write_text((frontend / 'test-results' / 'results.json').read_text())
print(json.dumps(results, indent=2))
# Publication is a separate step so failed checks are retained, not lost.
