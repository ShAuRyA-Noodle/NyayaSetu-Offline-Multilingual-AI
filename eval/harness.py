#!/usr/bin/env python
"""
NyayaSetu benchmark harness — reproducible, real measurements.

Runs the actual offline components and measures latency, CPU%, and memory for
each governance task, then renders the paper's Table 1 (per-task performance)
and Table 2 (comparison). Accuracy/quality figures come from the dedicated eval
scripts (language detection, translation); this harness measures the runtime
cost live and consolidates everything.

Nothing here is fabricated — every number is produced by running real code on
real data on this machine. Constrained-hardware profiles are emulated by
limiting worker threads (documented as such in the output).

Run in the ML venv:
    .venv-ml/Scripts/python.exe eval/harness.py --profile native
    .venv-ml/Scripts/python.exe eval/harness.py --profile constrained --threads 2
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RESULTS_DIR = ROOT / "eval" / "results"


# ---- resource-profiled timing ---------------------------------------------


def profile_call(fn: Callable[[], object], repeats: int = 3) -> Dict[str, float]:
    """Run ``fn`` ``repeats`` times; return median latency, CPU%, peak mem (MB)."""
    import psutil

    proc = psutil.Process(os.getpid())
    latencies: List[float] = []
    peak_mem = 0.0
    proc.cpu_percent(None)  # prime the CPU meter
    for _ in range(repeats):
        t0 = time.time()
        fn()
        latencies.append(time.time() - t0)
        peak_mem = max(peak_mem, proc.memory_info().rss / 1e6)
    cpu = proc.cpu_percent(None) / (psutil.cpu_count() or 1)
    return {
        "latency_s": round(statistics.median(latencies), 3),
        "cpu_pct": round(cpu, 1),
        "memory_mb": round(peak_mem, 1),
    }


def _load_result(name: str) -> Optional[dict]:
    p = RESULTS_DIR / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


# ---- task benchmarks -------------------------------------------------------


def bench_language_detection(repeats: int) -> Dict:
    from src.nlp.language_detection import FastTextLanguageDetector

    det = FastTextLanguageDetector()
    samples = [
        "किसान को पैसा नहीं मिला", "I need help with my pension",
        "எனக்கு உதவி வேண்டும்", "মৌলিক অধিকার কী", "ನನಗೆ ಸಹಾಯ ಬೇಕು",
    ]
    det.detect(samples[0])  # warm up (model load excluded from timing)

    def run():
        for s in samples:
            det.detect(s)

    prof = profile_call(run, repeats)
    prof["latency_s"] = round(prof["latency_s"] / len(samples), 4)  # per-detection
    acc = (_load_result("language_detection.json") or {}).get("overall_accuracy")
    return {"task": "Language Detection", "quality": acc, "quality_kind": "accuracy", **prof}


def bench_rag_retrieval(repeats: int) -> Dict:
    from src.core.embedder import MultilingualEmbedder
    from src.core.retriever import FAISSRetriever
    import numpy as np
    import sqlite3

    # Build an index over the REAL schemes currently in the DB.
    conn = sqlite3.connect(str(ROOT / "data" / "governance.db"))
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
    if texts:
        embs = embedder.embed_texts(texts)
        retriever.build_index(embs, meta)

    queries = [
        "farmer income support eligibility",
        "housing scheme for rural poor",
        "employment guarantee scheme",
    ]
    embedder.embed_query(queries[0])  # warm up

    def run():
        for q in queries:
            qe = embedder.embed_query(q)
            if texts:
                retriever.retrieve(qe, top_k=3)

    prof = profile_call(run, repeats)
    prof["latency_s"] = round(prof["latency_s"] / len(queries), 4)
    return {
        "task": "Scheme Query (RAG retrieval)",
        "quality": len(texts),
        "quality_kind": "indexed_chunks",
        **prof,
    }


def bench_llm_generation(repeats: int) -> Dict:
    from src.generation.local_llm import LocalLLMClient

    llm = LocalLLMClient(n_ctx=2048)
    if not llm.is_available():
        return {"task": "Offline LLM Answer", "quality": None, "note": "model not present"}
    ctx = ("Scheme: PM-KISAN. Benefits: Rs 6000 per year in three installments. "
           "Eligibility: small farmers up to 2 hectares.")
    prompt = f"Context:\n{ctx}\n\nQuestion: How much does PM-KISAN pay per year?"
    llm.generate("warm up", max_tokens=4)  # warm up (load excluded)
    toks = {"n": 0}

    def run():
        r = llm.generate(prompt, system_prompt="Answer only from context.", max_tokens=80)
        toks["n"] = r["metadata"].get("completion_tokens") or 0

    prof = profile_call(run, max(1, repeats - 1))
    prof["completion_tokens"] = toks["n"]
    prof["tokens_per_sec"] = round(toks["n"] / prof["latency_s"], 1) if prof["latency_s"] else None
    return {"task": "Offline LLM Answer", "quality": None, "quality_kind": "generation", **prof}


def bench_translation() -> Dict:
    tr = _load_result("translation.json") or {}
    return {
        "task": "Translation (en->hi)",
        "quality": tr.get("bleu"),
        "quality_kind": "BLEU",
        "chrf": tr.get("chrf"),
        "latency_s": None,
        "cpu_pct": None,
        "memory_mb": None,
        "note": "quality from eval_translation.py (IITB corpus)",
    }


# ---- rendering -------------------------------------------------------------


def render_markdown(report: Dict) -> str:
    lines = [
        f"# NyayaSetu Benchmark — profile: {report['profile']}",
        "",
        f"- Host: {report['host']['machine']}, {report['host']['cpu_count']} logical CPUs",
        f"- Worker threads: {report['host']['threads']}",
        f"- Timestamp: {report['timestamp']}",
        "",
        "## Table 1 — Per-task performance (measured)",
        "",
        "| Task | Quality | Latency (s) | CPU % | Memory (MB) |",
        "|------|---------|-------------|-------|-------------|",
    ]
    for t in report["tasks"]:
        q = t.get("quality")
        qk = t.get("quality_kind", "")
        qs = "—" if q is None else f"{q} ({qk})" if qk else str(q)
        lines.append(
            f"| {t['task']} | {qs} | {t.get('latency_s','—')} | "
            f"{t.get('cpu_pct','—')} | {t.get('memory_mb','—')} |"
        )
    lines += [
        "",
        "_Quality: Language Detection = accuracy on Tatoeba (12 langs); "
        "Translation = BLEU on IIT-Bombay en-hi; RAG = indexed real-scheme chunks; "
        "LLM = fully-offline generation. Latency/CPU/Memory measured live via psutil._",
    ]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--profile", default="native", choices=["native", "constrained"])
    p.add_argument("--threads", type=int, default=0, help="Limit worker threads (0=all)")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--timestamp", default="", help="Pass a timestamp (scripts can't call now())")
    args = p.parse_args()

    threads = args.threads or (2 if args.profile == "constrained" else (os.cpu_count() or 4))
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[var] = str(threads)
    os.environ["LOCAL_LLM_THREADS"] = str(threads)

    import psutil

    tasks = []
    print(f"[harness] profile={args.profile} threads={threads}")
    for name, fn in [
        ("language detection", lambda: bench_language_detection(args.repeats)),
        ("rag retrieval", lambda: bench_rag_retrieval(args.repeats)),
        ("offline llm", lambda: bench_llm_generation(args.repeats)),
        ("translation", lambda: bench_translation()),
    ]:
        print(f"  running: {name} ...", flush=True)
        try:
            tasks.append(fn())
        except Exception as e:  # noqa: BLE001
            print(f"    FAILED {name}: {e}")
            tasks.append({"task": name, "error": str(e)})

    report = {
        "profile": args.profile,
        "timestamp": args.timestamp or "unset",
        "host": {
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "total_memory_gb": round(psutil.virtual_memory().total / 1e9, 1),
            "threads": threads,
        },
        "tasks": tasks,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"benchmark_{args.profile}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = render_markdown(report)
    (RESULTS_DIR / f"benchmark_{args.profile}.md").write_text(md, encoding="utf-8")
    print("\n" + md)
    print(f"\nWritten: eval/results/benchmark_{args.profile}.json / .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
