#!/usr/bin/env python
"""
Measure RAG retrieval accuracy on the real scheme-query gold set.

Loads eval/datasets/scheme_queries.jsonl (built from real schemes), embeds each
query, retrieves top-k from a FAISS index over the real scheme corpus, and
computes recall@1 / recall@3 (does the gold scheme appear?). Real data, real
metric.

    .venv-ml/Scripts/python.exe eval/eval_rag_retrieval.py
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from src.core.embedder import MultilingualEmbedder
    from src.core.retriever import FAISSRetriever

    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/governance.db")
    p.add_argument("--queries", default="eval/datasets/scheme_queries.jsonl")
    p.add_argument("--out", default="eval/results/rag_retrieval.json")
    args = p.parse_args()

    # Build index over the real schemes.
    conn = sqlite3.connect(str(ROOT / args.db))
    rows = conn.execute(
        "SELECT scheme_name, eligibility, benefits, process FROM schemes"
    ).fetchall()
    conn.close()
    texts, meta = [], []
    for name, elig, ben, proc in rows:
        for section, content in (("eligibility", elig), ("benefits", ben), ("process", proc)):
            if content and content.strip():
                texts.append(f"{name}: {content}")
                meta.append({"scheme_name": name, "section_type": section})

    embedder = MultilingualEmbedder(cache_dir=str(ROOT / "models"))
    retriever = FAISSRetriever(embedding_dim=embedder.get_embedding_dim())
    retriever.build_index(embedder.embed_texts(texts), meta)

    queries = [
        json.loads(line)
        for line in (ROOT / args.queries).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    hit1 = hit3 = 0
    for q in queries:
        qe = embedder.embed_query(q["query"])
        results = retriever.retrieve(qe, top_k=3)
        names = [m["scheme_name"] for _, m in results]
        if names and names[0] == q["gold_scheme"]:
            hit1 += 1
        if q["gold_scheme"] in names:
            hit3 += 1

    n = len(queries)
    result = {
        "dataset": "scheme_queries.jsonl (grounded in real schemes)",
        "n_queries": n,
        "n_indexed_chunks": len(texts),
        "recall_at_1": round(hit1 / n, 4) if n else 0.0,
        "recall_at_3": round(hit3 / n, 4) if n else 0.0,
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"recall@1={result['recall_at_1']}  recall@3={result['recall_at_3']}  "
          f"(n={n} queries over {len(texts)} chunks)")
    print(f"Results written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
