#!/usr/bin/env python
"""
Consolidate every measured result into one summary report.

Reads all eval/results/*.json produced by the individual evals + the benchmark
harness and renders eval/results/SUMMARY.md — a single, honest view of the
real, measured metrics (the "metrics proven" table).

    python eval/summarize.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "eval" / "results"


def _load(name):
    p = RESULTS / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main() -> int:
    ld = _load("language_detection.json")
    tr = _load("translation.json")
    rag = _load("rag_retrieval.json")
    clf = _load("classifier.json")
    bench_n = _load("benchmark_native.json")
    bench_c = _load("benchmark_constrained.json")

    lines = [
        "# NyayaSetu — Measured Results Summary",
        "",
        "All figures below are produced by running real code on real data on the "
        "development machine (RTX 4080 Laptop, 32 logical CPUs). No synthetic data, "
        "no hand-entered numbers. Reproduce with the scripts in `eval/` (see "
        "`eval/README.md`).",
        "",
        "## Core quality metrics",
        "",
        "| Capability | Metric | Value | Dataset (real) |",
        "|------------|--------|-------|----------------|",
    ]
    if ld:
        lines.append(
            f"| Language detection (12 langs) | overall accuracy | "
            f"**{ld['overall_accuracy']*100:.2f}%** | {ld['dataset']} "
            f"({ld['total_samples']} sentences) |"
        )
    if rag:
        lines.append(
            f"| RAG scheme retrieval | recall@1 / recall@3 | "
            f"**{rag['recall_at_1']*100:.1f}% / {rag['recall_at_3']*100:.1f}%** | "
            f"{rag['n_queries']} grounded queries / {rag['n_indexed_chunks']} chunks |"
        )
    if clf:
        lines.append(
            f"| Governance text classifier | accuracy / macro-F1 | "
            f"**{clf['accuracy']*100:.1f}% / {clf['macro_f1']*100:.1f}%** | "
            f"myScheme scheme→category, {clf['n_total']} labeled records, "
            f"{clf['n_classes']} classes |"
        )
    if tr:
        lines.append(
            f"| Offline translation (en→hi) | BLEU / chrF | "
            f"{tr['bleu']} / {tr['chrf']} | {tr['dataset']} |"
        )

    lines += ["", "## Runtime performance (measured live)", ""]
    if bench_n:
        lines += [
            "| Task | Latency (s) | CPU % | Memory (MB) | Profile |",
            "|------|-------------|-------|-------------|---------|",
        ]
        for prof, rep in (("native", bench_n), ("constrained (2 threads)", bench_c)):
            if not rep:
                continue
            for t in rep["tasks"]:
                if t.get("latency_s") is None:
                    continue
                lines.append(
                    f"| {t['task']} | {t.get('latency_s')} | {t.get('cpu_pct')} | "
                    f"{t.get('memory_mb')} | {prof} |"
                )

    lines += [
        "",
        "## Honesty notes",
        "",
        "- The offline translation BLEU reflects the on-device LLM backend; a "
        "dedicated NMT backend (IndicTrans2) is the path to paper-grade scores.",
        "- Constrained profiles are **emulated** via thread-limiting, not physical "
        "Pi/budget-phone runs (clearly labeled).",
        "- The scheme corpus grows as the scraper + daily cron ingest more real "
        "schemes; retrieval numbers scale with corpus size.",
    ]

    out = RESULTS / "SUMMARY.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWritten: eval/results/SUMMARY.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
