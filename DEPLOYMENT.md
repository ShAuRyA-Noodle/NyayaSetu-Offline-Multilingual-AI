# NyayaSetu Deployment Guide

Step-by-step guide to deploy NyayaSetu to production with **zero behavior drift from localhost**.

**Target stack:** Neon (Postgres) + Render (backend) + Vercel (frontend)
**Cost:** $0/month on free tiers (upgrade to ~$7/mo Render Starter for always-on)

---

## Architecture

```
Browser
  |
  v
Vercel (React SPA)   --- VITE_API_URL --->   Render (FastAPI backend)
                                                  |
                                                  v
                                             Neon (Postgres)
                                                  |
                                                  v
                                         Sarvam AI + Groq Cloud
```

---

## Prerequisites

1. GitHub account with this repo pushed
2. Neon account (free, https://console.neon.tech)
3. Render account (free, https://render.com)
4. Vercel account (free, https://vercel.com)
5. Groq API key (https://console.groq.com)
6. Sarvam AI API key (https://dashboard.sarvam.ai)

---

## Phase 0 - Pre-deploy safety (5 min)

### 0.1 Stop tracking the SQLite database in git

Your `data/governance.db` contains user PII (emails, password hashes) and is currently tracked in git. Untrack it before any public push:

```bash
git rm --cached data/governance.db
git commit -m "Stop tracking SQLite database (contains PII)"
```

The file stays on your laptop. It just won't be pushed to GitHub anymore.

### 0.2 Verify no secrets are committed

```bash
git log --all --full-history -- .env | head
# Should return nothing. If it returns anything, rotate those keys immediately.
```

### 0.3 Generate a production JWT secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Save the output - you'll paste it into Render env vars in Phase 3.

---

## Phase 1 - Neon (Postgres) setup (5 min)

1. Go to https://console.neon.tech and create a project named `nyayasetu`.
2. When prompted for region, pick the one closest to your Render region (usually `US East`).
3. From the project dashboard, click **Connection Details**.
4. Copy the **pooled connection string** - it looks like:
   ```
   postgresql://neondb_owner:xxx@ep-cool-mountain-123456-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
5. Save it - this is your `DATABASE_URL`.

### 1.1 Initialize schema and migrate data

From your laptop:

```bash
# Set the URL (PowerShell)
$env:DATABASE_URL = "postgresql://neondb_owner:xxx@...neon.tech/neondb?sslmode=require"

# Dry-run first to see what will be copied
python scripts/migrate_sqlite_to_postgres.py --dry-run

# Init schema AND copy data
python scripts/migrate_sqlite_to_postgres.py --init-schema
```

Expected output:
```
Source:      data/governance.db
Destination: postgresql://neondb_owner:***@ep-....neon.tech/neondb

[1/3] Initializing Postgres schema...
  Postgres schema initialized from postgres_schema.sql

[3/3] Copying rows (live)...
  users: 4/4 row(s) inserted
  sessions: 62/62 row(s) inserted
  ...
  Resetting Postgres SERIAL sequences...

Done. Rows read: 213, rows inserted: 213
```

### 1.2 Verify data made it to Neon

Run the parity test pointing at Neon:

```bash
python tests/test_db_parity.py
```

All 32 tests should pass.

---

## Phase 2 - Local Docker parity test (optional but recommended, 10 min)

This step proves the Dockerized backend behaves identically to your localhost. Skip if short on time.

```bash
# Build the backend image
docker build -t nyaya-backend .

# Run it against Neon
docker run --rm -p 8001:8001 \
  -e DATABASE_URL="$env:DATABASE_URL" \
  -e GROQ_API_KEY="your-groq-key" \
  -e SARVAM_API_KEY="your-sarvam-key" \
  -e JWT_SECRET_KEY="your-generated-secret" \
  -e CORS_ORIGINS="http://localhost:5173" \
  nyaya-backend

# In another terminal, hit the health endpoint
curl http://localhost:8001/health
```

If this returns 200 OK and the regular frontend (npm run dev:vite) works against it, you're golden.

---

## Phase 3 - Render (backend) deploy (10 min)

1. Push your code to GitHub (if not already).
2. Go to https://dashboard.render.com and click **New > Web Service**.
3. Connect your GitHub repo.
4. Fill out:
   - **Name:** `nyayasetu-api`
   - **Region:** Same as Neon (e.g. Ohio)
   - **Branch:** `main`
   - **Runtime:** `Docker`
   - **Dockerfile path:** `./Dockerfile`
   - **Instance type:** `Free` (or `Starter` for always-on, $7/mo)

5. Under **Environment Variables**, add:

   | Key | Value |
   |---|---|
   | `ENV` | `production` |
   | `DATABASE_URL` | (paste from Neon step 1.4) |
   | `GROQ_API_KEY` | (your Groq key) |
   | `SARVAM_API_KEY` | (your Sarvam key) |
   | `JWT_SECRET_KEY` | (the token you generated in 0.3) |
   | `JWT_ALGORITHM` | `HS256` |
   | `JWT_EXPIRY_HOURS` | `24` |
   | `CORS_ORIGINS` | `https://nyayasetu.vercel.app` (fill after Phase 4) |

6. Click **Create Web Service**.

Render will build the Docker image (takes ~5-8 minutes - the sentence-transformer model is 1GB).

Once deployed, your backend is live at `https://nyayasetu-api.onrender.com`.

### 3.1 Verify backend

```bash
curl https://nyayasetu-api.onrender.com/health
# First request after idle may take 30s on free tier (cold start) - this is normal.
```

---

## Phase 4 - Vercel (frontend) deploy (5 min)

1. Go to https://vercel.com and click **Add New > Project**.
2. Import your GitHub repo.
3. Fill out:
   - **Project Name:** `nyayasetu`
   - **Framework Preset:** `Vite`
   - **Root Directory:** `desktop` (click Edit, select `desktop`)
   - **Build Command:** (leave default - Vercel reads `vercel.json`)
   - **Output Directory:** `dist`

4. Under **Environment Variables**, add:

   | Key | Value |
   |---|---|
   | `VITE_API_URL` | `https://nyayasetu-api.onrender.com` |

5. Click **Deploy**.

Build takes ~30-60 seconds. Your app is live at `https://nyayasetu.vercel.app`.

### 4.1 Update Render CORS

Go back to Render > Environment and update `CORS_ORIGINS` to your actual Vercel URL. Render will auto-redeploy.

---

## Phase 5 - Smoke test the live deployment (5 min)

Run the automated smoke test:

```bash
$env:API_URL = "https://nyayasetu-api.onrender.com"
$env:FRONTEND_URL = "https://nyayasetu.vercel.app"
python scripts/smoke_test.py
```

Expected: all checks PASS. If anything fails, the script tells you exactly what.

---

## Phase 6 - Post-deploy checklist

- [ ] Custom domain wired (optional: nyayasetu.app -> Vercel, api.nyayasetu.app -> Render)
- [ ] Billing alerts set on Groq and Sarvam (avoid surprise costs)
- [ ] Sentry DSN added to Render env vars (optional error monitoring)
- [ ] README updated with live URL
- [ ] Portfolio post drafted

---

## Troubleshooting

### "Failed to connect to Neon"
- Check `DATABASE_URL` includes `?sslmode=require` at the end.
- Verify you copied the **pooled** connection string (ends with `-pooler`).

### "Cold start takes 30s"
- Expected on Render free tier. Upgrade to Starter ($7/mo) for always-on.
- Alternatively, use a cron job (e.g. UptimeRobot free) to ping `/health` every 10 minutes.

### "CORS error in browser console"
- Verify `CORS_ORIGINS` on Render matches your Vercel URL exactly (including `https://` prefix, no trailing slash).
- Force a Render redeploy after changing env vars.

### "Voice / transcribe endpoint 500s"
- Check Sarvam API key is valid (hit `https://api.sarvam.ai/health` with your key).
- Check Render logs for the actual error.

### "Feature X worked locally but not in production"
- Compare the exact SQL that was run. Postgres is stricter than SQLite about types.
- Run `python tests/test_db_parity.py` against production `DATABASE_URL` - if it passes, the adapter is fine and the issue is higher up.

---

## Rollback plan

If something goes wrong in production:

1. **Frontend:** Vercel keeps every deploy. Dashboard > Deployments > click older version > Promote to Production.
2. **Backend:** Render keeps last 10 deploys. Dashboard > Events > Rollback.
3. **Database:** Neon has point-in-time recovery (free tier: 24 hours). Dashboard > Restore.

Your SQLite `data/governance.db` on your laptop remains untouched the whole time. Worst case, you fall back to running the app locally and keep debugging.
