"""
One-shot data migration: SQLite -> PostgreSQL (e.g. Neon).

Copies every row from your local data/governance.db into the Postgres
database pointed at by DATABASE_URL, preserving primary keys, JSON blobs,
timestamps, and booleans.

Prerequisites:
  1. Postgres DB is empty (fresh Neon branch) OR you don't mind appending.
  2. postgres_schema.sql has been applied to it (the script does this if
     --init-schema is passed).
  3. DATABASE_URL env var is set to the Postgres URL.

Usage:
  # Dry run (shows what would happen, no writes)
  python scripts/migrate_sqlite_to_postgres.py --dry-run

  # Initialize Postgres schema AND copy data
  DATABASE_URL="postgresql://user:pass@host/db?sslmode=require" \
      python scripts/migrate_sqlite_to_postgres.py --init-schema

  # Copy data only (schema already initialized)
  DATABASE_URL="postgresql://..." python scripts/migrate_sqlite_to_postgres.py

  # Wipe destination tables first, then copy (DESTRUCTIVE)
  DATABASE_URL="postgresql://..." python scripts/migrate_sqlite_to_postgres.py --wipe

Safety:
  - Uses explicit transaction per table (rollback on error).
  - Never auto-drops tables.
  - After migration, resets Postgres sequences so new INSERTs use correct next IDs.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2-binary not installed. Run: pip install psycopg2-binary")
    sys.exit(2)


# Table copy order respects foreign-key dependencies (parents first).
TABLE_ORDER = [
    "users",
    "user_profiles",
    "sessions",
    "password_reset_tokens",
    "audit_logs",
    "schemes_metadata",
    "scheme_versions",
    "scheme_assignments",
    "scheme_chunks",
    "upload_history",
    "grievances",
    "grievance_status_updates",
    "grievance_status_history",
    "grievance_comments",
    "sla_config",
    "grievance_sla",
    "sla_records",
    "grievance_notifications",
    "notifications",
    "grievance_ratings",
    "grievance_escalations",
    "notices",
    "officer_registration_codes",
    "schemes",  # legacy - only if present
    "_migrations",
]

# Tables that have a SERIAL id column - sequences need resetting after migration
TABLES_WITH_SERIAL_ID = [t for t in TABLE_ORDER if t != "_migrations"] + ["_migrations"]


def _sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def _pg_columns(pg_conn, table: str) -> list[str]:
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return [row[0] for row in cur.fetchall()]


def _sqlite_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (table,)
    )
    return cur.fetchone() is not None


def _pg_table_exists(pg_conn, table: str) -> bool:
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (table,),
        )
        return cur.fetchone() is not None


def _normalize_value(val, col_name: str):
    """
    Convert SQLite-native value to a Postgres-friendly value.
    SQLite stores BOOLEAN as 0/1 INTEGER; Postgres expects true/false.
    """
    if val is None:
        return None
    # Heuristic: column name starts with 'is_' or ends with '_enabled' / specific bool names
    bool_hints = (
        "is_active", "is_used", "is_breached", "is_escalated", "is_paused",
        "is_internal", "is_public", "is_pinned", "is_auto_change",
        "is_current", "is_current_version", "is_read",
        "email_verified", "phone_verified", "can_edit", "can_delete",
        "can_reassign", "can_publish", "auto_escalated",
        "escalation_enabled", "validation_passed", "resolution_within_sla",
        "used", "has_attachments", "paused",
    )
    if col_name in bool_hints and isinstance(val, int) and val in (0, 1):
        return bool(val)
    return val


def _init_schema(pg_conn):
    schema_path = _ROOT / "src" / "api" / "postgres_schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    sql = schema_path.read_text(encoding="utf-8")
    with pg_conn.cursor() as cur:
        cur.execute(sql)
    pg_conn.commit()
    print("  Postgres schema initialized from postgres_schema.sql")


def _wipe_table(pg_conn, table: str):
    with pg_conn.cursor() as cur:
        cur.execute(f'DELETE FROM "{table}"')
    pg_conn.commit()


def _copy_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    table: str,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Copy all rows from a SQLite table to Postgres. Returns (rows_read, rows_inserted)."""
    if not _sqlite_table_exists(sqlite_conn, table):
        return (0, 0)
    # In dry-run without a PG connection, assume destination has matching schema
    if pg_conn is not None and not _pg_table_exists(pg_conn, table):
        print(f"  SKIP {table}: not in Postgres schema")
        return (0, 0)

    sqlite_cols = _sqlite_columns(sqlite_conn, table)
    if pg_conn is not None:
        pg_cols = _pg_columns(pg_conn, table)
        common_cols = [c for c in sqlite_cols if c in pg_cols]
    else:
        # Dry-run fallback: assume all SQLite columns exist in PG
        common_cols = sqlite_cols

    if not common_cols:
        print(f"  SKIP {table}: no matching columns")
        return (0, 0)

    # Read all rows
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.execute(f'SELECT {", ".join(common_cols)} FROM "{table}"')
    rows = cur.fetchall()
    total = len(rows)

    if total == 0:
        print(f"  {table}: 0 rows (empty)")
        return (0, 0)

    if dry_run:
        print(f"  {table}: would copy {total} row(s)  [columns: {len(common_cols)}]")
        return (total, 0)

    # Build INSERT statement
    col_list = ", ".join(f'"{c}"' for c in common_cols)
    placeholders = ", ".join(["%s"] * len(common_cols))
    insert_sql = (
        f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) '
        f'ON CONFLICT DO NOTHING'
    )

    # Normalize and batch-insert
    inserted = 0
    with pg_conn.cursor() as pg_cur:
        batch = []
        for row in rows:
            values = tuple(_normalize_value(row[c], c) for c in common_cols)
            batch.append(values)
            if len(batch) >= 500:
                psycopg2.extras.execute_batch(pg_cur, insert_sql, batch, page_size=500)
                inserted += len(batch)
                batch.clear()
        if batch:
            psycopg2.extras.execute_batch(pg_cur, insert_sql, batch, page_size=500)
            inserted += len(batch)
    pg_conn.commit()
    print(f"  {table}: {inserted}/{total} row(s) inserted")
    return (total, inserted)


def _reset_sequences(pg_conn):
    """After direct INSERT with explicit IDs, bump SERIAL sequences to max(id)+1."""
    with pg_conn.cursor() as cur:
        for table in TABLES_WITH_SERIAL_ID:
            if not _pg_table_exists(pg_conn, table):
                continue
            seq = f"{table}_id_seq"
            try:
                cur.execute(
                    f"SELECT setval(%s, COALESCE((SELECT MAX(id) FROM \"{table}\"), 0) + 1, false)",
                    (seq,),
                )
            except Exception as e:
                print(f"  seq-reset {table}: {e}")
    pg_conn.commit()
    print("  Postgres sequences realigned to max(id)+1")


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite -> PostgreSQL")
    parser.add_argument(
        "--sqlite-path", default="data/governance.db",
        help="Path to source SQLite DB (default: data/governance.db)",
    )
    parser.add_argument(
        "--init-schema", action="store_true",
        help="Apply postgres_schema.sql before copying data",
    )
    parser.add_argument(
        "--wipe", action="store_true",
        help="DELETE all rows from destination tables before copying (DESTRUCTIVE)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without writing anything",
    )
    args = parser.parse_args()

    pg_url = os.environ.get("DATABASE_URL", "").strip()
    if not pg_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set. Get one from https://console.neon.tech")
        sys.exit(2)

    sqlite_path = args.sqlite_path
    if not Path(sqlite_path).exists():
        print(f"ERROR: SQLite DB not found at {sqlite_path}")
        sys.exit(2)

    print(f"Source:      {sqlite_path}")
    if pg_url:
        import re
        masked = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", pg_url)
        print(f"Destination: {masked}")
    else:
        print("Destination: (dry-run, no Postgres)")

    sqlite_conn = sqlite3.connect(sqlite_path)
    pg_conn = None
    if pg_url:
        pg_conn = psycopg2.connect(pg_url)
        pg_conn.autocommit = False

    try:
        if args.init_schema and pg_conn:
            print("\n[1/3] Initializing Postgres schema...")
            _init_schema(pg_conn)

        if args.wipe and pg_conn:
            print("\n[2/3] Wiping destination tables (reverse FK order)...")
            for table in reversed(TABLE_ORDER):
                if _pg_table_exists(pg_conn, table):
                    _wipe_table(pg_conn, table)
            print("  Done")

        # Disable FK checks during bulk load. SQLite often has orphaned rows
        # (FKs aren't enforced by default); Postgres enforces them strictly.
        # We re-enable after the migration and data stays consistent for new rows.
        if pg_conn and not args.dry_run:
            with pg_conn.cursor() as cur:
                cur.execute("SET session_replication_role = 'replica'")
            pg_conn.commit()
            print("  FK checks deferred for load session")

        print(f"\n[3/3] Copying rows ({'dry-run' if args.dry_run else 'live'})...")
        total_read = 0
        total_inserted = 0
        for table in TABLE_ORDER:
            if pg_conn is None and not args.dry_run:
                break
            read, inserted = _copy_table(
                sqlite_conn, pg_conn, table, dry_run=args.dry_run
            )
            total_read += read
            total_inserted += inserted

        if pg_conn and not args.dry_run:
            print("\nResetting Postgres SERIAL sequences...")
            _reset_sequences(pg_conn)
            # Re-enable FK enforcement for future writes
            with pg_conn.cursor() as cur:
                cur.execute("SET session_replication_role = 'origin'")
            pg_conn.commit()
            print("  FK checks re-enabled")

        print(f"\nDone. Rows read: {total_read}, rows inserted: {total_inserted}")
    except Exception as e:
        if pg_conn:
            pg_conn.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        sqlite_conn.close()
        if pg_conn:
            pg_conn.close()


if __name__ == "__main__":
    main()
