"""
Daily scheme-refresh scheduler.

Keeps the knowledge base current by re-scraping myScheme.gov.in once a day and
rebuilding the FAISS index. Mirrors the SLA scheduler's pattern: APScheduler is
imported lazily, the job is idempotent, and it degrades to a no-op where
APScheduler isn't installed.

Wire ``start_scheme_refresh_scheduler()`` into the FastAPI lifespan startup and
``stop_scheme_refresh_scheduler()`` into shutdown.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_scheduler = None

# Hour of day (local time, 0-23) to run the refresh. Off-peak by default.
REFRESH_HOUR = int(os.getenv("SCHEME_REFRESH_HOUR", "3"))
# Set SCHEME_REFRESH_ENABLED=0 to disable (e.g. on ephemeral serverless hosts).
REFRESH_ENABLED = os.getenv("SCHEME_REFRESH_ENABLED", "1") == "1"


def refresh_schemes_job() -> None:
    """Scrape the full portal, upsert, and rebuild the index. Safe to re-run."""
    from .scheme_ingest import DEFAULT_DB, rebuild_faiss_index, scrape_and_ingest

    db_path = os.getenv("NYAYASETU_DB_PATH", DEFAULT_DB)
    logger.info("Daily scheme refresh starting (db=%s)", db_path)
    try:
        stats = scrape_and_ingest(db_path=db_path)
        logger.info(
            "Daily scheme refresh: inserted=%d updated=%d skipped=%d errors=%d",
            stats.inserted, stats.updated, stats.skipped_empty, stats.errors,
        )
        rebuild_faiss_index(db_path)
    except Exception as e:  # noqa: BLE001 — never let the cron kill the process
        logger.error("Daily scheme refresh failed: %s", e)


def start_scheme_refresh_scheduler() -> None:
    """Start the daily refresh job. Idempotent."""
    global _scheduler
    if not REFRESH_ENABLED:
        logger.info("Scheme refresh scheduler disabled via env")
        return
    if _scheduler is not None:
        logger.info("Scheme refresh scheduler: already running")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("APScheduler not installed; scheme refresh will not run")
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        refresh_schemes_job,
        CronTrigger(hour=REFRESH_HOUR, minute=0),
        id="daily_scheme_refresh",
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Scheme refresh scheduler started (daily at %02d:00)", REFRESH_HOUR)


def stop_scheme_refresh_scheduler() -> None:
    """Stop the refresh scheduler. Idempotent."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheme refresh scheduler stopped")
