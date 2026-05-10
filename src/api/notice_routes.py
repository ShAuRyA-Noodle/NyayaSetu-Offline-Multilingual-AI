"""
Notice Routes

Full notice lifecycle: generate, draft, review, approve, publish, withdraw, PDF.
"""

import hashlib
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth_routes import get_current_user, require_role
from .auth_utils import log_audit_action
from .schemas import DraftNoticeRequest, NoticeResponse, SaveDraftRequest, UpdateNoticeRequest
from .dependencies import get_notice_drafter
from .database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Notice Drafter"])


def generate_notice_id(notice_type: str, scheme_name: str) -> str:
    year = datetime.utcnow().year
    hash_suffix = hashlib.md5(f"{scheme_name}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:8].upper()
    return f"NOT-{year}-{notice_type.upper()[:4]}-{hash_suffix}"


def generate_reference_number(notice_type: str) -> str:
    year = datetime.utcnow().year
    ts = datetime.utcnow().strftime("%m%d%H%M%S")
    return f"NS/{notice_type.upper()[:4]}/{year}/{ts}"


@router.post("/api/v1/notices/generate", response_model=NoticeResponse)
async def generate_notice(
    request: DraftNoticeRequest,
    current_user: dict = Depends(get_current_user),
):
    """AI-generate notice content (officer/admin only - LLM cost gate). Falls back to direct LLM if RAG fails."""
    if current_user["role"] not in ("officer", "admin"):
        raise HTTPException(403, "Officer or admin access required")

    effective_date = None
    if request.effective_date:
        effective_date = datetime.strptime(request.effective_date, "%Y-%m-%d").date()

    # Try RAG-based notice generation first
    try:
        drafter = get_notice_drafter()
        notice = drafter.draft_notice(
            scheme_name=request.scheme_name,
            notice_type=request.notice_type,
            language=request.language,
            effective_date=effective_date,
        )
        return NoticeResponse(
            reference_number=notice.reference_number,
            notice_type=notice.notice_type,
            scheme_name=notice.scheme_name,
            issue_date=notice.issue_date.isoformat(),
            effective_date=notice.effective_date.isoformat() if notice.effective_date else None,
            subject=notice.subject,
            body=notice.body,
            formatted_notice=notice.format_gazette_style(),
            language=notice.language,
            metadata=notice.metadata,
        )
    except Exception as rag_err:
        logger.warning(f"RAG notice generation failed, trying LLM fallback: {rag_err}")

    # LLM-only fallback
    try:
        from .dependencies import get_answer_generator
        generator = get_answer_generator()
        llm_client = generator.llm_client

        lang_label = "Hindi" if request.language == "hi" else "English"
        prompt = (
            f"You are an official government notice drafter. Generate a formal government "
            f"{request.notice_type} notice about the '{request.scheme_name}' scheme.\n\n"
            f"Language: {lang_label}\n"
            f"Format: Official Government Gazette Style\n\n"
            f"Return ONLY valid JSON:\n"
            f'{{"subject": "...", "body": "...(200-500 words, formal, factual)...", '
            f'"issuing_authority": "...", "signature_block": "..."}}'
        )
        response = llm_client.generate(prompt=prompt, temperature=0.3, max_tokens=2000)

        if not response or not response.get("success"):
            raise HTTPException(503, "LLM unavailable for notice generation")

        import json as _json
        text = response.get("response", "")
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            content = _json.loads(text[start:end])
        else:
            content = {
                "subject": f"Notice regarding {request.scheme_name}",
                "body": text,
                "issuing_authority": "Ministry of Rural Development",
                "signature_block": "Joint Secretary, Government of India",
            }

        today = datetime.utcnow().date()
        ref_number = generate_reference_number(request.notice_type)
        eff_str = effective_date.isoformat() if effective_date else None

        # Build formatted notice
        sep = "=" * 80
        formatted = (
            f"{sep}\nGOVERNMENT OF INDIA\n"
            f"{'MINISTRY OF RURAL DEVELOPMENT' if request.language == 'en' else 'ग्रामीण विकास मंत्रालय'}\n"
            f"{sep}\n\n"
            f"Reference No.: {ref_number}\n"
            f"Date: {today.strftime('%d-%m-%Y')}\n\n"
            f"SUBJECT: {content.get('subject', '')}\n\n"
            f"{content.get('body', '')}\n\n"
        )
        if effective_date:
            formatted += f"Effective from: {effective_date.strftime('%d-%m-%Y')}\n\n"
        formatted += (
            f"{content.get('signature_block', '')}\n"
            f"{content.get('issuing_authority', '')}\n"
            f"\n{sep}\nEND OF NOTICE\n{sep}\n"
        )

        return NoticeResponse(
            reference_number=ref_number,
            notice_type=request.notice_type,
            scheme_name=request.scheme_name,
            issue_date=today.isoformat(),
            effective_date=eff_str,
            subject=content.get("subject", f"Notice regarding {request.scheme_name}"),
            body=content.get("body", ""),
            formatted_notice=formatted,
            language=request.language,
            metadata={"method": "llm_fallback", "confidence": 0.0},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("LLM notice fallback also failed")
        raise HTTPException(503, "Notice generation unavailable")


# Keep legacy endpoint for backward compatibility
@router.post("/api/v1/draft-notice", response_model=NoticeResponse)
async def draft_notice_legacy(
    request: DraftNoticeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Draft official government notice (legacy endpoint, officer/admin only)."""
    return await generate_notice(request, current_user=current_user)


@router.post("/api/v1/notices/draft")
async def save_notice_draft(
    request: "SaveDraftRequest",
    current_user: dict = Depends(get_current_user),
):
    """Save notice as draft. Officer/admin only."""
    if current_user["role"] not in ("officer", "admin"):
        raise HTTPException(403, "Officer or admin access required")
    try:
        notice_id = generate_notice_id(request.notice_type, request.scheme_name)
        ref_number = generate_reference_number(request.notice_type)

        with get_db() as conn:
            conn.execute("""
                INSERT INTO notices
                (notice_id, reference_number, scheme_name, notice_type,
                 officer_id, officer_name, officer_department,
                 subject, body, formatted_notice, language,
                 effective_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
            """, (
                notice_id, ref_number, request.scheme_name, request.notice_type,
                current_user["id"], current_user["username"],
                current_user.get("department", ""),
                request.subject, request.body, request.formatted_notice, request.language,
                request.effective_date,
            ))

        return {
            "success": True, "notice_id": notice_id,
            "reference_number": ref_number, "status": "draft",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Save draft failed")
        raise HTTPException(500, "Internal server error")


@router.get("/api/v1/notices")
async def list_notices(
    status: str = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    """List officer's notices."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cols = """notice_id, reference_number, scheme_name, notice_type,
                       officer_name, subject, body, formatted_notice, language,
                       status, effective_date, published_at,
                       review_notes, reviewed_at,
                       view_count, created_at, updated_at"""
            if current_user["role"] == "admin":
                if status:
                    cursor.execute(f"""
                        SELECT {cols}
                        FROM notices WHERE status = ?
                        ORDER BY updated_at DESC
                    """, (status,))
                else:
                    cursor.execute(f"""
                        SELECT {cols}
                        FROM notices ORDER BY updated_at DESC
                    """)
            else:
                if status:
                    cursor.execute(f"""
                        SELECT {cols}
                        FROM notices WHERE officer_id = ? AND status = ?
                        ORDER BY updated_at DESC
                    """, (current_user["id"], status))
                else:
                    cursor.execute(f"""
                        SELECT {cols}
                        FROM notices WHERE officer_id = ?
                        ORDER BY updated_at DESC
                    """, (current_user["id"],))

            notices = [dict(r) for r in cursor.fetchall()]
        return {"notices": notices, "count": len(notices)}
    except Exception as e:
        logger.exception("List notices failed")
        raise HTTPException(500, "Internal server error")


@router.get("/api/v1/notices/public")
async def public_notice_board(
    notice_type: str = Query(default=None),
    department: str = Query(default=None),
    limit: int = Query(default=20),
    offset: int = Query(default=0),
):
    """Public notice board - no auth required."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            query = """
                SELECT notice_id, reference_number, scheme_name, notice_type,
                       officer_name, officer_department, subject, language,
                       effective_date, published_at, view_count
                FROM notices WHERE status = 'published'
            """
            params = []
            if notice_type:
                query += " AND notice_type = ?"
                params.append(notice_type)
            if department:
                query += " AND officer_department = ?"
                params.append(department)
            query += " ORDER BY published_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            notices = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT COUNT(*) as cnt FROM notices WHERE status = 'published'")
            total = cursor.fetchone()["cnt"]

        return {"notices": notices, "count": len(notices), "total": total}
    except Exception as e:
        logger.exception("Public board failed")
        raise HTTPException(500, "Internal server error")


@router.get("/api/v1/notices/public/{notice_id}")
async def public_notice_detail(notice_id: str):
    """Public notice detail."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT notice_id, reference_number, scheme_name, notice_type,
                       officer_name, officer_department, officer_designation,
                       subject, body, formatted_notice, language,
                       effective_date, published_at, view_count
                FROM notices WHERE notice_id = ? AND status = 'published'
            """, (notice_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, "Notice not found")

            conn.execute(
                "UPDATE notices SET view_count = view_count + 1 WHERE notice_id = ?",
                (notice_id,),
            )

        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Public detail failed")
        raise HTTPException(500, "Internal server error")


@router.get("/api/v1/notices/{notice_id}")
async def get_notice(notice_id: str, current_user: dict = Depends(get_current_user)):
    """Get notice details. Admin sees all; officer sees only own department's; citizen sees only published."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notices WHERE notice_id = ?", (notice_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, "Notice not found")
            data = dict(row)

            role = current_user.get("role")
            if role == "admin":
                return data
            if role == "officer":
                if data.get("officer_department") and data["officer_department"] != current_user.get("department"):
                    raise HTTPException(403, "You can only view notices in your own department")
                return data
            # citizen: only published notices
            if data.get("status") != "published":
                raise HTTPException(403, "Citizens can only view published notices")
            return data
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Get notice failed")
        raise HTTPException(500, "Internal server error")


@router.put("/api/v1/notices/{notice_id}")
async def update_notice(
    notice_id: str,
    request: UpdateNoticeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update draft notice."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, officer_id FROM notices WHERE notice_id = ?", (notice_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, "Notice not found")
            if row["status"] != "draft":
                raise HTTPException(400, "Can only edit draft notices")
            if row["officer_id"] != current_user["id"] and current_user["role"] != "admin":
                raise HTTPException(403, "Permission denied")

            updates = []
            params = []
            if request.subject is not None:
                updates.append("subject = ?")
                params.append(request.subject)
            if request.body is not None:
                updates.append("body = ?")
                params.append(request.body)
            if request.formatted_notice is not None:
                updates.append("formatted_notice = ?")
                params.append(request.formatted_notice)
            if request.effective_date is not None:
                updates.append("effective_date = ?")
                params.append(request.effective_date)

            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(notice_id)
                conn.execute(
                    f"UPDATE notices SET {', '.join(updates)} WHERE notice_id = ?",
                    params,
                )

        return {"success": True, "notice_id": notice_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Update notice failed")
        raise HTTPException(500, "Internal server error")


@router.delete("/api/v1/notices/{notice_id}")
async def delete_notice(notice_id: str, current_user: dict = Depends(get_current_user)):
    """Delete draft notice. Owner-officer or admin only."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, officer_id FROM notices WHERE notice_id = ?", (notice_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, "Notice not found")
            if row["status"] != "draft":
                raise HTTPException(400, "Can only delete draft notices")
            # Ownership check: must own the notice OR be admin
            if row["officer_id"] != current_user["id"] and current_user["role"] != "admin":
                raise HTTPException(403, "You can only delete your own draft notices")

            conn.execute("DELETE FROM notices WHERE notice_id = ?", (notice_id,))

        log_audit_action(
            action="notice_delete",
            user_id=current_user["id"],
            target_id=notice_id,
        )
        return {"success": True, "notice_id": notice_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Delete notice failed")
        raise HTTPException(500, "Internal server error")


@router.post("/api/v1/notices/{notice_id}/submit-review")
async def submit_for_review(notice_id: str, current_user: dict = Depends(get_current_user)):
    """Submit notice for review. Owner-officer only (admins don't submit their own to themselves)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, officer_id FROM notices WHERE notice_id = ?", (notice_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, "Notice not found")
            if row["status"] != "draft":
                raise HTTPException(400, "Notice must be in draft status")
            # Ownership check
            if row["officer_id"] != current_user["id"] and current_user["role"] != "admin":
                raise HTTPException(403, "You can only submit your own notices for review")

            conn.execute(
                "UPDATE notices SET status = 'pending_review', updated_at = CURRENT_TIMESTAMP WHERE notice_id = ?",
                (notice_id,),
            )
        log_audit_action(
            action="notice_submit_review",
            user_id=current_user["id"],
            target_id=notice_id,
        )
        return {"success": True, "notice_id": notice_id, "status": "pending_review"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Submit for review failed")
        raise HTTPException(500, "Internal server error")


@router.post("/api/v1/notices/{notice_id}/review")
async def review_notice(
    notice_id: str,
    approved: bool = Query(...),
    review_notes: str = Query(default=""),
    current_user: dict = Depends(require_role("admin")),
):
    """Approve or reject notice. Admin only. Atomic single-UPDATE state transition."""
    try:
        now = datetime.utcnow().isoformat()
        new_status = "approved" if approved else "draft"

        with get_db() as conn:
            cursor = conn.cursor()
            # Atomic review: collapses status flip + reviewer + (conditionally) approver into one UPDATE.
            # Only succeeds when current status is 'pending_review'.
            if approved:
                cursor.execute("""
                    UPDATE notices
                    SET status = ?, reviewed_by = ?, reviewed_at = ?,
                        review_notes = ?, approved_by = ?, approved_at = ?,
                        updated_at = ?
                    WHERE notice_id = ? AND status = 'pending_review'
                """, (new_status, current_user["id"], now, review_notes,
                      current_user["id"], now, now, notice_id))
            else:
                cursor.execute("""
                    UPDATE notices
                    SET status = ?, reviewed_by = ?, reviewed_at = ?,
                        review_notes = ?, updated_at = ?
                    WHERE notice_id = ? AND status = 'pending_review'
                """, (new_status, current_user["id"], now, review_notes, now, notice_id))

            if cursor.rowcount == 0:
                raise HTTPException(409, "Notice not in 'pending_review' state or not found")

        log_audit_action(
            action="notice_review",
            user_id=current_user["id"],
            target_id=notice_id,
            metadata={"approved": approved, "notes": review_notes},
        )
        return {"success": True, "notice_id": notice_id, "status": new_status}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Review notice failed")
        raise HTTPException(500, "Internal server error")


@router.post("/api/v1/notices/{notice_id}/publish")
async def publish_notice(
    notice_id: str,
    current_user: dict = Depends(require_role("admin")),
):
    """Publish an approved notice. Admin only."""
    try:
        now = datetime.utcnow().isoformat()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM notices WHERE notice_id = ?", (notice_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, "Notice not found")
            if row["status"] not in ("approved", "draft"):
                raise HTTPException(400, f"Cannot publish notice in '{row['status']}' status")

            conn.execute("""
                UPDATE notices
                SET status = 'published', published_by = ?, published_at = ?, updated_at = ?
                WHERE notice_id = ?
            """, (current_user["id"], now, now, notice_id))

        log_audit_action(
            action="notice_publish",
            user_id=current_user["id"],
            target_id=notice_id,
        )
        return {"success": True, "notice_id": notice_id, "status": "published"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Publish notice failed")
        raise HTTPException(500, "Internal server error")


@router.post("/api/v1/notices/{notice_id}/withdraw")
async def withdraw_notice(
    notice_id: str,
    reason: str = Query(...),
    current_user: dict = Depends(require_role("admin")),
):
    """Withdraw a published notice. Admin only."""
    try:
        now = datetime.utcnow().isoformat()
        with get_db() as conn:
            conn.execute("""
                UPDATE notices
                SET status = 'withdrawn', withdrawn_by = ?, withdrawn_at = ?,
                    withdrawal_reason = ?, updated_at = ?
                WHERE notice_id = ? AND status = 'published'
            """, (current_user["id"], now, reason, now, notice_id))

        log_audit_action(
            action="notice_withdraw",
            user_id=current_user["id"],
            target_id=notice_id,
            metadata={"reason": reason},
        )
        return {"success": True, "notice_id": notice_id, "status": "withdrawn"}
    except Exception as e:
        logger.exception("Withdraw notice failed")
        raise HTTPException(500, "Internal server error")
