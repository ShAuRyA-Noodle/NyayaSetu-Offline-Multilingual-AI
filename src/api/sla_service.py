"""
SLA Service

SLA tracking, breach detection, escalation management, and a single-leader
APScheduler that drives periodic breach checks.

TODO (auth/app agent): the FastAPI lifespan in app.py must call
`start_sla_scheduler()` on startup and `stop_sla_scheduler()` on shutdown.
The scheduler self-elects via Postgres advisory lock so it's safe to call
from every replica — only one will become leader.
"""

import logging
from datetime import datetime, timedelta

from .database import get_db
from . import notification_service

logger = logging.getLogger(__name__)


# ============================================================================
# CORE SLA OPERATIONS
# ============================================================================

def create_sla_record(grievance_id: str, department: str, priority: str):
    """Create SLA record for a new grievance."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sla_config WHERE department = ?", (department,)
            )
            config = cursor.fetchone()

            if config:
                sla_map = {
                    "critical": config["critical_sla_hours"],
                    "high": config["high_sla_hours"],
                    "medium": config["medium_sla_hours"],
                    "low": config["low_sla_hours"],
                }
            else:
                sla_map = {"critical": 24, "high": 72, "medium": 168, "low": 336}

            sla_hours = sla_map.get(priority, 168)
            due_date = datetime.utcnow() + timedelta(hours=sla_hours)

            cursor.execute("""
                INSERT INTO grievance_sla
                (grievance_id, sla_hours, due_date)
                VALUES (?, ?, ?)
                ON CONFLICT (grievance_id) DO NOTHING
            """, (grievance_id, sla_hours, due_date.isoformat()))
            conn.commit()

    except Exception as e:
        logger.exception("Failed to create SLA record")


def get_sla_status(grievance_id: str) -> dict:
    """Get SLA status for a grievance."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM grievance_sla WHERE grievance_id = ?",
                (grievance_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            sla = dict(row)
            due = datetime.fromisoformat(sla["due_date"])
            now = datetime.utcnow()

            if sla["resolved_at"]:
                sla["remaining_hours"] = 0
                sla["status"] = "resolved"
            elif sla["is_paused"]:
                sla["remaining_hours"] = (due - now).total_seconds() / 3600
                sla["status"] = "paused"
            elif now > due:
                sla["remaining_hours"] = 0
                sla["status"] = "breached"
                sla["overdue_hours"] = (now - due).total_seconds() / 3600
            else:
                sla["remaining_hours"] = (due - now).total_seconds() / 3600
                pct = sla["remaining_hours"] / sla["sla_hours"] * 100 if sla["sla_hours"] else 0
                sla["status"] = "warning" if pct < 25 else "on_track"
                sla["percentage_remaining"] = round(pct, 1)

            return sla
    except Exception as e:
        logger.exception("Failed to get SLA status")
        return None


def _record_escalation(conn, grievance_id: str, hours_overdue: float, department: str):
    """Insert into grievance_escalations (migration 003) for the breach event.

    Best-effort: silently no-ops if the table is absent (e.g. running before
    migration 003). The notify_* calls remain authoritative.
    """
    try:
        conn.execute("""
            INSERT INTO grievance_escalations
            (grievance_id, escalation_level, escalation_reason,
             hours_overdue, department, escalated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            grievance_id, 1, "sla_breach",
            hours_overdue, department, datetime.utcnow().isoformat(),
        ))
    except Exception as e:
        logger.debug(f"Could not record escalation (table missing?): {e}")


def _notify_admins_of_breach(grievance_id: str, hours_overdue: float):
    """Notify every active admin of an SLA breach."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM users WHERE role = 'admin' AND is_active = TRUE"
            )
            admin_ids = [r["id"] for r in cursor.fetchall()]
        for admin_id in admin_ids:
            notification_service.notify_sla_breach(grievance_id, admin_id, hours_overdue)
    except Exception as e:
        logger.exception("Failed to notify admins of breach")


def check_all_sla_breaches():
    """Check for SLA breaches across all active grievances. Logs new breaches,
    creates escalation rows, and notifies the assigned officer + all admins."""
    try:
        now = datetime.utcnow().isoformat()
        new_breach_count = 0
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gs.grievance_id, gs.due_date, gs.sla_hours,
                       g.department, g.assigned_officer_name, g.assigned_officer_id
                FROM grievance_sla gs
                JOIN grievances g ON gs.grievance_id = g.grievance_id
                WHERE gs.is_breached = FALSE
                  AND gs.resolved_at IS NULL
                  AND gs.is_paused = FALSE
                  AND gs.due_date < ?
            """, (now,))

            breaches = cursor.fetchall()
            breach_list = [dict(b) for b in breaches]

            for breach in breach_list:
                due = datetime.fromisoformat(breach["due_date"])
                hours_overdue = (datetime.utcnow() - due).total_seconds() / 3600

                conn.execute("""
                    UPDATE grievance_sla
                    SET is_breached = TRUE, breached_at = ?,
                        breach_duration_hours = ?, updated_at = ?
                    WHERE grievance_id = ?
                """, (now, hours_overdue, now, breach["grievance_id"]))

                _record_escalation(
                    conn, breach["grievance_id"], hours_overdue, breach["department"],
                )
                new_breach_count += 1

            conn.commit()

        # Notify outside the DB context so we never hold locks during fan-out
        for breach in breach_list:
            due = datetime.fromisoformat(breach["due_date"])
            hours_overdue = (datetime.utcnow() - due).total_seconds() / 3600

            officer_id = breach.get("assigned_officer_id")
            if officer_id:
                try:
                    notification_service.notify_sla_breach(
                        breach["grievance_id"], officer_id, hours_overdue,
                    )
                except Exception:
                    logger.exception("Failed to notify officer of breach")

            _notify_admins_of_breach(breach["grievance_id"], hours_overdue)

        return new_breach_count

    except Exception as e:
        logger.exception("SLA breach check failed")
        return 0


def pause_sla(grievance_id: str, reason: str):
    """Pause SLA when requesting info from citizen."""
    try:
        now = datetime.utcnow().isoformat()
        with get_db() as conn:
            conn.execute("""
                UPDATE grievance_sla
                SET is_paused = TRUE, paused_at = ?, pause_reason = ?, updated_at = ?
                WHERE grievance_id = ? AND is_paused = FALSE
            """, (now, reason, now, grievance_id))
    except Exception as e:
        logger.exception("SLA pause failed")


def resume_sla(grievance_id: str):
    """Resume SLA when citizen responds."""
    try:
        now = datetime.utcnow()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT paused_at, due_date FROM grievance_sla WHERE grievance_id = ? AND is_paused = TRUE",
                (grievance_id,),
            )
            row = cursor.fetchone()
            if not row:
                return

            paused_at = datetime.fromisoformat(row["paused_at"])
            paused_hours = (now - paused_at).total_seconds() / 3600

            old_due = datetime.fromisoformat(row["due_date"])
            new_due = old_due + timedelta(hours=paused_hours)

            conn.execute("""
                UPDATE grievance_sla
                SET is_paused = FALSE, paused_at = NULL,
                    total_paused_hours = COALESCE(total_paused_hours, 0) + ?,
                    due_date = ?, updated_at = ?
                WHERE grievance_id = ?
            """, (paused_hours, new_due.isoformat(), now.isoformat(), grievance_id))
    except Exception as e:
        logger.exception("SLA resume failed")


def resolve_sla(grievance_id: str):
    """Mark SLA as resolved."""
    try:
        now = datetime.utcnow()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT created_at, due_date FROM grievance_sla WHERE grievance_id = ?",
                (grievance_id,),
            )
            row = cursor.fetchone()
            if not row:
                return

            created = datetime.fromisoformat(row["created_at"])
            due = datetime.fromisoformat(row["due_date"])
            resolution_hours = (now - created).total_seconds() / 3600
            within_sla = now <= due

            conn.execute("""
                UPDATE grievance_sla
                SET resolved_at = ?, resolution_within_sla = ?,
                    resolution_time_hours = ?, updated_at = ?
                WHERE grievance_id = ?
            """, (now.isoformat(), within_sla, resolution_hours, now.isoformat(), grievance_id))
    except Exception as e:
        logger.exception("SLA resolve failed")


def get_department_sla_report(department: str) -> dict:
    """Get SLA report for a department."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN gs.is_breached THEN 1 ELSE 0 END) as breached,
                       SUM(CASE WHEN gs.resolution_within_sla THEN 1 ELSE 0 END) as within_sla,
                       AVG(gs.resolution_time_hours) as avg_resolution_hours
                FROM grievance_sla gs
                JOIN grievances g ON gs.grievance_id = g.grievance_id
                WHERE g.department = ?
            """, (department,))
            row = cursor.fetchone()

            total = row["total"] or 0
            within_sla = row["within_sla"] or 0
            compliance = round((within_sla / total * 100) if total > 0 else 100, 1)

            return {
                "department": department,
                "total": total,
                "breached": row["breached"] or 0,
                "within_sla": within_sla,
                "compliance_rate": compliance,
                "avg_resolution_hours": round(row["avg_resolution_hours"] or 0, 1),
            }
    except Exception as e:
        logger.exception("SLA report failed")
        return {"department": department, "total": 0, "compliance_rate": 100}


def get_sla_dashboard() -> dict:
    """Get system-wide SLA overview."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.department,
                       COUNT(*) as total,
                       SUM(CASE WHEN gs.is_breached THEN 1 ELSE 0 END) as breached,
                       SUM(CASE WHEN gs.resolved_at IS NOT NULL THEN 1 ELSE 0 END) as resolved,
                       SUM(CASE WHEN gs.resolution_within_sla THEN 1 ELSE 0 END) as within_sla
                FROM grievance_sla gs
                JOIN grievances g ON gs.grievance_id = g.grievance_id
                GROUP BY g.department
            """)
            departments = []
            for r in cursor.fetchall():
                total = r["total"] or 0
                within = r["within_sla"] or 0
                departments.append({
                    "department": r["department"],
                    "total": total,
                    "breached": r["breached"] or 0,
                    "resolved": r["resolved"] or 0,
                    "compliance_rate": round((within / total * 100) if total else 100, 1),
                })

            # Active breaches
            cursor.execute("""
                SELECT gs.grievance_id, g.department, g.priority, gs.due_date, gs.breached_at
                FROM grievance_sla gs
                JOIN grievances g ON gs.grievance_id = g.grievance_id
                WHERE gs.is_breached = TRUE AND gs.resolved_at IS NULL
                ORDER BY gs.breached_at ASC LIMIT 20
            """)
            active_breaches = [dict(r) for r in cursor.fetchall()]

        return {"departments": departments, "active_breaches": active_breaches}
    except Exception as e:
        logger.exception("SLA dashboard failed")
        return {"departments": [], "active_breaches": []}


# ============================================================================
# SCHEDULER (single-leader via Postgres advisory lock)
# ============================================================================

# APScheduler is imported lazily so the module is still importable in
# environments without it (the scheduler simply won't start).
_scheduler = None


def start_sla_scheduler():
    """Start the periodic SLA breach-check job.

    Idempotent. Uses a Postgres advisory lock (id 847291) for single-leader
    election so multiple replicas can call this safely - only one wins. On
    SQLite the advisory-lock probe fails silently and every process schedules
    its own job (acceptable for dev / single-process pilot).

    The auth/app agent must wire this into the FastAPI lifespan startup.
    """
    global _scheduler
    if _scheduler is not None:
        logger.info("SLA scheduler: already running")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning("APScheduler not installed; SLA scheduler will not run")
        return

    # Postgres advisory lock for single-leader election. SQLite has no
    # pg_try_advisory_lock; the except branch handles both "no such function"
    # and "wrong dialect" gracefully.
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT pg_try_advisory_lock(847291)")
            row = cursor.fetchone()
            # row[0] is True if lock acquired; False if another replica holds it
            if row is not None:
                got_lock = row[0] if not hasattr(row, "keys") else list(row)[0]
                if got_lock is False:
                    logger.info("SLA scheduler: another replica holds the lock; skipping")
                    return
    except Exception:
        # SQLite or no advisory_lock function — fine for dev/pilot
        pass

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        check_all_sla_breaches,
        "interval",
        minutes=5,
        id="sla_breach_check",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("SLA scheduler started (5-minute breach-check interval)")


def stop_sla_scheduler():
    """Stop the SLA scheduler. Idempotent; safe in lifespan shutdown hook."""
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception as e:
            logger.warning(f"SLA scheduler shutdown hit error: {e}")
        _scheduler = None
        logger.info("SLA scheduler stopped")
