"""
Dual-mode database adapter: SQLite (local dev) <-> PostgreSQL (production).

Goal: ZERO changes to route code. Existing `.execute(sql, ?)`, `row[0]`,
`row['col']`, `cursor.lastrowid`, `PRAGMA ...` all continue to work.

Mode selection:
  - DATABASE_URL unset, empty, or sqlite://... -> SQLite
  - DATABASE_URL starts with postgresql:// or postgres:// -> PostgreSQL

What this adapter translates at runtime (Postgres mode only):
  - '?' placeholders         -> '%s' (respects string literals)
  - 'PRAGMA ...'             -> no-op (Postgres doesn't use PRAGMAs)
  - "datetime('now')"        -> "CURRENT_TIMESTAMP"
  - INSERT ... (no RETURNING) -> INSERT ... RETURNING id (for lastrowid)
  - Tuple rows               -> dict-like rows (supports row[0] AND row['col'])

Callers do NOT need to know which backend is active.
"""

import os
import re
import sqlite3
import logging
from contextlib import contextmanager
from typing import Any, Iterable, List, Optional, Sequence, Union

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Mode detection
# --------------------------------------------------------------------------
_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
_SQLITE_PATH = os.environ.get("NYAYASETU_DB_PATH", "data/governance.db")


def _is_postgres_url(url: str) -> bool:
    return url.startswith("postgresql://") or url.startswith("postgres://")


IS_POSTGRES = _is_postgres_url(_DATABASE_URL)
IS_SQLITE = not IS_POSTGRES


def get_backend_name() -> str:
    return "postgresql" if IS_POSTGRES else "sqlite"


def get_db_path() -> str:
    """Returns the SQLite DB path (for callers that expect a filesystem path)."""
    return _SQLITE_PATH


# --------------------------------------------------------------------------
# Lazy psycopg2 import - only required in production
# --------------------------------------------------------------------------
_psycopg2 = None
_psycopg2_extras = None


def _load_psycopg2():
    global _psycopg2, _psycopg2_extras
    if _psycopg2 is None:
        import psycopg2 as _pg
        import psycopg2.extras as _pg_extras
        _psycopg2 = _pg
        _psycopg2_extras = _pg_extras
    return _psycopg2, _psycopg2_extras


# --------------------------------------------------------------------------
# SQL translation (Postgres mode only)
# --------------------------------------------------------------------------
_PRAGMA_RE = re.compile(r"^\s*PRAGMA\b.*$", re.IGNORECASE | re.DOTALL)
_DATETIME_NOW_RE = re.compile(r"datetime\s*\(\s*['\"]now['\"]\s*\)", re.IGNORECASE)
_DATE_NOW_RE = re.compile(r"date\s*\(\s*['\"]now['\"]\s*\)", re.IGNORECASE)


def _translate_placeholders(sql: str) -> str:
    """Replace '?' with '%s', but skip '?' inside string literals."""
    out = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch in ("'", '"'):
            # Scan through string literal
            quote = ch
            out.append(ch)
            i += 1
            while i < n:
                c = sql[i]
                out.append(c)
                if c == "\\" and i + 1 < n:
                    # Escaped char
                    out.append(sql[i + 1])
                    i += 2
                    continue
                if c == quote:
                    # Check for SQL-style escaped quote ('')
                    if i + 1 < n and sql[i + 1] == quote:
                        out.append(sql[i + 1])
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue
        if ch == "?":
            out.append("%s")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _translate_sql(sql: str) -> str:
    """Translate SQLite-specific SQL to PostgreSQL-compatible SQL."""
    # datetime('now') / date('now') -> CURRENT_TIMESTAMP
    sql = _DATETIME_NOW_RE.sub("CURRENT_TIMESTAMP", sql)
    sql = _DATE_NOW_RE.sub("CURRENT_DATE", sql)
    # ? -> %s (must be last to avoid disturbing literals)
    sql = _translate_placeholders(sql)
    return sql


def _is_pragma(sql: str) -> bool:
    return bool(_PRAGMA_RE.match(sql))


# --------------------------------------------------------------------------
# Row wrappers: dict-like access that ALSO supports integer indexing
# --------------------------------------------------------------------------
import datetime as _datetime


def _coerce_pg_value(v):
    """
    Make Postgres return values match SQLite's string-based behavior.

    SQLite stores TIMESTAMP as TEXT (ISO strings), so route code often does
    `datetime.fromisoformat(row['col'])`. Postgres returns native datetime objects,
    which would break that code. Convert them back to ISO strings here.
    """
    if isinstance(v, _datetime.datetime):
        return v.isoformat(sep=" ")  # SQLite uses space separator
    if isinstance(v, _datetime.date):
        return v.isoformat()
    return v


class _PGRow:
    """Wraps a psycopg2 DictRow to also support row[0], row[1] tuple-style access."""

    __slots__ = ("_row", "_keys")

    def __init__(self, row, keys):
        self._row = row
        self._keys = keys

    def __getitem__(self, key):
        if isinstance(key, int):
            return _coerce_pg_value(self._row[self._keys[key]])
        return _coerce_pg_value(self._row[key])

    def __contains__(self, key):
        return key in self._row

    def get(self, key, default=None):
        if key in self._row:
            return _coerce_pg_value(self._row[key])
        return default

    def keys(self):
        return self._keys

    def values(self):
        return [_coerce_pg_value(self._row[k]) for k in self._keys]

    def items(self):
        return [(k, _coerce_pg_value(self._row[k])) for k in self._keys]

    def __iter__(self):
        return iter(self._keys)

    def __len__(self):
        return len(self._keys)

    def __repr__(self):
        return f"_PGRow({dict(self._row)!r})"


# --------------------------------------------------------------------------
# Postgres cursor wrapper
# --------------------------------------------------------------------------
class _PGCursor:
    """
    Cursor wrapper that mimics sqlite3.Cursor behavior on top of psycopg2.

    - .execute(sql, params): translates SQL, runs on psycopg2 cursor
    - .executemany(sql, seq): translates SQL once, runs on psycopg2 cursor
    - .fetchone() / .fetchall(): returns _PGRow objects (dict + tuple access)
    - .lastrowid: returns ID from last INSERT via RETURNING id
    - .rowcount: pass-through
    - .close(): pass-through
    """

    def __init__(self, pg_cursor):
        self._cur = pg_cursor
        self._lastrowid: Optional[int] = None

    # Context manager support for `with cursor:`
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close()
        except Exception:
            pass

    def execute(self, sql: str, params: Optional[Sequence] = None):
        # Silently skip PRAGMA statements - Postgres doesn't need them
        if _is_pragma(sql):
            return self
        translated = _translate_sql(sql)
        # Auto-inject RETURNING id for plain INSERTs (so lastrowid works)
        needs_returning = (
            translated.lstrip().upper().startswith("INSERT ")
            and "RETURNING" not in translated.upper()
        )
        if needs_returning:
            # Strip trailing semicolons/whitespace before appending
            stripped = translated.rstrip().rstrip(";")
            translated = stripped + " RETURNING id"
        try:
            if params is None:
                self._cur.execute(translated)
            else:
                self._cur.execute(translated, tuple(params))
        except Exception as e:
            # If RETURNING failed because table has no 'id' column, retry without it
            if needs_returning and "id" in str(e).lower() and "does not exist" in str(e).lower():
                original = _translate_sql(sql)
                if params is None:
                    self._cur.execute(original)
                else:
                    self._cur.execute(original, tuple(params))
                self._lastrowid = None
                return self
            raise
        # Capture lastrowid from RETURNING
        if needs_returning:
            try:
                row = self._cur.fetchone()
                self._lastrowid = row[0] if row else None
            except Exception:
                self._lastrowid = None
        return self

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence]):
        if _is_pragma(sql):
            return self
        translated = _translate_sql(sql)
        self._cur.executemany(translated, [tuple(p) for p in seq_of_params])
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        keys = [d.name for d in (self._cur.description or [])]
        return _PGRow(row, keys)

    def fetchall(self) -> List[_PGRow]:
        rows = self._cur.fetchall()
        if not rows:
            return []
        keys = [d.name for d in (self._cur.description or [])]
        return [_PGRow(r, keys) for r in rows]

    def fetchmany(self, size: int = 1):
        rows = self._cur.fetchmany(size)
        if not rows:
            return []
        keys = [d.name for d in (self._cur.description or [])]
        return [_PGRow(r, keys) for r in rows]

    @property
    def lastrowid(self):
        return self._lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass

    def __iter__(self):
        # sqlite3.Cursor is iterable; mirror that behavior
        keys = [d.name for d in (self._cur.description or [])]
        for row in self._cur:
            yield _PGRow(row, keys)


# --------------------------------------------------------------------------
# Postgres connection wrapper
# --------------------------------------------------------------------------
class _PGConnection:
    """
    Connection wrapper that mimics sqlite3.Connection.

    - .cursor() returns a _PGCursor
    - .execute(sql, params) mirrors sqlite3 shortcut - creates a temp cursor
    - .commit() / .rollback() / .close() pass-through
    - Assigning .row_factory = sqlite3.Row is a no-op (PG uses DictCursor)
    """

    def __init__(self, pg_conn):
        self._conn = pg_conn
        self._row_factory = None  # set by legacy code; ignored

    @property
    def row_factory(self):
        return self._row_factory

    @row_factory.setter
    def row_factory(self, value):
        # sqlite3.Row compatibility - we always return dict-like rows anyway
        self._row_factory = value

    def cursor(self) -> _PGCursor:
        _, extras = _load_psycopg2()
        return _PGCursor(self._conn.cursor(cursor_factory=extras.DictCursor))

    def execute(self, sql: str, params: Optional[Sequence] = None) -> _PGCursor:
        # sqlite3.Connection supports .execute() as shortcut for .cursor().execute()
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence]) -> _PGCursor:
        cur = self.cursor()
        cur.executemany(sql, seq_of_params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Public connection factory
# --------------------------------------------------------------------------
def _connect_sqlite(path: Optional[str] = None):
    actual = path or _SQLITE_PATH
    # Ensure parent directory exists
    parent = os.path.dirname(actual)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(actual)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
    except Exception as e:
        logger.warning(f"PRAGMA setup failed: {e}")
    return conn


def _connect_postgres():
    pg, _ = _load_psycopg2()
    raw = pg.connect(_DATABASE_URL)
    # Explicit transaction control - we manage commits ourselves
    raw.autocommit = False
    return _PGConnection(raw)


def connect(db_path: Optional[str] = None) -> Any:
    """
    Returns a DB connection in the current mode.
    Behaves like sqlite3.Connection in either mode.
    """
    if IS_POSTGRES:
        return _connect_postgres()
    return _connect_sqlite(db_path)


@contextmanager
def get_db(db_path: Optional[str] = None):
    """
    Context manager for DB access. Same semantics as the original sqlite3 version:
      - auto-commit on success
      - auto-rollback on exception
      - always close
    """
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_connection(db_path: Optional[str] = None):
    """
    Get a raw connection (caller must close). Prefer get_db() context manager.
    """
    return connect(db_path)
