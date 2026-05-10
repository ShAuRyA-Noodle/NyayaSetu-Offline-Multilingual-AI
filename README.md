<p align="center">
  <img src="https://img.shields.io/badge/NyayaSetu-AI%20Governance-0D92F4?style=for-the-badge&labelColor=060B18" alt="NyayaSetu" />
</p>

<h1 align="center">NyayaSetu (न्यायसेतु)</h1>

<p align="center">
  <strong>AI-Powered Citizen Governance Platform for India</strong><br/>
  <em>Speak Your Language. Know Your Rights. Get Heard.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Production%20Ready-success?style=flat-square" />
  <img src="https://img.shields.io/badge/UI-en%20%C2%B7%20hi-0D92F4?style=flat-square" />
  <img src="https://img.shields.io/badge/Voice-12%20Indian%20languages-77CDFF?style=flat-square" />
  <img src="https://img.shields.io/badge/LLM-Groq%20%2B%20Ollama-blueviolet?style=flat-square" />
  <img src="https://img.shields.io/badge/Endpoints-80%2B-informational?style=flat-square" />
  <img src="https://img.shields.io/badge/RAG-FAISS%20%2B%20Embeddings-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/License-Apache%202.0-blue?style=flat-square" />
</p>

<p align="center">
  <em>UI ships in English and Hindi. Voice (ASR / TTS / translation) supports 12 Indian languages via Sarvam AI.</em>
</p>

---

## The Problem

India has 1.4 billion citizens, 22 official languages, and hundreds of dialects. Government services remain inaccessible to the people who need them most:

- **Language barriers** — portals are English-first; a Tamil farmer can't navigate a Hindi scheme website
- **Digital divide** — 65%+ rural population can't use complex government interfaces; many are illiterate
- **Grievance black holes** — citizens file complaints with zero visibility into routing, status, or accountability
- **Officer overload** — thousands of complaints manually read, classified, and routed by hand
- **Notice opacity** — gazette notifications in dense legal language are unreadable by common citizens
- **No voice pathway** — illiterate, elderly, and disabled citizens have no digital entry point
- **Connectivity gaps** — internet is unreliable in rural India; cloud-dependent solutions fail where needed most

---

## The Solution

NyayaSetu is an offline-capable, voice-native, multilingual AI platform that connects citizens to government schemes, grievance resolution, and official notices. The web UI is bilingual (English + Hindi); the voice pipeline (ASR / TTS / translation) covers 12 Indian languages, even without internet.

> An illiterate farmer in rural Rajasthan speaks into their phone in Hindi. The system transcribes it, understands it's a payment delay grievance, routes it to the Agriculture department, assigns priority and an SLA deadline, saves it, translates a confirmation back to Hindi, synthesizes it as audio, and plays it back. **One API call. Zero typing. No internet required.**

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  ELECTRON DESKTOP APP                                        │
│  React 18 + TypeScript + Vite 5                              │
│  10 role-adaptive pages | Indian earth-tone design system    │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP (Bearer JWT)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  FASTAPI GATEWAY  (port 8001)                                │
│  CORS | Rate Limiting | Security Headers | Request Logging   │
│                                                              │
│  ┌─────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ ┌────────┐   │
│  │  Auth   │ │Schemes │ │Grievance │ │ Notice │ │ Admin  │   │
│  │12 endpt │ │15+ endp│ │30+ endpt │ │13 endpt│ │14 endpt│   │
│  └────┬────┘ └───┬────┘ └────┬─────┘ └───┬────┘ └───┬────┘   │
│       └──────────┼───────────┼────────────┼──────────┘       │
│                  ▼           ▼            ▼                  │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  RAG ENGINE                                          │    │
│  │  Chunker → Embedder (768d) → FAISS → Qwen 2.5 14B    │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐    │
│  │  NYAYAVAANI VOICE ENGINE                             │    │
│  │  ASR (Sarvam/Whisper) → Intent → TTS (Bulbul/pyttsx3)│    │
│  │  Translation (Mayura/Ollama) — 12 languages          │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────┬───────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌────────────┐ ┌─────────┐ ┌──────────┐
   │  SQLite    │ │  FAISS  │ │  Ollama  │
   │  20+ tables│ │  768d   │ │ Qwen 14B │
   │  WAL mode  │ │  index  │ │ localhost│
   └────────────┘ └─────────┘ └──────────┘
```

---

## Tech Stack

### Backend

| Component | Technology | Details |
|-----------|-----------|---------|
| Framework | FastAPI + Uvicorn | 80+ endpoints across 7 routers |
| LLM | Groq (llama-3.3-70b) / Ollama (Qwen 2.5 14B) | Cloud-first with local fallback, auto-switches via GROQ_API_KEY env var |
| Embeddings | paraphrase-multilingual-mpnet-base-v2 | 768-dim, 50+ languages, L2-normalized, ~420MB |
| Vector Store | FAISS IndexFlatIP | Exact cosine similarity, persisted to disk |
| Database | SQLite (WAL mode) | 20+ tables, 4 versioned migrations, foreign keys |
| Auth | JWT (HS256) + bcrypt | 24h tokens, DB-backed sessions, audit logging |
| ASR | Sarvam AI saarika v2.5 / faster-whisper | Online + offline dual-mode |
| TTS | Sarvam AI bulbul v3 / pyttsx3 | 22050Hz WAV, priya/shubh voices |
| Translation | Sarvam AI mayura v1 / Groq LLM fallback | Formal + colloquial modes |

### Frontend

| Component | Technology | Details |
|-----------|-----------|---------|
| Framework | React 18 + TypeScript | HashRouter for Electron compatibility |
| Build | Vite 5 | Hot module replacement |
| Desktop | Electron 28 | Native window, 1400x900, context isolation |
| Styling | Tailwind CSS | Deep sea-navy glass morphism design system (blue/cyan/coral palette) |
| Animation | Framer Motion + GSAP + Lenis | Apple-grade smooth scroll, page transitions, scroll reveals |
| 3D | Three.js / react-three-fiber | Ambient aurora orbs, gradient mesh backgrounds |
| Charts | Recharts | AreaChart, BarChart, LineChart for analytics |
| i18n | react-i18next | English + Hindi |
| HTTP | Axios | Auth interceptor, 401 auto-redirect |

---

## Core Modules

### 1. RAG Engine — The Intelligence Core

A complete Retrieval-Augmented Generation pipeline that answers citizen queries grounded in real government scheme data.

```
Query (any language)
  → Embed (768-dim multilingual vector)
  → FAISS search (top-k=3 for Q&A, k=5 for routing)
  → Build grounded prompt with retrieved context
  → Qwen 2.5 14B generates answer (temp=0.1)
  → Multi-stage validation
  → Return answer + citations + confidence
```

**Chunking:** Each government scheme is split into 3 semantic chunks — eligibility, benefits, and application process — aligned to how citizens actually ask questions.

**Anti-hallucination system (6 layers):**

| Layer | Mechanism |
|-------|-----------|
| Prompt grounding | "ANSWER ONLY FROM PROVIDED CONTEXT — DO NOT use general knowledge" |
| Explicit refusal | "If missing, say 'I don't have sufficient information'" |
| Length validation | Rejects too-short or too-long responses |
| Source validation | Verifies cited scheme names exist in the provided context |
| Number detection | Flags fabricated statistics not present in any context chunk |
| JSON repair | Bracket balancing and truncation recovery for structured output |

Minimum confidence threshold: **0.3** — below this, chunks are excluded entirely.

---

### 2. NyayaVaani — Voice Interface

Voice-native cross-lingual system enabling citizens who can't read or type to interact with government services by speaking.

**12 supported languages:**

| Language | Native | Script | Language | Native | Script |
|----------|--------|--------|----------|--------|--------|
| Hindi | हिन्दी | Devanagari | Malayalam | മലയാളം | Malayalam |
| Bengali | বাংলা | Bengali | Punjabi | ਪੰਜਾਬੀ | Gurmukhi |
| Tamil | தமிழ் | Tamil | Odia | ଓଡ଼ିଆ | Odia |
| Telugu | తెలుగు | Telugu | Assamese | অসমীয়া | Bengali |
| Marathi | मराठी | Devanagari | English | English | Latin |
| Gujarati | ગુજરાતી | Gujarati | Kannada | ಕನ್ನಡ | Kannada |

**Dual-mode architecture (online + offline):**

| Component | Online (Sarvam AI) | Offline (Local) |
|-----------|-------------------|-----------------|
| Speech-to-Text | saarika v2.5 (25MB / 300s max) | faster-whisper (base, int8, beam=5) |
| Text-to-Speech | bulbul v3 (22050Hz, priya/shubh) | pyttsx3 (rate=150, vol=0.9) |
| Translation | mayura v1 (formal/colloquial) | Ollama sarvam-m-tools (temp=0.2) |
| Intent | — | Ollama sarvam-m-tools (7 intents, 8 categories) |

Online mode auto-detected via API key prefix. Degrades gracefully — never crashes.

**Voice grievance end-to-end flow (single API call):**

```
1. Citizen speaks in any of 12 languages
2. ASR transcribes audio → text
3. Language auto-detected (langdetect + Devanagari script fallback)
4. Intent classified, entities extracted (title, category, location)
5. Translated to English for standardized routing
6. AI assigns department + priority + SLA deadline
7. Grievance saved with unique ID (GR-{date}-{UUID})
8. Acknowledgement translated back to citizen's language
9. TTS synthesizes audio confirmation (22050Hz WAV)
10. Audio returned to citizen
```

---

### 3. Grievance Router — AI-Powered Classification

Routes citizen complaints to the correct department with priority assignment and SLA enforcement.

**Complete lifecycle:**
```
Submit → Pending → Accepted/Rejected → In Progress → Under Review → Resolved → Closed
```

**10 routable departments:** agriculture, rural_development, urban_development, social_welfare, health, education, finance, law_enforcement, infrastructure, employment

**9 categories:** scheme_eligibility, payment_delay, application_rejected, documentation, corruption, service_denial, quality_complaint, information_request, other

**Priority logic:**

| Priority | Triggers | SLA (standard) | SLA (health/law) |
|----------|----------|----------------|-------------------|
| Critical | Emergency keywords | 24 hours | 12 hours |
| High | Payment delay, corruption, service denial | 72 hours | 48 hours |
| Medium | Rejections, documentation, quality | 168 hours | 120 hours |
| Low | Information requests | 336 hours | 240 hours |

**SLA states:** on_track (>25% remaining) → warning (<25%) → breached (overdue) → paused/resolved

Pause/resume support — when waiting for citizen documents, the SLA clock pauses and the deadline extends automatically.

**Resolution estimates:** 7 days (info requests) → 14 days (eligibility) → 30 days (rejections) → 45 days (payment delays) → 60 days (corruption)

**Citizen rating:** 1-5 stars + sub-ratings for resolution quality, response time, and officer behavior.

---

### 4. Scheme Summarizer

RAG + LLM generates structured scheme summaries with fields: `one_line_purpose`, `eligibility[]`, `benefits[]`, `application_steps[]`, `contact_info`. Falls back to LLM-only when the scheme isn't in the RAG database. Supports batch summarization for multiple schemes in one call.

---

### 5. Notice Drafter

AI generates gazette-style government notices across 6 types: circular, order, memo, notification, advisory, amendment.

**Lifecycle:** Draft → Pending Review → Approved → Published → Withdrawn

Officer provides topic and context → RAG retrieves scheme data → Qwen generates 400+ word official notice → Officer reviews and edits → Admin approves → Published to public board. Any published notice can be narrated as TTS audio in all 12 languages with file-level caching.

---

## Authentication & Security

| Feature | Implementation |
|---------|---------------|
| Tokens | JWT HS256, 24h expiry, hourly refresh on frontend |
| Passwords | bcrypt, min 8 chars (upper + lower + digit), cannot reuse last 5 |
| Lockout | 5 failed attempts → 15-minute lock |
| Sessions | DB-stored — forced logout, device tracking (mobile/desktop/web), IP logging |
| Roles | citizen (1) → officer (2) → admin (3) hierarchy |
| Officer Signup | Admin-generated 8-char codes, 30-day expiry |
| Inactivity | 30-minute auto-logout (mouse/key/scroll/touch monitoring) |
| Rate Limiting | 100 req/60s default; login 5/60s; forgot-password 3/60s; 10k key cap |
| Audit Trail | Every action: user, endpoint, IP, status code, duration_ms |
| Headers | X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy |

---

## Database

SQLite with WAL journal mode and enforced foreign keys. 20+ tables across a core schema and 4 versioned migrations (applied automatically on startup, tracked in a `_migrations` table).

**Tables:** `users`, `sessions`, `user_profiles`, `grievances` (30+ columns with AI fields), `grievance_status_updates`, `grievance_status_history`, `grievance_comments`, `grievance_ratings`, `schemes_metadata`, `scheme_chunks`, `scheme_versions`, `scheme_assignments`, `notices`, `notifications`, `sla_records`, `sla_config` (8 pre-populated departments), `upload_history`, `audit_logs`, `officer_registration_codes`, `password_reset_tokens`

**Migration history:**

| # | Name | What it adds |
|---|------|-------------|
| 001 | enterprise_auth | Password history, failed login tracking, session enrichment, audit logs |
| 002 | advanced_schemes | Versioning, assignments, file hashes, tags, keywords, descriptions |
| 003 | grievance_lifecycle | SLA tables, ratings, enhanced status history, AI analysis columns |
| 004 | notice_publishing | Notice workflow with type/status constraints, review/publish columns |

---

## Frontend — 10 Pages

Every page is **role-adaptive** — the same route renders different UI for citizen, officer, and admin.

| Page | Route | Access | What It Does |
|------|-------|--------|-------------|
| Login | `/login` | All | Login + register tabs, officer code real-time validation |
| Dashboard | `/dashboard` | All | Stat cards with tilt effect, AreaChart + BarChart, WarliIllustration |
| Department | `/department` | Officers | Grievance inbox, my active cases, accept/reject/comment, analytics |
| Grievances | `/grievances` | All | Submit + track (citizen), inbox + cases (officer), all + analytics (admin), voice input, ratings |
| Schemes | `/schemes` | All | Browse + summarize (all), upload + rename + delete + manage (officer/admin) |
| Chat | `/chat` | All | RAG Q&A chatbot, voice input, message history, typing indicator |
| Notices | `/notices` | All | Generate + draft (officer), review + approve (admin), public board (all) |
| NyayaVaani | `/nyayavaani` | All | Audio players for notices + schemes, language selector, system status |
| Admin | `/admin` | Admin | 7-tab dashboard: Overview, Grievances, Users, Officer Codes, Audit, SLA, System |
| Settings | `/settings` | All | Theme toggle, language, notifications, password change, sessions |

### Design System — Indian Earth Tones

A custom Tailwind palette rooted in Indian cultural identity. This is not a Material/Bootstrap skin — every visual choice is intentional.

| Name | Meaning | Role |
|------|---------|------|
| **mitti** | Clay / Earth | Primary brand — warm browns |
| **haldi** | Turmeric / Gold | Accent — warm yellows |
| **neel** | Indigo / Navy | Secondary — deep blues |
| **kora** | Unbleached cloth | Background — natural cream |
| **sukhiGhaas** | Dried grass | Surface — muted greens |
| **saffron** | India flag orange | `#FF9933` |
| **india-green** | India flag green | `#138808` |
| **terracotta** | Baked earth | Deep orange accent |

**Dark mode:** bg `#0F0D0A`, surface `#1A1714`, card `#231F1A` — warm dark tones, not cold blacks.

**Typography:** Noto Sans + Noto Sans Devanagari (body), Playfair Display (headings), Yatra One (Devanagari accent).

**Cultural elements:** WarliIllustration (Maharashtra tribal art), AshokaChakra (animated 8s spin), TricolorDivider (saffron-white-green), khadi-texture (hand-woven cloth SVG pattern at 3% opacity).

**Gradients:** gradient-tricolor, gradient-village, gradient-mitti, gradient-saffron, gradient-warm, gradient-night.

---

## Offline-First Architecture

The entire AI core runs on-device. No data leaves the machine. No cloud costs. No internet dependency for core functionality.

| Component | Local | Cloud Enhancement |
|-----------|-------|-------------------|
| LLM (Qwen 2.5 14B via Ollama) | Always | — |
| Embeddings (768-dim multilingual) | Always | — |
| Vector Search (FAISS) | Always | — |
| Database (SQLite) | Always | — |
| Speech-to-Text | faster-whisper | Sarvam saarika v2.5 |
| Text-to-Speech | pyttsx3 | Sarvam bulbul v3 |
| Translation | Ollama sarvam-m-tools | Sarvam mayura v1 |

Online mode auto-detected. System degrades gracefully — lower quality voice, same core functionality.

---

## API Surface

80+ endpoints across 7 router groups:

| Group | Prefix | Count | Scope |
|-------|--------|-------|-------|
| Auth | `/api/v1/auth` | 12 | Register, login, logout, sessions, password management, refresh |
| Core | `/api/v1` | 3 | Health check, system stats, RAG Q&A |
| Schemes | `/api/v1/schemes` | 15+ | CRUD, upload, summarize (single + batch), assign officers, analytics |
| Grievances | `/api/v1/grievances` | 30+ | Full lifecycle, SLA management, ratings, notifications, analytics |
| Notices | `/api/v1/notices` | 13 | Generate, draft, review, approve, publish, withdraw, public board |
| Admin | `/api/v1/admin` | 14 | Users, audit logs, analytics, officer codes, system health, cache |
| NyayaVaani | `/api/v1/nyayavaani` | 10 | ASR, TTS, intent, voice grievance, audio serve, languages |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com) installed and running
- 16GB RAM recommended

### Backend

```bash
# Pull the LLM model (~9GB one-time download)
ollama pull qwen2.5:14b-instruct-q4_0

# Install Python dependencies
pip install -r requirements.txt

# Start the API server
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```bash
cd desktop
npm install
npm run dev:vite
```

Open **http://localhost:5173** in your browser.

### Environment Variables

```env
# Required
JWT_SECRET_KEY=your-secret-key

# Optional
NYAYASETU_DB_PATH=data/governance.db           # Default: data/governance.db
OLLAMA_HOST=http://localhost:11434              # Default: localhost:11434
SARVAM_API_KEY=sk_...                          # Enables online Sarvam AI voice services
```

---

## Key Metrics

| Metric | Value |
|--------|-------|
| API endpoints | 80+ |
| Supported languages | 12 |
| Embedding dimensions | 768 |
| LLM parameters | 14 billion (Q4_0 quantized) |
| Database tables | 20+ |
| Schema migrations | 4 |
| Routable departments | 10 |
| Grievance categories | 9 |
| Voice intents | 7 |
| Notice types | 6 |
| Frontend pages | 10 (all role-adaptive) |
| Custom color families | 8 |
| Auth token expiry | 24 hours |
| Inactivity timeout | 30 minutes |
| Account lockout | 5 attempts / 15 min |
| Password history | Last 5 blocked |
| TTS sample rate | 22,050 Hz |
| Rate limit (default) | 100 req/60s/IP |
| LLM temperature | 0.1 |
| FAISS top-k | 3 (Q&A), 5 (routing) |
| Min confidence | 0.3 |

---

## Project Structure

```
NyayaSetu/
├── src/
│   ├── api/                            # FastAPI application layer
│   │   ├── app.py                      # Entry point, lifespan, router registration
│   │   ├── auth_routes.py              # 12 auth endpoints
│   │   ├── auth_utils.py               # JWT, bcrypt, session management
│   │   ├── core_routes.py              # Health, stats, RAG Q&A
│   │   ├── scheme_routes.py            # Scheme CRUD, upload, summarize
│   │   ├── grievance_routes.py         # 30+ grievance lifecycle endpoints
│   │   ├── notice_routes.py            # Notice generation and workflow
│   │   ├── admin_routes.py             # User mgmt, audit, analytics, officer codes
│   │   ├── database.py                 # SQLite connection manager (WAL + FK)
│   │   ├── middleware.py               # Rate limiting, logging, security headers
│   │   ├── schemas.py                  # Pydantic request/response models
│   │   ├── sla_service.py              # SLA enforcement engine
│   │   ├── notification_service.py     # Notification dispatch
│   │   ├── errors.py                   # Custom exception hierarchy
│   │   └── migrations/                 # Versioned schema migrations
│   │       ├── runner.py               # Auto-applies pending migrations
│   │       ├── 001_enterprise_auth.py
│   │       ├── 002_advanced_schemes.py
│   │       ├── 003_grievance_lifecycle.py
│   │       └── 004_notice_publishing.py
│   │
│   ├── core/                           # RAG pipeline
│   │   ├── embedder.py                 # Multilingual sentence embeddings (768d)
│   │   ├── rag_engine.py               # Chunk → embed → retrieve → generate
│   │   └── document_processor.py       # PDF/DOCX/TXT extraction + chunking
│   │
│   ├── generation/                     # LLM generation layer
│   │   ├── llm_client.py              # Ollama HTTP client (retries, backoff)
│   │   ├── answer_generator.py        # Context + LLM → validated answer
│   │   └── prompt_templates.py        # System prompts, anti-hallucination rules
│   │
│   └── modules/                        # Feature modules
│       ├── summarizer.py              # Scheme summarization (RAG + LLM)
│       ├── grievance_router.py        # AI complaint classification + routing
│       ├── notice_drafter.py          # Gazette-style notice generation
│       └── nyayavaani/                # Voice engine (12 languages)
│           ├── asr_engine.py          # Speech-to-text (Sarvam / Whisper)
│           ├── tts_engine.py          # Text-to-speech (Bulbul / pyttsx3)
│           ├── cross_lingual_engine.py # Translation (Mayura / Ollama)
│           ├── intent_engine.py       # Intent classification + entity extraction
│           ├── language_registry.py   # 12-language registry with full mappings
│           ├── config.py              # Online/offline mode detection
│           ├── router.py              # FastAPI voice endpoints
│           └── startup.py             # Service initialization
│
├── desktop/                            # Electron + React frontend
│   ├── main.js                        # Electron main process
│   ├── src/
│   │   ├── App.tsx                    # Root component
│   │   ├── routes.tsx                 # Route definitions (10 pages)
│   │   ├── pages/                     # Login, Dashboard, Grievances, Schemes,
│   │   │                              # Chat, Notices, NyayaVaani, Admin, Settings,
│   │   │                              # DepartmentDashboard
│   │   ├── components/                # AudioPlayer, VoiceInputButton, WarliIllustration,
│   │   │                              # AshokaChakra, TricolorDivider, LanguageSelector
│   │   ├── contexts/                  # AuthContext, ThemeContext
│   │   ├── services/api.ts           # Axios client (60+ typed methods)
│   │   └── i18n/                     # English + Hindi translation files
│   ├── tailwind.config.js            # Indian earth-tone design system
│   └── vite.config.ts
│
├── data/
│   ├── governance.db                  # SQLite database
│   ├── schemes_faiss.index            # Persisted FAISS vector index
│   ├── schemes_metadata.pkl           # Chunk metadata for FAISS
│   └── audio/                         # TTS audio file cache
│
└── models/                            # Cached sentence-transformer (~420MB)
```

---

## System Requirements

| Tier | CPU | RAM | Storage | Use Case |
|------|-----|-----|---------|----------|
| Minimum | 4 cores | 8 GB | 15 GB | Development, basic testing |
| Recommended | 8 cores | 16 GB | 25 GB | Production, full voice pipeline |
| Optimal | 8+ cores + GPU | 32 GB | 30 GB | Max throughput, fast LLM inference |

---

## Deployment

NyayaSetu deploys to a **$0/month** stack:

- **Backend** — Hugging Face Spaces (Docker SDK, 16 GB RAM, persistent FS).
- **Frontend** — Vercel (Hobby tier, edge-cached SPA).
- **Database** — Neon Postgres (0.5 GB, 24 h point-in-time recovery).
- **LLM** — Groq Cloud free tier (~14 400 req/day).
- **Voice** — Web Speech API in-browser for live ASR/TTS; Sarvam Bulbul
  server-side for cached notice narration.
- **Edge / WAF** — Cloudflare proxied DNS + Turnstile.
- **Uptime** — UptimeRobot. **Errors** — Sentry (free tier).

Step-by-step instructions live in **[DEPLOYMENT.md](DEPLOYMENT.md)**.
The architecture diagram and rationale are in
**[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**. Day-2 operations
(backups, recovery, common 5xxs) are in
**[docs/RUNBOOK.md](docs/RUNBOOK.md)**.

---

## Project meta

- **License** — [Apache 2.0](LICENSE).
- **Security** — please report vulnerabilities privately, see [SECURITY.md](SECURITY.md).
- **Contributing** — branch / commit conventions and PR process in [CONTRIBUTING.md](CONTRIBUTING.md).
- **Changelog** — release history in [CHANGELOG.md](CHANGELOG.md).

---

<p align="center">
  <strong>Built for Rural India</strong><br/>
  <em>Because access to justice shouldn't depend on literacy, language, or internet connectivity.</em>
</p>
