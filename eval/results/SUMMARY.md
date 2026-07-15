# NyayaSetu — Measured Results Summary

All figures below are produced by running real code on real data on the development machine (RTX 4080 Laptop, 32 logical CPUs). No synthetic data, no hand-entered numbers. Reproduce with the scripts in `eval/` (see `eval/README.md`).

## Core quality metrics

| Capability | Metric | Value | Dataset (real) |
|------------|--------|-------|----------------|
| Language detection (12 langs) | overall accuracy | **96.88%** | Tatoeba (per-language sentences) (2368 sentences) |
| RAG scheme retrieval | recall@1 / recall@3 | **94.9% / 100.0%** | 39 grounded queries / 13 chunks |
| Governance text classifier | accuracy / macro-F1 | **73.2% / 46.5%** | myScheme scheme→category, 3516 labeled records, 15 classes |
| Offline translation (en→hi) | BLEU / chrF | 3.87 / 23.92 | IIT-Bombay en-hi test |

## Runtime performance (measured live)

| Task | Latency (s) | CPU % | Memory (MB) | Profile |
|------|-------------|-------|-------------|---------|
| Language Detection | 0.0 | 0.0 | 177.0 | native |
| Scheme Query (RAG retrieval) | 0.0237 | 80.8 | 1175.1 | native |
| Offline LLM Answer | 1.085 | 69.2 | 3450.3 | native |
| Language Detection | 0.0002 | 0.0 | 176.5 | constrained (2 threads) |
| Scheme Query (RAG retrieval) | 0.027 | 5.7 | 1164.5 | constrained (2 threads) |
| Offline LLM Answer | 1.413 | 61.0 | 2811.6 | constrained (2 threads) |

## Honesty notes

- The offline translation BLEU reflects the on-device LLM backend; a dedicated NMT backend (IndicTrans2) is the path to paper-grade scores.
- Constrained profiles are **emulated** via thread-limiting, not physical Pi/budget-phone runs (clearly labeled).
- The scheme corpus grows as the scraper + daily cron ingest more real schemes; retrieval numbers scale with corpus size.