"""
Notification Service

In-app notification creation, retrieval, and management.
"""

import logging
from datetime import datetime

from .database import get_db

logger = logging.getLogger(__name__)


def create_notification(
    recipient_id: int,
    message: str,
    grievance_id: str = None,
    subject: str = None,
    priority: str = "normal",
):
    """Create an in-app notification."""
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO grievance_notifications
                (grievance_id, recipient_id, notification_type, subject, message, status, priority_level)
                VALUES (?, ?, 'in_app', ?, ?, 'pending', ?)
            """, (grievance_id, recipient_id, subject, message, priority))
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")


def get_unread_notifications(user_id: int, limit: int = 50):
    """Get unread notifications for a user."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, grievance_id, subject, message, priority_level, created_at
                FROM grievance_notifications
                WHERE recipient_id = ? AND (status = 'pending' OR read_at IS NULL)
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Failed to get notifications: {e}")
        return []


def get_notification_count(user_id: int) -> int:
    """Get unread notification count."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM grievance_notifications
                WHERE recipient_id = ? AND read_at IS NULL
            """, (user_id,))
            return cursor.fetchone()["cnt"]
    except Exception:
        return 0


def mark_as_read(notification_id: int, user_id: int):
    """Mark a notification as read."""
    try:
        with get_db() as conn:
            conn.execute("""
                UPDATE grievance_notifications
                SET read_at = ?, status = 'read'
                WHERE id = ? AND recipient_id = ?
            """, (datetime.utcnow().isoformat(), notification_id, user_id))
    except Exception as e:
        logger.error(f"Failed to mark notification read: {e}")


def mark_all_read(user_id: int):
    """Mark all notifications as read for a user."""
    try:
        with get_db() as conn:
            conn.execute("""
                UPDATE grievance_notifications
                SET read_at = ?, status = 'read'
                WHERE recipient_id = ? AND read_at IS NULL
            """, (datetime.utcnow().isoformat(), user_id))
    except Exception as e:
        logger.error(f"Failed to mark all read: {e}")


def notify_grievance_submitted(grievance_id: str, citizen_id: int, department: str):
    """Notify citizen that grievance was submitted."""
    create_notification(
        recipient_id=citizen_id,
        grievance_id=grievance_id,
        subject="Grievance Submitted",
        message=f"Your grievance {grievance_id} has been submitted and routed to {department}.",
    )


def notify_status_change(grievance_id: str, citizen_id: int, new_status: str):
    """Notify citizen of status change."""
    create_notification(
        recipient_id=citizen_id,
        grievance_id=grievance_id,
        subject="Status Update",
        message=f"Your grievance {grievance_id} status has been updated to: {new_status}.",
    )


def notify_sla_breach(grievance_id: str, officer_id: int, hours_overdue: float):
    """Notify officer of SLA breach."""
    create_notification(
        recipient_id=officer_id,
        grievance_id=grievance_id,
        subject="SLA Breach Alert",
        message=f"Grievance {grievance_id} has breached SLA by {hours_overdue:.1f} hours. Immediate action required.",
        priority="high",
    )
