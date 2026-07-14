#!/usr/bin/env python
"""
Scrape real government schemes from myScheme.gov.in into the governance DB.

Usage:
    # Full scrape (all ~4,300+ schemes) + rebuild FAISS
    python scripts/scrape_schemes.py --rebuild-index

    # Quick smoke test (first 20 schemes)
    python scripts/scrape_schemes.py --limit 20

    # Daily incremental refresh (cron) — re-upserts everything, updating changed
    python scripts/scrape_schemes.py --rebuild-index --quiet

All data is real and scraped live. Nothing synthetic is written.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Windows consoles default to cp1252 and choke on non-Latin scheme text.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from src.data_pipeline.scheme_ingest import (  # noqa: E402
    DEFAULT_DB,
    rebuild_faiss_index,
    scrape_and_ingest,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Scrape myScheme.gov.in into the DB")
    p.add_argument("--db", default=DEFAULT_DB, help="SQLite governance DB path")
    p.add_argument("--limit", type=int, default=None, help="Max schemes (default: all)")
    p.add_argument("--keyword", default="", help="Optional search filter")
    p.add_argument("--page-size", type=int, default=100, help="List pagination size")
    p.add_argument("--rebuild-index", action="store_true", help="Rebuild FAISS after")
    p.add_argument("--quiet", action="store_true", help="Less logging (cron)")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    start = time.time()
    print(f"Scraping myScheme.gov.in → {args.db} (limit={args.limit or 'ALL'})")
    stats = scrape_and_ingest(
        db_path=args.db,
        limit=args.limit,
        keyword=args.keyword,
        page_size=args.page_size,
    )
    dur = time.time() - start
    print(
        f"\nDone in {dur:.0f}s | fetched={stats.fetched} "
        f"inserted={stats.inserted} updated={stats.updated} "
        f"skipped_empty={stats.skipped_empty} errors={stats.errors}"
    )

    if args.rebuild_index:
        print("Rebuilding FAISS index...")
        ok = rebuild_faiss_index(args.db)
        print("FAISS rebuild:", "OK" if ok else "SKIPPED (run from backend env)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
