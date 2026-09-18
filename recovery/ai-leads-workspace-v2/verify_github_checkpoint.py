#!/usr/bin/env python3
"""Verify the preserved text snapshot only; never import or run Relay code."""
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

MANIFEST_SHA256 = "c6fefb9a8ce312567b66b6687f7a23522adc27e3b2c99c76522b3f104e187ca0"
OMITTED = {
    "screenshots/workspace-evidence-desktop.png",
    "screenshots/workspace-first-desktop.png",
    "screenshots/workspace-third-mobile.png",
}


def safe_path(root: Path, name: str) -> Path:
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or "\\" in name or str(p) != name:
        raise ValueError(f"Unsafe snapshot path: {name!r}")
    target = root.joinpath(*p.parts)
    if any(part.is_symlink() for part in [target, *target.parents]):
        raise ValueError(f"Symlink not allowed: {name!r}")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes snapshot: {name!r}")
    return target


def verify(root: Path) -> dict:
    data = safe_path(root, "MANIFEST.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != MANIFEST_SHA256:
        raise ValueError("Original recovery manifest hash mismatch")
    entries = json.loads(data)["files"]
    if len(entries) != 69 or len({e["path"] for e in entries}) != 69:
        raise ValueError("Unexpected recovery manifest inventory")
    checked = parsed = 0
    for entry in entries:
        name = entry["path"]
        if name in OMITTED:
            continue
        path = safe_path(root, name)
        content = path.read_bytes()
        if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise ValueError(f"Payload hash/size mismatch: {name}")
        content.decode("utf-8")
        checked += 1
        if path.suffix == ".py":
            ast.parse(content, filename=name)
            parsed += 1
    if (checked, parsed) != (66, 26):
        raise ValueError(f"Unexpected verification counts: {checked}, {parsed}")
    return {
        "original_manifest_sha256": MANIFEST_SHA256,
        "original_text_payload_hashes_verified": checked,
        "original_text_files_including_manifest": checked + 1,
        "original_python_files_parsed": parsed,
        "historical_screenshots_not_published": sorted(OMITTED),
        "functional_tests_run": False,
        "live_model_or_provider_tests_run": False,
        "note": "Integrity and Python syntax only; not a complete or functionally verified implementation.",
    }


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path(__file__).resolve().parent
    print(json.dumps(verify(root), indent=2))
