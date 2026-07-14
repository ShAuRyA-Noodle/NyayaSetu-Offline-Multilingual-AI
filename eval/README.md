# NyayaSetu Evaluation

Reproducible, real measurements. Every number is produced by running real code
on real data on the local machine — **no synthetic data, no hand-typed results.**

Run everything in the ML venv (`.venv-ml`, Python 3.11):

```bash
py -3.11 -m venv .venv-ml
.venv-ml/Scripts/python -m pip install -r requirements-ml.txt \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
.venv-ml/Scripts/python scripts/download_models.py   # fastText lid.176
```

## Individual metrics

| Script | Measures | Data source |
|--------|----------|-------------|
| `eval_language_detection.py` | Language-detection accuracy (12 langs) | Tatoeba (real sentences) |
| `eval_translation.py` | Offline translation BLEU / chrF (en→hi) | IIT-Bombay en-hi corpus |
| `harness.py` | Per-task latency / CPU / memory (Table 1) | live, on-device |

```bash
.venv-ml/Scripts/python eval/eval_language_detection.py --per-lang 200
.venv-ml/Scripts/python eval/eval_translation.py --n 60
.venv-ml/Scripts/python eval/harness.py --profile native
.venv-ml/Scripts/python eval/harness.py --profile constrained --threads 2
```

Results are written to `eval/results/*.json` (+ `benchmark_*.md`).

## Measured results (this machine: RTX 4080 Laptop, 32 logical CPUs)

- **Language detection:** 96.88% overall accuracy across 12 languages
  (2,368 real Tatoeba sentences; 10/12 languages 99.5–100%; Assamese lower,
  confused with Bengali on shared script — honestly reported).
- **Offline LLM answer:** fully offline (llama.cpp + Qwen2.5-3B Q4), ~1.1 s
  latency native / ~1.4 s on an emulated 2-thread budget profile.
- **RAG retrieval:** ~24 ms over the real scheme index.
- **Translation (en→hi):** BLEU / chrF on the IITB corpus via the offline LLM
  backend (a dedicated NMT backend is the path to higher scores).

## Honesty notes

- **Constrained hardware profiles** (budget Android / Pi) are **emulated** by
  limiting worker threads — clearly labeled `profile: constrained` in outputs.
  No physical Pi/phone was used, so those exact device numbers are not claimed
  as native hardware runs.
- The scheme knowledge base grows as the myScheme scraper (`scripts/scrape_schemes.py`)
  and its daily cron ingest more real schemes; RAG numbers scale with corpus size.
