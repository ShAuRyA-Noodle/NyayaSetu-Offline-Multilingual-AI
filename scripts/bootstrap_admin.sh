#!/usr/bin/env bash
# =============================================================================
# scripts/bootstrap_admin.sh
#
# Wrapper around scripts/create_first_admin.py.
# Reads the BOOTSTRAP_ADMIN_* env vars, validates them, then runs the Python
# script which actually inserts the admin row in Postgres / SQLite.
#
# Required env vars:
#   BOOTSTRAP_ADMIN_EMAIL     e.g. admin@nyayasetu.example
#   BOOTSTRAP_ADMIN_PASSWORD  >= 8 chars, must contain upper, lower, digit
#   DATABASE_URL              Postgres URL (Neon) OR sqlite:// path
#
# Optional:
#   BOOTSTRAP_ADMIN_FULL_NAME (default: "Platform Admin")
#   BOOTSTRAP_ADMIN_PHONE     (default: empty)
#
# Usage:
#   export BOOTSTRAP_ADMIN_EMAIL=admin@nyayasetu.example
#   export BOOTSTRAP_ADMIN_PASSWORD='SuperStr0ngP@ss'
#   export DATABASE_URL='postgresql://...neon.tech/neondb?sslmode=require'
#   bash scripts/bootstrap_admin.sh
# =============================================================================

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

missing=0
for var in BOOTSTRAP_ADMIN_EMAIL BOOTSTRAP_ADMIN_PASSWORD DATABASE_URL; do
  if [[ -z "${!var:-}" ]]; then
    echo "ERROR: $var is not set" >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  cat <<'EOF' >&2

Required environment variables are missing. Set them and re-run:

  export BOOTSTRAP_ADMIN_EMAIL="admin@nyayasetu.example"
  export BOOTSTRAP_ADMIN_PASSWORD='ChangeMe-Now-9!'
  export DATABASE_URL='postgresql://...neon.tech/neondb?sslmode=require'
  bash scripts/bootstrap_admin.sh
EOF
  exit 1
fi

# Soft password sanity check (the Python script enforces the real rules).
pw="${BOOTSTRAP_ADMIN_PASSWORD}"
if [[ ${#pw} -lt 8 ]]; then
  echo "ERROR: BOOTSTRAP_ADMIN_PASSWORD must be at least 8 characters." >&2
  exit 2
fi
if ! [[ "$pw" =~ [A-Z] && "$pw" =~ [a-z] && "$pw" =~ [0-9] ]]; then
  echo "ERROR: BOOTSTRAP_ADMIN_PASSWORD must contain upper, lower, and digit." >&2
  exit 2
fi

if [[ ! -f "scripts/create_first_admin.py" ]]; then
  echo "ERROR: scripts/create_first_admin.py is missing." >&2
  echo "       This script is owned by another agent — ask them to land it first." >&2
  exit 3
fi

PY="${PYTHON:-python}"
echo "==> Running create_first_admin.py against ${DATABASE_URL%%@*}@..."
exec "$PY" scripts/create_first_admin.py \
  --email "$BOOTSTRAP_ADMIN_EMAIL" \
  --password "$BOOTSTRAP_ADMIN_PASSWORD" \
  --full-name "${BOOTSTRAP_ADMIN_FULL_NAME:-Platform Admin}" \
  --phone "${BOOTSTRAP_ADMIN_PHONE:-}"
