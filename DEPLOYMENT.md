# NyayaSetu Deployment Guide

Step-by-step path from a clean checkout to a live, multi-user, $0/month
public deployment. The target audience is a small village pilot.

**Recommended stack ($0/mo):**

| Layer | Service | Free tier shape |
| --- | --- | --- |
| Backend | **Hugging Face Spaces** (Docker SDK) | 16 GB RAM, persistent FS, ffmpeg present |
| Frontend | **Vercel** (Hobby) | Static SPA, edge cache |
| Database | **Neon** (Postgres) | 0.5 GB storage, 24 h PITR |
| LLM | **Groq Cloud** | ~14 400 req / day on free tier |
| Voice (live) | **Web Speech API** (browser) | Free, in-browser ASR/TTS |
| Voice (cached narration) | **Sarvam Bulbul** | Server-side TTS for notice audio only |
| Edge / DDoS / CAPTCHA | **Cloudflare** | Proxied DNS + Turnstile |
| Uptime | **UptimeRobot** | 50 monitors, 5-min interval |
| Errors | **Sentry** | 5 000 events / month |

**Total: $0 / month.** No credit card required.

For the architecture diagram and topology rationale, see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). For day-2 operations
(restore, recovery, common 5xxs), see [docs/RUNBOOK.md](docs/RUNBOOK.md).

---

## Prerequisites

1. Forked or cloned this repo on your laptop, with `main` checked out.
2. Accounts created (no card needed):
   - GitHub
   - [Neon](https://console.neon.tech)
   - [Hugging Face](https://huggingface.co/)
   - [Vercel](https://vercel.com/)
   - [Groq Cloud](https://console.groq.com/)
   - [Sarvam AI](https://dashboard.sarvam.ai/)
   - [Cloudflare](https://dash.cloudflare.com/)
   - [UptimeRobot](https://uptimerobot.com/)
   - [Sentry](https://sentry.io/)
3. Locally installed: Python 3.11, Node 20, Docker (for the optional
   parity test), `git`, `bash`.

---

## Phase 0 — Repo cleanup (5 min)

Untrack runtime artifacts that should never have been in git
(`data/governance.db`, the FAISS index, `.agents/`, `skills-lock.json`)
and remove empty placeholder dirs.

```bash
# Dry run first — shows what would happen
bash scripts/cleanup_repo.sh

# When you're satisfied
bash scripts/cleanup_repo.sh --apply

# Review and commit yourself
git status
git add -A
git commit -m "chore: untrack runtime artifacts; remove empty dirs"
git push
```

---

## Phase 1 — Neon (Postgres) (10 min)

### 1.0 Create project

1. Go to <https://console.neon.tech> and create a project named
   `nyayasetu`.
2. Pick a region geographically close to your HF Space (HF runs in
   `us-east-1` by default; pick **AWS US East**).
3. From the project dashboard, click **Connection Details** and copy the
   **pooled** connection string (the one that ends with `-pooler`):

   ```
   postgresql://neondb_owner:xxx@ep-xxx-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

   Save it as `DATABASE_URL`.

### 1.1 Initialize the schema

From your laptop:

```bash
export DATABASE_URL='postgresql://neondb_owner:xxx@...neon.tech/neondb?sslmode=require'

# Just create the tables; do NOT copy local SQLite data into a public DB
python scripts/migrate_sqlite_to_postgres.py --init-schema --skip-data
```

(If you do want to migrate your local data, drop `--skip-data`. Be aware
that your local `data/governance.db` may contain test users and PII.)

### 1.2 Verify with the parity test

```bash
python tests/test_db_parity.py
```

All tests should pass. If any fail, do **not** continue to phase 2 — the
adapter is the contract between SQLite and Postgres and the entire
production path depends on it.

### 1.3 Bootstrap the first admin

```bash
export BOOTSTRAP_ADMIN_EMAIL="admin@your-domain.example"
export BOOTSTRAP_ADMIN_PASSWORD='ChangeMe-Now-9!'
bash scripts/bootstrap_admin.sh
```

Log in once via the local frontend pointed at Neon (or via curl) to
confirm the credentials work, then change the password from the Settings
page.

---

## Phase 2 — Hugging Face Spaces (backend) (15 min)

1. Go to <https://huggingface.co/new-space>.
2. Fill out:
   - **Owner**: your username or org.
   - **Space name**: `nyayasetu` (or whatever you like).
   - **License**: Apache 2.0.
   - **SDK**: **Docker** ▸ **Blank**.
   - **Hardware**: CPU basic (free).
3. Click **Create Space**.

### 2.1 Wire it to GitHub

The simplest path is to push your repo's contents to the Space's git
remote. From your laptop:

```bash
git remote add hf https://huggingface.co/spaces/<your-username>/nyayasetu
# HF will prompt for an HF token (Settings ▸ Access Tokens, "write" scope)
git push hf main
```

(You can also use the GitHub-sync option in the Space's Settings to
mirror automatically.)

### 2.2 Replace the Space README

The Space's `README.md` is what Hugging Face renders on the Space's
landing page **and** is where the Docker SDK metadata lives. Use the
template at [`docs/HF_SPACES_README.md`](docs/HF_SPACES_README.md):

```bash
# Copy our template into the Space's README
cp docs/HF_SPACES_README.md README.md  # only if the Space repo is separate
git add README.md
git commit -m "chore(hf): add Spaces metadata"
git push hf main
```

If your Space repo and your GitHub repo are the **same** (recommended),
skip this — the Docker SDK reads metadata from the README's YAML
frontmatter, and we keep `docs/HF_SPACES_README.md` ready for that
purpose.

### 2.3 Set Space secrets

In the Space ▸ **Settings** ▸ **Variables and secrets**:

| Key | Value |
| --- | --- |
| `DATABASE_URL` | (paste from Phase 1) |
| `GROQ_API_KEY` | (your Groq key) |
| `SARVAM_API_KEY` | (your Sarvam key) |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_EXPIRY_HOURS` | `24` |
| `ENV` | `production` |
| `CORS_ORIGINS` | `https://<placeholder>` (you'll fill the real Vercel URL in Phase 4) |
| `TRUSTED_PROXIES` | `*` |

The Space will rebuild after secrets change. Build time is ~6–9 minutes
the first time (model download); subsequent rebuilds are warm.

Once the Space shows "Running":

```bash
curl https://<your-username>-nyayasetu.hf.space/health
```

You should get a 200.

---

## Phase 3 — Vercel (frontend) (10 min)

1. Go to <https://vercel.com/new> and import the GitHub repo.
2. Configure:
   - **Framework Preset**: Vite.
   - **Root Directory**: `desktop` (click Edit and select).
   - **Build Command**: leave default — `vercel.json` in `desktop/`
     handles it.
   - **Output Directory**: `dist`.
3. Add environment variables:

   | Key | Value |
   | --- | --- |
   | `VITE_API_URL` | `https://<your-username>-nyayasetu.hf.space` |
   | `VITE_TURNSTILE_SITE_KEY` | (filled in Phase 5; placeholder for now) |

4. Click **Deploy**.

The build takes ~30–60 s. Note your Vercel URL, e.g.
`https://nyayasetu.vercel.app`.

The GitHub `Deploy frontend (Vercel webhook)` workflow is manual-only until a
Vercel project exists. After the first successful deployment, create a deploy
hook for the production branch in Vercel and save its URL as the GitHub Actions
secret `VERCEL_DEPLOY_HOOK_URL`. Run the workflow manually and verify the new
deployment in Vercel before restoring its push trigger. A manual run fails
clearly while the secret is absent.

---

## Phase 4 — CORS handshake (2 min)

Go back to the Space ▸ Settings ▸ Variables and secrets and update
`CORS_ORIGINS` to the actual Vercel URL (no trailing slash):

```
https://nyayasetu.vercel.app
```

The Space rebuilds. Once it's back up, your Vercel SPA can talk to your
HF backend.

---

## Phase 5 — Cloudflare + Turnstile (10 min)

1. In Cloudflare, add your domain and switch its nameservers (this only
   matters if you're using a custom domain — skip if you're fine with
   `*.vercel.app`).
2. **DNS**: in **proxied** mode (orange cloud), point your apex/CNAME
   at the Vercel URL.
3. **Turnstile**: <https://dash.cloudflare.com/?to=/:account/turnstile>.
   Create a site key for your Vercel domain. Copy the **site key**.
4. Update Vercel env: set `VITE_TURNSTILE_SITE_KEY` to the site key,
   and **redeploy**.

The login page now requires Turnstile.

---

## Phase 6 — Smoke test (5 min)

```bash
export API_URL='https://<your-username>-nyayasetu.hf.space'
export FRONTEND_URL='https://nyayasetu.vercel.app'
python scripts/smoke_test.py
```

Expected: every check **PASS**. The script tells you exactly which
endpoint failed if not.

---

## Phase 7 — Observability (10 min)

### UptimeRobot

1. <https://uptimerobot.com/dashboard>.
2. Add monitor → **HTTP(s)** → URL `https://<your-space>.hf.space/health`,
   interval **5 minutes**.
3. Add another for `https://<your-vercel>.vercel.app`.
4. Add an alert contact (email).

This also keeps the HF Space warm.

### Sentry

1. Create a project of type **FastAPI** in Sentry — copy the DSN.
2. Add `SENTRY_DSN` as a Space secret.
3. Create another project of type **React** — copy the DSN.
4. Add `VITE_SENTRY_DSN` to Vercel env and redeploy.

(The wiring on the code side is done lazily — if `SENTRY_DSN` is unset,
Sentry stays disabled. No silent failures.)

---

## Phase 8 — Compliance (5 min)

Before announcing the URL publicly, confirm the legal pages are live:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://<your-vercel>.vercel.app/privacy
curl -s -o /dev/null -w "%{http_code}\n" https://<your-vercel>.vercel.app/terms
```

Both must return 200. The pages should describe:

- What user data is collected (email, hashed password, grievance
  content, IP, audit logs).
- How long it's retained.
- Who to contact for deletion (link to `SECURITY.md` contact).
- That voice audio is processed transiently and not stored beyond the
  cache TTL on `data/audio/`.

---

## Rollback plan

| Layer | Rollback |
| --- | --- |
| Frontend | Vercel ▸ Deployments ▸ pick a previous build ▸ "Promote to Production". |
| Backend | HF Space ▸ Settings ▸ Factory rebuild from a previous commit, or `git revert` and push. |
| Database | Neon ▸ Branches / PITR — restore to a point-in-time within 24 h. |
| DNS | Cloudflare ▸ DNS ▸ flip the orange cloud or change the target. |

---

## Troubleshooting

### "Failed to connect to Neon"
- Make sure `DATABASE_URL` ends with `?sslmode=require`.
- Confirm you're using the **pooled** connection string (host ends with
  `-pooler`).

### "Cold start takes 30s+ on HF Space"
- First request after idle re-warms the embedder. UptimeRobot every
  5 min keeps it warm.

### "CORS error in browser console"
- `CORS_ORIGINS` on the Space must match the Vercel URL **exactly** —
  scheme, no trailing slash.
- Force a Space rebuild after changing the env var.

### "Voice / transcribe endpoint 500s"
- Browser-side: confirm the user granted mic permission.
- Server-side: check Sarvam API key validity; `/api/v1/nyayavaani/health`
  reports the offline-vs-online state.

### "Feature X worked locally but not in production"
- Run `python tests/test_db_parity.py` against the production
  `DATABASE_URL`. If it passes, the issue is application-level.
- Check the Space logs for the actual exception. HF Spaces keeps logs
  for 7 days.

---

For everything that breaks after deploy, see
[docs/RUNBOOK.md](docs/RUNBOOK.md).
