# NyayaSetu - Project Intelligence

## Project Overview
NyayaSetu (न्यायसेतु) is an AI-powered citizen governance platform for India. Electron desktop app (React 18 + TypeScript + Vite) backed by a Python FastAPI backend with RAG pipeline, voice interface (12 Indian languages), and enterprise auth.

## Tech Stack
- **Backend**: Python, FastAPI, Uvicorn (port 8001)
- **Frontend**: React 18 + TypeScript + Vite 5 + Electron 28
- **LLM**: Qwen 2.5 14B (Q4_0) via Ollama (localhost:11434)
- **Embeddings**: paraphrase-multilingual-mpnet-base-v2 (768-dim)
- **Vector Store**: FAISS IndexFlatIP
- **Database**: SQLite (WAL mode), 20+ tables, 4 migrations
- **Auth**: JWT HS256 + bcrypt
- **Voice**: Sarvam AI (online) / faster-whisper + pyttsx3 (offline)
- **Styling**: Tailwind CSS with custom Indian earth-tone palette

## Key Directories
- `src/api/` — FastAPI routes, middleware, auth, database, migrations
- `src/core/` — RAG pipeline (embedder, rag_engine, document_processor)
- `src/generation/` — LLM client, answer generator, prompt templates
- `src/modules/` — Summarizer, grievance router, notice drafter, NyayaVaani voice
- `desktop/src/` — React frontend (pages, components, contexts, services)
- `data/` — SQLite DB, FAISS index, audio cache
- `models/` — Cached sentence-transformer model

## API Base URLs
- Backend: `http://localhost:8001`
- Frontend: `http://localhost:5173`
- Ollama: `http://localhost:11434`

## Design System
Custom Tailwind palette: mitti (clay), haldi (turmeric), neel (indigo), kora (cream), sukhiGhaas (grass), saffron (#FF9933), india-green (#138808), terracotta. Cultural elements: WarliIllustration, AshokaChakra, TricolorDivider, khadi-texture. Fonts: Noto Sans, Playfair Display, Yatra One.

## Frontend UI/UX Skills (Installed)

### Impeccable Design (pbakaus/impeccable)
21 design commands for frontend polish. Use `/polish`, `/audit`, `/typeset`, `/critique`, `/arrange`, `/distill`, `/bolder`, `/overdrive`, `/colorize`, `/animate`, `/adapt`, `/clarify`, `/delight`, `/extract`, `/frontend-design`, `/harden`, `/normalize`, `/onboard`, `/optimize`, `/quieter`, `/teach-impeccable`.

### shadcn/ui (shadcn/ui)
Component management skill. Auto-detects project config via `components.json`. Use for adding, searching, styling, and composing shadcn UI components.

### UI UX Pro Max (nextlevelbuilder/ui-ux-pro-max-skill)
Design intelligence skill with 7 sub-skills: `/ui-ux-pro-max` (core), `/ckm-banner-design`, `/ckm-brand`, `/ckm-design`, `/ckm-design-system`, `/ckm-slides`, `/ckm-ui-styling`.

### Interaction Design (ui-skills/interaction-design)
Microinteractions, motion design, transitions, and user feedback patterns. Timing: 100-150ms (micro), 200-300ms (small), 300-500ms (medium). Always respect `prefers-reduced-motion`. Animate only `transform` and `opacity`.

### Interface Design (ui-skills/interface-design)
Dashboard and admin panel craft. Intent-first process: domain exploration → color world → signature element → default rejection. Mandates: every choice must be intentional (swap test, squint test, signature test, token test). Subtle layering for hierarchy. Commands: `/interface-design:status`, `/interface-design:audit`, `/interface-design:extract`, `/interface-design:critique`.

### Web Design Guidelines (ui-skills/web-design-guidelines)
Vercel's web interface guidelines compliance checker. Audits design, accessibility, and UX. Reports findings in `file:line` format.

## Conventions
- All frontend API calls go through `desktop/src/services/api.ts` (Axios with auth interceptor)
- Backend API prefix: `/api/v1/`
- Role hierarchy: citizen (1) → officer (2) → admin (3)
- Database connection: use `get_db()` context manager from `src/api/database.py`
- Pydantic models for request validation in `src/api/schemas.py`
- All pages are role-adaptive (same route, different UI per role)

## Running the Project
```bash
# Backend
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd desktop && npm run dev:vite
```
