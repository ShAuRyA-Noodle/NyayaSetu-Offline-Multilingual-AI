"""
Scheme ingestion — upsert normalized schemes into the governance DB.

Writes to both tables the app uses:
- ``schemes``          → the flat table the RAG chunker reads.
- ``schemes_metadata`` → the rich table the admin/scheme UI reads.

Idempotent: keyed on the myScheme ``slug`` so re-running (e.g. the daily cron)
updates existing rows instead of duplicating them. After ingest it can trigger
a FAISS rebuild so retrieval sees the new data immediately.

100% real scraped data. No synthetic content is ever written.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .myscheme_client import MySchemeClient, MySchemeError
from .normalizer import NormalizedScheme, normalize_scheme

logger = logging.getLogger(__name__)

DEFAULT_DB = "data/governance.db"


@dataclass
class IngestStats:
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    skipped_empty: int = 0
    errors: int = 0

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def ensure_schema(conn: sqlite3.Connection) -> None:
    """
    Ensure the flat ``schemes`` table exists and carries a ``slug`` + ``source``
    column for idempotent upserts. Non-destructive — only adds if missing.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schemes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_name TEXT NOT NULL,
            department TEXT,
            eligibility TEXT,
            benefits TEXT,
            process TEXT
        )
        """
    )
    if not _column_exists(conn, "schemes", "slug"):
        conn.execute("ALTER TABLE schemes ADD COLUMN slug TEXT")
    if not _column_exists(conn, "schemes", "source"):
        conn.execute("ALTER TABLE schemes ADD COLUMN source TEXT")
    # Unique index on slug (partial: only where slug is set) for fast upsert.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_schemes_slug "
        "ON schemes(slug) WHERE slug IS NOT NULL"
    )
    conn.commit()


def _upsert_schemes(conn: sqlite3.Connection, ns: NormalizedScheme) -> str:
    """Upsert into the flat ``schemes`` table. Returns 'inserted' | 'updated'."""
    cur = conn.execute("SELECT id FROM schemes WHERE slug = ?", (ns.slug,))
    row = cur.fetchone()
    if row:
        conn.execute(
            """
            UPDATE schemes
               SET scheme_name = ?, department = ?, eligibility = ?,
                   benefits = ?, process = ?, source = ?
             WHERE slug = ?
            """,
            (
                ns.scheme_name, ns.department, ns.eligibility,
                ns.benefits, ns.process, ns.source, ns.slug,
            ),
        )
        return "updated"
    conn.execute(
        """
        INSERT INTO schemes (scheme_name, department, eligibility, benefits, process, slug, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ns.scheme_name, ns.department, ns.eligibility,
            ns.benefits, ns.process, ns.slug, ns.source,
        ),
    )
    return "inserted"


def _upsert_metadata(conn: sqlite3.Connection, ns: NormalizedScheme) -> None:
    """Upsert into ``schemes_metadata`` (rich metadata for the UI)."""
    if not _column_exists(conn, "schemes_metadata", "scheme_id"):
        return  # table not provisioned in this DB — skip gracefully
    scheme_id = f"myscheme:{ns.slug}"
    total_chars = len(ns.eligibility) + len(ns.benefits) + len(ns.process)
    tags_json = json.dumps(ns.tags, ensure_ascii=False)
    keywords = ", ".join(ns.tags)
    cur = conn.execute(
        "SELECT id FROM schemes_metadata WHERE scheme_id = ?", (scheme_id,)
    )
    exists = cur.fetchone() is not None
    if exists:
        conn.execute(
            """
            UPDATE schemes_metadata
               SET scheme_name = ?, department = ?, category = ?, tags = ?,
                   keywords = ?, description = ?, target_audience = ?,
                   source_file = ?, document_type = ?, status = ?,
                   total_characters = ?, updated_at = CURRENT_TIMESTAMP,
                   indexed_at = CURRENT_TIMESTAMP
             WHERE scheme_id = ?
            """,
            (
                ns.scheme_name, ns.department, ns.category, tags_json,
                keywords, ns.brief_description, ns.target_audience,
                ns.source, "scheme", "active", total_chars, scheme_id,
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO schemes_metadata
                (scheme_id, scheme_name, department, category, tags, keywords,
                 description, target_audience, source_file, document_type,
                 status, total_characters, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                scheme_id, ns.scheme_name, ns.department, ns.category, tags_json,
                keywords, ns.brief_description, ns.target_audience,
                ns.source, "scheme", "active", total_chars,
            ),
        )


def ingest_schemes(
    schemes: Iterable[NormalizedScheme],
    db_path: str = DEFAULT_DB,
) -> IngestStats:
    """Upsert an iterable of normalized schemes into the DB."""
    stats = IngestStats()
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        for ns in schemes:
            stats.fetched += 1
            if not ns.has_content():
                stats.skipped_empty += 1
                continue
            try:
                result = _upsert_schemes(conn, ns)
                _upsert_metadata(conn, ns)
                conn.commit()
                if result == "inserted":
                    stats.inserted += 1
                else:
                    stats.updated += 1
            except sqlite3.Error as e:
                conn.rollback()
                stats.errors += 1
                logger.warning("DB upsert failed for %s: %s", ns.slug, e)
    finally:
        conn.close()
    return stats


def _existing_slugs(db_path: str) -> set[str]:
    """Return slugs already ingested (for resume / incremental skip)."""
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        rows = conn.execute(
            "SELECT slug FROM schemes WHERE slug IS NOT NULL"
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def scrape_and_ingest(
    db_path: str = DEFAULT_DB,
    limit: Optional[int] = None,
    keyword: str = "",
    page_size: int = 100,
    client: Optional[MySchemeClient] = None,
    resume: bool = True,
    progress: bool = False,
) -> IngestStats:
    """
    End-to-end: page through myScheme, fetch+normalize each scheme, upsert.

    Args:
        db_path: SQLite governance DB path.
        limit: Cap the number of NEW schemes ingested this run (None = all).
        keyword: Optional search filter.
        page_size: List pagination size.
        client: Injectable client (for testing).
        resume: Skip slugs already present in the DB (makes the scrape
            restartable and the daily cron incremental for new schemes).
        progress: Print flushed per-batch progress (for monitored background runs).
    """
    client = client or MySchemeClient()
    stats = IngestStats()

    seen = _existing_slugs(db_path) if resume else set()
    if seen and progress:
        print(f"[resume] {len(seen)} schemes already in DB; skipping those",
              flush=True)

    count = 0          # new schemes attempted this run
    scanned = 0        # slugs scanned (incl. skipped)
    batch: list[NormalizedScheme] = []
    for slug in client.iter_slugs(keyword=keyword, page_size=page_size):
        scanned += 1
        if slug in seen:
            continue
        if limit is not None and count >= limit:
            break
        count += 1
        try:
            detail = client.get_scheme_detail(slug)
            ns = normalize_scheme(detail)
        except MySchemeError as e:
            stats.errors += 1
            logger.warning("Detail fetch failed for %s: %s", slug, e)
            continue
        if ns is None:
            stats.skipped_empty += 1
            continue
        batch.append(ns)
        if progress:
            print(f"[ok] {count} {slug[:40]}", flush=True)
        if len(batch) >= 10:
            _merge_stats(stats, ingest_schemes(batch, db_path))
            msg = (f"[progress] scanned={scanned} new={count} "
                   f"inserted={stats.inserted} updated={stats.updated} "
                   f"errors={stats.errors}")
            logger.info(msg)
            if progress:
                print(msg, flush=True)
            batch = []
    if batch:
        _merge_stats(stats, ingest_schemes(batch, db_path))
    return stats


def _merge_stats(acc: IngestStats, part: IngestStats) -> None:
    acc.fetched += part.fetched
    acc.inserted += part.inserted
    acc.updated += part.updated
    acc.skipped_empty += part.skipped_empty
    acc.errors += part.errors


def rebuild_faiss_index(db_path: str = DEFAULT_DB) -> bool:
    """
    Rebuild the FAISS index so retrieval reflects freshly-ingested schemes.

    Requires the embedding model (sentence-transformers/torch). Returns True on
    success, False if the ML deps aren't available in this environment (in which
    case run the backend's rebuild path instead).
    """
    try:
        import sys
        root = Path(__file__).resolve().parents[2]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from src.core.rag_engine import RAGEngine  # noqa: WPS433

        engine = RAGEngine(db_path=db_path, force_rebuild=True)
        stats = engine.get_stats()
        logger.info(
            "FAISS rebuilt: %s vectors",
            stats.get("retriever_stats", {}).get("total_vectors"),
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "FAISS rebuild skipped (%s). Trigger it from the backend env "
            "(RAGEngine(force_rebuild=True)) which has the embedding model.",
            e,
        )
        return False
