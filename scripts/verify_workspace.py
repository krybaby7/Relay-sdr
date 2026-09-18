"""Run native deterministic verification. Installs/deployment/calling are not performed."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'verification/local')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    npm = shutil.which('npm')
    if not npm:
        parser.error('npm is required; install the documented Node toolchain first.')
    env = dict(os.environ, ENABLE_OUTBOUND='false', OPENAI_API_KEY='', WORKSPACE_API_KEY='',
               TWILIO_AUTH_TOKEN='', LANGSMITH_TRACING='false', RELAY_TEST_PYTHON=sys.executable)
    source = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(['git','status','--porcelain'], cwd=ROOT, text=True)
    # Fingerprint the code/test/build configuration actually executed, including
    # uncommitted development changes; never read runtime data or credentials.
    paths = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'], cwd=ROOT, text=True).splitlines()
    hashes = {}
    for name in sorted(set(paths)):
        p = ROOT / name
        if p.is_file() and (name.startswith(('app/','frontend/src/','frontend/e2e/','frontend/unit/','tests/','scripts/')) or
                            name.startswith('requirements') or (name.startswith('frontend/') and p.suffix in ('.json','.ts'))):
            hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    checks = [('integrity', [sys.executable,'recovery/ai-leads-workspace-v2/verify_github_checkpoint.py'], ROOT),
              ('backend', [sys.executable,'-m','pytest','tests','-q'], ROOT),
              *[(name, [npm,'run',script], ROOT/'frontend') for name,script in
                [('typecheck','typecheck'),('lint','lint'),('unit','test:unit'),('build','build'),('browser','test:e2e')]]]
    report = {'source_commit':source, 'initial_worktree_status':status, 'source_sha256':hashes,
              'scope':'Mocked providers and fictional loopback fixtures only. No live provider verification.',
              'checks':[], 'all_executed_checks_passed':False}
    for name,command,cwd in checks:
        start = time.monotonic()
        print(f'Running {name}: {command}', flush=True)
        with (out/f'{name}.txt').open('w') as log:
            try:
                done = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=900)
                code = done.returncode
            except subprocess.TimeoutExpired:
                log.write('\nVerification stage exceeded 900 seconds; not reported as passing.\n')
                code = 124
        report['checks'].append({'name':name,'command':command,'cwd':str(cwd.relative_to(ROOT)) or '.',
                                 'exit_code':code,'seconds':round(time.monotonic()-start,2)})
        (out/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
        print((out/f'{name}.txt').read_text(), flush=True)
        if code:
            print(f'Stopped at {name}; later stages were not executed.', file=sys.stderr)
            return code
    report['all_executed_checks_passed'] = True
    (out/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'All executed checks passed. Results: {out}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
