"""
Grievance Routes

Full grievance lifecycle: submission, routing, management, tracking, SLA, comments, ratings, notifications.

TODO (migration): add columns:
  ALTER TABLE grievances ADD COLUMN submitted_by_officer_id INTEGER;
  ALTER TABLE grievance_comments ADD COLUMN is_internal BOOLEAN DEFAULT FALSE;
  ALTER TABLE grievance_comments ADD COLUMN author_department TEXT;
Until migrated, officer-on-behalf submissions set citizen_id = NULL and the
officer id is captured via log_audit_action; internal-comment scoping falls
back to is_public/comment_type heuristics.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .auth_routes import get_current_user, require_role
from .auth_utils import log_audit_action
from .schemas import (
    RouteGrievanceRequest, GrievanceRouteResponse,
    SubmitGrievanceRequest, AcceptGrievanceRequest,
    RejectGrievanceRequest, UpdateStatusRequest,
    ResolveGrievanceRequest,
)
from .errors import map_module_error
from .dependencies import get_grievance_router
from .database import get_db
from . import notification_service
from . import sla_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/grievances", tags=["Grievances"])


# ============================================================================
# STATE MACHINE
# ============================================================================

VALID_TRANSITIONS = {
    "pending": {"under_review", "in_progress", "rejected"},
    "under_review": {"in_progress", "rejected"},
    "in_progress": {"resolved", "rejected"},
    "resolved": {"reopened", "closed"},
    "rejected": set(),
    "closed": set(),
    "reopened": {"in_progress"},
}


# ============================================================================
# LOCAL REQUEST MODELS
# ============================================================================

class CommentRequest(BaseModel):
    comment_text: str = Field(..., min_length=1, max_length=5000)
    is_internal: bool = False
    comment_type: str = "note"


class ReopenRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


# ============================================================================
# HELPERS
# ============================================================================

def log_status_update(conn, grievance_id, old_status, new_status, updated_by, notes=None, user_id=None, user_role=None):
    """Log a status update to both legacy and new tables."""
    conn.execute("""
        INSERT INTO grievance_status_updates
        (grievance_id, old_status, new_status, updated_by, update_notes)
        VALUES (?, ?, ?, ?, ?)
    """, (grievance_id, old_status, new_status, updated_by, notes))

    try:
        conn.execute("""
            INSERT INTO grievance_status_history
            (grievance_id, old_status, new_status, changed_by, changed_by_name, changed_by_role, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (grievance_id, old_status, new_status, user_id, updated_by, user_role, notes))
    except Exception:
        pass

    try:
        conn.execute(
            "UPDATE grievances SET last_status_change_at = ? WHERE grievance_id = ?",
            (datetime.utcnow().isoformat(), grievance_id),
        )
    except Exception:
        pass


def get_citizen_id_for_grievance(conn, grievance_id):
    """Get citizen_id for a grievance."""
    cursor = conn.cursor()
    cursor.execute("SELECT citizen_id FROM grievances WHERE grievance_id = ?", (grievance_id,))
    row = cursor.fetchone()
    return row["citizen_id"] if row else None


def _load_grievance_for_action(conn, grievance_id: str) -> dict:
    """Load grievance row needed for authorization. Raises 404 if not found."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT grievance_id, status, citizen_id, department, assigned_officer_name "
        "FROM grievances WHERE grievance_id = ?",
        (grievance_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(404, f"Grievance {grievance_id} not found")
    return dict(row)


def _authorize_officer_or_admin_for_grievance(current_user: dict, grievance: dict):
    """Officer must match grievance department; admin bypasses dept check."""
    role = current_user.get("role")
    if role == "admin":
        return
    if role == "officer":
        if current_user.get("department") != grievance.get("department"):
            raise HTTPException(403, "Officer can only act on grievances in their own department")
        return
    raise HTTPException(403, "Officer or admin access required")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/route", response_model=GrievanceRouteResponse)
async def route_grievance(request: RouteGrievanceRequest):
    """Route citizen grievance to appropriate department."""
    try:
        gr_router = get_grievance_router()
        route = gr_router.route_grievance(
            grievance_text=request.grievance_text,
            language=request.language,
            citizen_location=request.citizen_location,
        )

        return GrievanceRouteResponse(
            grievance_id=route.grievance_id,
            department=route.department,
            sub_department=route.sub_department,
            priority=route.priority,
            category=route.category,
            summary=route.summary,
            reasoning=route.reasoning,
            estimated_resolution_days=route.estimated_resolution_days,
            related_schemes=route.related_schemes,
            language=route.language,
            metadata=route.metadata,
        )
    except Exception as e:
        logger.exception("Route grievance failed")
        raise map_module_error(e, "GrievanceRouter")


@router.post("/submit")
async def submit_grievance(
    request: SubmitGrievanceRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit and store grievance with AI routing and SLA."""
    try:
        is_officer_submission = current_user["role"] != "citizen"

        if not is_officer_submission:
            citizen_name = current_user.get("username")
            citizen_email = current_user.get("email")
            citizen_location = current_user.get("location")
            citizen_id_for_row = current_user["id"]
        else:
            # Officer-on-behalf submission. citizen_id is NULL until the
            # submitted_by_officer_id column lands in the next migration.
            citizen_name = request.citizen_name
            citizen_email = request.citizen_email
            citizen_location = request.citizen_location
            citizen_id_for_row = None

        gr_router = get_grievance_router()
        route = gr_router.route_grievance(
            grievance_text=request.description,
            language=request.language,
            citizen_location=citizen_location,
        )

        now = datetime.utcnow().isoformat()

        with get_db() as conn:
            conn.execute("""
                INSERT INTO grievances (
                    grievance_id, citizen_id, citizen_name, citizen_phone, citizen_email,
                    citizen_location, title, description, category, language,
                    department, sub_department, priority, routing_reasoning,
                    confidence_score, estimated_resolution_days, related_schemes,
                    status, submitted_at, ai_confidence, ai_summary, ai_reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                route.grievance_id, citizen_id_for_row, citizen_name,
                request.citizen_phone, citizen_email, citizen_location,
                request.title or route.summary, request.description,
                route.category, request.language, route.department,
                route.sub_department, route.priority, route.reasoning,
                route.metadata.get("confidence", 0.0),
                route.estimated_resolution_days,
                json.dumps(route.related_schemes), "pending", now,
                route.metadata.get("confidence", 0.0),
                route.summary, route.reasoning,
            ))

        # Create SLA record
        sla_service.create_sla_record(route.grievance_id, route.department, route.priority)

        # Notify citizen (only for self-submissions; officer-on-behalf has no citizen_id)
        if citizen_id_for_row is not None:
            notification_service.notify_grievance_submitted(
                route.grievance_id, citizen_id_for_row, route.department
            )

        if is_officer_submission:
            log_audit_action(
                action="grievance_submit_on_behalf",
                user_id=current_user["id"],
                target_id=route.grievance_id,
                metadata={
                    "department": route.department,
                    "priority": route.priority,
                    "citizen_name": citizen_name,
                },
            )

        logger.info(f"Grievance submitted by {current_user['username']}: {route.grievance_id}")

        return {
            "success": True,
            "grievance_id": route.grievance_id,
            "department": route.department,
            "priority": route.priority,
            "category": route.category,
            "summary": route.summary,
            "reasoning": route.reasoning,
            "status": "pending",
            "message": f"Grievance submitted successfully! Track with ID: {route.grievance_id}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Submit grievance failed")
        raise HTTPException(500, "Internal server error")


@router.get("/my")
async def get_my_grievances(current_user: dict = Depends(get_current_user)):
    """Get citizen's own grievances."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.grievance_id, g.title, g.description, g.department,
                       g.priority, g.status, g.category, g.submitted_at,
                       g.resolved_at, g.resolution_notes,
                       g.estimated_resolution_days, g.assigned_officer_name,
                       g.routing_reasoning, g.accepted_at
                FROM grievances g
                WHERE g.citizen_id = ?
                ORDER BY g.submitted_at DESC
            """, (current_user["id"],))
            grievances = [dict(r) for r in cursor.fetchall()]

            # Add SLA info and rating
            for g in grievances:
                sla = sla_service.get_sla_status(g["grievance_id"])
                g["sla"] = sla
                cursor.execute(
                    "SELECT rating FROM grievance_ratings WHERE grievance_id = ?",
                    (g["grievance_id"],),
                )
                rating_row = cursor.fetchone()
                g["rating"] = dict(rating_row) if rating_row else None

        return {"grievances": grievances, "count": len(grievances)}
    except Exception as e:
        logger.exception("Get my grievances failed")
        raise HTTPException(500, "Internal server error")


@router.get("/department-inbox")
async def get_department_inbox(current_user: dict = Depends(get_current_user)):
    """Get ALL grievances for officer's department (breaks the deadlock -
    officers can see pending grievances before accepting them)."""
    try:
        department = current_user.get("department")
        if not department and current_user["role"] == "admin":
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT grievance_id, citizen_name, citizen_phone, title, description,
                           department, category, priority, status, submitted_at,
                           routing_reasoning, estimated_resolution_days, assigned_officer_name
                    FROM grievances
                    WHERE status NOT IN ('resolved', 'rejected', 'closed')
                    ORDER BY CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END, submitted_at ASC
                """)
                grievances = [dict(r) for r in cursor.fetchall()]
                for g in grievances:
                    g["sla"] = sla_service.get_sla_status(g["grievance_id"])
            return {"grievances": grievances, "count": len(grievances)}

        if not department:
            return {"grievances": [], "count": 0, "message": "No department assigned"}

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT grievance_id, citizen_name, citizen_phone, title, description,
                       department, category, priority, status, submitted_at,
                       routing_reasoning, estimated_resolution_days, assigned_officer_name
                FROM grievances
                WHERE department = ? AND status NOT IN ('resolved', 'rejected', 'closed')
                ORDER BY CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END, submitted_at ASC
            """, (department,))
            grievances = [dict(r) for r in cursor.fetchall()]
            for g in grievances:
                g["sla"] = sla_service.get_sla_status(g["grievance_id"])

        return {"grievances": grievances, "count": len(grievances)}
    except Exception as e:
        logger.exception("Department inbox failed")
        raise HTTPException(500, "Internal server error")


@router.get("/all")
async def get_all_grievances(
    status: str = Query(default=None),
    department: str = Query(default=None),
    priority: str = Query(default=None),
    limit: int = Query(default=100),
    current_user: dict = Depends(get_current_user),
):
    """Get all grievances system-wide (admin/officer). Officer is scoped to own department."""
    if current_user["role"] not in ("admin", "officer"):
        raise HTTPException(403, "Admin or officer access required")
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            query = """
                SELECT grievance_id, citizen_name, citizen_phone, title, description,
                       department, category, priority, status, submitted_at,
                       routing_reasoning, estimated_resolution_days, assigned_officer_name,
                       resolved_at, resolution_notes
                FROM grievances WHERE 1=1
            """
            params = []

            # Officer scope: force department to officer's own dept
            if current_user["role"] == "officer":
                officer_dept = current_user.get("department")
                if not officer_dept:
                    return {"grievances": [], "count": 0}
                query += " AND department = ?"
                params.append(officer_dept)
            elif department:
                query += " AND department = ?"
                params.append(department)

            if status:
                query += " AND status = ?"
                params.append(status)
            if priority:
                query += " AND priority = ?"
                params.append(priority)
            query += """ ORDER BY CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END, submitted_at DESC LIMIT ?"""
            params.append(limit)
            cursor.execute(query, params)
            grievances = [dict(r) for r in cursor.fetchall()]
        return {"grievances": grievances, "count": len(grievances)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Get all grievances failed")
        raise HTTPException(500, "Internal server error")


@router.get("/assigned")
async def get_assigned_grievances(current_user: dict = Depends(get_current_user)):
    """Get officer's assigned grievances."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT grievance_id, citizen_name, title, description, department,
                       priority, status, category, submitted_at, estimated_resolution_days
                FROM grievances
                WHERE assigned_officer_id = ? AND status NOT IN ('resolved', 'rejected', 'closed')
                ORDER BY
                    CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END,
                    submitted_at ASC
            """, (current_user["id"],))
            grievances = [dict(r) for r in cursor.fetchall()]

            # Fallback to legacy name-based lookup if assigned_officer_id column not populated
            if not grievances:
                cursor.execute("""
                    SELECT grievance_id, citizen_name, title, description, department,
                           priority, status, category, submitted_at, estimated_resolution_days
                    FROM grievances
                    WHERE assigned_officer_name = ? AND status NOT IN ('resolved', 'rejected', 'closed')
                    ORDER BY
                        CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END,
                        submitted_at ASC
                """, (current_user["username"],))
                grievances = [dict(r) for r in cursor.fetchall()]

            for g in grievances:
                sla = sla_service.get_sla_status(g["grievance_id"])
                g["sla"] = sla

        return {"grievances": grievances, "count": len(grievances)}
    except Exception as e:
        logger.exception("Get assigned failed")
        raise HTTPException(500, "Internal server error")


@router.get("/department/{department}")
async def get_department_grievances(
    department: str,
    status: str = "pending",
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """Get grievances for a department. Officer is restricted to own dept; admin can query any."""
    # Department scoping: officer can only query own department
    if current_user["role"] == "officer":
        officer_dept = current_user.get("department")
        if officer_dept != department:
            raise HTTPException(403, "Officer can only query their own department")
    elif current_user["role"] != "admin":
        raise HTTPException(403, "Officer or admin access required")

    try:
        officer = current_user.get("username")
        with get_db() as conn:
            cursor = conn.cursor()
            if status == "pending":
                # Pending grievances are visible to all officers in the department
                cursor.execute("""
                    SELECT grievance_id, citizen_name, citizen_phone, title, description,
                           category, priority, status, submitted_at, routing_reasoning,
                           estimated_resolution_days, assigned_officer_name
                    FROM grievances
                    WHERE department = ? AND status = ?
                    ORDER BY
                        CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END,
                        submitted_at DESC
                    LIMIT ?
                """, (department, status, limit))
            else:
                # Non-pending: only show grievances assigned to this officer (or all for admin)
                if current_user["role"] == "admin":
                    cursor.execute("""
                        SELECT grievance_id, citizen_name, citizen_phone, title, description,
                               category, priority, status, submitted_at, routing_reasoning,
                               estimated_resolution_days, assigned_officer_name
                        FROM grievances
                        WHERE department = ? AND status = ?
                        ORDER BY
                            CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                                WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END,
                            submitted_at DESC
                        LIMIT ?
                    """, (department, status, limit))
                else:
                    cursor.execute("""
                        SELECT grievance_id, citizen_name, citizen_phone, title, description,
                               category, priority, status, submitted_at, routing_reasoning,
                               estimated_resolution_days, assigned_officer_name
                        FROM grievances
                        WHERE department = ? AND status = ? AND assigned_officer_name = ?
                        ORDER BY
                            CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                                WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END,
                            submitted_at DESC
                        LIMIT ?
                    """, (department, status, officer, limit))
            grievances = [dict(row) for row in cursor.fetchall()]

        return {
            "department": department, "status": status,
            "count": len(grievances), "grievances": grievances,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Get grievances failed")
        raise HTTPException(500, "Internal server error")


@router.get("/department/{department}/dashboard")
async def department_dashboard(
    department: str,
    officer_name: str = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Get department dashboard data, filtered by officer if provided."""
    # Department scoping: officer can only view own department's dashboard
    if current_user["role"] == "officer":
        officer_dept = current_user.get("department")
        if officer_dept != department:
            raise HTTPException(403, "Officer can only view their own department's dashboard")
    elif current_user["role"] != "admin":
        raise HTTPException(403, "Officer or admin access required")

    try:
        # Use officer_name param, or fall back to logged-in user's username
        officer = officer_name or current_user.get("username")

        with get_db() as conn:
            cursor = conn.cursor()

            # Pending grievances are department-wide (not yet assigned)
            # Accepted/in_progress/resolved are officer-specific
            cursor.execute("""
                SELECT status, COUNT(*) as cnt FROM grievances
                WHERE department = ?
                  AND (status = 'pending' OR assigned_officer_name = ?)
                GROUP BY status
            """, (department, officer))
            by_status = {r["status"]: r["cnt"] for r in cursor.fetchall()}

            cursor.execute("""
                SELECT priority, COUNT(*) as cnt FROM grievances
                WHERE department = ?
                  AND status NOT IN ('resolved', 'rejected', 'closed')
                  AND (status = 'pending' OR assigned_officer_name = ?)
                GROUP BY priority
            """, (department, officer))
            by_priority = {r["priority"]: r["cnt"] for r in cursor.fetchall()}

            cursor.execute("""
                SELECT COUNT(*) as cnt FROM grievances
                WHERE department = ?
                  AND status NOT IN ('resolved', 'rejected', 'closed')
                  AND (status = 'pending' OR assigned_officer_name = ?)
            """, (department, officer))
            active = cursor.fetchone()["cnt"]

        sla_report = sla_service.get_department_sla_report(department)

        return {
            "department": department,
            "active_count": active,
            "by_status": by_status,
            "by_priority": by_priority,
            "sla": sla_report,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Dashboard failed")
        raise HTTPException(500, "Internal server error")



# ============================================================================
# STATIC ROUTES (must be above /{grievance_id} to avoid path shadowing)
# ============================================================================

@router.get("/stats")
async def grievance_stats(current_user: dict = Depends(require_role("officer"))):
    """Get grievance statistics. Staff only (system-wide operational metrics)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as cnt FROM grievances")
            total = cursor.fetchone()["cnt"]

            cursor.execute("SELECT status, COUNT(*) as cnt FROM grievances GROUP BY status")
            by_status = {row["status"]: row["cnt"] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT department, COUNT(*) as cnt FROM grievances
                GROUP BY department ORDER BY cnt DESC LIMIT 10
            """)
            by_department = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT priority, COUNT(*) as cnt FROM grievances GROUP BY priority")
            by_priority = {row["priority"]: row["cnt"] for row in cursor.fetchall()}

            cursor.execute("SELECT AVG(rating) as avg_rating FROM grievance_ratings")
            avg_rating_row = cursor.fetchone()
            avg_rating = round(avg_rating_row["avg_rating"], 1) if avg_rating_row and avg_rating_row["avg_rating"] else None

        return {
            "total": total,
            "by_status": by_status,
            "by_department": by_department,
            "by_priority": by_priority,
            "avg_rating": avg_rating,
        }
    except Exception as e:
        logger.exception("Stats failed")
        raise HTTPException(500, "Internal server error")


@router.get("/sla/dashboard")
async def sla_dashboard(current_user: dict = Depends(require_role("officer"))):
    """System-wide SLA overview. Staff only."""
    return sla_service.get_sla_dashboard()


@router.get("/sla/breaches")
async def sla_breaches(current_user: dict = Depends(require_role("officer"))):
    """Current active SLA breaches. Staff only."""
    dashboard = sla_service.get_sla_dashboard()
    return {"breaches": dashboard.get("active_breaches", [])}


@router.get("/analytics")
async def grievance_analytics(current_user: dict = Depends(require_role("officer"))):
    """Grievance analytics. Staff only (exposes officer names and metrics)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DATE(submitted_at) as date, COUNT(*) as cnt
                FROM grievances
                GROUP BY DATE(submitted_at)
                ORDER BY date DESC LIMIT 30
            """)
            daily_trend = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT category, COUNT(*) as cnt FROM grievances
                GROUP BY category ORDER BY cnt DESC
            """)
            by_category = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT assigned_officer_name as officer, COUNT(*) as total,
                       SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved
                FROM grievances
                WHERE assigned_officer_name IS NOT NULL
                GROUP BY assigned_officer_name
                ORDER BY total DESC LIMIT 10
            """)
            officer_stats = [dict(r) for r in cursor.fetchall()]

        return {
            "daily_trend": daily_trend,
            "by_category": by_category,
            "officer_stats": officer_stats,
        }
    except Exception as e:
        logger.exception("Analytics failed")
        raise HTTPException(500, "Internal server error")


# ============================================================================
# NOTIFICATION ENDPOINTS
# ============================================================================

@router.get("/notifications", tags=["Notifications"])
async def get_notifications(current_user: dict = Depends(get_current_user)):
    """Get user's notifications."""
    notifications = notification_service.get_unread_notifications(current_user["id"])
    count = notification_service.get_notification_count(current_user["id"])
    return {"notifications": notifications, "unread_count": count}


@router.post("/notifications/{notification_id}/read", tags=["Notifications"])
async def mark_notification_read(
    notification_id: int, current_user: dict = Depends(get_current_user)
):
    """Mark notification as read."""
    notification_service.mark_as_read(notification_id, current_user["id"])
    return {"success": True}


@router.post("/notifications/read-all", tags=["Notifications"])
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read."""
    notification_service.mark_all_read(current_user["id"])
    return {"success": True}


@router.get("/notifications/count", tags=["Notifications"])
async def notification_count(current_user: dict = Depends(get_current_user)):
    """Get unread notification count."""
    count = notification_service.get_notification_count(current_user["id"])
    return {"unread_count": count}


# ============================================================================
# SLA CONFIG ENDPOINTS
# ============================================================================

@router.get("/admin/sla/config", tags=["Admin"])
async def get_sla_config(current_user: dict = Depends(require_role("admin"))):
    """Get all SLA configurations."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sla_config ORDER BY department")
            configs = [dict(r) for r in cursor.fetchall()]
        return {"configs": configs}
    except Exception as e:
        logger.exception("Get SLA config failed")
        raise HTTPException(500, "Internal server error")


@router.post("/admin/sla/config", tags=["Admin"])
async def update_sla_config(
    department: str = Query(...),
    critical_sla_hours: int = Query(default=24),
    high_sla_hours: int = Query(default=72),
    medium_sla_hours: int = Query(default=168),
    low_sla_hours: int = Query(default=336),
    current_user: dict = Depends(require_role("admin")),
):
    """Create/update SLA config for a department."""
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO sla_config
                (department, critical_sla_hours, high_sla_hours, medium_sla_hours, low_sla_hours, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (department) DO UPDATE SET
                    critical_sla_hours = EXCLUDED.critical_sla_hours,
                    high_sla_hours = EXCLUDED.high_sla_hours,
                    medium_sla_hours = EXCLUDED.medium_sla_hours,
                    low_sla_hours = EXCLUDED.low_sla_hours,
                    updated_at = EXCLUDED.updated_at
            """, (department, critical_sla_hours, high_sla_hours, medium_sla_hours, low_sla_hours))
        log_audit_action(
            action="sla_config_update",
            user_id=current_user["id"],
            target_id=department,
            metadata={
                "critical_sla_hours": critical_sla_hours,
                "high_sla_hours": high_sla_hours,
                "medium_sla_hours": medium_sla_hours,
                "low_sla_hours": low_sla_hours,
            },
        )
        return {"success": True, "department": department}
    except Exception as e:
        logger.exception("Update SLA config failed")
        raise HTTPException(500, "Internal server error")


# ============================================================================
# GRIEVANCE DETAIL (dynamic /{grievance_id} routes MUST be last)
# ============================================================================

@router.get("/{grievance_id}")
async def get_grievance_detail(
    grievance_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get full grievance details with timeline and SLA."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM grievances WHERE grievance_id = ?", (grievance_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, f"Grievance {grievance_id} not found")

            grievance = dict(row)

            # Authorization: only the filing citizen, assigned officer, or admin can view
            user_role = current_user.get("role")
            user_id = current_user.get("id")
            if user_role == "citizen" and grievance.get("citizen_id") != user_id:
                raise HTTPException(403, "You can only view your own grievances")
            if user_role == "officer":
                # Officer can view if grievance is in their department
                if grievance.get("department") != current_user.get("department"):
                    raise HTTPException(403, "This grievance is not in your department")

            # Timeline
            cursor.execute("""
                SELECT new_status, update_notes, timestamp
                FROM grievance_status_updates WHERE grievance_id = ?
                ORDER BY timestamp ASC
            """, (grievance_id,))
            grievance["timeline"] = [dict(r) for r in cursor.fetchall()]

            # Comments
            cursor.execute("""
                SELECT id, author_name, author_role, comment_text, comment_type,
                       is_public, created_at
                FROM grievance_comments WHERE grievance_id = ?
                ORDER BY created_at ASC
            """, (grievance_id,))
            grievance["comments"] = [dict(r) for r in cursor.fetchall()]

            # SLA
            grievance["sla"] = sla_service.get_sla_status(grievance_id)

            # Rating
            cursor.execute(
                "SELECT * FROM grievance_ratings WHERE grievance_id = ?",
                (grievance_id,),
            )
            rating_row = cursor.fetchone()
            grievance["rating"] = dict(rating_row) if rating_row else None

            # Increment view count
            try:
                conn.execute(
                    "UPDATE grievances SET view_count = COALESCE(view_count, 0) + 1 WHERE grievance_id = ?",
                    (grievance_id,),
                )
            except Exception:
                pass

        return grievance
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Get detail failed")
        raise HTTPException(500, "Internal server error")


@router.get("/{grievance_id}/timeline")
async def get_grievance_timeline(grievance_id: str):
    """Get redacted public timeline (PII stripped). Returns minimal fields for tracking."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Verify the grievance exists; return minimal public info
            cursor.execute(
                "SELECT grievance_id, status, priority, submitted_at, last_updated_at "
                "FROM grievances WHERE grievance_id = ?",
                (grievance_id,),
            )
            head = cursor.fetchone()
            if not head:
                raise HTTPException(404, f"Grievance {grievance_id} not found")

            cursor.execute("""
                SELECT new_status, timestamp
                FROM grievance_status_updates WHERE grievance_id = ?
                ORDER BY timestamp ASC
            """, (grievance_id,))
            timeline = [dict(r) for r in cursor.fetchall()]
        return {"grievance_id": grievance_id, "timeline": timeline}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Timeline failed")
        raise HTTPException(500, "Internal server error")


@router.post("/{grievance_id}/accept")
async def accept_grievance(
    grievance_id: str, request: AcceptGrievanceRequest,
    current_user: dict = Depends(get_current_user),
):
    """Accept a grievance. Atomic state-machine UPDATE prevents double-assignment race."""
    try:
        with get_db() as conn:
            grievance = _load_grievance_for_action(conn, grievance_id)
            _authorize_officer_or_admin_for_grievance(current_user, grievance)

            old_status = grievance["status"]
            citizen_id = grievance["citizen_id"]
            now = datetime.utcnow().isoformat()
            officer_name = request.officer_name or current_user["username"]

            cursor = conn.cursor()
            # Atomic accept: only succeeds if status is still 'pending'
            cursor.execute("""
                UPDATE grievances
                SET assigned_officer_id = ?,
                    assigned_officer_name = ?,
                    status = 'in_progress',
                    accepted_at = ?,
                    updated_at = ?
                WHERE grievance_id = ? AND status = 'pending'
            """, (current_user["id"], officer_name, now, now, grievance_id))

            if cursor.rowcount == 0:
                raise HTTPException(409, "Grievance already assigned or not pending")

            log_status_update(conn, grievance_id, old_status, "in_progress",
                              officer_name, request.notes,
                              current_user["id"], current_user["role"])

        log_audit_action(
            action="grievance_accept",
            user_id=current_user["id"],
            target_id=grievance_id,
        )

        if citizen_id:
            notification_service.notify_status_change(grievance_id, citizen_id, "in_progress")

        return {"success": True, "grievance_id": grievance_id, "status": "in_progress"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Accept failed")
        raise HTTPException(500, "Internal server error")


@router.post("/{grievance_id}/reject")
async def reject_grievance(
    grievance_id: str, request: RejectGrievanceRequest,
    current_user: dict = Depends(get_current_user),
):
    """Reject a grievance."""
    try:
        with get_db() as conn:
            grievance = _load_grievance_for_action(conn, grievance_id)
            _authorize_officer_or_admin_for_grievance(current_user, grievance)

            old_status = grievance["status"]
            citizen_id = grievance["citizen_id"]
            now = datetime.utcnow().isoformat()

            conn.execute("""
                UPDATE grievances
                SET status = 'rejected', resolution_notes = ?, updated_at = ?
                WHERE grievance_id = ?
            """, (request.reason, now, grievance_id))

            log_status_update(conn, grievance_id, old_status, "rejected",
                              request.officer_name or current_user["username"], request.reason,
                              current_user["id"], current_user["role"])

        log_audit_action(
            action="grievance_reject",
            user_id=current_user["id"],
            target_id=grievance_id,
            metadata={"reason": request.reason},
        )

        if citizen_id:
            notification_service.notify_status_change(grievance_id, citizen_id, "rejected")

        return {"success": True, "grievance_id": grievance_id, "status": "rejected"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Reject failed")
        raise HTTPException(500, "Internal server error")


@router.post("/{grievance_id}/resolve")
async def resolve_grievance(
    grievance_id: str, request: ResolveGrievanceRequest,
    current_user: dict = Depends(get_current_user),
):
    """Resolve a grievance."""
    try:
        with get_db() as conn:
            grievance = _load_grievance_for_action(conn, grievance_id)
            _authorize_officer_or_admin_for_grievance(current_user, grievance)

            old_status = grievance["status"]
            citizen_id = grievance["citizen_id"]
            now = datetime.utcnow().isoformat()

            conn.execute("""
                UPDATE grievances
                SET status = 'resolved', resolved_at = ?,
                    resolution_notes = ?, updated_at = ?
                WHERE grievance_id = ?
            """, (now, request.resolution_notes, now, grievance_id))

            log_status_update(conn, grievance_id, old_status, "resolved",
                              request.officer_name or current_user["username"],
                              request.resolution_notes,
                              current_user["id"], current_user["role"])

        sla_service.resolve_sla(grievance_id)

        log_audit_action(
            action="grievance_resolve",
            user_id=current_user["id"],
            target_id=grievance_id,
        )

        if citizen_id:
            notification_service.notify_status_change(grievance_id, citizen_id, "resolved")

        return {"success": True, "grievance_id": grievance_id, "status": "resolved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Resolve failed")
        raise HTTPException(500, "Internal server error")


@router.post("/{grievance_id}/update-status")
async def update_status(
    grievance_id: str, request: UpdateStatusRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update grievance status. Validates against the state machine."""
    try:
        with get_db() as conn:
            grievance = _load_grievance_for_action(conn, grievance_id)
            _authorize_officer_or_admin_for_grievance(current_user, grievance)

            old_status = grievance["status"]
            citizen_id = grievance["citizen_id"]

            allowed = VALID_TRANSITIONS.get(old_status, set())
            if request.new_status not in allowed:
                raise HTTPException(
                    400,
                    f"Invalid transition: {old_status} -> {request.new_status}. "
                    f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}",
                )

            conn.execute("""
                UPDATE grievances SET status = ?, updated_at = ? WHERE grievance_id = ?
            """, (request.new_status, datetime.utcnow().isoformat(), grievance_id))

            log_status_update(conn, grievance_id, old_status, request.new_status,
                              request.officer_name or current_user["username"], request.notes,
                              current_user["id"], current_user["role"])

        log_audit_action(
            action="grievance_status_update",
            user_id=current_user["id"],
            target_id=grievance_id,
            metadata={"old_status": old_status, "new_status": request.new_status},
        )

        if citizen_id:
            notification_service.notify_status_change(grievance_id, citizen_id, request.new_status)

        return {
            "success": True, "grievance_id": grievance_id,
            "old_status": old_status, "new_status": request.new_status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Update status failed")
        raise HTTPException(500, "Internal server error")


@router.post("/{grievance_id}/reopen")
async def reopen_grievance(
    grievance_id: str,
    request: ReopenRequest,
    current_user: dict = Depends(get_current_user),
):
    """Citizen owner reopens a resolved grievance."""
    try:
        with get_db() as conn:
            grievance = _load_grievance_for_action(conn, grievance_id)

            # Only the filing citizen may reopen
            if current_user["role"] != "citizen" or grievance.get("citizen_id") != current_user["id"]:
                raise HTTPException(403, "Only the filing citizen can reopen a grievance")

            old_status = grievance["status"]
            if "reopened" not in VALID_TRANSITIONS.get(old_status, set()):
                raise HTTPException(
                    400,
                    f"Cannot reopen from status '{old_status}'. Only resolved grievances can be reopened.",
                )

            now = datetime.utcnow().isoformat()
            conn.execute(
                "UPDATE grievances SET status = 'reopened', updated_at = ? WHERE grievance_id = ?",
                (now, grievance_id),
            )

            log_status_update(
                conn, grievance_id, old_status, "reopened",
                current_user["username"], request.reason,
                current_user["id"], current_user["role"],
            )

            # Add a comment capturing the reopen reason
            try:
                conn.execute("""
                    INSERT INTO grievance_comments
                    (grievance_id, comment_text, commenter_type, commenter_name,
                     author_id, author_name, author_role,
                     comment_type, is_public, created_at, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    grievance_id, f"[Reopen] {request.reason}",
                    current_user["role"], current_user["username"],
                    current_user["id"],
                    current_user["username"], current_user["role"],
                    "reopen", True, now, now,
                ))
            except Exception:
                pass

        log_audit_action(
            action="grievance_reopen",
            user_id=current_user["id"],
            target_id=grievance_id,
            metadata={"reason": request.reason},
        )

        return {"success": True, "grievance_id": grievance_id, "status": "reopened"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Reopen failed")
        raise HTTPException(500, "Internal server error")


@router.post("/{grievance_id}/comment")
async def add_comment(
    grievance_id: str,
    body: CommentRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a comment to a grievance. is_internal=true requires officer/admin."""
    try:
        if body.is_internal and current_user["role"] not in ("officer", "admin"):
            raise HTTPException(403, "Only officers/admins can post internal comments")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT grievance_id, citizen_id, department FROM grievances WHERE grievance_id = ?",
                (grievance_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, f"Grievance {grievance_id} not found")

            # Citizens can only comment on their own grievances
            if current_user["role"] == "citizen":
                if row["citizen_id"] != current_user["id"]:
                    raise HTTPException(403, "You can only comment on your own grievances")
            elif current_user["role"] == "officer":
                # Officer must be in the same department
                if current_user.get("department") != row["department"]:
                    raise HTTPException(403, "Officers can only comment on grievances in their department")

            # is_public is the inverse of is_internal
            is_public = not body.is_internal

            conn.execute("""
                INSERT INTO grievance_comments
                (grievance_id, comment_text, commenter_type, commenter_name,
                 author_id, author_name, author_role,
                 comment_type, is_public, created_at, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                grievance_id, body.comment_text,
                current_user["role"], current_user["username"],
                current_user["id"],
                current_user["username"], current_user["role"],
                body.comment_type, is_public,
                datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
            ))

            try:
                conn.execute(
                    "UPDATE grievances SET comment_count = COALESCE(comment_count, 0) + 1 WHERE grievance_id = ?",
                    (grievance_id,),
                )
            except Exception:
                pass

        return {"success": True, "grievance_id": grievance_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Add comment failed")
        raise HTTPException(500, "Internal server error")


@router.get("/{grievance_id}/comments")
async def get_comments(
    grievance_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get comments for a grievance.

    Citizens see only public comments. Officers see public + internal comments
    from their own department. Admins see everything.

    NOTE: until the migration adds `comment.author_department`, internal-comment
    department scoping for officers degrades to "officers see all internal
    comments on grievances in their dept" — author-level filtering will be
    enabled once the column exists. See header TODO.
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # First verify grievance exists and capture department for officer scoping
            cursor.execute(
                "SELECT department, citizen_id FROM grievances WHERE grievance_id = ?",
                (grievance_id,),
            )
            head = cursor.fetchone()
            if not head:
                raise HTTPException(404, f"Grievance {grievance_id} not found")

            if current_user["role"] == "citizen":
                if head["citizen_id"] != current_user["id"]:
                    raise HTTPException(403, "You can only view comments on your own grievances")
                cursor.execute("""
                    SELECT id, author_name, author_role, comment_text, comment_type,
                           is_public, created_at
                    FROM grievance_comments
                    WHERE grievance_id = ? AND is_public = TRUE
                    ORDER BY created_at ASC
                """, (grievance_id,))
            elif current_user["role"] == "officer":
                # Officer must be in same department
                if current_user.get("department") != head["department"]:
                    raise HTTPException(403, "Officers can only view comments on grievances in their department")
                cursor.execute("""
                    SELECT id, author_name, author_role, comment_text, comment_type,
                           is_public, created_at
                    FROM grievance_comments WHERE grievance_id = ?
                    ORDER BY created_at ASC
                """, (grievance_id,))
            else:
                # admin
                cursor.execute("""
                    SELECT id, author_name, author_role, comment_text, comment_type,
                           is_public, created_at
                    FROM grievance_comments WHERE grievance_id = ?
                    ORDER BY created_at ASC
                """, (grievance_id,))

            comments = [dict(r) for r in cursor.fetchall()]

        return {"grievance_id": grievance_id, "comments": comments}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Get comments failed")
        raise HTTPException(500, "Internal server error")


@router.post("/{grievance_id}/rate")
async def rate_grievance(
    grievance_id: str,
    rating: int = Query(..., ge=1, le=5),
    resolution_quality: int = Query(default=None, ge=1, le=5),
    response_time: int = Query(default=None, ge=1, le=5),
    officer_behavior: int = Query(default=None, ge=1, le=5),
    feedback_text: str = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    """Rate a resolved grievance. Only the filing citizen may rate."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, citizen_id FROM grievances WHERE grievance_id = ?",
                (grievance_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, f"Grievance {grievance_id} not found")
            if row["status"] != "resolved":
                raise HTTPException(400, "Can only rate resolved grievances")
            if current_user["role"] != "citizen" or row["citizen_id"] != current_user["id"]:
                raise HTTPException(403, "Only the submitting citizen can rate")

            cursor.execute("""
                INSERT INTO grievance_ratings
                (grievance_id, citizen_id, rating, resolution_quality,
                 response_time, officer_behavior, feedback_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (grievance_id) DO UPDATE SET
                    citizen_id = EXCLUDED.citizen_id,
                    rating = EXCLUDED.rating,
                    resolution_quality = EXCLUDED.resolution_quality,
                    response_time = EXCLUDED.response_time,
                    officer_behavior = EXCLUDED.officer_behavior,
                    feedback_text = EXCLUDED.feedback_text
            """, (
                grievance_id, current_user["id"], rating,
                resolution_quality, response_time, officer_behavior, feedback_text,
            ))

        return {"success": True, "grievance_id": grievance_id, "rating": rating}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Rate failed")
        raise HTTPException(500, "Internal server error")


@router.post("/{grievance_id}/pause-sla")
async def pause_grievance_sla(
    grievance_id: str,
    reason: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Pause SLA for a grievance. Officer/admin only."""
    if current_user["role"] not in ("officer", "admin"):
        raise HTTPException(403, "Officer or admin access required")
    try:
        with get_db() as conn:
            grievance = _load_grievance_for_action(conn, grievance_id)
            _authorize_officer_or_admin_for_grievance(current_user, grievance)
        sla_service.pause_sla(grievance_id, reason)
        log_audit_action(
            action="grievance_sla_pause",
            user_id=current_user["id"],
            target_id=grievance_id,
            metadata={"reason": reason},
        )
        return {"success": True, "grievance_id": grievance_id, "sla_paused": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Pause SLA failed")
        raise HTTPException(500, "Internal server error")


@router.post("/{grievance_id}/resume-sla")
async def resume_grievance_sla(
    grievance_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Resume SLA for a grievance. Officer/admin only."""
    if current_user["role"] not in ("officer", "admin"):
        raise HTTPException(403, "Officer or admin access required")
    try:
        with get_db() as conn:
            grievance = _load_grievance_for_action(conn, grievance_id)
            _authorize_officer_or_admin_for_grievance(current_user, grievance)
        sla_service.resume_sla(grievance_id)
        log_audit_action(
            action="grievance_sla_resume",
            user_id=current_user["id"],
            target_id=grievance_id,
        )
        return {"success": True, "grievance_id": grievance_id, "sla_resumed": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Resume SLA failed")
        raise HTTPException(500, "Internal server error")


@router.get("/{grievance_id}/track")
async def track_grievance(grievance_id: str):
    """Public tracking endpoint. Returns ONLY redacted fields - no PII.

    Exposes: id, status, priority, submitted_at, last_updated_at, status history.
    Drops: description, citizen_phone, citizen_email, citizen_name, address,
           internal notes, resolution_notes (may contain officer-level detail).
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT grievance_id, status, priority, submitted_at,
                       COALESCE(last_status_change_at, updated_at) as last_updated_at
                FROM grievances WHERE grievance_id = ?
            """, (grievance_id,))

            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, f"Grievance {grievance_id} not found")

            grievance = {
                "grievance_id": row["grievance_id"],
                "status": row["status"],
                "priority": row["priority"],
                "submitted_at": row["submitted_at"],
                "last_updated_at": row["last_updated_at"],
            }

            cursor.execute("""
                SELECT new_status, timestamp
                FROM grievance_status_updates WHERE grievance_id = ?
                ORDER BY timestamp ASC
            """, (grievance_id,))
            history = [dict(r) for r in cursor.fetchall()]

        sla = sla_service.get_sla_status(grievance_id)
        # Redact SLA to status-only (no due_date / officer-internal fields)
        sla_public = None
        if sla:
            sla_public = {
                "status": sla.get("status"),
                "is_paused": sla.get("is_paused"),
            }

        return {"grievance": grievance, "history": history, "sla": sla_public}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Track failed")
        raise HTTPException(500, "Internal server error")
