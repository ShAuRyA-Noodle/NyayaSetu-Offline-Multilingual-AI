#!/usr/bin/env python
"""
Build a REAL labeled text-classification dataset from the myScheme list API.

The search/list endpoint returns, per scheme, its name, brief description, and
official category + nodal ministry — with real human-assigned labels. One
request covers 100 schemes (~44 requests for the whole portal), so this avoids
the per-scheme detail endpoint's throttling entirely.

Output: data/classifier/scheme_category.jsonl  (text, category, ministry)

    python eval/build_classifier_dataset.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_pipeline.myscheme_client import MySchemeClient  # noqa: E402


def label_of(field: dict, key: str) -> str:
    val = field.get(key)
    if isinstance(val, list) and val:
        val = val[0]
    if isinstance(val, dict):
        return str(val.get("label") or val.get("value") or "").strip()
    return str(val or "").strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/classifier/scheme_category.jsonl")
    p.add_argument("--page-size", type=int, default=100)
    args = p.parse_args()

    client = MySchemeClient(request_delay=0.5, max_retries=5)
    total = client.total_count()
    print(f"myScheme total schemes: {total}")

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        frm = 0
        while frm < total:
            try:
                items = client.list_page(frm, args.page_size)
            except Exception as e:  # noqa: BLE001
                print(f"[skip] page from={frm}: {e}")
                frm += args.page_size
                continue
            for it in items:
                fields = it.get("fields") or {}
                slug = fields.get("slug")
                if not slug or slug in seen:
                    continue
                seen.add(slug)
                name = (fields.get("schemeName") or "").strip()
                brief = (fields.get("briefDescription") or "").strip()
                category = label_of(fields, "schemeCategory")
                ministry = label_of(fields, "nodalMinistryName") or label_of(
                    fields, "nodalDepartmentName"
                )
                text = f"{name}. {brief}".strip()
                if not text or not category:
                    continue
                f.write(json.dumps(
                    {"text": text, "category": category, "ministry": ministry},
                    ensure_ascii=False,
                ) + "\n")
                n += 1
            frm += args.page_size
            if frm % 500 == 0:
                print(f"  ...{n} labeled records", flush=True)

    print(f"Wrote {n} labeled records -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
