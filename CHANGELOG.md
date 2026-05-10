# Changelog

All notable changes to NyayaSetu are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - upcoming — "Deployment Ready"

The deployment-readiness release. No new user-facing features; the focus is
making the project deployable on free tiers in well under an hour and safe to
run as a public, multi-user pilot.

### Added
- Apache-2.0 `LICENSE`.
- `SECURITY.md` with private disclosure policy (90-day coordinated).
- `CONTRIBUTING.md` with branch / commit conventions.
- `CHANGELOG.md` (this file).
- `docs/ARCHITECTURE.md` — system architecture with diagrams.
- `docs/RUNBOOK.md` — operator runbook (backup, restore, recovery).
- `docs/HF_SPACES_README.md` — Hugging Face Spaces metadata + landing page.
- `.github/workflows/ci.yml` — push/PR CI: backend tests, frontend build, Docker build.
- `.github/workflows/deploy-frontend.yml` — webhook-triggered Vercel deploy.
- `.github/ISSUE_TEMPLATE/bug_report.md`, `feature_request.md`,
  `pull_request_template.md`.
- `scripts/cleanup_repo.sh` — one-shot cleanup of tracked runtime artifacts
  (governance.db, FAISS index, .agents/, etc.). Dry-run by default.
- `scripts/bootstrap_admin.sh` — env-driven wrapper around
  `scripts/create_first_admin.py`.
- `frontend` profile in `docker-compose.yml` — local Vite preview at port 4173.
- `EXPOSE 7860` in the Dockerfile so HF Spaces can route to the container.
- `TRANSFORMERS_CACHE` / `HF_HOME` set in the Dockerfile so the
  sentence-transformer downloads land in mounted persistent storage.

### Changed
- **Deployment target shifted from Render to Hugging Face Spaces.**
  Free-tier HF Spaces gives 16 GB RAM and persistent FS, which fits the
  embedder + FAISS index without paid hosting. Render section removed from
  `DEPLOYMENT.md`. `docs/ARCHITECTURE.md` reflects the new topology.
- `Dockerfile` is now multi-stage (builder + runtime). Final image drops the
  build toolchain. Healthcheck no longer depends on `curl`; it uses pure
  Python `urllib`. `PORT` env var is honored (8001 local, 7860 on HF Spaces).
- `docker-compose.yml` clearly marked LOCAL DEV ONLY. Adds an optional
  `frontend` service behind the `web` profile.
- README: corrected "12 Indian languages" claim — UI ships with English and
  Hindi only; voice supports 12 via Sarvam.
- README + `CLAUDE.md` deploy/API-base sections updated for HF Spaces.

### Removed
- Empty placeholder dirs `backend/` and `temp/`.
- Stale `desktop/electron/main.js` (duplicate of `desktop/main.js`, the
  one referenced by `desktop/package.json`'s `main` field).
- `desktop/launch.js` (unreferenced).
- Root `package-lock.json` 88-byte stub (real lockfile is in `desktop/`).
- `__pycache__/` directories committed under `src/`.
- Stale `backend/data/...` ignore lines from `.gitignore` (the dir no longer
  exists).

### Security
- `cleanup_repo.sh` untracks `data/governance.db` (contains user PII), the
  FAISS index, the metadata pickle, `.agents/`, and `skills-lock.json`.
  These remain on the developer's disk but stop being shipped to GitHub.
- `Dockerfile` now runs as a non-root user `appuser` (uid 1000) — matches
  HF Spaces' expected uid.

## [1.0.0] - 2026-04-17 — Initial public release

### Added
- FastAPI backend with 80+ endpoints across 7 routers (auth, core, schemes,
  grievances, notices, admin, NyayaVaani voice).
- React 18 + TypeScript + Vite + Electron frontend with 10 role-adaptive pages.
- RAG pipeline: 768-dim multilingual embeddings (`paraphrase-multilingual-
  mpnet-base-v2`), FAISS IndexFlatIP, Groq llama-3.3-70b primary with Ollama
  Qwen 2.5 14B fallback. Six-layer anti-hallucination system.
- NyayaVaani voice engine: ASR / TTS / translation / intent across 12 Indian
  languages. Sarvam AI online + faster-whisper / pyttsx3 / Ollama offline.
- Grievance lifecycle: AI routing, priority logic, SLA tracking with
  pause/resume, citizen ratings.
- Notice drafter: AI-generated gazette-style notices with review/approve
  workflow and TTS narration.
- Enterprise auth: JWT HS256 + bcrypt, password history (last 5 blocked),
  account lockout (5 attempts / 15 min), DB-backed sessions, audit logging.
- SQLite (WAL mode) with 20+ tables and four versioned migrations.
- Postgres adapter and `scripts/migrate_sqlite_to_postgres.py` for the
  Neon migration path.
- Indian earth-tones / glass-morphism design system in Tailwind.

[Unreleased]: https://github.com/<owner>/<repo>/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/<owner>/<repo>/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/<owner>/<repo>/releases/tag/v1.0.0
