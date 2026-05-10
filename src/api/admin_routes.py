"""
Admin Routes

User management, audit logs, analytics, system health, and admin operations.
"""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .auth_routes import require_role
from .auth_utils import revoke_all_user_sessions, log_audit_action
from .dependencies import get_summarizer
from .database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ============================================================================
# LOCAL REQUEST MODELS
# ============================================================================

# typing.Literal is preferred over Pydantic Field constraints for fixed enums.
try:
    from typing import Literal
except ImportError:  # pragma: no cover
    from typing_extensions import Literal  # type: ignore


class AdminUpdateUserRequest(BaseModel):
    role: Optional[Literal["citizen", "officer", "admin"]] = None
    department: Optional[str] = Field(default=None, max_length=200)
    designation: Optional[str] = Field(default=None, max_length=200)
    is_active: Optional[bool] = None


@router.get("/users")
async def list_users(
    role: str = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(require_role("admin")),
):
    """List all users with optional role filter. Paginated (max 100 per page)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            if role:
                cursor.execute("""
                    SELECT id, username, email, role, department, designation,
                           is_active, created_at, last_login, login_count,
                           failed_login_attempts, locked_until
                    FROM users WHERE role = ? ORDER BY created_at DESC LIMIT ? OFFSET ?
                """, (role, limit, offset))
            else:
                cursor.execute("""
                    SELECT id, username, email, role, department, designation,
                           is_active, created_at, last_login, login_count,
                           failed_login_attempts, locked_until
                    FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?
                """, (limit, offset))

            users = [dict(row) for row in cursor.fetchall()]

            # Total count for pagination UI
            if role:
                cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = ?", (role,))
            else:
                cursor.execute("SELECT COUNT(*) as cnt FROM users")
            total = cursor.fetchone()["cnt"]

        return {"users": users, "count": len(users), "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.exception("List users failed")
        raise HTTPException(500, "Failed to fetch users")


@router.get("/users/{user_id}")
async def get_user(user_id: int, current_user: dict = Depends(require_role("admin"))):
    """Get user details."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, role, department, designation,
                       location, phone, is_active, created_at, last_login,
                       login_count, failed_login_attempts, locked_until,
                       full_name, address, preferred_language
                FROM users WHERE id = ?
            """, (user_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, "User not found")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Get user failed")
        raise HTTPException(500, "Internal server error")


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: AdminUpdateUserRequest,
    current_user: dict = Depends(require_role("admin")),
):
    """Update user (role, department, status). Body validated via Pydantic."""
    try:
        # Capture pre-state for audit
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, department, designation, is_active FROM users WHERE id = ?",
                (user_id,),
            )
            old_row = cursor.fetchone()
            if not old_row:
                raise HTTPException(404, "User not found")
            old_state = dict(old_row)

            updates = []
            params = []
            changes = {}
            if body.role is not None:
                updates.append("role = ?")
                params.append(body.role)
                changes["role"] = {"old": old_state["role"], "new": body.role}
            if body.department is not None:
                updates.append("department = ?")
                params.append(body.department)
                changes["department"] = {"old": old_state["department"], "new": body.department}
            if body.designation is not None:
                updates.append("designation = ?")
                params.append(body.designation)
                changes["designation"] = {"old": old_state["designation"], "new": body.designation}
            if body.is_active is not None:
                updates.append("is_active = ?")
                params.append(body.is_active)
                changes["is_active"] = {"old": old_state["is_active"], "new": body.is_active}

            if not updates:
                raise HTTPException(400, "No fields to update")

            params.append(user_id)
            conn.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params
            )

        # If role was changed, treat as privileged action
        if "role" in changes:
            log_audit_action(
                action="user_role_change",
                user_id=current_user["id"],
                target_id=user_id,
                metadata=changes,
            )

        log_audit_action(
            action="user_update",
            user_id=current_user["id"],
            target_id=user_id,
            metadata=changes,
        )

        return {"success": True, "user_id": user_id, "changes": list(changes.keys())}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Update user failed")
        raise HTTPException(500, "Internal server error")


@router.post("/users/{user_id}/disable")
async def disable_user(user_id: int, current_user: dict = Depends(require_role("admin"))):
    """Disable a user account and revoke all of their active sessions."""
    try:
        with get_db() as conn:
            conn.execute("UPDATE users SET is_active = FALSE WHERE id = ?", (user_id,))

        # Revoke every active session so the disabled user is locked out immediately
        revoke_all_user_sessions(user_id)

        log_audit_action(
            action="user_disable",
            user_id=current_user["id"],
            target_id=user_id,
        )

        return {"success": True, "user_id": user_id, "is_active": False, "sessions_revoked": True}
    except Exception as e:
        logger.exception("Disable user failed")
        raise HTTPException(500, "Internal server error")


@router.post("/users/{user_id}/unlock")
async def unlock_user(user_id: int, current_user: dict = Depends(require_role("admin"))):
    """Unlock a locked user account."""
    try:
        with get_db() as conn:
            conn.execute("""
                UPDATE users SET failed_login_attempts = 0, locked_until = NULL
                WHERE id = ?
            """, (user_id,))
        log_audit_action(
            action="user_unlock",
            user_id=current_user["id"],
            target_id=user_id,
        )
        return {"success": True, "user_id": user_id, "unlocked": True}
    except Exception as e:
        logger.exception("Unlock user failed")
        raise HTTPException(500, "Internal server error")


@router.get("/audit-logs")
async def get_audit_logs(
    user_id: int = Query(default=None),
    action_type: str = Query(default=None),
    limit: int = Query(default=50),
    offset: int = Query(default=0),
    current_user: dict = Depends(require_role("admin")),
):
    """Get audit logs with filters."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            if action_type:
                query += " AND action_type = ?"
                params.append(action_type)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            logs = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT COUNT(*) as cnt FROM audit_logs")
            total = cursor.fetchone()["cnt"]

        return {"logs": logs, "count": len(logs), "total": total}
    except Exception as e:
        logger.exception("Audit logs failed")
        raise HTTPException(500, "Internal server error")


@router.get("/analytics/overview")
async def analytics_overview(current_user: dict = Depends(require_role("admin"))):
    """System-wide analytics dashboard."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE is_active = TRUE")
            total_users = cursor.fetchone()["cnt"]

            cursor.execute("SELECT role, COUNT(*) as cnt FROM users GROUP BY role")
            users_by_role = {r["role"]: r["cnt"] for r in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) as cnt FROM grievances")
            total_grievances = cursor.fetchone()["cnt"]

            cursor.execute("""
                SELECT COUNT(*) as cnt FROM grievances
                WHERE status NOT IN ('resolved', 'rejected', 'closed')
            """)
            active_grievances = cursor.fetchone()["cnt"]

            cursor.execute("SELECT AVG(rating) as avg FROM grievance_ratings")
            avg_row = cursor.fetchone()
            avg_satisfaction = round(avg_row["avg"], 1) if avg_row and avg_row["avg"] else None

            cursor.execute("SELECT COUNT(*) as cnt FROM notices WHERE status = 'published'")
            published_notices = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM schemes_metadata WHERE status = 'active'")
            active_schemes = cursor.fetchone()["cnt"]

        return {
            "total_users": total_users,
            "users_by_role": users_by_role,
            "total_grievances": total_grievances,
            "active_grievances": active_grievances,
            "avg_satisfaction": avg_satisfaction,
            "published_notices": published_notices,
            "active_schemes": active_schemes,
        }
    except Exception as e:
        logger.exception("Analytics overview failed")
        raise HTTPException(500, "Internal server error")


@router.get("/analytics/trends")
async def analytics_trends(
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(require_role("admin")),
):
    """Historical trend data. `days` clamped to 1..365."""
    try:
        # Compute cutoff in Python for dialect-agnostic queries.
        # SQLite's DATE('now', '-N days') doesn't exist in Postgres.
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DATE(submitted_at) as date, COUNT(*) as grievances
                FROM grievances
                WHERE submitted_at >= ?
                GROUP BY DATE(submitted_at) ORDER BY date
            """, (cutoff,))
            grievance_trend = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as users
                FROM users
                WHERE created_at >= ?
                GROUP BY DATE(created_at) ORDER BY date
            """, (cutoff,))
            user_trend = [dict(r) for r in cursor.fetchall()]

        return {
            "days": days,
            "grievance_trend": grievance_trend,
            "user_trend": user_trend,
        }
    except Exception as e:
        logger.exception("Analytics trends failed")
        raise HTTPException(500, "Internal server error")


@router.get("/analytics/officer-performance")
async def officer_performance(current_user: dict = Depends(require_role("admin"))):
    """Officer performance metrics."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    g.assigned_officer_name as officer,
                    COUNT(*) as total_assigned,
                    SUM(CASE WHEN g.status = 'resolved' THEN 1 ELSE 0 END) as resolved,
                    SUM(CASE WHEN g.status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                    AVG(CASE WHEN gs.resolution_time_hours IS NOT NULL THEN gs.resolution_time_hours END) as avg_resolution_hours,
                    SUM(CASE WHEN gs.resolution_within_sla THEN 1 ELSE 0 END) as within_sla
                FROM grievances g
                LEFT JOIN grievance_sla gs ON g.grievance_id = gs.grievance_id
                WHERE g.assigned_officer_name IS NOT NULL
                GROUP BY g.assigned_officer_name
                ORDER BY resolved DESC
            """)
            officers = []
            for r in cursor.fetchall():
                total = r["total_assigned"] or 0
                resolved = r["resolved"] or 0
                officers.append({
                    "officer": r["officer"],
                    "total_assigned": total,
                    "resolved": resolved,
                    "rejected": r["rejected"] or 0,
                    "resolution_rate": round((resolved / total * 100) if total else 0, 1),
                    "avg_resolution_hours": round(r["avg_resolution_hours"] or 0, 1),
                    "sla_compliance": round((r["within_sla"] or 0) / total * 100 if total else 100, 1),
                })

        return {"officers": officers}
    except Exception as e:
        logger.exception("Officer performance failed")
        raise HTTPException(500, "Internal server error")


@router.get("/system/health")
async def system_health(current_user: dict = Depends(require_role("admin"))):
    """System health check."""
    try:
        health = {"status": "healthy", "components": {}}

        # DB check
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as cnt FROM users")
                user_count = cursor.fetchone()["cnt"]
                health["components"]["database"] = {"status": "up", "users": user_count}
        except Exception as e:
            health["components"]["database"] = {"status": "down", "error": str(e)}
            health["status"] = "degraded"

        # DB file size
        db_path = os.environ.get("NYAYASETU_DB_PATH", "data/governance.db")
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path)
            health["components"]["storage"] = {
                "db_size_mb": round(db_size / (1024 * 1024), 2),
            }

        health["timestamp"] = datetime.utcnow().isoformat()
        return health
    except Exception as e:
        logger.exception("System health failed")
        raise HTTPException(500, "Internal server error")


@router.post("/officer-codes/generate")
async def generate_officer_code(
    department: str = Query(...),
    designation: str = Query(default=None),
    current_user: dict = Depends(require_role("admin")),
):
    """Generate a unique officer registration code."""
    import secrets
    import string
    from datetime import timedelta
    try:
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()

        with get_db() as conn:
            conn.execute("""
                INSERT INTO officer_registration_codes
                (code, department, designation, created_by, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (code, department, designation, current_user["id"], expires_at))

        log_audit_action(
            action="officer_code_create",
            user_id=current_user["id"],
            metadata={"department": department, "designation": designation},
        )

        return {
            "success": True, "code": code,
            "department": department, "designation": designation,
            "expires_at": expires_at,
        }
    except Exception as e:
        logger.exception("Generate officer code failed")
        raise HTTPException(500, "Internal server error")


@router.get("/officer-codes")
async def list_officer_codes(current_user: dict = Depends(require_role("admin"))):
    """List all officer registration codes."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT oc.*, u.username as used_by_name, c.username as created_by_name
                FROM officer_registration_codes oc
                LEFT JOIN users u ON oc.used_by = u.id
                LEFT JOIN users c ON oc.created_by = c.id
                ORDER BY oc.created_at DESC
            """)
            codes = []
            for row in cursor.fetchall():
                code_item = dict(row)
                now = datetime.utcnow()
                if code_item.get("is_used"):
                    code_item["status"] = "used"
                elif code_item.get("expires_at"):
                    try:
                        exp = datetime.fromisoformat(code_item["expires_at"])
                        code_item["status"] = "expired" if exp < now else "available"
                    except (ValueError, TypeError):
                        code_item["status"] = "available"
                else:
                    code_item["status"] = "available"
                codes.append(code_item)

        return {"codes": codes, "count": len(codes)}
    except Exception as e:
        logger.exception("List officer codes failed")
        raise HTTPException(500, "Internal server error")


@router.get("/officer-codes/validate")
async def validate_officer_code(code: str = Query(...)):
    """Validate an officer registration code (for real-time frontend check during registration).

    SECURITY: this endpoint is intentionally unauthenticated to enable the
    registration UX. To prevent department/designation enumeration, the
    response is restricted to `{"valid": bool}` only — no leak of department
    or designation. The full payload is available via the authenticated
    /officer-codes list endpoint.
    """
    logger.warning("officer-codes/validate called unauthenticated; redacted response only")
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT code, is_used, expires_at FROM officer_registration_codes WHERE code = ?",
                (code,),
            )
            row = cursor.fetchone()
            if not row:
                return {"valid": False}
            data = dict(row)
            if data.get("is_used"):
                return {"valid": False}
            if data.get("expires_at"):
                try:
                    exp = datetime.fromisoformat(data["expires_at"])
                    if exp < datetime.utcnow():
                        return {"valid": False}
                except (ValueError, TypeError):
                    pass
            return {"valid": True}
    except Exception:
        logger.exception("Validate officer code failed")
        return {"valid": False}


@router.post("/clear-cache")
async def clear_all_caches(current_user: dict = Depends(require_role("admin"))):
    """Clear all module caches. Admin only."""
    cleared = {}
    try:
        summarizer = get_summarizer()
        summarizer.clear_cache()
        cleared["summarizer"] = "cleared"
    except Exception as e:
        cleared["summarizer"] = f"failed: {e}"

    log_audit_action(
        action="cache_clear",
        user_id=current_user["id"],
        metadata=cleared,
    )

    return {"message": "Cache clearing attempted", "results": cleared}
