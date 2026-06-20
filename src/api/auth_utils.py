"""
JWT Authentication Utilities

Provides:
1. Password hashing and verification with policy enforcement
2. JWT token generation and validation
3. User authentication with lockout protection
4. Role-based access control
5. Audit logging
6. Session management with device tracking
"""

import os
import re
import json
import uuid
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import bcrypt
from jose import JWTError, jwt

from .database import get_db

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

_DEFAULT_SECRET = "nyayasetu-dev-secret-key-CHANGE-IN-PRODUCTION"

# Accept canonical JWT_SECRET_KEY first, fall back to legacy NYAYASETU_SECRET_KEY.
SECRET_KEY = (
    os.environ.get("JWT_SECRET_KEY")
    or os.environ.get("NYAYASETU_SECRET_KEY")
    or _DEFAULT_SECRET
)

_ENV = os.environ.get("ENV", "development").strip().lower()
if _ENV == "production" and (not SECRET_KEY or SECRET_KEY == _DEFAULT_SECRET):
    raise RuntimeError(
        "SECURITY: JWT_SECRET_KEY must be set to a strong random value in production. "
        "Refusing to start with default/missing secret."
    )
if SECRET_KEY == _DEFAULT_SECRET:
    logger.warning(
        "SECURITY: Using default secret key. Set JWT_SECRET_KEY env var in production!"
    )

ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

# Token expiry. Read from JWT_EXPIRY_HOURS, default 24h.
try:
    ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
except (TypeError, ValueError):
    ACCESS_TOKEN_EXPIRE_HOURS = 24

# Refresh tokens (separate, longer-lived).
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("JWT_REFRESH_EXPIRY_DAYS", "7"))


# ============================================================================
# PASSWORD UTILITIES
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


# ============================================================================
# JWT TOKEN UTILITIES
# ============================================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access",
) -> str:
    """Create JWT token with iat, nbf, exp, jti, type claims."""
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta is None:
        if token_type == "refresh":
            expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        else:
            expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    expire = now + expires_delta
    to_encode.update({
        "iat": now,
        "nbf": now,
        "exp": expire,
        "jti": uuid.uuid4().hex,
        "type": token_type,
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a long-lived refresh token (separate JTI, type=refresh)."""
    return create_access_token(data, token_type="refresh")


def decode_access_token(
    token: str, expected_type: str = "access"
) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT, enforcing the expected token type.

    Tokens minted with type="refresh" are longer-lived than access tokens, so
    they must not be accepted on access-protected routes. When ``expected_type``
    is None the type claim is not checked (used by flows that knowingly accept
    refresh tokens).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if expected_type is not None and payload.get("type", "access") != expected_type:
        return None
    return payload


# ============================================================================
# USER AUTHENTICATION
# ============================================================================

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with username and password."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, password_hash, role,
                   department, designation, assigned_schemes,
                   location, preferred_language, is_active
            FROM users
            WHERE (username = ? OR email = ?) AND is_active = TRUE
        """, (username, username))

        user = cursor.fetchone()

    if not user:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "department": user["department"],
        "designation": user["designation"],
        "assigned_schemes": user["assigned_schemes"],
        "location": user["location"],
        "preferred_language": user["preferred_language"],
    }


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, role, department, designation,
                   assigned_schemes, location, preferred_language, is_active
            FROM users
            WHERE id = ? AND is_active = TRUE
        """, (user_id,))

        user = cursor.fetchone()

    if not user:
        return None
    return dict(user)


def create_user(
    username: str,
    email: str,
    password: str,
    role: str,
    phone: Optional[str] = None,
    department: Optional[str] = None,
    designation: Optional[str] = None,
    location: Optional[str] = None,
    preferred_language: str = "en",
) -> Dict[str, Any]:
    """Create new user."""
    if role not in ["citizen", "officer", "admin"]:
        raise ValueError(f"Invalid role: {role}")

    password_hash = hash_password(password)

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (
                    username, email, phone, password_hash, role,
                    department, designation, location, preferred_language
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                username, email, phone, password_hash, role,
                department, designation, location, preferred_language,
            ))

            user_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO user_profiles (user_id) VALUES (?)", (user_id,)
            )

            return {
                "id": user_id,
                "username": username,
                "email": email,
                "role": role,
            }

        except Exception as e:
            error_str = str(e)
            if "username" in error_str:
                raise ValueError("Username already exists")
            elif "email" in error_str:
                raise ValueError("Email already exists")
            elif "phone" in error_str:
                raise ValueError("Phone number already exists")
            else:
                raise ValueError("User already exists")


def update_last_login(user_id: int):
    """Update user's last login timestamp."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,),
        )


def store_session(user_id: int, token: str, expires_at: datetime):
    """Store session token in database."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, token, expires_at.isoformat()),
        )


def invalidate_session(token: str):
    """Invalidate a session token."""
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET is_active = FALSE WHERE token = ?", (token,)
        )


def is_session_valid(token: str) -> bool:
    """Check if session token is valid."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT expires_at, is_active FROM sessions WHERE token = ?",
            (token,),
        )
        result = cursor.fetchone()

    if not result:
        return False

    if not result["is_active"]:
        return False

    expires = datetime.fromisoformat(result["expires_at"])
    return datetime.utcnow() <= expires


# ============================================================================
# ROLE-BASED ACCESS CONTROL
# ============================================================================

def check_permission(user_role: str, required_role: str) -> bool:
    """Check if user has required permission based on role hierarchy."""
    role_hierarchy = {"admin": 3, "officer": 2, "citizen": 1}
    return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)


def can_manage_scheme(user_id: int, scheme_name: str) -> bool:
    """Check if officer can manage a specific scheme."""
    user = get_user_by_id(user_id)
    if not user:
        return False
    if user["role"] == "admin":
        return True
    if user["role"] == "officer":
        import json
        assigned = json.loads(user["assigned_schemes"] or "[]")
        return scheme_name in assigned
    return False


def can_manage_grievance(user_id: int, department: str) -> bool:
    """Check if officer can manage grievances in a department."""
    user = get_user_by_id(user_id)
    if not user:
        return False
    if user["role"] == "admin":
        return True
    if user["role"] == "officer":
        return user["department"] == department
    return False


# ============================================================================
# PASSWORD POLICY
# ============================================================================

PASSWORD_MIN_LENGTH = 8
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
PASSWORD_HISTORY_SIZE = 5


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password against policy.
    Returns dict with 'valid' bool and 'errors' list.
    """
    errors = []
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if re.search(r"[A-Z]", password) and re.search(r"[a-z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1

    strength = "weak" if score <= 2 else "medium" if score <= 3 else "strong"

    return {"valid": len(errors) == 0, "errors": errors, "strength": strength, "score": score}


def check_password_history(user_id: int, new_password: str) -> bool:
    """Check if password was recently used. Returns True if password is OK (not reused)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_history FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

    if not row or not row["password_history"]:
        return True

    history = json.loads(row["password_history"])
    for old_hash in history:
        if verify_password(new_password, old_hash):
            return False
    return True


def update_password_history(user_id: int, old_hash: str):
    """Add old password hash to history, keeping last N entries."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_history FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        history = json.loads(row["password_history"] or "[]") if row and row["password_history"] else []
        history.append(old_hash)
        history = history[-PASSWORD_HISTORY_SIZE:]

        conn.execute(
            "UPDATE users SET password_history = ? WHERE id = ?",
            (json.dumps(history), user_id),
        )


# ============================================================================
# ACCOUNT LOCKOUT
# ============================================================================

def check_account_lockout(username: str) -> Optional[str]:
    """Check if account is locked. Returns lock message or None."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT failed_login_attempts, locked_until
            FROM users WHERE (username = ? OR email = ?) AND is_active = TRUE
        """, (username, username))
        row = cursor.fetchone()

    if not row:
        return None

    if row["locked_until"]:
        locked_until = datetime.fromisoformat(row["locked_until"])
        if datetime.utcnow() < locked_until:
            remaining = int((locked_until - datetime.utcnow()).total_seconds() / 60) + 1
            return f"Account locked. Try again in {remaining} minute(s)."
        # Lock expired, will be cleared on next successful login

    return None


def record_failed_login(username: str):
    """Record a failed login attempt, lock account if threshold exceeded.

    If a previous lock has expired, reset the counter before incrementing
    so users don't get re-locked instantly on a single wrong attempt.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, failed_login_attempts, locked_until FROM users
            WHERE (username = ? OR email = ?) AND is_active = TRUE
        """, (username, username))
        row = cursor.fetchone()

        if not row:
            return

        prior_attempts = row["failed_login_attempts"] or 0
        # If locked_until exists and is in the past, the lock has expired:
        # reset attempts before counting this new failure.
        locked_until_str = row["locked_until"]
        if locked_until_str:
            try:
                locked_until = datetime.fromisoformat(locked_until_str)
                if datetime.utcnow() >= locked_until:
                    prior_attempts = 0
            except (ValueError, TypeError):
                prior_attempts = 0

        attempts = prior_attempts + 1

        if attempts >= MAX_FAILED_ATTEMPTS:
            locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
            conn.execute("""
                UPDATE users SET failed_login_attempts = ?, locked_until = ?
                WHERE id = ?
            """, (attempts, locked_until.isoformat(), row["id"]))
            logger.warning(f"Account locked for user: {username}")
        else:
            conn.execute(
                "UPDATE users SET failed_login_attempts = ?, locked_until = NULL WHERE id = ?",
                (attempts, row["id"]),
            )


def clear_failed_attempts(user_id: int):
    """Clear failed login attempts on successful login."""
    with get_db() as conn:
        conn.execute("""
            UPDATE users SET failed_login_attempts = 0, locked_until = NULL
            WHERE id = ?
        """, (user_id,))


# ============================================================================
# ENHANCED SESSION MANAGEMENT
# ============================================================================

def store_session_enhanced(
    user_id: int, token: str, expires_at: datetime,
    ip_address: str = None, user_agent: str = None,
):
    """Store session with device tracking info."""
    device_type = "unknown"
    if user_agent:
        ua_lower = user_agent.lower()
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            device_type = "mobile"
        elif "electron" in ua_lower:
            device_type = "desktop"
        else:
            device_type = "web"

    with get_db() as conn:
        conn.execute("""
            INSERT INTO sessions
            (user_id, token, expires_at, ip_address, user_agent, device_type, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, token, expires_at.isoformat(),
            ip_address, user_agent, device_type,
            datetime.utcnow().isoformat(),
        ))


def get_user_sessions(user_id: int):
    """Get all active sessions for a user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, ip_address, user_agent, device_type,
                   created_at, last_activity, expires_at
            FROM sessions
            WHERE user_id = ? AND is_active = TRUE
            ORDER BY last_activity DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def revoke_session(session_id: int, user_id: int, reason: str = "user_revoke"):
    """Revoke a specific session."""
    with get_db() as conn:
        conn.execute("""
            UPDATE sessions
            SET is_active = FALSE, logout_at = ?, logout_reason = ?
            WHERE id = ? AND user_id = ?
        """, (datetime.utcnow().isoformat(), reason, session_id, user_id))


def revoke_all_sessions(user_id: int, except_token: str = None, reason: str = "user_logout_all"):
    """Revoke all sessions for a user, optionally keeping current."""
    with get_db() as conn:
        if except_token:
            conn.execute("""
                UPDATE sessions
                SET is_active = FALSE, logout_at = ?, logout_reason = ?
                WHERE user_id = ? AND is_active = TRUE AND token != ?
            """, (datetime.utcnow().isoformat(), reason, user_id, except_token))
        else:
            conn.execute("""
                UPDATE sessions
                SET is_active = FALSE, logout_at = ?, logout_reason = ?
                WHERE user_id = ? AND is_active = TRUE
            """, (datetime.utcnow().isoformat(), reason, user_id))


def update_session_activity(token: str):
    """Update last_activity for a session."""
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET last_activity = ? WHERE token = ? AND is_active = TRUE",
            (datetime.utcnow().isoformat(), token),
        )


def invalidate_all_sessions_except(user_id: int, keep_token: str, reason: str = "password_change"):
    """Revoke every active session for a user EXCEPT the one identified by keep_token.

    Used after password change to lock other devices out while keeping the
    current session alive.
    """
    revoke_all_sessions(user_id, except_token=keep_token, reason=reason)


def revoke_all_user_sessions(user_id: int, reason: str = "admin_disable"):
    """Revoke every active session for a user (no exceptions).

    Intended to be called by admin routes when disabling a user account.
    Note: admin route file is owned by another agent; that file should call
    this helper after flipping is_active=FALSE on the target user.
    """
    revoke_all_sessions(user_id, except_token=None, reason=reason)


# ============================================================================
# PASSWORD RESET
# ============================================================================

def _hash_reset_token(token: str) -> str:
    """SHA-256 hash a reset token for at-rest storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(user_id: int) -> str:
    """Generate a password reset token (valid for 1 hour).

    The raw token is returned to the caller (to be emailed to the user).
    Only the SHA-256 hash is persisted to the DB.
    """
    raw_token = uuid.uuid4().hex
    token_hash = _hash_reset_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    with get_db() as conn:
        conn.execute("""
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, token_hash, expires_at.isoformat()))

    return raw_token


def validate_reset_token(token: str) -> Optional[int]:
    """Validate reset token (compares SHA-256 hash), return user_id or None."""
    token_hash = _hash_reset_token(token)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, expires_at, used
            FROM password_reset_tokens WHERE token = ?
        """, (token_hash,))
        row = cursor.fetchone()

    if not row:
        return None
    if row["used"]:
        return None
    if datetime.utcnow() > datetime.fromisoformat(row["expires_at"]):
        return None
    return row["user_id"]


def mark_reset_token_used(token: str):
    """Mark reset token as used (looked up by SHA-256 hash)."""
    token_hash = _hash_reset_token(token)
    with get_db() as conn:
        conn.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE token = ?", (token_hash,)
        )


def change_user_password(user_id: int, new_password: str):
    """Change user password, update history."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            update_password_history(user_id, row["password_hash"])

        new_hash = hash_password(new_password)
        conn.execute("""
            UPDATE users SET password_hash = ?, password_changed_at = ?
            WHERE id = ?
        """, (new_hash, datetime.utcnow().isoformat(), user_id))


# ============================================================================
# AUDIT LOGGING
# ============================================================================

def log_audit(
    user_id: int = None, username: str = None, role: str = None,
    action_type: str = "", resource_type: str = None, resource_id: str = None,
    endpoint_path: str = None, request_method: str = None,
    ip_address: str = None, user_agent: str = None,
    status_code: int = None, error_message: str = None,
    duration_ms: int = None,
):
    """Write an audit log entry."""
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO audit_logs (
                    user_id, username, role, action_type, resource_type,
                    resource_id, endpoint_path, request_method,
                    ip_address, user_agent, status_code, error_message, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, username, role, action_type, resource_type,
                resource_id, endpoint_path, request_method,
                ip_address, user_agent, status_code, error_message, duration_ms,
            ))
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


def log_audit_action(
    action: str,
    user_id: Optional[int] = None,
    target_id: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Lightweight wrapper around log_audit() for privileged-action logging.

    Other agents will call this from their route files (admin, scheme,
    grievance, etc.). Resource_type is left generic; metadata is serialized
    into the error_message column when no dedicated metadata column exists.

    Args:
        action: short verb describing the action (e.g. "user_disable",
                "scheme_publish", "officer_code_create").
        user_id: id of the actor (admin/officer performing the action).
        target_id: id of the resource being acted on (e.g. target user id).
        metadata: extra context (dict will be JSON-serialized).
    """
    serialized = None
    if metadata:
        try:
            serialized = json.dumps(metadata, default=str)
        except (TypeError, ValueError):
            serialized = str(metadata)
    try:
        log_audit(
            user_id=user_id,
            action_type=action,
            resource_id=str(target_id) if target_id is not None else None,
            error_message=serialized,
        )
    except Exception as e:
        logger.error(f"log_audit_action failed: {e}")
