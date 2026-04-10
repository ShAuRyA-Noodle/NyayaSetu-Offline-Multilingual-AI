"""
Scheme Routes

Scheme listing, summarization, upload, version management, and analytics.
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query

from .auth_routes import get_current_user, require_role
from .schemas import (
    SummarizeRequest, SchemeSummaryResponse,
    BatchSummarizeRequest, BatchSummarizeResponse,
    UpdateSchemeMetadataRequest,
)
from .errors import ServiceUnavailableError, map_module_error
from .dependencies import get_rag_engine, get_summarizer
from .database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Scheme Summarizer"])


# ============================================================================
# HELPERS
# ============================================================================

def generate_scheme_id(scheme_name: str) -> str:
    base = scheme_name.upper().replace(" ", "-")[:20]
    hash_suffix = hashlib.md5(scheme_name.encode()).hexdigest()[:6].upper()
    return f"SCHEME-{base}-{hash_suffix}"


def can_user_manage_scheme(user_id: int, scheme_id: str, conn) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user and user[0] == "admin":
        return True
    cursor.execute("""
        SELECT COUNT(*) FROM scheme_assignments
        WHERE scheme_id = ? AND officer_id = ? AND is_active = 1
    """, (scheme_id, user_id))
    return cursor.fetchone()[0] > 0


def log_upload_history(
    conn, scheme_id, user_id, upload_type, filename, file_size,
    upload_status, chunks_processed=0, processing_time_ms=0, error_message=None,
):
    conn.execute("""
        INSERT INTO upload_history
        (scheme_id, uploaded_by, upload_type, filename, file_size,
         status, chunks_processed, processing_time_ms, error_message,
         uploaded_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (
        scheme_id, user_id, upload_type, filename, file_size,
        upload_status, chunks_processed, processing_time_ms, error_message,
    ))
    conn.commit()


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/api/v1/schemes/list")
async def list_schemes(detailed: bool = False):
    """List all available schemes from both RAG and metadata tables."""
    try:
        schemes = set()

        # Try RAG engine's schemes table
        try:
            rag_engine = get_rag_engine()
            with get_db(rag_engine.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT scheme_name FROM schemes ORDER BY scheme_name")
                for row in cursor.fetchall():
                    schemes.add(row[0])
        except Exception:
            pass

        # Also query schemes_metadata (governance DB)
        id_map = {}
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT scheme_id, scheme_name FROM schemes_metadata WHERE status = 'active' ORDER BY scheme_name")
                for row in cursor.fetchall():
                    name = row[1] if isinstance(row, (list, tuple)) else row["scheme_name"]
                    sid = row[0] if isinstance(row, (list, tuple)) else row["scheme_id"]
                    schemes.add(name)
                    id_map[name] = sid
        except Exception:
            pass

        sorted_schemes = sorted(schemes)

        if detailed:
            return {
                "schemes": sorted_schemes,
                "scheme_ids": {name: id_map[name] for name in sorted_schemes if name in id_map},
                "count": len(sorted_schemes),
            }

        return {"schemes": sorted_schemes, "count": len(sorted_schemes)}
    except Exception as e:
        logger.error(f"List schemes failed: {e}")
        raise ServiceUnavailableError("Database")


@router.post("/api/v1/summarize", response_model=SchemeSummaryResponse)
async def summarize_scheme(request: SummarizeRequest):
    """Get structured summary of government scheme. Falls back to LLM if RAG fails."""
    # Try RAG-based summarizer first
    try:
        summarizer = get_summarizer()
        summary = summarizer.summarize(
            scheme_name=request.scheme_name, language=request.language
        )
        return SchemeSummaryResponse(
            scheme_name=summary.scheme_name,
            one_line_purpose=summary.one_line_purpose,
            eligibility=summary.eligibility,
            benefits=summary.benefits,
            application_steps=summary.application_steps,
            contact_info=summary.contact_info,
            language=summary.language,
            metadata=summary.metadata,
        )
    except Exception as rag_err:
        logger.warning(f"RAG summarizer failed, trying LLM fallback: {rag_err}")

    # LLM-only fallback
    try:
        from .dependencies import get_answer_generator
        import json as _json

        generator = get_answer_generator()
        lang_label = "Hindi" if request.language == "hi" else "English"
        prompt = (
            f"Provide a detailed summary of the '{request.scheme_name}' Indian government scheme "
            f"in {lang_label}.\n\n"
            f"Return ONLY valid JSON in this exact format:\n"
            f'{{"one_line_purpose": "...", '
            f'"eligibility": ["criterion 1", "criterion 2", ...], '
            f'"benefits": ["benefit 1", "benefit 2", ...], '
            f'"application_steps": ["step 1", "step 2", ...], '
            f'"contact_info": "helpline or website"}}'
        )
        response = generator.llm_client.generate(prompt=prompt, temperature=0.3, max_tokens=1000)

        if not response or not response.get("success"):
            raise ServiceUnavailableError("Summarizer")

        text = response.get("response", "")
        # Parse JSON from LLM response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = _json.loads(text[start:end])
        else:
            # Couldn't parse JSON — use raw text as purpose
            data = {
                "one_line_purpose": text[:200],
                "eligibility": ["Please refer to official scheme documents"],
                "benefits": ["Please refer to official scheme documents"],
                "application_steps": ["Visit the official scheme portal"],
                "contact_info": "Contact your local government office",
            }

        return SchemeSummaryResponse(
            scheme_name=request.scheme_name,
            one_line_purpose=data.get("one_line_purpose", ""),
            eligibility=data.get("eligibility", []),
            benefits=data.get("benefits", []),
            application_steps=data.get("application_steps", []),
            contact_info=data.get("contact_info"),
            language=request.language,
            metadata={"method": "llm_fallback", "confidence": 0.0},
        )
    except Exception as e:
        logger.error(f"LLM summarizer fallback also failed: {e}")
        raise map_module_error(e, "Summarizer")


@router.post("/api/v1/summarize/batch", response_model=BatchSummarizeResponse)
async def batch_summarize_schemes(request: BatchSummarizeRequest):
    """Batch summarize multiple schemes."""
    try:
        summarizer = get_summarizer()
        summaries = []
        success_count = 0

        for scheme_name in request.scheme_names:
            try:
                summary = summarizer.summarize(
                    scheme_name=scheme_name, language=request.language
                )
                summaries.append({
                    "scheme_name": summary.scheme_name,
                    "one_line_purpose": summary.one_line_purpose,
                    "eligibility": summary.eligibility,
                    "benefits": summary.benefits,
                    "application_steps": summary.application_steps,
                    "status": "success",
                })
                success_count += 1
            except Exception as e:
                summaries.append({
                    "scheme_name": scheme_name,
                    "status": "failed",
                    "error": str(e),
                })

        return BatchSummarizeResponse(
            summaries=summaries,
            language=request.language,
            metadata={"success_count": success_count},
        )
    except Exception as e:
        logger.error(f"Batch summarize failed: {e}")
        raise map_module_error(e, "Summarizer")


# ----------------------------------------------------------------------------
# LLM-powered document formatter (with file cache)
# ----------------------------------------------------------------------------
FORMATTED_DOCS_DIR = os.path.join("data", "formatted_docs")
os.makedirs(FORMATTED_DOCS_DIR, exist_ok=True)


def _format_document_with_llm(raw_text: str) -> dict:
    """
    Use Ollama to transform raw scheme text into a structured JSON document
    with title + sections containing paragraphs, bullets, and numbered lists.
    Falls back to a single-paragraph structure if the LLM is unavailable.
    """
    system_prompt = (
        "You are a document structuring assistant for an Indian government scheme portal. "
        "Your ONLY job is to reformat a raw government scheme document into a clean, structured JSON "
        "that will be rendered in a UI. You MUST preserve ALL factual information exactly — do NOT "
        "summarize, shorten, omit, or invent details. Only reorganize and format the existing text."
    )

    user_prompt = f"""Reformat the following government scheme document into structured JSON.

OUTPUT FORMAT (strict — output ONLY valid JSON, no markdown fences, no explanations):
{{
  "title": "Scheme name as a clean title",
  "sections": [
    {{
      "heading": "SECTION NAME IN UPPERCASE",
      "blocks": [
        {{"type": "paragraph", "text": "A paragraph of text..."}},
        {{"type": "bullets", "items": ["first bullet", "second bullet"]}},
        {{"type": "numbered", "items": ["first step", "second step"]}}
      ]
    }}
  ]
}}

RULES:
1. Preserve EVERY fact, number, date, amount, and detail from the source. No summarization.
2. Break the content into logical sections like: OVERVIEW, OBJECTIVES, BENEFITS, ELIGIBILITY, APPLICATION PROCESS, DOCUMENTS REQUIRED, CONTACT / HELPLINE, etc.
3. Use "bullets" for unordered lists of features, criteria, or items.
4. Use "numbered" for sequential steps or ordered processes.
5. Use "paragraph" for descriptive/explanatory text.
6. Section headings should be short (2–5 words), ALL UPPERCASE.
7. Keep exact URLs, phone numbers, emails, and amounts verbatim.
8. Output MUST be a single valid JSON object. No markdown. No extra text.

RAW DOCUMENT:
\"\"\"
{raw_text}
\"\"\"

JSON OUTPUT:"""

    try:
        import requests as _requests

        input_chars = len(raw_text)
        needed_tokens = min(max(int(input_chars / 2), 4096), 16384)
        logger.info(f"Formatting doc: {input_chars} chars, requesting {needed_tokens} max_tokens")

        # Explicit JSON schema — Ollama's structured output mode enforces this shape.
        json_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "heading": {"type": "string"},
                            "blocks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string", "enum": ["paragraph", "bullets", "numbered"]},
                                        "text": {"type": "string"},
                                        "items": {"type": "array", "items": {"type": "string"}},
                                    },
                                    "required": ["type"],
                                },
                            },
                        },
                        "required": ["heading", "blocks"],
                    },
                },
            },
            "required": ["title", "sections"],
        }

        payload = {
            "model": "qwen2.5:14b-instruct-q4_0",
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "format": json_schema,  # Structured output — enforces exact schema
            "options": {
                "temperature": 0.1,
                "num_predict": needed_tokens,
                "top_p": 0.9,
            },
        }
        response = _requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=300,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Ollama returned {response.status_code}: {response.text[:200]}")

        result = response.json()
        response_text = result.get("response", "").strip()
        logger.info(f"LLM response length: {len(response_text)} chars")

        if not response_text:
            raise ValueError("Empty LLM response")

        structured = json.loads(response_text)
        if "title" not in structured or "sections" not in structured:
            raise ValueError(f"LLM output missing required keys. Got: {list(structured.keys())}")
        return structured
    except Exception as e:
        logger.warning(f"LLM formatting failed, returning raw fallback: {e}")
        return {
            "title": "",
            "sections": [
                {
                    "heading": "DOCUMENT",
                    "blocks": [{"type": "paragraph", "text": raw_text}],
                }
            ],
            "_fallback": True,
        }


def _get_or_build_formatted_doc(scheme_id: str, raw_text: str) -> dict:
    """Return cached formatted doc if source hash matches; otherwise regenerate."""
    source_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
    cache_path = os.path.join(FORMATTED_DOCS_DIR, f"{scheme_id}.json")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("source_hash") == source_hash:
                return cached["formatted"]
        except Exception:
            pass

    formatted = _format_document_with_llm(raw_text)

    # Only cache successful (non-fallback) outputs
    if not formatted.get("_fallback"):
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"source_hash": source_hash, "formatted": formatted}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write formatted-doc cache: {e}")

    return formatted


@router.get("/api/v1/schemes/by-name/{scheme_name}/document")
async def get_scheme_document_by_name(scheme_name: str, formatted: bool = False):
    """Get the full scheme document text by scheme name (for citizens to read full scheme).
    Pass ?formatted=true to get an LLM-structured JSON response (cached).
    """
    try:
        chunks_text = []

        # 1) Try schemes.process column (where uploaded scheme text is stored)
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT process FROM schemes WHERE scheme_name = ? LIMIT 1",
                    (scheme_name,),
                )
                row = cursor.fetchone()
                if row:
                    val = row["process"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
                    if val and len(str(val)) > 100:
                        chunks_text.append(str(val))
        except Exception:
            pass

        # 2) Try scheme_chunks table
        if not chunks_text:
            try:
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT scheme_id FROM schemes_metadata WHERE scheme_name = ? LIMIT 1",
                        (scheme_name,),
                    )
                    row = cursor.fetchone()
                    if row:
                        sid = row["scheme_id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
                        cursor.execute("""
                            SELECT chunk_text FROM scheme_chunks
                            WHERE scheme_id = ? ORDER BY chunk_index
                        """, (sid,))
                        for r in cursor.fetchall():
                            chunks_text.append(r["chunk_text"] if isinstance(r, dict) or hasattr(r, "keys") else r[0])
            except Exception:
                pass

        # 3) Fallback: try RAG engine's schemes table
        if not chunks_text:
            try:
                rag_engine = get_rag_engine()
                with get_db(rag_engine.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT process FROM schemes WHERE scheme_name = ? LIMIT 1",
                        (scheme_name,),
                    )
                    row = cursor.fetchone()
                    if row:
                        val = row[0] if not hasattr(row, "keys") else row.get("process") or row.get("content", "")
                        if val and len(str(val)) > 100:
                            chunks_text.append(str(val))
            except Exception:
                pass

        if not chunks_text:
            raise HTTPException(404, f"No document found for scheme '{scheme_name}'")

        full_document = "\n\n".join(chunks_text)

        if formatted:
            scheme_id = None
            try:
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT scheme_id FROM schemes_metadata WHERE scheme_name = ? LIMIT 1",
                        (scheme_name,),
                    )
                    row = cursor.fetchone()
                    if row:
                        scheme_id = row["scheme_id"] if hasattr(row, "keys") else row[0]
            except Exception:
                pass
            if not scheme_id:
                scheme_id = generate_scheme_id(scheme_name)
            fmt = _get_or_build_formatted_doc(scheme_id, full_document)
            return {
                "scheme_name": scheme_name,
                "scheme_id": scheme_id,
                "formatted": fmt,
            }

        return {
            "scheme_name": scheme_name,
            "document": full_document,
            "chunks_count": len(chunks_text),
            "total_characters": len(full_document),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get scheme document failed: {e}")
        raise HTTPException(500, str(e))


# Static routes MUST be above /{scheme_id} to avoid path shadowing

@router.get("/api/v1/schemes/my-schemes")
async def get_my_schemes(current_user: dict = Depends(get_current_user)):
    """Get schemes assigned to current officer."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            if current_user["role"] == "admin":
                cursor.execute("""
                    SELECT scheme_id, scheme_name, version, status, total_chunks,
                           category, department, view_count, query_count, created_at, updated_at
                    FROM schemes_metadata ORDER BY updated_at DESC
                """)
            else:
                cursor.execute("""
                    SELECT sm.scheme_id, sm.scheme_name, sm.version, sm.status,
                           sm.total_chunks, sm.category, sm.department,
                           sm.view_count, sm.query_count, sm.created_at, sm.updated_at
                    FROM schemes_metadata sm
                    JOIN scheme_assignments sa ON sm.scheme_id = sa.scheme_id
                    WHERE sa.officer_id = ? AND sa.is_active = 1
                    ORDER BY sm.updated_at DESC
                """, (current_user["id"],))
            schemes = [dict(row) for row in cursor.fetchall()]
        return {"schemes": schemes, "count": len(schemes)}
    except Exception as e:
        logger.error(f"Get my schemes failed: {e}")
        raise HTTPException(500, str(e))




@router.get("/api/v1/admin/schemes/analytics", tags=["Admin"])
async def scheme_analytics(current_user: dict = Depends(require_role("admin"))):
    """Scheme analytics."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM schemes_metadata WHERE status = 'active'")
            total = cursor.fetchone()["cnt"]
            cursor.execute("""
                SELECT department, COUNT(*) as cnt FROM schemes_metadata
                WHERE status = 'active' AND department IS NOT NULL
                GROUP BY department ORDER BY cnt DESC
            """)
            by_department = [dict(r) for r in cursor.fetchall()]
            cursor.execute("""
                SELECT u.username, COUNT(*) as uploads FROM upload_history uh
                JOIN users u ON uh.uploaded_by = u.id WHERE uh.status = 'success'
                GROUP BY uh.uploaded_by ORDER BY uploads DESC LIMIT 10
            """)
            top_uploaders = [dict(r) for r in cursor.fetchall()]
            cursor.execute("SELECT SUM(file_size) as total_bytes, SUM(total_chunks) as total_chunks FROM schemes_metadata WHERE status = 'active'")
            storage = dict(cursor.fetchone())
        return {"total_schemes": total, "by_department": by_department, "top_uploaders": top_uploaders, "storage": storage}
    except Exception as e:
        logger.error(f"Analytics failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/api/v1/schemes/{scheme_id}")
async def get_scheme_detail(scheme_id: str):
    """Get full scheme details."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schemes_metadata WHERE scheme_id = ?", (scheme_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(404, f"Scheme {scheme_id} not found")

            conn.execute(
                "UPDATE schemes_metadata SET view_count = COALESCE(view_count, 0) + 1 WHERE scheme_id = ?",
                (scheme_id,),
            )

            scheme = dict(row)

            cursor.execute("""
                SELECT chunk_id, chunk_index, chunk_size, section_type, language
                FROM scheme_chunks WHERE scheme_id = ?
                ORDER BY chunk_index
            """, (scheme_id,))
            scheme["chunks"] = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT sa.officer_id, u.username, sa.can_edit, sa.can_delete
                FROM scheme_assignments sa
                JOIN users u ON sa.officer_id = u.id
                WHERE sa.scheme_id = ? AND sa.is_active = 1
            """, (scheme_id,))
            scheme["assignments"] = [dict(r) for r in cursor.fetchall()]

        return scheme
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get scheme detail failed: {e}")
        raise HTTPException(500, str(e))


@router.put("/api/v1/schemes/{scheme_id}/metadata")
async def update_scheme_metadata(
    scheme_id: str,
    body: UpdateSchemeMetadataRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update scheme metadata."""
    logger.info(f"Update metadata request: scheme_id={scheme_id}, body={body.dict(exclude_none=True)}, user={current_user.get('username')}/{current_user.get('role')}")
    try:
        old_scheme_name = None
        with get_db() as conn:
            if not can_user_manage_scheme(current_user["id"], scheme_id, conn):
                raise HTTPException(403, "Permission denied")

            # Capture old name before rename so we can update RAG DB too
            if body.scheme_name is not None:
                cursor = conn.cursor()
                cursor.execute("SELECT scheme_name FROM schemes_metadata WHERE scheme_id = ?", (scheme_id,))
                row = cursor.fetchone()
                if row:
                    old_scheme_name = row[0] if isinstance(row, (list, tuple)) else row["scheme_name"]

            updates = []
            params = []
            if body.scheme_name is not None:
                updates.append("scheme_name = ?")
                params.append(body.scheme_name)
            if body.tags is not None:
                updates.append("tags = ?")
                params.append(json.dumps(body.tags))
            if body.keywords is not None:
                updates.append("keywords = ?")
                params.append(json.dumps(body.keywords))
            if body.description is not None:
                updates.append("description = ?")
                params.append(body.description)
            if body.category is not None:
                updates.append("category = ?")
                params.append(body.category)
            if body.target_audience is not None:
                updates.append("target_audience = ?")
                params.append(body.target_audience)
            if body.department is not None:
                updates.append("department = ?")
                params.append(body.department)

            if not updates:
                raise HTTPException(400, "No fields to update")

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(scheme_id)
            conn.execute(
                f"UPDATE schemes_metadata SET {', '.join(updates)} WHERE scheme_id = ?",
                params,
            )

        # Also update scheme_name in the RAG engine's schemes table
        # (list_schemes reads from both DBs — stale name here causes duplicates)
        if body.scheme_name is not None and old_scheme_name and old_scheme_name != body.scheme_name:
            try:
                rag_engine = get_rag_engine()
                with get_db(rag_engine.db_path) as rag_conn:
                    rag_conn.execute(
                        "UPDATE schemes SET scheme_name = ? WHERE scheme_name = ?",
                        (body.scheme_name, old_scheme_name),
                    )
                    rag_conn.commit()
            except Exception as e:
                logger.warning(f"Failed to update RAG schemes table: {e}")

        return {"success": True, "scheme_id": scheme_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update metadata failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/api/v1/schemes/{scheme_id}")
async def delete_scheme(scheme_id: str, current_user: dict = Depends(get_current_user)):
    """Soft delete (archive) a scheme."""
    try:
        with get_db() as conn:
            if not can_user_manage_scheme(current_user["id"], scheme_id, conn):
                raise HTTPException(403, "Permission denied")
            conn.execute(
                "UPDATE schemes_metadata SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE scheme_id = ?",
                (scheme_id,),
            )
        return {"success": True, "scheme_id": scheme_id, "status": "archived"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete scheme failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/api/v1/schemes/{scheme_id}/versions")
async def get_scheme_versions(scheme_id: str):
    """Get version history."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sv.version, sv.change_type, sv.change_description,
                       sv.source_file, sv.chunk_count, sv.created_at,
                       u.username
                FROM scheme_versions sv
                LEFT JOIN users u ON sv.changed_by = u.id
                WHERE sv.scheme_id = ?
                ORDER BY sv.version DESC
            """, (scheme_id,))
            history = [dict(r) for r in cursor.fetchall()]
        return {"scheme_id": scheme_id, "history": history}
    except Exception as e:
        logger.error(f"Get versions failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/api/v1/schemes/{scheme_id}/chunks")
async def get_scheme_chunks(scheme_id: str):
    """Get all chunks for a scheme."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT chunk_id, chunk_index, chunk_text, chunk_size,
                       section_type, section_title, language, version
                FROM scheme_chunks WHERE scheme_id = ?
                ORDER BY chunk_index
            """, (scheme_id,))
            chunks = [dict(r) for r in cursor.fetchall()]
        return {"scheme_id": scheme_id, "chunks": chunks, "count": len(chunks)}
    except Exception as e:
        logger.error(f"Get chunks failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/api/v1/admin/schemes/upload", tags=["Admin"])
async def upload_scheme(
    file: UploadFile = File(...),
    scheme_name: str = None,
    current_user: dict = Depends(get_current_user),
):
    """Upload new government scheme document."""
    from src.core.document_processor import DocumentProcessor

    start_time = time.time()
    logger.info(f"Upload started by {current_user['username']}: {file.filename}")

    with get_db() as conn:
        try:
            if not file.filename.endswith((".pdf", ".docx", ".txt")):
                raise HTTPException(400, "Only PDF, DOCX, TXT files supported")

            file_content = await file.read()
            file_size = len(file_content)

            if file_size > 10 * 1024 * 1024:
                raise HTTPException(400, f"File too large: {file_size} bytes (max: 10MB)")

            file_hash = hashlib.sha256(file_content).hexdigest()

            os.makedirs("temp", exist_ok=True)
            # Sanitize filename to prevent path traversal
            safe_filename = os.path.basename(file.filename)
            if not safe_filename:
                safe_filename = f"upload_{hashlib.md5(file_content[:256]).hexdigest()[:8]}.txt"
            temp_path = os.path.join("temp", safe_filename)
            with open(temp_path, "wb") as f:
                f.write(file_content)

            processor = DocumentProcessor()
            text = processor.extract_text(temp_path, file.filename)

            if len(text) < 500:
                os.remove(temp_path)
                raise HTTPException(400, f"Document too short: {len(text)} chars (min: 500)")

            chunks = processor.chunk_text(text, max_length=1000)

            if not scheme_name:
                scheme_name = file.filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")

            scheme_id = generate_scheme_id(scheme_name)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT scheme_id, version, assigned_officer FROM schemes_metadata WHERE scheme_id = ?",
                (scheme_id,),
            )
            existing_scheme = cursor.fetchone()
            is_update = existing_scheme is not None
            upload_type = "update_scheme" if is_update else "new_scheme"

            if is_update:
                if not can_user_manage_scheme(current_user["id"], scheme_id, conn):
                    log_upload_history(conn, scheme_id, current_user["id"], upload_type, file.filename, file_size, "failed", error_message="Permission denied")
                    raise HTTPException(403, f"You don't have permission to update '{scheme_name}'")
                current_version = existing_scheme["version"]
                new_version = current_version + 1
            else:
                new_version = 1

            try:
                rag_engine = get_rag_engine()
                for i, chunk in enumerate(chunks):
                    rag_engine.add_to_index(text=chunk, metadata={
                        "scheme_name": scheme_name, "scheme_id": scheme_id,
                        "chunk_index": i, "source_file": file.filename, "version": new_version,
                    })
            except Exception as e:
                os.remove(temp_path)
                log_upload_history(conn, scheme_id, current_user["id"], upload_type, file.filename, file_size, "failed", error_message=f"Indexing failed: {e}")
                raise HTTPException(500, f"Failed to index: {e}")

            # Store chunks
            for i, chunk in enumerate(chunks):
                chunk_id = f"{scheme_id}-v{new_version}-{i}"
                try:
                    cursor.execute("""
                        INSERT INTO scheme_chunks (chunk_id, scheme_id, chunk_index, chunk_text, chunk_size, version)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (chunk_id, scheme_id, i, chunk, len(chunk), new_version))
                except Exception:
                    pass

            if is_update:
                cursor.execute("""
                    UPDATE schemes_metadata SET version = ?, source_file = ?, file_size = ?,
                        total_chunks = ?, total_characters = ?, file_hash = ?,
                        indexed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE scheme_id = ?
                """, (new_version, file.filename, file_size, len(chunks), len(text), file_hash, scheme_id))
            else:
                cursor.execute("""
                    INSERT INTO schemes_metadata
                    (scheme_id, scheme_name, created_by, assigned_officer, source_file,
                     document_type, file_size, status, version, total_chunks, total_characters,
                     file_hash, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    scheme_id, scheme_name, current_user["id"],
                    current_user["id"] if current_user["role"] == "officer" else None,
                    file.filename, file.filename.split(".")[-1], file_size,
                    new_version, len(chunks), len(text), file_hash,
                ))
                if current_user["role"] == "officer":
                    cursor.execute("""
                        INSERT INTO scheme_assignments (scheme_id, officer_id, assigned_by, can_edit, can_delete)
                        VALUES (?, ?, ?, 1, 0)
                    """, (scheme_id, current_user["id"], current_user["id"]))

            cursor.execute("UPDATE scheme_versions SET is_current = 0 WHERE scheme_id = ?", (scheme_id,))
            cursor.execute("""
                INSERT INTO scheme_versions
                (scheme_id, version, changed_by, change_type, change_description,
                 source_file, file_size, chunk_count, is_current, file_hash, character_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                scheme_id, new_version, current_user["id"],
                "update" if is_update else "create",
                f"{'Updated' if is_update else 'Created'} from {file.filename}",
                file.filename, file_size, len(chunks), file_hash, len(text),
            ))

            processing_time = int((time.time() - start_time) * 1000)
            log_upload_history(conn, scheme_id, current_user["id"], upload_type, file.filename, file_size, "success", len(chunks), processing_time)
            conn.commit()
            os.remove(temp_path)

            return {
                "success": True, "scheme_id": scheme_id, "scheme_name": scheme_name,
                "version": new_version, "is_update": is_update, "source_file": file.filename,
                "chunks_added": len(chunks), "total_characters": len(text),
                "file_size": file_size, "processing_time_ms": processing_time,
                "uploaded_by": current_user["username"],
                "message": f"Successfully {'updated' if is_update else 'created'} '{scheme_name}' (v{new_version}) with {len(chunks)} chunks!",
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise HTTPException(500, f"Upload failed: {e}")


@router.get("/api/v1/schemes/my-schemes")
async def get_my_schemes(current_user: dict = Depends(get_current_user)):
    """Get schemes assigned to current officer."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            if current_user["role"] == "admin":
                cursor.execute("""
                    SELECT scheme_id, scheme_name, version, status, total_chunks,
                           category, department, view_count, query_count, created_at, updated_at
                    FROM schemes_metadata ORDER BY updated_at DESC
                """)
            else:
                cursor.execute("""
                    SELECT sm.scheme_id, sm.scheme_name, sm.version, sm.status,
                           sm.total_chunks, sm.category, sm.department,
                           sm.view_count, sm.query_count, sm.created_at, sm.updated_at
                    FROM schemes_metadata sm
                    JOIN scheme_assignments sa ON sm.scheme_id = sa.scheme_id
                    WHERE sa.officer_id = ? AND sa.is_active = 1
                    ORDER BY sm.updated_at DESC
                """, (current_user["id"],))
            schemes = [dict(row) for row in cursor.fetchall()]
        return {"schemes": schemes, "count": len(schemes)}
    except Exception as e:
        logger.error(f"Get my schemes failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/api/v1/schemes/{scheme_id}/history")
async def get_scheme_history(scheme_id: str, current_user: dict = Depends(get_current_user)):
    """Get version history of a scheme (authenticated)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            if current_user["role"] != "admin":
                if not can_user_manage_scheme(current_user["id"], scheme_id, conn):
                    raise HTTPException(403, "Permission denied")
            cursor.execute("""
                SELECT sv.version, sv.change_type, sv.change_description,
                       sv.source_file, sv.chunk_count, sv.created_at, u.username
                FROM scheme_versions sv
                JOIN users u ON sv.changed_by = u.id
                WHERE sv.scheme_id = ?
                ORDER BY sv.version DESC
            """, (scheme_id,))
            history = [{
                "version": r["version"], "change_type": r["change_type"],
                "description": r["change_description"], "source_file": r["source_file"],
                "chunk_count": r["chunk_count"], "created_at": r["created_at"],
                "changed_by": r["username"],
            } for r in cursor.fetchall()]
        return {"scheme_id": scheme_id, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get scheme history failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/api/v1/admin/schemes/{scheme_id}/assign", tags=["Admin"])
async def assign_scheme_officer(
    scheme_id: str, officer_id: int = Query(...),
    can_edit: bool = True, can_delete: bool = False,
    current_user: dict = Depends(require_role("admin")),
):
    """Assign officer to a scheme."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT scheme_id FROM schemes_metadata WHERE scheme_id = ?", (scheme_id,))
            if not cursor.fetchone():
                raise HTTPException(404, f"Scheme {scheme_id} not found")
            cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'officer'", (officer_id,))
            if not cursor.fetchone():
                raise HTTPException(404, f"Officer {officer_id} not found")
            cursor.execute("""
                INSERT OR REPLACE INTO scheme_assignments
                (scheme_id, officer_id, assigned_by, can_edit, can_delete, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (scheme_id, officer_id, current_user["id"], can_edit, can_delete))
        return {"success": True, "scheme_id": scheme_id, "officer_id": officer_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assign failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/api/v1/admin/schemes/{scheme_id}/unassign/{officer_id}", tags=["Admin"])
async def unassign_scheme_officer(
    scheme_id: str, officer_id: int,
    current_user: dict = Depends(require_role("admin")),
):
    """Remove officer assignment."""
    try:
        with get_db() as conn:
            conn.execute("UPDATE scheme_assignments SET is_active = 0 WHERE scheme_id = ? AND officer_id = ?", (scheme_id, officer_id))
        return {"success": True, "scheme_id": scheme_id, "officer_id": officer_id}
    except Exception as e:
        logger.error(f"Unassign failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/api/v1/admin/schemes/analytics", tags=["Admin"])
async def scheme_analytics(current_user: dict = Depends(require_role("admin"))):
    """Scheme analytics."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM schemes_metadata WHERE status = 'active'")
            total = cursor.fetchone()["cnt"]
            cursor.execute("""
                SELECT department, COUNT(*) as cnt FROM schemes_metadata
                WHERE status = 'active' AND department IS NOT NULL
                GROUP BY department ORDER BY cnt DESC
            """)
            by_department = [dict(r) for r in cursor.fetchall()]
            cursor.execute("""
                SELECT u.username, COUNT(*) as uploads FROM upload_history uh
                JOIN users u ON uh.uploaded_by = u.id WHERE uh.status = 'success'
                GROUP BY uh.uploaded_by ORDER BY uploads DESC LIMIT 10
            """)
            top_uploaders = [dict(r) for r in cursor.fetchall()]
            cursor.execute("SELECT SUM(file_size) as total_bytes, SUM(total_chunks) as total_chunks FROM schemes_metadata WHERE status = 'active'")
            storage = dict(cursor.fetchone())
        return {"total_schemes": total, "by_department": by_department, "top_uploaders": top_uploaders, "storage": storage}
    except Exception as e:
        logger.error(f"Analytics failed: {e}")
        raise HTTPException(500, str(e))
