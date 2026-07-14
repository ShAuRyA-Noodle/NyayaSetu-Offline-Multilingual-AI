#!/usr/bin/env python
"""
Measure offline translation quality (BLEU) on the real IIT-Bombay en-hi corpus.

The IIT-Bombay English-Hindi parallel corpus (cfilt/iitb-english-hindi) is a
standard, openly-available benchmark. We translate held-out test sentences with
the offline LLM translator and score with sacreBLEU — real data, real metric.

Run in the ML venv:
    .venv-ml/Scripts/python.exe eval/eval_translation.py --n 60
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.nlp.translation import OfflineTranslator  # noqa: E402


def load_iitb(n: int, cache: Path) -> list[tuple[str, str]]:
    """Return up to n (english, hindi) reference pairs from the IITB test set."""
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq

    f = hf_hub_download(
        "cfilt/iitb-english-hindi",
        "data/test-00000-of-00001.parquet",
        repo_type="dataset",
        local_dir=str(cache),
    )
    rows = pq.read_table(f).to_pylist()
    pairs: list[tuple[str, str]] = []
    for r in rows:
        tr = r.get("translation") or {}
        en, hi = (tr.get("en") or "").strip(), (tr.get("hi") or "").strip()
        # Keep reasonably-sized sentences (skip fragments / very long).
        if 15 <= len(en) <= 200 and hi:
            pairs.append((en, hi))
        if len(pairs) >= n:
            break
    return pairs


def main() -> int:
    import sacrebleu

    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=60, help="Number of test sentences")
    p.add_argument("--out", default="eval/results/translation.json")
    args = p.parse_args()

    cache = ROOT / "data" / "iitb_cache"
    pairs = load_iitb(args.n, cache)
    translator = OfflineTranslator()
    if not translator.is_available():
        print("Offline LLM not available; cannot run translation eval.")
        return 1

    en_src = [en for en, _ in pairs]
    hi_ref = [hi for _, hi in pairs]

    print(f"Translating {len(pairs)} EN->HI sentences offline...")
    hi_hyp = []
    for i, en in enumerate(en_src, 1):
        hi_hyp.append(translator.translate(en, "en", "hi"))
        if i % 10 == 0:
            print(f"  {i}/{len(pairs)}", flush=True)

    # sacreBLEU with the built-in tokenizer for Hindi (intl / 13a handles Deva).
    bleu = sacrebleu.corpus_bleu(hi_hyp, [hi_ref], tokenize="13a")
    chrf = sacrebleu.corpus_chrf(hi_hyp, [hi_ref])

    result = {
        "backend": "offline LLM (Qwen2.5-3B-Instruct Q4_K_M via llama.cpp)",
        "dataset": "IIT-Bombay en-hi test",
        "direction": "en->hi",
        "n": len(pairs),
        "bleu": round(bleu.score, 2),
        "chrf": round(chrf.score, 2),
        "samples": [
            {"src": s, "ref": r, "hyp": h}
            for s, r, h in list(zip(en_src, hi_ref, hi_hyp))[:5]
        ],
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nBLEU (en->hi): {result['bleu']} | chrF: {result['chrf']} "
          f"over {result['n']} sentences")
    print(f"Results written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
