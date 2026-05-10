# Contributing to NyayaSetu

Thanks for your interest in NyayaSetu. This project exists so that government
services in India become accessible to people who currently can't reach them —
because of language, literacy, or connectivity. Contributions that move the
needle on that mission are very welcome.

## Ground rules

1. Be respectful. We follow the spirit of the
   [Contributor Covenant](https://www.contributor-covenant.org/).
2. Security issues do **not** go in public issues — see
   [SECURITY.md](SECURITY.md).
3. Don't commit secrets, real user data, real grievances, or anything that
   could identify a citizen. Use `data/schemes_seed.json`-style synthetic data.

## Development setup

See the **Quick Start** section of [README.md](README.md) for local setup.
For deployment-related changes, see [DEPLOYMENT.md](DEPLOYMENT.md).

In short:

```bash
# Backend
pip install -r requirements.txt
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd desktop && npm install --legacy-peer-deps && npm run dev:vite
```

## Branch naming

Use prefixes so the branch tells a reviewer what the change is, at a glance:

- `feat/...` — a new user-visible feature
- `fix/...` — a bug fix
- `docs/...` — documentation only
- `chore/...` — tooling, deps, repo plumbing
- `refactor/...` — internal change, no user-visible delta
- `test/...` — tests only
- `perf/...` — performance work

Examples: `feat/notice-narration-cache`, `fix/sla-pause-clock-drift`,
`docs/runbook-postgres-backup`.

## Commit format

We use [Conventional Commits](https://www.conventionalcommits.org/). The
short form:

```
<type>(<optional scope>): <short summary>

<optional body, wrapped at ~72 chars>

<optional footer: BREAKING CHANGE, refs #123, etc.>
```

Common types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`,
`build`, `ci`. Example:

```
feat(grievance): pause SLA clock when waiting on citizen docs

When a grievance enters status 'waiting_for_citizen', the SLA deadline
is paused and resumed on next status transition. This prevents officers
from being penalized for delays they don't control.

Refs #142
```

## Pull request process

1. Fork the repo (or create a branch if you're a maintainer).
2. Create your branch off `main` using the naming convention above.
3. Open a draft PR early if you want feedback on direction.
4. Fill out the PR template — explain the *why*, not just the *what*.
5. Make sure CI passes (`.github/workflows/ci.yml`):
   - Backend tests (DB parity vs Postgres).
   - Frontend build (`npm run build:web`).
   - Docker build.
6. At least **one approving review** from a maintainer is required before
   merge.
7. Squash-merge into `main`. Keep the merged commit message Conventional.

## Coding standards

These aren't yet wired into a pre-commit hook (TODO), but please match the
existing style:

### Python (`src/`)

- Target Python **3.11**.
- Format with **black**, lint with **ruff**.
- Type hints on all public functions.
- Use `get_db()` context manager for DB access — never open raw connections.
- Pydantic models for request/response shapes (`src/api/schemas.py`).

### TypeScript / React (`desktop/src/`)

- Strict TypeScript — no `any` without a `// @ts-expect-error: <reason>`.
- Lint with **eslint**, format with **prettier** (TODO: shared config).
- All API calls go through `desktop/src/services/api.ts`. Don't fetch from
  random components.
- Respect `prefers-reduced-motion`. Animate only `transform` and `opacity`.

### General

- Tests for new behavior. The CI workflow runs `tests/test_db_parity.py` and
  the smoke test — your change should not break either.
- Keep PRs focused. One concern per PR.
- Update docs (`README.md`, `docs/RUNBOOK.md`, etc.) if you change observable
  behavior.

## Security issues

**Stop.** If your contribution touches a security-sensitive area (auth, JWT,
sessions, password hashing, rate limiting, file upload, SQL construction,
admin endpoints), please:

1. Read [SECURITY.md](SECURITY.md).
2. If the issue you're fixing is a vulnerability, report it privately first.
   We'll coordinate the public PR with the disclosure.

## License

By contributing, you agree that your contributions will be licensed under
the [Apache License 2.0](LICENSE).
