"""
SHA-256 integrity manifests for the local knowledge base.

The offline knowledge base (FAISS index, metadata JSON, SQLite DB) lives on disk
on kiosk/edge devices. A SHA-256 manifest lets the app detect silent corruption
or tampering at startup and refuse to serve a compromised index.

A manifest is a JSON file mapping relative paths → SHA-256 hex digests, plus a
top-level digest over the sorted entries (so the manifest itself is
tamper-evident against reordering).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

_CHUNK = 1 << 20  # 1 MiB streaming read


class IntegrityError(RuntimeError):
    """Raised when a file's hash does not match its manifest entry."""


def compute_sha256(path: str | Path) -> str:
    """Stream a file and return its SHA-256 hex digest."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(_CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _manifest_digest(entries: Dict[str, str]) -> str:
    """Digest over the sorted (path, hash) pairs — detects reordering/edits."""
    h = hashlib.sha256()
    for rel in sorted(entries):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(entries[rel].encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def build_manifest(paths: Iterable[str | Path], base_dir: str | Path) -> dict:
    """Compute a manifest for the given files, relative to ``base_dir``."""
    base = Path(base_dir).resolve()
    entries: Dict[str, str] = {}
    for p in paths:
        fp = Path(p).resolve()
        if not fp.exists():
            continue
        rel = fp.relative_to(base).as_posix() if base in fp.parents or base == fp.parent else fp.name
        entries[rel] = compute_sha256(fp)
    return {
        "algorithm": "sha256",
        "base_dir": str(base),
        "entries": entries,
        "digest": _manifest_digest(entries),
    }


def write_manifest(
    paths: Iterable[str | Path],
    manifest_path: str | Path,
    base_dir: str | Path | None = None,
) -> dict:
    """Build and persist a manifest. Returns the manifest dict."""
    manifest_path = Path(manifest_path)
    base = base_dir or manifest_path.parent
    manifest = build_manifest(paths, base)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def verify_manifest(manifest_path: str | Path) -> Tuple[bool, List[str]]:
    """
    Verify every file against a manifest.

    Returns ``(ok, problems)`` where ``problems`` lists human-readable issues
    (missing files, hash mismatches, or a tampered manifest digest).
    """
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries: Dict[str, str] = manifest.get("entries", {})
    base = Path(manifest.get("base_dir", manifest_path.parent))
    problems: List[str] = []

    # 1) Manifest self-integrity (guards against edited/reordered entries).
    if manifest.get("digest") != _manifest_digest(entries):
        problems.append("manifest digest mismatch — manifest itself was altered")

    # 2) Per-file verification.
    for rel, expected in entries.items():
        fp = base / rel
        if not fp.exists():
            problems.append(f"missing file: {rel}")
            continue
        actual = compute_sha256(fp)
        if actual != expected:
            problems.append(f"hash mismatch: {rel}")

    return (len(problems) == 0, problems)


def verify_or_raise(manifest_path: str | Path) -> None:
    """Verify a manifest and raise :class:`IntegrityError` on any problem."""
    ok, problems = verify_manifest(manifest_path)
    if not ok:
        raise IntegrityError(
            "Local knowledge-base integrity check failed:\n  - "
            + "\n  - ".join(problems)
        )
