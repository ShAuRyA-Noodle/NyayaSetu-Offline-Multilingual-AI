"""
SLA Service

SLA tracking, breach detection, and escalation management.
"""

import logging
from datetime import datetime, timedelta

from .database import get_db
from . import notification_service

logger = logging.getLogger(__name__)


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
        logger.error(f"Failed to create SLA record: {e}")


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
        logger.error(f"Failed to get SLA status: {e}")
        return None


def check_all_sla_breaches():
    """Check for SLA breaches across all active grievances."""
    try:
        now = datetime.utcnow().isoformat()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gs.grievance_id, gs.due_date, gs.sla_hours,
                       g.department, g.assigned_officer_name
                FROM grievance_sla gs
                JOIN grievances g ON gs.grievance_id = g.grievance_id
                WHERE gs.is_breached = FALSE
                  AND gs.resolved_at IS NULL
                  AND gs.is_paused = FALSE
                  AND gs.due_date < ?
            """, (now,))

            breaches = cursor.fetchall()
            for breach in breaches:
                due = datetime.fromisoformat(breach["due_date"])
                hours_overdue = (datetime.utcnow() - due).total_seconds() / 3600

                conn.execute("""
                    UPDATE grievance_sla
                    SET is_breached = TRUE, breached_at = ?,
                        breach_duration_hours = ?, updated_at = ?
                    WHERE grievance_id = ?
                """, (now, hours_overdue, now, breach["grievance_id"]))

            conn.commit()
            return len(breaches)

    except Exception as e:
        logger.error(f"SLA breach check failed: {e}")
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
        logger.error(f"SLA pause failed: {e}")


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
        logger.error(f"SLA resume failed: {e}")


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
        logger.error(f"SLA resolve failed: {e}")


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
        logger.error(f"SLA report failed: {e}")
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
        logger.error(f"SLA dashboard failed: {e}")
        return {"departments": [], "active_breaches": []}
