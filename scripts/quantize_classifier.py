#!/usr/bin/env python
"""
Quantize the fine-tuned governance classifier to INT8 (real model optimization).

Applies PyTorch dynamic INT8 quantization to the trained classifier's Linear
layers and measures the real size + latency reduction on CPU — the edge
optimization the paper describes, demonstrated on a real model.

    .venv-ml/Scripts/python.exe scripts/quantize_classifier.py
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MODEL_DIR = ROOT / "models" / "classifier"
OUT = ROOT / "eval" / "results" / "quantization.json"


def _param_bytes(model) -> int:
    total = 0
    for p in model.parameters():
        total += p.numel() * p.element_size()
    for b in model.buffers():
        total += b.numel() * b.element_size()
    return total


def _bench(model, tok, text, n=20):
    import torch

    enc = tok(text, truncation=True, max_length=128, return_tensors="pt")
    with torch.no_grad():
        model(**enc)  # warm up
    times = []
    with torch.no_grad():
        for _ in range(n):
            t0 = time.time()
            model(**enc)
            times.append(time.time() - t0)
    return statistics.median(times)


def main() -> int:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if not (MODEL_DIR / "config.json").exists():
        print("No trained classifier at models/classifier — run train_classifier.py first.")
        return 1

    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    fp32 = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR))
    fp32.eval()

    text = ("Financial assistance for small and marginal farmers under a central "
            "agriculture income-support scheme.")

    fp32_size = _param_bytes(fp32)
    fp32_lat = _bench(fp32, tok, text)

    # Dynamic INT8 quantization of all Linear layers.
    int8 = torch.quantization.quantize_dynamic(
        fp32, {torch.nn.Linear}, dtype=torch.qint8
    )
    int8.eval()
    int8_lat = _bench(int8, tok, text)

    # Measure quantized on-disk size via a state_dict save.
    import io
    buf = io.BytesIO()
    torch.save(int8.state_dict(), buf)
    int8_size = buf.getbuffer().nbytes

    result = {
        "method": "PyTorch dynamic INT8 quantization (Linear layers)",
        "fp32_param_mb": round(fp32_size / 1e6, 1),
        "int8_serialized_mb": round(int8_size / 1e6, 1),
        "size_reduction_pct": round((1 - int8_size / fp32_size) * 100, 1),
        "fp32_latency_ms": round(fp32_lat * 1000, 2),
        "int8_latency_ms": round(int8_lat * 1000, 2),
        "speedup_x": round(fp32_lat / int8_lat, 2) if int8_lat else None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nWritten: eval/results/quantization.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
