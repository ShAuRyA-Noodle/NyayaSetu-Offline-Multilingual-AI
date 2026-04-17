"""
Database Migration Runner

Tracks and applies schema migrations in order.
Each migration is a .py file in the migrations/ directory with an `upgrade(conn)` function.
"""

import os
import importlib
import logging
import sqlite3
from typing import List, Tuple

from ..database import get_db, get_db_path

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.dirname(os.path.abspath(__file__))


def _ensure_migrations_table(conn):
    """Create migrations tracking table if it doesn't exist (dialect-aware)."""
    from .. import db_adapter
    id_type = "SERIAL PRIMARY KEY" if db_adapter.IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS _migrations (
            id {id_type},
            name TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def get_applied_migrations(conn: sqlite3.Connection) -> List[str]:
    """Get list of already-applied migration names."""
    _ensure_migrations_table(conn)
    cursor = conn.execute("SELECT name FROM _migrations ORDER BY id")
    return [row[0] for row in cursor.fetchall()]


def get_pending_migrations() -> List[Tuple[str, str]]:
    """
    Discover migration files and return those not yet applied.
    Returns list of (name, filepath) tuples sorted by name.
    """
    migration_files = []
    for filename in sorted(os.listdir(MIGRATIONS_DIR)):
        if filename.startswith("__") or not filename.endswith(".py"):
            continue
        if filename == "runner.py":
            continue
        name = filename[:-3]  # strip .py
        filepath = os.path.join(MIGRATIONS_DIR, filename)
        migration_files.append((name, filepath))

    with get_db() as conn:
        applied = get_applied_migrations(conn)

    return [(name, path) for name, path in migration_files if name not in applied]


def apply_migration(name: str, filepath: str):
    """Apply a single migration."""
    logger.info(f"Applying migration: {name}")

    spec = importlib.util.spec_from_file_location(name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "upgrade"):
        raise ValueError(f"Migration {name} missing upgrade() function")

    with get_db() as conn:
        _ensure_migrations_table(conn)
        module.upgrade(conn)
        conn.execute("INSERT INTO _migrations (name) VALUES (?)", (name,))
        conn.commit()

    logger.info(f"Migration applied: {name}")


def run_all_pending():
    """Apply all pending migrations in order."""
    # In Postgres mode, postgres_schema.sql already contains every column and table
    # that the migration files would add. Skip legacy migrations (they use PRAGMA
    # table_info which is SQLite-only). Mark them as applied for bookkeeping.
    from .. import db_adapter
    if db_adapter.IS_POSTGRES:
        logger.info("Postgres backend detected - marking legacy migrations as applied (schema already current)")
        with get_db() as conn:
            _ensure_migrations_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM _migrations")
            applied = {row[0] for row in cursor.fetchall()}
            all_migrations = [name for name, _ in [
                (f[:-3], None) for f in sorted(os.listdir(MIGRATIONS_DIR))
                if not f.startswith("__") and f.endswith(".py") and f != "runner.py"
            ]]
            for name in all_migrations:
                if name not in applied:
                    cursor.execute("INSERT INTO _migrations (name) VALUES (?)", (name,))
        return 0

    pending = get_pending_migrations()

    if not pending:
        logger.info("No pending migrations")
        return 0

    logger.info(f"Found {len(pending)} pending migration(s)")

    for name, filepath in pending:
        apply_migration(name, filepath)

    logger.info(f"Applied {len(pending)} migration(s)")
    return len(pending)


def rollback_last():
    """Rollback the last applied migration (if it has a downgrade function)."""
    with get_db() as conn:
        applied = get_applied_migrations(conn)

    if not applied:
        logger.info("No migrations to rollback")
        return

    last = applied[-1]
    filepath = os.path.join(MIGRATIONS_DIR, f"{last}.py")

    if not os.path.exists(filepath):
        logger.error(f"Migration file not found: {filepath}")
        return

    spec = importlib.util.spec_from_file_location(last, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "downgrade"):
        logger.error(f"Migration {last} has no downgrade() function")
        return

    with get_db() as conn:
        module.downgrade(conn)
        conn.execute("DELETE FROM _migrations WHERE name = ?", (last,))
        conn.commit()

    logger.info(f"Rolled back migration: {last}")
