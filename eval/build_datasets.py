#!/usr/bin/env python
"""
Build real evaluation datasets from the scraped scheme corpus.

Generates grounded governance queries directly from the REAL schemes in the DB
(one per section that actually has content), each paired with the source scheme
and section so RAG retrieval can be scored against a real gold reference. The
set scales automatically as the myScheme scraper ingests more schemes.

This complements the externally-sourced eval sets already in place:
- language detection  → Tatoeba (eval_language_detection.py)
- translation (BLEU)  → IIT-Bombay corpus (eval_translation.py)

Output: eval/datasets/scheme_queries.jsonl  (real, versioned)

    .venv-ml/Scripts/python.exe eval/build_datasets.py
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Natural citizen questions per section. Grounded in the real scheme name.
SECTION_QUESTIONS = {
    "eligibility": [
        "Who is eligible for {name}?",
        "What are the eligibility criteria for {name}?",
        "Am I eligible for {name}?",
    ],
    "benefits": [
        "What benefits does {name} provide?",
        "How much money will I get from {name}?",
        "What do I receive under {name}?",
    ],
    "process": [
        "How do I apply for {name}?",
        "What is the application process for {name}?",
        "Where do I register for {name}?",
    ],
}


def build(db_path: str, out_path: Path, per_section: int) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT scheme_name, department, eligibility, benefits, process FROM schemes"
    ).fetchall()
    conn.close()

    records = []
    for r in rows:
        name = r["scheme_name"]
        for section in ("eligibility", "benefits", "process"):
            content = (r[section] or "").strip()
            if not content:
                continue
            for q in SECTION_QUESTIONS[section][:per_section]:
                records.append({
                    "query": q.format(name=name),
                    "gold_scheme": name,
                    "gold_section": section,
                    "department": r["department"],
                    # Short reference snippet (real content) for answer grading.
                    "reference": content[:400],
                })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/governance.db")
    p.add_argument("--out", default="eval/datasets/scheme_queries.jsonl")
    p.add_argument("--per-section", type=int, default=3)
    args = p.parse_args()

    n = build(str(ROOT / args.db), ROOT / args.out, args.per_section)
    print(f"Built {n} grounded scheme queries -> {args.out}")
    print("(scales automatically as the scraper ingests more real schemes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
