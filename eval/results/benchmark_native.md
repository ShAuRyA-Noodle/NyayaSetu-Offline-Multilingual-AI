# NyayaSetu Benchmark — profile: native

- Host: AMD64, 32 logical CPUs
- Worker threads: 32
- Timestamp: 2026-07-14T23:14:02Z

## Table 1 — Per-task performance (measured)

| Task | Quality | Latency (s) | CPU % | Memory (MB) |
|------|---------|-------------|-------|-------------|
| Language Detection | 0.9688 (accuracy) | 0.0 | 0.0 | 177.0 |
| Scheme Query (RAG retrieval) | 13 (indexed_chunks) | 0.0237 | 80.8 | 1175.1 |
| Offline LLM Answer | — | 1.085 | 69.2 | 3450.3 |
| Translation (en->hi) | 3.87 (BLEU) | None | None | None |

_Quality: Language Detection = accuracy on Tatoeba (12 langs); Translation = BLEU on IIT-Bombay en-hi; RAG = indexed real-scheme chunks; LLM = fully-offline generation. Latency/CPU/Memory measured live via psutil._