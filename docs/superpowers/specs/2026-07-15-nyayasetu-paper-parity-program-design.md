# NyayaSetu Paper-Parity Program — Design Spec

**Date:** 2026-07-15
**Branch:** `feature/paper-parity-program`
**Author:** Shaurya Punj (with Claude Code)

## Purpose

The published paper *"NyayaSetu-GovAgent: An Offline-First Multilingual AI System for Rural
Governance Workflows"* makes claims the current codebase does not yet implement. The conference
is already complete; the paper will **not** be rewritten. Instead, this program brings the **code
up to the paper** — building every claimed capability for real, measured honestly, and running
entirely on the developer's hardware.

## Ground-truth gap (audit summary)

Verified against the repo on 2026-07-15:

| Paper claim | Repo reality |
|---|---|
| Offline-first, compact on-device LLM (Phi-2/MobileLLM), 8-bit quant, "no internet required" | Cloud-first: Groq `llama-3.3-70b` primary; Ollama fallback is dev-only + unbundled |
| fastText language detection @ 98.7% | `langdetect` library, no measured accuracy |
| Custom 40M translation model, gov-fine-tuned | Sarvam `mayura` cloud API |
| Grievance routing 89% via hierarchical-attention multi-label net | LLM prompt → JSON + keyword-dict fallback; no trained model |
| CRDT sync protocol | Simple operation queue |
| AES-256 local encryption + SHA-256 integrity | JWT + bcrypt; SHA-256 only for token/cache hashing |
| ~350MB Android APK, Raspberry Pi kiosk, hardware profiles | Web SPA + dev-only Electron shell; no mobile build |
| 15,000+ scheme descriptions | 3 seed schemes |
| Eval: 1,200 queries / 450 grievances / 300 drafting tasks; Tables 1 & 2 numbers; 25-user + 8-official study | No datasets, no benchmark harness, no results artifacts |
| 12 languages offline | 12 langs via **Sarvam cloud**; UI only en/hi; offline voice off-by-default |

Real strengths the paper under-sells (kept, not rebuilt): 6-layer anti-hallucination RAG, full
grievance-lifecycle FSM + SLA engine, enterprise auth/authz, prompt-injection sanitization,
circuit breaker, Postgres/Docker/Vercel/HF deploy stack.

## Goals

1. Every paper capability exists and runs on the developer's Alienware M16 R1 (RTX 4080 Laptop,
   12 GB VRAM).
2. Every reported number is produced by a **reproducible benchmark harness** on **real data** —
   no synthetic ground truth, no hand-typed results.
3. A genuine **offline lane** (LLM, ASR, TTS, translation, langdetect) runs with **zero network**,
   alongside the existing cloud lane.

## Non-goals / honesty constraints

- **No fabricated results.** Numbers come only from the harness.
- **No physical Pi / Android phone.** Constrained hardware profiles are reproduced via
  **CPU-thread + memory-capped runs** and the **Android Studio emulator** (real APK on an
  emulated low-end device). Every emulated profile is labeled as such in outputs.
- **No synthetic scheme data.** Knowledge base is scraped from real government portals.
- Cloud lane (Groq, Sarvam) stays as an optional enhancement, not removed.

## Constraints

- Single machine: Alienware M16 R1, RTX 4080 Laptop 12 GB VRAM.
- ML modules run in a pinned **Python 3.11/3.12 venv** (`.venv-ml`) — system Python is 3.14, too
  new for torch/ctranslate2/llama-cpp-python wheels. Backend keeps its current environment.
- Node 24 (fine for frontend + Capacitor).

## Module backlog

Dependency order: M0 → (M1 → M2) → M3–M6 → M7 → M8/M9 → M10 → M11 → M13.

### Phase 1 — Data
- **M0 — Scheme corpus + daily refresh.** Scraper for `myScheme.gov.in` (~3,600+ schemes) +
  `data.gov.in`; normalize → chunk (eligibility/benefits/process) → embed → FAISS + Postgres.
  APScheduler daily cron keeps the KB live. 100% real data.

### Phase 2 — Offline AI core
- **M3 — Bundled quantized on-device LLM.** `llama-cpp-python` + bundled GGUF. Ship
  **Qwen2.5-3B-Instruct Q4_K_M** as the compact edge model (matches paper's "compact"; runs
  CPU-only for emulated profiles); **Qwen2.5-7B-Instruct Q4_K_M** available for the full-power
  profile. Runtime is self-contained (no Ollama). Cloud Groq remains optional. Makes
  "compact, on-device, quantized, no-internet" literally true.
- **M5 — fastText language detection.** Bundle `lid.176`; replace `langdetect`; measure accuracy
  on a labeled 12-language set.
- **M4 — Offline voice, bundled + default-capable.** faster-whisper (ASR) + Piper (TTS, higher
  quality than pyttsx3); models bundled; wired as working default across 12 languages.
- **M6 — Offline compact NMT.** IndicTrans2-distilled (AI4Bharat) or NLLB-distilled, quantized;
  offline translation; measured BLEU. Satisfies the compact-NMT capability.

### Phase 3 — ML model
- **M7 — Trained grievance classifier.** Fine-tune **MuRIL / IndicBERT** as a two-level
  (category → subcategory) multi-label classifier with attention head, on the local GPU. Keep the
  existing LLM+keyword path as fallback. Report real accuracy/F1.

### Phase 4 — Evaluation
- **M1 — Eval datasets.** Built from the real scraped corpus + real grievance patterns; expert-rubric
  labeled. Targets: ~1,200 queries (6 langs), ~450 grievances, ~300 drafting tasks. Versioned.
- **M2 — Benchmark harness.** One command → every Table-1 metric (accuracy/quality, latency,
  CPU %, memory, BLEU) and Table-2 comparison, across native + emulated-constrained profiles.
  Reproducible, committed, results written to `eval/results/`.

### Phase 5 — Offline infra
- **M8 — CRDT sync engine.** OR-Set (collections) + LWW-register (fields) over the existing
  operation queue; bidirectional conflict-free sync with officer-action priority.
- **M9 — At-rest encryption.** SQLCipher (AES-256 DB) + AES-GCM for KB files + SHA-256 integrity
  manifest.

### Phase 6 — Edge deploy
- **M10 — PWA + Android APK.** Complete the PWA (service worker + generated icons); wrap with
  **Capacitor** → real Android APK (real artifact + measured size); validate in Android Studio
  emulator on an emulated low-end device profile.

### Phase 7 — Depth + study
- **M11 — Model-optimization depth.** 8-bit/4-bit quantization (done via GGUF), structured
  head-pruning + knowledge distillation + operator-fusion experiments on the compact models, with
  before/after metrics. Deepest / last.
- **M13 — Evaluation study.** Build the study instrument (task scripts, rubrics, consent/notes
  templates) and run a **real expert-rubric evaluation** on actual system outputs at meaningful N.
  Field recruitment of citizens/officials remains the author's to run whenever available.

## Architecture note

New code adds an **offline lane** parallel to the existing cloud lane. A capability router selects
lane per request (offline default when models present; cloud when keys set and enhancement wanted).
Existing production stack, RAG safety layers, auth, and lifecycle engine are preserved and reused.

## Testing / methodology

- Each module ships with its own tests.
- All reported metrics originate from M2; results files are committed and regenerable.
- Constrained-profile emulation methodology is documented alongside results and clearly labeled.

## Risks / open items

- **Python 3.14 vs ML wheels** → mitigated by dedicated 3.11/3.12 ML venv.
- **myScheme scraping** may need rate-limiting / HTML-structure resilience; cron must tolerate
  portal changes.
- **IndicTrans2 exact param count** differs from the paper's "40M"; we satisfy the capability and
  report the real model + measured BLEU (per agreed "capability, measured" decision).
- **VRAM** comfortably fits 3B/7B Q4 and small-model fine-tuning; 13B+ full fine-tunes are out.

## Sequencing summary

```
M0 ─▶ M1 ─▶ M2
      ▲      ▲
M3 ─┬─┘      │
M5 ─┤        │
M4 ─┤        │
M6 ─┘        │
M7 ──────────┘
M8, M9  (parallel, after core)
M10 (after M3/M4)
M11, M13 (last)
```

Each module gets its own implementation plan via the writing-plans skill, built and verified in
sequence with review checkpoints.
