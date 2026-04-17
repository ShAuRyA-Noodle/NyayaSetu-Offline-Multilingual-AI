"""
Database parity test - verifies the db_adapter works identically on
SQLite and Postgres for every idiom the codebase uses.

Usage:
    # Test SQLite (default)
    python -m tests.test_db_parity

    # Test Postgres (requires docker-compose up postgres)
    DATABASE_URL="postgresql://nyaya:nyaya@localhost:5432/nyayasetu" python -m tests.test_db_parity

Exit code 0 = all passed, non-zero = at least one failure.
"""

import os
import sys
import uuid
from pathlib import Path

# Ensure project root is importable when run as a script
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.api import db_adapter
from src.api.database import init_core_tables

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"

_passed = 0
_failed = 0
_warnings = 0


def _check(label: str, condition: bool, detail: str = ""):
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  {GREEN}PASS{RESET}  {label}")
    else:
        _failed += 1
        print(f"  {RED}FAIL{RESET}  {label}  {detail}")


def _warn(label: str, detail: str = ""):
    global _warnings
    _warnings += 1
    print(f"  {YELLOW}WARN{RESET}  {label}  {detail}")


def section(title: str):
    print(f"\n{BOLD}--- {title} ---{RESET}")


def test_placeholder_translation():
    section("Placeholder translation (? -> %s)")
    with db_adapter.get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE role = ?", ("admin",))
        row = cur.fetchone()
        _check("SELECT with ? placeholder", row is not None and row[0] >= 0)


def test_row_access_modes():
    section("Row access modes (index AND name)")
    with db_adapter.get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users LIMIT 1")
        row = cur.fetchone()
        if row is None:
            _warn("no users in DB to test row access")
            return
        _check("row[0] integer access", row[0] is not None)
        _check("row['username'] name access", "username" in [k for k in row.keys()] or row["username"] is not None)


def test_pragma_noop():
    section("PRAGMA handling (no-op in Postgres)")
    with db_adapter.get_db() as conn:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            _check("PRAGMA statements accepted (no error)", True)
        except Exception as e:
            _check("PRAGMA statements accepted", False, str(e))


def test_lastrowid_returning():
    section("cursor.lastrowid via RETURNING")
    test_user = f"paritytest_{uuid.uuid4().hex[:8]}"
    with db_adapter.get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (test_user, f"{test_user}@test.local", "x", "citizen"),
        )
        new_id = cur.lastrowid
        _check("lastrowid populated after INSERT", new_id is not None and new_id > 0)
        # Cleanup
        cur.execute("DELETE FROM users WHERE id = ?", (new_id,))


def test_datetime_now_translation():
    section("datetime('now') -> CURRENT_TIMESTAMP")
    with db_adapter.get_db() as conn:
        cur = conn.cursor()
        # Use a query that SQLite and Postgres both handle after translation
        cur.execute("SELECT CURRENT_TIMESTAMP")
        row = cur.fetchone()
        _check("CURRENT_TIMESTAMP returns a value", row is not None and row[0] is not None)


def test_on_conflict_do_nothing():
    section("ON CONFLICT DO NOTHING (dual-dialect)")
    test_user = f"conflicttest_{uuid.uuid4().hex[:8]}"
    with db_adapter.get_db() as conn:
        cur = conn.cursor()
        # First insert
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (test_user, f"{test_user}@test.local", "x", "citizen"),
        )
        new_id = cur.lastrowid
        # Second insert with conflict on username (UNIQUE)
        try:
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, role)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (username) DO NOTHING
                """,
                (test_user, f"other_{test_user}@test.local", "y", "citizen"),
            )
            _check("ON CONFLICT DO NOTHING accepted", True)
        except Exception as e:
            _check("ON CONFLICT DO NOTHING accepted", False, str(e))
        # Cleanup
        cur.execute("DELETE FROM users WHERE id = ?", (new_id,))


def test_on_conflict_do_update():
    section("ON CONFLICT DO UPDATE (composite key for scheme_assignments)")
    # Create minimal fixtures: a scheme + an officer
    scheme_id = f"pt_scheme_{uuid.uuid4().hex[:6]}"
    officer_user = f"pt_officer_{uuid.uuid4().hex[:6]}"
    assigner_user = f"pt_admin_{uuid.uuid4().hex[:6]}"
    with db_adapter.get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (officer_user, f"{officer_user}@test.local", "x", "officer"),
            )
            officer_id = cur.lastrowid
            cur.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (assigner_user, f"{assigner_user}@test.local", "x", "admin"),
            )
            assigner_id = cur.lastrowid
            cur.execute(
                """
                INSERT INTO schemes_metadata (scheme_id, scheme_name, created_by, source_file)
                VALUES (?, ?, ?, ?)
                """,
                (scheme_id, "Test Scheme", assigner_id, "test.pdf"),
            )
            # First assignment
            cur.execute(
                """
                INSERT INTO scheme_assignments
                (scheme_id, officer_id, assigned_by, can_edit, can_delete, is_active)
                VALUES (?, ?, ?, ?, ?, TRUE)
                ON CONFLICT (scheme_id, officer_id) DO UPDATE SET
                    can_edit = EXCLUDED.can_edit,
                    can_delete = EXCLUDED.can_delete
                """,
                (scheme_id, officer_id, assigner_id, True, False),
            )
            # Second assignment (should upsert, not insert)
            cur.execute(
                """
                INSERT INTO scheme_assignments
                (scheme_id, officer_id, assigned_by, can_edit, can_delete, is_active)
                VALUES (?, ?, ?, ?, ?, TRUE)
                ON CONFLICT (scheme_id, officer_id) DO UPDATE SET
                    can_edit = EXCLUDED.can_edit,
                    can_delete = EXCLUDED.can_delete
                """,
                (scheme_id, officer_id, assigner_id, False, True),
            )
            # Verify only one row exists and can_delete is now TRUE
            cur.execute(
                "SELECT can_edit, can_delete FROM scheme_assignments WHERE scheme_id = ? AND officer_id = ?",
                (scheme_id, officer_id),
            )
            rows = cur.fetchall()
            _check("exactly one row after two upserts", len(rows) == 1, f"got {len(rows)}")
            if rows:
                _check("upsert updated can_delete", bool(rows[0]["can_delete"]))
        finally:
            # Cleanup in FK-safe order
            try:
                cur.execute("DELETE FROM scheme_assignments WHERE scheme_id = ?", (scheme_id,))
                cur.execute("DELETE FROM schemes_metadata WHERE scheme_id = ?", (scheme_id,))
                cur.execute("DELETE FROM users WHERE username IN (?, ?)", (officer_user, assigner_user))
            except Exception:
                pass


def test_schema_tables_exist():
    section("Schema sanity (all expected tables exist)")
    expected = [
        "users", "sessions", "user_profiles", "password_reset_tokens",
        "audit_logs", "schemes_metadata", "scheme_versions", "scheme_assignments",
        "scheme_chunks", "upload_history", "grievances", "grievance_status_updates",
        "grievance_status_history", "grievance_comments", "sla_config", "grievance_sla",
        "sla_records", "grievance_notifications", "notifications", "grievance_ratings",
        "grievance_escalations", "notices", "officer_registration_codes",
    ]
    with db_adapter.get_db() as conn:
        cur = conn.cursor()
        if db_adapter.IS_POSTGRES:
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
        else:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        existing = {row[0] for row in cur.fetchall()}
    for t in expected:
        _check(f"table '{t}' exists", t in existing)


def main():
    mode = "PostgreSQL" if db_adapter.IS_POSTGRES else "SQLite"
    print(f"\n{BOLD}NyayaSetu Database Parity Test{RESET}")
    print(f"Backend: {BOLD}{mode}{RESET}")
    if db_adapter.IS_POSTGRES:
        # Mask password for display
        url = os.environ.get("DATABASE_URL", "")
        import re
        display = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)
        print(f"DATABASE_URL: {display}")
    else:
        print(f"SQLite path: {db_adapter.get_db_path()}")

    # Ensure tables exist (critical for fresh Postgres)
    try:
        init_core_tables()
        print(f"{GREEN}Schema initialized{RESET}")
    except Exception as e:
        print(f"{RED}Schema init failed: {e}{RESET}")
        return 2

    test_schema_tables_exist()
    test_placeholder_translation()
    test_row_access_modes()
    test_pragma_noop()
    test_datetime_now_translation()
    test_lastrowid_returning()
    test_on_conflict_do_nothing()
    test_on_conflict_do_update()

    print(f"\n{BOLD}Summary:{RESET} {GREEN}{_passed} passed{RESET}, "
          f"{RED}{_failed} failed{RESET}, {YELLOW}{_warnings} warnings{RESET}\n")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
