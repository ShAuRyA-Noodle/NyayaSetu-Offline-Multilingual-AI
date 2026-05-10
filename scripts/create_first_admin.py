"""Create the first admin user. Idempotent: refuses if an admin exists.

Usage:
  export BOOTSTRAP_ADMIN_USERNAME=admin
  export BOOTSTRAP_ADMIN_EMAIL=admin@example.org
  export BOOTSTRAP_ADMIN_PASSWORD='S0me!StrongPass'
  python scripts/create_first_admin.py
  unset BOOTSTRAP_ADMIN_USERNAME BOOTSTRAP_ADMIN_EMAIL BOOTSTRAP_ADMIN_PASSWORD
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repo root on sys.path so `import src...` works when run from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.database import get_db, init_core_tables  # type: ignore
from src.api.auth_utils import (  # type: ignore
    create_user,
    validate_password_strength,
)


def main() -> int:
    username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "").strip()
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")

    if not all([username, email, password]):
        print(
            "ERROR: BOOTSTRAP_ADMIN_USERNAME, _EMAIL, _PASSWORD must all be set.",
            file=sys.stderr,
        )
        return 2

    pw_check = validate_password_strength(password)
    if isinstance(pw_check, dict) and not pw_check.get("valid", False):
        print(
            f"ERROR: weak password — {pw_check.get('errors', pw_check)}",
            file=sys.stderr,
        )
        return 2

    init_core_tables()

    with get_db() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=TRUE"
        )
        row = cur.fetchone()
        # Support both sqlite Row (index access) and psycopg2 dict-like rows.
        if row is None:
            admin_count = 0
        else:
            try:
                admin_count = row[0]
            except (KeyError, TypeError):
                admin_count = list(row.values())[0] if hasattr(row, "values") else 0

        if admin_count and admin_count > 0:
            print(
                f"OK: {admin_count} admin user(s) already exist. No action taken."
            )
            return 0

    try:
        # create_user() returns a dict: {"id", "username", "email", "role"}
        result = create_user(
            username=username,
            email=email,
            password=password,
            role="admin",
            phone=None,
            preferred_language="en",
        )
    except Exception as exc:
        print(f"ERROR: failed to create admin: {exc}", file=sys.stderr)
        return 1

    user_id = result.get("id") if isinstance(result, dict) else result
    print(
        f"SUCCESS: created admin user id={user_id}, username={username}, email={email}"
    )
    print("Reminder: unset BOOTSTRAP_ADMIN_* env vars now.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
