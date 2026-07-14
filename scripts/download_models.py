#!/usr/bin/env python
"""
Download the offline models NyayaSetu bundles (kept out of git; ~large).

Currently:
- fastText lid.176  → models/fasttext/lid.176.bin  (language detection, M5)

Run in the ML venv:
    .venv-ml/Scripts/python.exe scripts/download_models.py
"""

from __future__ import annotations

import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

# (destination, [mirror urls]) — first reachable mirror wins.
MODELS = [
    (
        "models/fasttext/lid.176.bin",
        [
            "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin",
            "https://huggingface.co/julien-c/fasttext-language-id/resolve/main/lid.176.bin",
        ],
    ),
]


def _download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120, context=_SSL) as r:
            data = r.read()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"    mirror failed ({url.split('/')[2]}): {type(e).__name__}")
        return False


def main() -> int:
    for rel, mirrors in MODELS:
        dest = ROOT / rel
        if dest.exists() and dest.stat().st_size > 0:
            print(f"[skip] {rel} already present ({dest.stat().st_size} bytes)")
            continue
        print(f"[get ] {rel}")
        ok = False
        for url in mirrors:
            for attempt in range(3):
                if _download(url, dest):
                    print(f"    OK ({dest.stat().st_size} bytes)")
                    ok = True
                    break
            if ok:
                break
        if not ok:
            print(f"    FAILED all mirrors for {rel}")
            return 1
    print("All models present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
