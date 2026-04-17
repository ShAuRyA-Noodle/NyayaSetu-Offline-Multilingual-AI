"""
Authentication Routes

Handles user registration, login, logout, token management,
password reset, session management, and enterprise auth features.
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from .auth_utils import (
    authenticate_user, create_access_token, decode_access_token,
    create_user, get_user_by_id, update_last_login,
    invalidate_session, is_session_valid,
    check_permission, validate_password_strength,
    check_password_history, check_account_lockout,
    record_failed_login, clear_failed_attempts,
    store_session_enhanced, get_user_sessions,
    revoke_session, revoke_all_sessions, update_session_activity,
    create_password_reset_token, validate_reset_token,
    mark_reset_token_used, change_user_password,
    log_audit, verify_password,
)
from .schemas import (
    LoginRequest, LoginResponse,
    RegisterRequest, RegisterResponse,
    UserResponse,
)
from .database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
security = HTTPBearer()


# ============================================================================
# ADDITIONAL SCHEMAS (auth-specific, kept here to avoid circular imports)
# ============================================================================

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# ============================================================================
# AUTH DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Dependency to get current authenticated user from JWT token."""
    token = credentials.credentials

    if not is_session_valid(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update session activity
    update_session_activity(token)

    return user


def require_role(required_role: str):
    """Dependency factory for role-based access control."""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if not check_permission(current_user["role"], required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_role}",
            )
        return current_user
    return role_checker


# ============================================================================
# CORE AUTH ENDPOINTS
# ============================================================================

@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest, req: Request):
    """Register new user with password policy enforcement and officer code validation."""
    try:
        # Block admin self-registration
        if request.role == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin accounts cannot be self-registered",
            )

        # Validate password strength
        strength = validate_password_strength(request.password)
        if not strength["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Weak password: {'; '.join(strength['errors'])}",
            )

        # Officer code validation
        officer_department = None
        officer_designation = request.designation
        if request.role == "officer":
            if not request.officer_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Officer registration code is required",
                )
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM officer_registration_codes WHERE code = ?",
                    (request.officer_code,),
                )
                code_row = cursor.fetchone()
                if not code_row:
                    raise HTTPException(400, "Invalid officer registration code")
                code_data = dict(code_row)
                if code_data.get("is_used"):
                    raise HTTPException(400, "This code has already been used")
                if code_data.get("expires_at"):
                    try:
                        exp = datetime.fromisoformat(code_data["expires_at"])
                        if exp < datetime.utcnow():
                            raise HTTPException(400, "This code has expired")
                    except (ValueError, TypeError):
                        pass
                officer_department = code_data["department"]
                officer_designation = code_data.get("designation") or officer_designation

        user = create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            role=request.role,
            phone=request.phone,
            location=request.location,
            preferred_language=request.preferred_language,
        )

        # Set department and designation for officers
        if request.role == "officer" and officer_department:
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET department = ?, designation = ? WHERE id = ?",
                    (officer_department, officer_designation, user["id"]),
                )
                conn.execute(
                    "UPDATE officer_registration_codes SET is_used = TRUE, used_by = ?, used_at = CURRENT_TIMESTAMP WHERE code = ?",
                    (user["id"], request.officer_code),
                )
            user["department"] = officer_department
            user["designation"] = officer_designation

        logger.info(f"New user registered: {user['username']} ({user['role']})")

        log_audit(
            user_id=user["id"], username=user["username"], role=user["role"],
            action_type="register", resource_type="user", resource_id=str(user["id"]),
            endpoint_path="/api/v1/auth/register", request_method="POST",
            ip_address=req.client.host if req.client else None,
            status_code=200,
        )

        return RegisterResponse(
            success=True,
            message="User registered successfully",
            user=user,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, req: Request):
    """Login with lockout protection and device tracking."""
    try:
        # Check lockout
        lock_msg = check_account_lockout(request.username)
        if lock_msg:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=lock_msg,
            )

        user = authenticate_user(request.username, request.password)

        if not user:
            record_failed_login(request.username)
            log_audit(
                username=request.username, action_type="login_failed",
                endpoint_path="/api/v1/auth/login", request_method="POST",
                ip_address=req.client.host if req.client else None,
                status_code=401, error_message="Invalid credentials",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Clear failed attempts on success
        clear_failed_attempts(user["id"])

        access_token_expires = timedelta(hours=4)
        access_token = create_access_token(
            data={
                "user_id": user["id"],
                "username": user["username"],
                "role": user["role"],
            },
            expires_delta=access_token_expires,
        )

        expires_at = datetime.utcnow() + access_token_expires

        # Enhanced session with device tracking
        ip_address = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent", "")
        store_session_enhanced(
            user["id"], access_token, expires_at,
            ip_address=ip_address, user_agent=user_agent,
        )

        update_last_login(user["id"])

        # Increment login count
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET login_count = COALESCE(login_count, 0) + 1 WHERE id = ?",
                (user["id"],),
            )

        log_audit(
            user_id=user["id"], username=user["username"], role=user["role"],
            action_type="login", endpoint_path="/api/v1/auth/login",
            request_method="POST", ip_address=ip_address,
            user_agent=user_agent, status_code=200,
        )

        logger.info(f"User logged in: {user['username']} ({user['role']})")

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.post("/logout")
async def logout(
    req: Request,
    current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Logout user and invalidate token."""
    try:
        token = credentials.credentials

        # Enhanced: mark with logout reason
        with get_db() as conn:
            conn.execute("""
                UPDATE sessions
                SET is_active = FALSE, logout_at = ?, logout_reason = 'user_logout'
                WHERE token = ?
            """, (datetime.utcnow().isoformat(), token))

        log_audit(
            user_id=current_user["id"], username=current_user["username"],
            role=current_user["role"], action_type="logout",
            endpoint_path="/api/v1/auth/logout", request_method="POST",
            ip_address=req.client.host if req.client else None,
            status_code=200,
        )

        logger.info(f"User logged out: {current_user['username']}")
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        )


@router.post("/logout-all")
async def logout_all(
    current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Revoke all sessions except current."""
    revoke_all_sessions(
        current_user["id"],
        except_token=credentials.credentials,
        reason="user_logout_all",
    )
    return {"success": True, "message": "All other sessions revoked"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current logged-in user's information."""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"],
        department=current_user.get("department"),
        designation=current_user.get("designation"),
        location=current_user.get("location"),
    )


@router.get("/check")
async def check_auth(current_user: dict = Depends(get_current_user)):
    """Check if user is authenticated."""
    return {
        "authenticated": True,
        "user": {
            "username": current_user["username"],
            "role": current_user["role"],
        },
    }


# ============================================================================
# PASSWORD MANAGEMENT
# ============================================================================

@router.put("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Change password with policy enforcement and history check."""
    # Verify current password
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (current_user["id"],))
        row = cursor.fetchone()

    if not row or not verify_password(request.current_password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password
    strength = validate_password_strength(request.new_password)
    if not strength["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weak password: {'; '.join(strength['errors'])}",
        )

    # Check history
    if not check_password_history(current_user["id"], request.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reuse a recent password",
        )

    change_user_password(current_user["id"], request.new_password)

    return {"success": True, "message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Generate password reset token."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM users WHERE email = ? AND is_active = TRUE",
            (request.email,),
        )
        row = cursor.fetchone()

    if not row:
        # Don't reveal whether email exists
        return {"success": True, "message": "If the email exists, a reset token has been generated"}

    create_password_reset_token(row["id"])

    # TODO: Send token via email in production (e.g., SendGrid, SES)
    logger.info(f"Password reset token generated for user {row['id']} (token should be emailed, not returned)")
    return {
        "success": True,
        "message": "If the email exists, a password reset link has been sent",
    }


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Reset password using token."""
    user_id = validate_reset_token(request.token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    strength = validate_password_strength(request.new_password)
    if not strength["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weak password: {'; '.join(strength['errors'])}",
        )

    change_user_password(user_id, request.new_password)
    mark_reset_token_used(request.token)

    # Revoke all sessions for security
    revoke_all_sessions(user_id, reason="password_reset")

    return {"success": True, "message": "Password reset successfully. Please login again."}


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

@router.get("/sessions")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    """List user's active sessions with device info."""
    sessions = get_user_sessions(current_user["id"])
    return {"sessions": sessions, "count": len(sessions)}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Revoke a specific session."""
    revoke_session(session_id, current_user["id"])
    return {"success": True, "message": "Session revoked"}


@router.post("/refresh")
async def refresh_token(
    req: Request,
    current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Refresh an expiring JWT token."""
    old_token = credentials.credentials

    # Create new token
    access_token_expires = timedelta(hours=24)
    new_token = create_access_token(
        data={
            "user_id": current_user["id"],
            "username": current_user["username"],
            "role": current_user["role"],
        },
        expires_delta=access_token_expires,
    )

    expires_at = datetime.utcnow() + access_token_expires
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent", "")

    # Store new session, invalidate old
    store_session_enhanced(
        current_user["id"], new_token, expires_at,
        ip_address=ip_address, user_agent=user_agent,
    )
    invalidate_session(old_token)

    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
    }
