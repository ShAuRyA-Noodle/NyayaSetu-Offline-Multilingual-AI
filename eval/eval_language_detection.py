#!/usr/bin/env python
"""
Measure fastText language-detection accuracy on real Tatoeba data.

Tatoeba is a large, openly-licensed corpus of real human-written sentences
tagged by language. We evaluate detection across the 12 supported languages
using real held-out sentences — no synthetic data.

Outputs eval/results/language_detection.json with overall accuracy, per-language
accuracy, and a confusion summary. Run in the ML venv:

    .venv-ml/Scripts/python.exe eval/eval_language_detection.py --per-lang 200
"""

from __future__ import annotations

import argparse
import bz2
import json
import ssl
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.nlp.language_detection import FastTextLanguageDetector  # noqa: E402

# Our short code → Tatoeba ISO 639-3 code.
TATOEBA_ISO = {
    "hi": "hin", "bn": "ben", "ta": "tam", "te": "tel", "mr": "mar",
    "gu": "guj", "kn": "kan", "ml": "mal", "pa": "pan", "or": "ori",
    "as": "asm", "en": "eng",
}
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE


def load_tatoeba(code: str, iso3: str, limit: int, cache: Path) -> list[str]:
    """Download (cached) and read up to ``limit`` sentences for a language."""
    cache.mkdir(parents=True, exist_ok=True)
    tsv = cache / f"{iso3}_sentences.tsv"
    if not tsv.exists():
        url = f"https://downloads.tatoeba.org/exports/per_language/{iso3}/{iso3}_sentences.tsv.bz2"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90, context=_SSL) as r:
            raw = r.read()
        tsv.write_bytes(bz2.decompress(raw))
    texts: list[str] = []
    with open(tsv, "r", encoding="utf-8") as f:
        for line in f:
            if len(texts) >= limit:
                break
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3 and parts[2].strip():
                texts.append(parts[2].strip())
    return texts


FLORES_FILES = TATOEBA_ISO  # alias kept for the main loop below


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--per-lang", type=int, default=100, help="Sentences per language")
    p.add_argument("--out", default="eval/results/language_detection.json")
    args = p.parse_args()

    cache = ROOT / "data" / "tatoeba_cache"
    cache.mkdir(parents=True, exist_ok=True)
    detector = FastTextLanguageDetector()

    total = correct = 0
    per_lang: dict[str, dict] = {}
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for code, iso3 in TATOEBA_ISO.items():
        try:
            texts = load_tatoeba(code, iso3, args.per_lang, cache)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {code}: {e}")
            continue
        c = 0
        for t in texts:
            pred = detector.detect(t).lang
            confusion[code][pred] += 1
            if pred == code:
                c += 1
        n = len(texts)
        per_lang[code] = {"n": n, "correct": c, "accuracy": round(c / n, 4) if n else 0.0}
        total += n
        correct += c
        print(f"{code}: {c}/{n} = {per_lang[code]['accuracy']:.3f}")

    overall = round(correct / total, 4) if total else 0.0
    result = {
        "model": "fastText lid.176",
        "dataset": "Tatoeba (per-language sentences)",
        "languages": list(per_lang.keys()),
        "total_samples": total,
        "overall_accuracy": overall,
        "per_language": per_lang,
        "confusion": {k: dict(v) for k, v in confusion.items()},
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOVERALL ACCURACY: {overall:.4f} over {total} samples")
    print(f"Results written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
