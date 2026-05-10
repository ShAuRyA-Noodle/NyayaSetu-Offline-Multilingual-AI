# NyayaSetu Architecture

This document describes how NyayaSetu is wired in production. For local
development setup see [README.md](../README.md). For deployment steps see
[DEPLOYMENT.md](../DEPLOYMENT.md). For day-2 operations see
[RUNBOOK.md](RUNBOOK.md).

---

## Production topology

```
                            ┌─────────────────────┐
                            │      Cloudflare     │
                            │  proxied DNS + WAF  │
                            │   + Turnstile CAPT  │
                            └──────────┬──────────┘
                                       │ HTTPS
                ┌──────────────────────┼──────────────────────┐
                ▼                                             ▼
    ┌─────────────────────┐                       ┌────────────────────────┐
    │   Vercel (SPA)      │ ─── Bearer JWT ─────▶ │  HF Spaces (Docker)    │
    │   React 18 + Vite   │   (VITE_API_URL)      │  FastAPI + uvicorn     │
    │   /privacy /terms   │                       │  port 7860, persist FS │
    └─────────────────────┘                       └───────────┬────────────┘
        Web Speech API                                        │
        live ASR/TTS in browser                               │
                                                              │
                              ┌───────────────────────────────┼───────────────────────┐
                              ▼                               ▼                       ▼
                  ┌────────────────────┐         ┌────────────────────┐   ┌────────────────────┐
                  │  Neon (Postgres)   │         │   Groq Cloud LLM   │   │   Sarvam AI        │
                  │  pooled, sslmode   │         │ llama-3.3-70b      │   │  Bulbul TTS only   │
                  │  24h PITR          │         │  ~14.4k req/day    │   │  (server cache)    │
                  └────────────────────┘         └────────────────────┘   └────────────────────┘

    Observability:  UptimeRobot ─▶ /health        Sentry ─▶ backend + SPA
```

Total monthly cost on the recommended stack: **$0**. Free tiers of:
Vercel Hobby, Hugging Face Spaces (Docker, 16 GB RAM), Neon (0.5 GB), Groq
(~14.4k req/day), Cloudflare DNS + Turnstile, UptimeRobot, Sentry (5k events).

---

## Logical layers

### 1. Frontend layer — Vercel SPA

- **Build**: `desktop/` is a Vite-built React 18 SPA. `npm run build:web`
  produces a static bundle that Vercel serves from its edge.
- **Routing**: `HashRouter` for Electron compatibility; works equally well
  on Vercel.
- **Auth**: Axios interceptor in `desktop/src/services/api.ts` attaches the
  Bearer JWT to every request and redirects to `/login` on 401.
- **Voice**: live ASR/TTS uses the browser's **Web Speech API**. Server-side
  Sarvam Bulbul is only used to generate cached audio for published notices
  (because that audio outlives any one session and is shared across users).
- **i18n**: `react-i18next` with English + Hindi UI strings only. The 12
  voice languages are powered by Sarvam server-side.
- **Compliance**: `/privacy` and `/terms` static pages must be live before
  the Vercel deploy is considered "done."

### 2. Backend layer — Hugging Face Spaces (Docker SDK)

- **Image**: built from the multi-stage `Dockerfile` at the repo root.
  Stage 1 (`builder`) compiles wheels with `build-essential`; stage 2
  (`runtime`) is slim, non-root, drops compilers and curl.
- **Port**: `EXPOSE 7860` (HF Spaces requirement). The `PORT` env var is
  honored at runtime — HF sets `PORT=7860`; locally we default to `8001`.
- **User**: runs as `appuser` (uid 1000) — matches the uid HF Spaces uses
  for persistent volumes.
- **Persistent FS**: `TRANSFORMERS_CACHE=/app/models` and `HF_HOME=/app/models`
  point at the persistent volume, so the 420 MB sentence-transformer is
  downloaded once and reused across container restarts.
- **FAISS**: `data/schemes_faiss.index` is **not** baked into the image.
  If it's missing on first boot, the RAG engine rebuilds it from
  `data/schemes_seed.json`.
- **Healthcheck**: pure-Python `urllib` against `/health` (no curl).

### 3. Database layer — Neon Postgres

- **Tier**: free (0.5 GB storage, 24 h point-in-time recovery).
- **Connection**: pooled connection string (ends `-pooler`) with
  `?sslmode=require`.
- **Schema**: 20+ tables, 4 versioned migrations (`src/api/migrations/`)
  applied automatically on backend boot.
- **Migration from local SQLite**: one-shot via
  `scripts/migrate_sqlite_to_postgres.py` (init schema or copy data).
- **Parity**: `tests/test_db_parity.py` exercises every adapter path
  against both backends so SQL written for SQLite still behaves on
  Postgres.

### 4. AI layer — Groq + RAG + Voice

```
User question
   │
   ▼
Embedder (paraphrase-multilingual-mpnet-base-v2, 768d)
   │
   ▼
FAISS IndexFlatIP   ─▶ top-k=3 (Q&A) or k=5 (routing)
   │
   ▼
Prompt builder (anti-hallucination rules from src/generation/prompt_templates.py)
   │
   ▼
LLM client
   ├─ primary:  Groq Cloud  (llama-3.3-70b-versatile, temp 0.1)
   └─ fallback: Ollama localhost (Qwen 2.5 14B, dev only)
   │
   ▼
Multi-stage validation (length / source / number / JSON repair)
   │
   ▼
Answer + citations + confidence
```

Voice (`src/modules/nyayavaani/`) plugs into the same layer for the
voice grievance flow:

```
Audio in (WebM/Opus) ─▶ ASR (Sarvam saarika v2.5)
                           │
                           ▼
                       Language detect (langdetect + Devanagari fallback)
                           │
                           ▼
                       Intent + entity extraction (LLM)
                           │
                           ▼
                       Translate to English (Sarvam mayura v1)
                           │
                           ▼
                       Grievance router (department + priority + SLA)
                           │
                           ▼
                       Translate ack back to source language
                           │
                           ▼
                       TTS (Sarvam bulbul v3, 22 050 Hz WAV) ─▶ cached + returned
```

### 5. Authentication flow

```
1. POST /api/v1/auth/register or /login
2. Backend verifies password (bcrypt), checks lockout state,
   creates a session row, signs a JWT (HS256, 24 h).
3. Frontend stores JWT in localStorage; Axios interceptor adds it
   to every request as `Authorization: Bearer <token>`.
4. Backend middleware decodes JWT, looks up the session row,
   enforces rate limits and audit logging.
5. On 401 the frontend redirects to /login. On inactivity
   (30 min mouse/key/scroll/touch silence) the frontend logs out
   pre-emptively.
6. POST /api/v1/auth/logout invalidates the session row.
```

Security extras: 5 failed logins ⇒ 15 min lockout; password history
(last 5 blocked); officer signup gated by 8-char admin-issued codes
(30-day expiry); audit log row for every privileged action.

### 6. Role hierarchy

NyayaSetu uses three numeric roles. Higher numbers can do everything a
lower number can.

| Role     | Level | Can do |
| -------- | :---: | --- |
| citizen  | 1     | Submit grievances, browse schemes, ask the chatbot, listen to notices, view own profile/sessions. |
| officer  | 2     | Everything a citizen can, plus: triage the grievance inbox, update statuses, comment, draft notices, upload schemes. |
| admin    | 3     | Everything an officer can, plus: user management, audit logs, system health, officer registration codes, SLA config, approve/publish notices, system cache. |

Pages are **role-adaptive**: the same route renders different UI per role
(e.g. `/grievances` shows the submit form for citizens, the inbox for
officers, and global analytics for admins).

---

## Why this topology

A few non-obvious choices:

- **HF Spaces over Render** — the embedder + FAISS index need ~1.5 GB RAM
  hot. Render free tier gives 512 MB and aggressively cold-starts; HF Spaces
  gives 16 GB and persistent FS, both free.
- **Web Speech API for live voice** — keeps audio out of our backend on the
  hot path, eliminates Sarvam quota burn for casual chat. Sarvam is only
  invoked for cacheable assets (notice narration), where the cost amortizes
  across all listeners of that notice.
- **Cloudflare Turnstile over reCAPTCHA** — free, no third-party tracking,
  works in India.
- **Neon over Supabase** — we don't need Supabase's auth/storage/edge
  functions; we just need Postgres with backups. Neon's free tier is
  smaller but its PITR is enough for a village pilot.
