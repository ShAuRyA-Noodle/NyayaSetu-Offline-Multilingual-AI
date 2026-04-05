"""
Grievance Routes

Full grievance lifecycle: submission, routing, management, tracking, SLA, comments, ratings, notifications.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth_routes import get_current_user, require_role
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
        logger.error(f"Route grievance failed: {e}")
        raise map_module_error(e, "GrievanceRouter")


@router.post("/submit")
async def submit_grievance(
    request: SubmitGrievanceRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit and store grievance with AI routing and SLA."""
    try:
        if current_user["role"] == "citizen":
            citizen_name = current_user.get("username")
            citizen_email = current_user.get("email")
            citizen_location = current_user.get("location")
        else:
            citizen_name = request.citizen_name
            citizen_email = request.citizen_email
            citizen_location = request.citizen_location

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
                route.grievance_id, current_user["id"], citizen_name,
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

        # Notify citizen
        notification_service.notify_grievance_submitted(
            route.grievance_id, current_user["id"], route.department
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
    except Exception as e:
        logger.error(f"Submit grievance failed: {e}")
        raise HTTPException(500, str(e))


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
        logger.error(f"Get my grievances failed: {e}")
        raise HTTPException(500, str(e))


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
        logger.error(f"Department inbox failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/all")
async def get_all_grievances(
    status: str = Query(default=None),
    department: str = Query(default=None),
    priority: str = Query(default=None),
    limit: int = Query(default=100),
    current_user: dict = Depends(get_current_user),
):
    """Get all grievances system-wide (admin/officer). Supports filtering."""
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
            if status:
                query += " AND status = ?"
                params.append(status)
            if department:
                query += " AND department = ?"
                params.append(department)
            if priority:
                query += " AND priority = ?"
                params.append(priority)
            query += """ ORDER BY CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END, submitted_at DESC LIMIT ?"""
            params.append(limit)
            cursor.execute(query, params)
            grievances = [dict(r) for r in cursor.fetchall()]
        return {"grievances": grievances, "count": len(grievances)}
    except Exception as e:
        logger.error(f"Get all grievances failed: {e}")
        raise HTTPException(500, str(e))


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
        logger.error(f"Get assigned failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/department/{department}")
async def get_department_grievances(
    department: str,
    status: str = "pending",
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """Get grievances for a department. Pending shows all; other statuses filter by assigned officer."""
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
                # Non-pending: only show grievances assigned to this officer
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
    except Exception as e:
        logger.error(f"Get grievances failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/department/{department}/dashboard")
async def department_dashboard(
    department: str,
    officer_name: str = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Get department dashboard data, filtered by officer if provided."""
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
    except Exception as e:
        logger.error(f"Dashboard failed: {e}")
        raise HTTPException(500, str(e))



# ============================================================================
# STATIC ROUTES (must be above /{grievance_id} to avoid path shadowing)
# ============================================================================

@router.get("/stats")
async def grievance_stats():
    """Get grievance statistics."""
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
        logger.error(f"Stats failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/sla/dashboard")
async def sla_dashboard():
    """System-wide SLA overview."""
    return sla_service.get_sla_dashboard()


@router.get("/sla/breaches")
async def sla_breaches():
    """Current active SLA breaches."""
    dashboard = sla_service.get_sla_dashboard()
    return {"breaches": dashboard.get("active_breaches", [])}


@router.get("/analytics")
async def grievance_analytics():
    """Grievance analytics."""
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
        logger.error(f"Analytics failed: {e}")
        raise HTTPException(500, str(e))


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
        raise HTTPException(500, str(e))


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
                INSERT OR REPLACE INTO sla_config
                (department, critical_sla_hours, high_sla_hours, medium_sla_hours, low_sla_hours, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (department, critical_sla_hours, high_sla_hours, medium_sla_hours, low_sla_hours))
        return {"success": True, "department": department}
    except Exception as e:
        raise HTTPException(500, str(e))


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
                assigned = grievance.get("assigned_officer_name") or ""
                if assigned != current_user.get("username"):
                    raise HTTPException(403, "This grievance is not assigned to you")

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
        logger.error(f"Get detail failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/{grievance_id}/timeline")
async def get_grievance_timeline(grievance_id: str):
    """Get complete status change history."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT new_status, update_notes as notes, updated_by, timestamp
                FROM grievance_status_updates WHERE grievance_id = ?
                ORDER BY timestamp ASC
            """, (grievance_id,))
            timeline = [dict(r) for r in cursor.fetchall()]
        return {"grievance_id": grievance_id, "timeline": timeline}
    except Exception as e:
        logger.error(f"Timeline failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/{grievance_id}/accept")
async def accept_grievance(
    grievance_id: str, request: AcceptGrievanceRequest,
    current_user: dict = Depends(get_current_user),
):
    """Accept a grievance."""
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

            old_status = row["status"]
            citizen_id = row["citizen_id"]
            now = datetime.utcnow().isoformat()

            conn.execute("""
                UPDATE grievances
                SET status = 'accepted', accepted_at = ?,
                    assigned_officer_name = ?, updated_at = ?
                WHERE grievance_id = ?
            """, (now, request.officer_name or current_user["username"], now, grievance_id))

            log_status_update(conn, grievance_id, old_status, "accepted",
                              request.officer_name or current_user["username"], request.notes,
                              current_user["id"], current_user["role"])

        if citizen_id:
            notification_service.notify_status_change(grievance_id, citizen_id, "accepted")

        return {"success": True, "grievance_id": grievance_id, "status": "accepted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Accept failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/{grievance_id}/reject")
async def reject_grievance(
    grievance_id: str, request: RejectGrievanceRequest,
    current_user: dict = Depends(get_current_user),
):
    """Reject a grievance."""
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

            old_status = row["status"]
            citizen_id = row["citizen_id"]
            now = datetime.utcnow().isoformat()

            conn.execute("""
                UPDATE grievances
                SET status = 'rejected', resolution_notes = ?, updated_at = ?
                WHERE grievance_id = ?
            """, (request.reason, now, grievance_id))

            log_status_update(conn, grievance_id, old_status, "rejected",
                              request.officer_name or current_user["username"], request.reason,
                              current_user["id"], current_user["role"])

        if citizen_id:
            notification_service.notify_status_change(grievance_id, citizen_id, "rejected")

        return {"success": True, "grievance_id": grievance_id, "status": "rejected"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reject failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/{grievance_id}/resolve")
async def resolve_grievance(
    grievance_id: str, request: ResolveGrievanceRequest,
    current_user: dict = Depends(get_current_user),
):
    """Resolve a grievance."""
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

            old_status = row["status"]
            citizen_id = row["citizen_id"]
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

        if citizen_id:
            notification_service.notify_status_change(grievance_id, citizen_id, "resolved")

        return {"success": True, "grievance_id": grievance_id, "status": "resolved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resolve failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/{grievance_id}/update-status")
async def update_status(
    grievance_id: str, request: UpdateStatusRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update grievance status."""
    try:
        valid_statuses = [
            "pending", "accepted", "in_progress", "under_review",
            "resolved", "rejected", "closed",
        ]
        if request.new_status not in valid_statuses:
            raise HTTPException(400, f"Invalid status. Must be: {', '.join(valid_statuses)}")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, citizen_id FROM grievances WHERE grievance_id = ?",
                (grievance_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, f"Grievance {grievance_id} not found")

            old_status = row["status"]
            citizen_id = row["citizen_id"]

            conn.execute("""
                UPDATE grievances SET status = ?, updated_at = ? WHERE grievance_id = ?
            """, (request.new_status, datetime.utcnow().isoformat(), grievance_id))

            log_status_update(conn, grievance_id, old_status, request.new_status,
                              request.officer_name or current_user["username"], request.notes,
                              current_user["id"], current_user["role"])

        if citizen_id:
            notification_service.notify_status_change(grievance_id, citizen_id, request.new_status)

        return {
            "success": True, "grievance_id": grievance_id,
            "old_status": old_status, "new_status": request.new_status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update status failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/{grievance_id}/comment")
async def add_comment(
    grievance_id: str,
    comment_text: str = Query(...),
    comment_type: str = Query(default="note"),
    is_public: bool = Query(default=True),
    current_user: dict = Depends(get_current_user),
):
    """Add a comment to a grievance."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT grievance_id FROM grievances WHERE grievance_id = ?", (grievance_id,))
            if not cursor.fetchone():
                raise HTTPException(404, f"Grievance {grievance_id} not found")

            conn.execute("""
                INSERT INTO grievance_comments
                (grievance_id, comment_text, commenter_type, commenter_name,
                 author_id, author_name, author_role,
                 comment_type, is_public, created_at, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                grievance_id, comment_text,
                current_user["role"], current_user["username"],
                current_user["id"],
                current_user["username"], current_user["role"],
                comment_type, is_public,
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
        logger.error(f"Add comment failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/{grievance_id}/comments")
async def get_comments(
    grievance_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get comments for a grievance."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            if current_user["role"] == "citizen":
                cursor.execute("""
                    SELECT id, author_name, author_role, comment_text, comment_type,
                           is_public, created_at
                    FROM grievance_comments
                    WHERE grievance_id = ? AND is_public = 1
                    ORDER BY created_at ASC
                """, (grievance_id,))
            else:
                cursor.execute("""
                    SELECT id, author_name, author_role, comment_text, comment_type,
                           is_public, created_at
                    FROM grievance_comments WHERE grievance_id = ?
                    ORDER BY created_at ASC
                """, (grievance_id,))

            comments = [dict(r) for r in cursor.fetchall()]

        return {"grievance_id": grievance_id, "comments": comments}
    except Exception as e:
        logger.error(f"Get comments failed: {e}")
        raise HTTPException(500, str(e))


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
    """Rate a resolved grievance."""
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
            if row["citizen_id"] != current_user["id"]:
                raise HTTPException(403, "Only the submitting citizen can rate")

            cursor.execute("""
                INSERT OR REPLACE INTO grievance_ratings
                (grievance_id, citizen_id, rating, resolution_quality,
                 response_time, officer_behavior, feedback_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                grievance_id, current_user["id"], rating,
                resolution_quality, response_time, officer_behavior, feedback_text,
            ))

        return {"success": True, "grievance_id": grievance_id, "rating": rating}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/{grievance_id}/pause-sla")
async def pause_grievance_sla(
    grievance_id: str,
    reason: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Pause SLA for a grievance."""
    sla_service.pause_sla(grievance_id, reason)
    return {"success": True, "grievance_id": grievance_id, "sla_paused": True}


@router.post("/{grievance_id}/resume-sla")
async def resume_grievance_sla(
    grievance_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Resume SLA for a grievance."""
    sla_service.resume_sla(grievance_id)
    return {"success": True, "grievance_id": grievance_id, "sla_resumed": True}


@router.get("/{grievance_id}/track")
async def track_grievance(grievance_id: str):
    """Track grievance status (public endpoint)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT grievance_id, title, description, department, priority,
                       status, submitted_at, resolved_at, resolution_notes
                FROM grievances WHERE grievance_id = ?
            """, (grievance_id,))

            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, f"Grievance {grievance_id} not found")

            grievance = dict(row)

            cursor.execute("""
                SELECT new_status, update_notes, timestamp
                FROM grievance_status_updates WHERE grievance_id = ?
                ORDER BY timestamp ASC
            """, (grievance_id,))
            history = [dict(r) for r in cursor.fetchall()]

        sla = sla_service.get_sla_status(grievance_id)

        return {"grievance": grievance, "history": history, "sla": sla}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Track failed: {e}")
        raise HTTPException(500, str(e))


