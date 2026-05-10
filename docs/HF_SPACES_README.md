---
title: NyayaSetu
emoji: 🇮🇳
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
---

# NyayaSetu — Backend (Docker SDK)

This Hugging Face Space hosts the **FastAPI backend** for
[NyayaSetu](https://github.com/) (न्यायसेतु), an AI-powered citizen
governance platform for India. The frontend SPA is hosted separately on
Vercel.

> Source code: <https://github.com/> (replace with the canonical GitHub URL).

## What runs here

- FastAPI + Uvicorn on port `7860` (HF Spaces requirement).
- RAG pipeline with multilingual sentence-transformer (`paraphrase-multilingual-mpnet-base-v2`, 768-dim).
- FAISS vector store, persisted to `/app/data/`.
- LLM calls go to **Groq Cloud** (`llama-3.3-70b-versatile`).
- Voice synthesis via **Sarvam AI** (Bulbul TTS) for cached notice narration.
- Postgres connection to **Neon** for all relational state.

## Required Space secrets

Set these in the Space's Settings ▸ Variables and secrets:

| Key | Value |
| --- | --- |
| `DATABASE_URL` | Pooled Neon connection string (`postgresql://...?sslmode=require`) |
| `GROQ_API_KEY` | From <https://console.groq.com> |
| `SARVAM_API_KEY` | From <https://dashboard.sarvam.ai> |
| `JWT_SECRET_KEY` | Output of `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_EXPIRY_HOURS` | `24` |
| `ENV` | `production` |
| `CORS_ORIGINS` | `https://<your-vercel-domain>` (no trailing slash) |
| `TRUSTED_PROXIES` | `*` (HF Spaces sits behind a proxy) |

## First-boot behavior

On a cold start with no persistent data, the container will:

1. Download the sentence-transformer model into `$TRANSFORMERS_CACHE`
   (`/app/models`) — about 420 MB, one-time.
2. If `data/schemes_faiss.index` is absent, rebuild it from
   `data/schemes_seed.json`.
3. Run the four DB migrations against `DATABASE_URL`.

Subsequent boots are warm and start in seconds.

## Health check

```
GET /health  ->  200 OK
```

Used by both the container `HEALTHCHECK` and UptimeRobot.

## License

[Apache-2.0](https://github.com/-/-/blob/main/LICENSE).
