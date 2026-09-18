#!/usr/bin/env python3
"""Verify this recovery archive's hashes and Python syntax; no application execution."""
import ast
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'MANIFEST.json').read_text(encoding='utf-8'))
failures = []
python_count = 0
for entry in manifest['files']:
    relative = Path(entry['path'])
    path = (root / relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(root):
        failures.append(f"Unsafe manifest path: {relative}")
        continue
    if not path.is_file():
        failures.append(f"Missing file: {relative}")
        continue
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != entry['sha256'] or len(data) != entry['bytes']:
        failures.append(f"Integrity mismatch: {relative}")
    if path.suffix == '.py':
        try:
            ast.parse(data, filename=str(relative))
            python_count += 1
        except (SyntaxError, ValueError) as exc:
            failures.append(f"Python syntax: {relative}: {exc}")
if failures:
    print('\n'.join(failures))
    raise SystemExit(1)
print(f"Verified {len(manifest['files'])} payload hashes; parsed {python_count} Python files.")
print('Integrity and syntax only. This does not establish a working or tested implementation.')
