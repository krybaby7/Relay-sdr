#!/usr/bin/env python3
"""Materialize an exact text-only checkpoint. Standard library; no application execution."""
import base64
import hashlib
import io
import json
import lzma
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import zipfile

from verify_github_checkpoint import MANIFEST_SHA256, OMITTED, safe_path, verify

TRANSPORT_SHA256 = "803b4d6830384709beba8ca37172b7be93b571500f3da172be479987a98e16ce"
ARTIFACT_SHA256 = "842b186b3628d6c47b2adde635e5cf618ebe3fe010e2fefd9a7d0caca8972990"
ORIGINAL_ZIP_SHA256 = "4fecffa26cffe162762573b44499be77435621a25281f276a9d9f1ac4982953c"
DESTINATION = "ai-leads-workspace-v2"


def read_tar(archive: bytes, wanted: set[str]) -> dict[str, bytes]:
    """Read only whitelisted regular members, without extractall or cached dependencies."""
    found = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
        for member in tf:
            name = member.name.removeprefix("./")
            if name not in wanted:
                continue
            if name in found or not member.isfile() or member.size > 2_000_000:
                raise ValueError(f"Invalid or duplicate archive member: {name}")
            with tf.extractfile(member) as f:
                found[name] = f.read(2_000_001)
    if set(found) != wanted:
        raise ValueError("Historical artifact is missing whitelisted files")
    return found


def main(artifact_path: Path) -> None:
    here = Path(__file__).resolve().parent
    transport = b"".join((here / "transport" / f"part-{i:02d}.b64").read_bytes() for i in range(1, 7))
    if len(transport) != 91_232 or hashlib.sha256(transport).hexdigest() != TRANSPORT_SHA256:
        raise ValueError("Recovery transport checksum mismatch")
    decoder = lzma.LZMADecompressor(memlimit=64 * 1024 * 1024)
    raw = decoder.decompress(base64.b64decode(transport, validate=True), max_length=2_000_001)
    if not decoder.eof or decoder.unused_data or len(raw) != 278_881:
        raise ValueError("Unexpected recovery transport payload size")
    mapping = json.loads(raw)
    if not isinstance(mapping, dict) or len(mapping) != 28:
        raise ValueError("Unexpected transported file inventory")
    blobs = {}
    for name, content in mapping.items():
        if not isinstance(name, str) or not isinstance(content, str):
            raise ValueError("Transport is not a text file mapping")
        safe_path(here / DESTINATION, name)
        blobs[name] = content.encode("utf-8")
    if hashlib.sha256(blobs["MANIFEST.json"]).hexdigest() != MANIFEST_SHA256:
        raise ValueError("Original manifest mismatch")
    entries = json.loads(blobs["MANIFEST.json"])["files"]
    expected = {e["path"]: e for e in entries if e["path"] not in OMITTED}
    artifact_bytes = artifact_path.read_bytes()
    if len(artifact_bytes) != 48_448_809 or hashlib.sha256(artifact_bytes).hexdigest() != ARTIFACT_SHA256:
        raise ValueError("Historical GitHub Actions artifact checksum mismatch")
    with zipfile.ZipFile(io.BytesIO(artifact_bytes)) as zf:
        source_wanted = {n.removeprefix("Relay-sdr/") for n in expected if n.startswith("Relay-sdr/")}
        for name, content in read_tar(zf.read("source.tar.gz"), source_wanted).items():
            blobs["Relay-sdr/" + name] = content
        frontend_wanted = {"package.json", "package-lock.json", "audit.json", "dependency-tree.json"}
        for name, content in read_tar(zf.read("frontend-toolchain.tar.gz"), frontend_wanted).items():
            blobs["recovered-dependency-manifests/" + name] = content
        for name in ("baseline-test-results.txt", "python-audit.json", "python-resolved.txt"):
            blobs["recovered-dependency-manifests/" + name] = zf.read(name)
    if set(blobs) != set(expected) | {"MANIFEST.json"}:
        raise ValueError("Complete native file inventory mismatch")
    # Validate every original payload before writing any destination file.
    for name, content in blobs.items():
        path = PurePosixPath(name)
        if any(p in {".env", ".data", ".git", "node_modules", "wheels"} for p in path.parts):
            raise ValueError(f"Excluded runtime/credential/cache path: {name}")
        content.decode("utf-8")
        if name != "MANIFEST.json":
            e = expected[name]
            if len(content) != e["bytes"] or hashlib.sha256(content).hexdigest() != e["sha256"]:
                raise ValueError(f"Original payload mismatch: {name}")
    target = here / DESTINATION
    stage = here / (DESTINATION + ".staging")
    if stage.exists():
        raise ValueError("Staging path already exists; preserve it for inspection")
    stage.mkdir()
    for name, content in blobs.items():
        p = safe_path(stage, name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    shutil.copyfile(here / "verify_github_checkpoint.py", stage / "verify_github_checkpoint.py")
    result = verify(stage)
    result.update({
        "purpose": "Published recovery source, not a completed feature release",
        "repository": "krybaby7/Relay-sdr",
        "recovery_branch": "recovery/ai-leads-workspace-2026-09-17",
        "source_archive_sha256": ORIGINAL_ZIP_SHA256,
        "transport_sha256": TRANSPORT_SHA256,
        "historical_dependency_artifact_id": 10511895652,
        "historical_dependency_artifact_sha256": ARTIFACT_SHA256,
        "historical_artifact_dependency_after_publication": False,
        "recovered_source_files": 22,
        "screenshot_omission_reason": "Text-only GitHub transfer. Original PNGs remain in the original ZIP in the user's Library; they are not required to restore source.",
        "omitted_files": [e for e in entries if e["path"] in OMITTED],
        "notes": [
            "All 67 original text files, including the manifest, are preserved byte-for-byte.",
            "The baseline source and dependency manifests are historical; they do not establish final compatible dependencies or passing feature tests.",
            "No application, server, model, provider, or outbound action was executed for publication.",
            "Use this directory's verify_github_checkpoint.py. The original checker expects the three historical PNGs and is retained unchanged.",
        ],
    })
    (stage / "GITHUB-PRESERVATION.json").write_text(json.dumps(result, indent=2) + "\n")
    if target.exists():
        # Idempotent reruns may verify but may not overwrite later human edits.
        stage_files = {p.relative_to(stage): p.read_bytes() for p in stage.rglob("*") if p.is_file()}
        target_files = {p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()}
        if stage_files != target_files:
            raise ValueError("Existing native recovery differs; do not overwrite it")
        shutil.rmtree(stage)
    else:
        stage.rename(target)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python recovery/publish_checkpoint.py <historical-artifact.zip>")
    main(Path(sys.argv[1]))
