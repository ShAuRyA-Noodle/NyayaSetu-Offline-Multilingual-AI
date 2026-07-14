#!/usr/bin/env python
"""
Knowledge-base integrity tool.

Generates or verifies a SHA-256 manifest over the local knowledge-base files
(FAISS index, metadata JSON, SQLite DB). Run `--generate` after a scrape/rebuild
and `--verify` at startup (or in the runbook) to detect corruption/tampering.

Usage:
    python scripts/kb_integrity.py --generate
    python scripts/kb_integrity.py --verify
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.security.integrity import verify_manifest, write_manifest  # noqa: E402

KB_FILES = [
    "data/schemes_faiss.index",
    "data/schemes_metadata.json",
    "data/schemes_metadata.pkl",  # legacy, hashed only if present
    "data/governance.db",
]
MANIFEST = "data/kb_manifest.json"


def main() -> int:
    p = argparse.ArgumentParser(description="KB integrity manifest tool")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--generate", action="store_true", help="Create the manifest")
    g.add_argument("--verify", action="store_true", help="Verify against manifest")
    p.add_argument("--manifest", default=MANIFEST)
    args = p.parse_args()

    present = [f for f in KB_FILES if (ROOT / f).exists()]
    if args.generate:
        m = write_manifest([ROOT / f for f in present], ROOT / args.manifest, base_dir=ROOT)
        print(f"Manifest written: {args.manifest}")
        for rel, h in m["entries"].items():
            print(f"  {h[:16]}…  {rel}")
        return 0

    ok, problems = verify_manifest(ROOT / args.manifest)
    if ok:
        print("KB integrity: OK — all files match the manifest")
        return 0
    print("KB integrity: FAILED")
    for pr in problems:
        print("  -", pr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
