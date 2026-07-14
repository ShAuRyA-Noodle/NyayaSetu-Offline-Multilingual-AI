# NyayaSetu Benchmark — profile: constrained

- Host: AMD64, 32 logical CPUs
- Worker threads: 2
- Timestamp: 2026-07-14T23:14:50Z

## Table 1 — Per-task performance (measured)

| Task | Quality | Latency (s) | CPU % | Memory (MB) |
|------|---------|-------------|-------|-------------|
| Language Detection | 0.9688 (accuracy) | 0.0002 | 0.0 | 176.5 |
| Scheme Query (RAG retrieval) | 13 (indexed_chunks) | 0.027 | 5.7 | 1164.5 |
| Offline LLM Answer | — | 1.413 | 61.0 | 2811.6 |
| Translation (en->hi) | 3.87 (BLEU) | None | None | None |

_Quality: Language Detection = accuracy on Tatoeba (12 langs); Translation = BLEU on IIT-Bombay en-hi; RAG = indexed real-scheme chunks; LLM = fully-offline generation. Latency/CPU/Memory measured live via psutil._