"""
NyayaVaani FastAPI Router — All voice/cross-lingual endpoints.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse

from .models import (
    TTSRequest, IntentClassifyRequest,
    VoiceGrievanceSubmitRequest,
    TranscriptionResponse, TTSResponse,
    IntentResponse, VoiceGrievanceResponse, NyayaVaaniStatusResponse,
)
from .audio_utils import save_upload_audio
from .language_registry import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/nyayavaani", tags=["NyayaVaani"])


def _get_service():
    """Get NyayaVaani service from app state."""
    from src.api.dependencies import get_nyayavaani_service
    return get_nyayavaani_service()


def _get_current_user():
    """Resolve the auth dep at call time so this module is importable even
    if `src.api.auth_routes` does heavy lazy initialisation."""
    from src.api.auth_routes import get_current_user
    return get_current_user


# ---------------------------------------------------------------------------
# audio_files ownership table
#
# Maps a generated TTS filename → owner_id + scope. Without this, any
# authenticated user could iterate filenames and listen to other citizens'
# grievance acknowledgements (PII leak). Public-scope rows are allowed for
# notice / scheme narration which any citizen may stream.
# ---------------------------------------------------------------------------

_AUDIO_FILES_TABLE_READY = False


def _ensure_audio_files_table() -> None:
    global _AUDIO_FILES_TABLE_READY
    if _AUDIO_FILES_TABLE_READY:
        return
    try:
        from src.api.database import get_db
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audio_files (
                    filename   TEXT PRIMARY KEY,
                    owner_id   INTEGER,
                    scope      TEXT NOT NULL DEFAULT 'private',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        _AUDIO_FILES_TABLE_READY = True
    except Exception as e:
        logger.error(f"Failed to ensure audio_files table: {e}")


def _register_audio_file(filename: str, owner_id: Optional[int], scope: str = "private") -> None:
    """Insert a row mapping a generated audio file to its owner + scope."""
    _ensure_audio_files_table()
    try:
        from src.api.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO audio_files (filename, owner_id, scope) VALUES (?, ?, ?)",
                (filename, owner_id, scope),
            )
    except Exception as e:
        # Don't let ownership-tracking failure break TTS — but log loudly.
        logger.error(f"Failed to register audio file {filename}: {e}")


def _audio_file_acl(filename: str) -> Optional[dict]:
    """Look up scope + owner_id for a filename. Returns None if no row."""
    _ensure_audio_files_table()
    try:
        from src.api.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT owner_id, scope FROM audio_files WHERE filename = ?",
                (filename,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            if hasattr(row, "keys"):
                return {"owner_id": row["owner_id"], "scope": row["scope"]}
            return {"owner_id": row[0], "scope": row[1]}
    except Exception as e:
        logger.error(f"Failed to read audio_files ACL for {filename}: {e}")
        return None


# ============================================================================
# STATUS
# ============================================================================

@router.get("/status", response_model=NyayaVaaniStatusResponse)
async def nyayavaani_status():
    """NyayaVaani service health and capabilities."""
    service = _get_service()
    status = await service.get_status()
    return NyayaVaaniStatusResponse(**status)


# ============================================================================
# ASR — Speech to Text
# ============================================================================

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language_hint: str = Form(default=""),
):
    """Transcribe uploaded audio to text."""
    service = _get_service()

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    ext = audio.filename.rsplit(".", 1)[-1] if audio.filename and "." in audio.filename else "webm"
    audio_path = save_upload_audio(audio_bytes, service.config.audio_upload_dir, ext)

    try:
        hint = language_hint if language_hint and language_hint in SUPPORTED_LANGUAGES else None
        result = await service.asr.transcribe(audio_path, language_hint=hint)
        return TranscriptionResponse(
            text=result.text,
            language=result.language,
            confidence=result.confidence,
            method=result.method,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# ============================================================================
# TTS — Text to Speech
# ============================================================================

@router.post("/synthesize", response_model=TTSResponse)
async def synthesize_speech(
    request: TTSRequest,
    current_user: dict = Depends(_get_current_user()),
):
    """Convert text to speech audio."""
    service = _get_service()

    try:
        result = await service.tts.synthesize(
            text=request.text,
            language_code=request.language,
            voice_gender=request.voice_gender,
        )
        filename = result.audio_path.name
        # Register the file with its owner so /audio/<filename> can ACL-check.
        _register_audio_file(
            filename=filename,
            owner_id=current_user.get("id") if current_user else None,
            scope="private",
        )
        return TTSResponse(
            audio_url=f"/api/v1/nyayavaani/audio/{filename}",
            duration_seconds=result.duration_seconds,
            language=result.language,
            method=result.method,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"TTS failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


# ============================================================================
# INTENT CLASSIFICATION
# ============================================================================

@router.post("/classify-intent", response_model=IntentResponse)
async def classify_intent(request: IntentClassifyRequest):
    """Classify user intent from text."""
    service = _get_service()

    try:
        result = await service.intent.classify_intent(
            text=request.text, language=request.language
        )
        return IntentResponse(
            intent=result.intent,
            confidence=result.confidence,
            entities=result.entities,
            language=result.language,
        )
    except Exception as e:
        logger.error(f"Intent classification failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Intent classification unavailable")


# ============================================================================
# VOICE GRIEVANCE (Full Flow)
# ============================================================================

@router.post("/voice-grievance", response_model=VoiceGrievanceResponse)
async def submit_voice_grievance(
    request: VoiceGrievanceSubmitRequest,
    current_user: dict = Depends(_get_current_user()),
):
    """Full voice grievance flow: extract → route → submit → acknowledge."""
    service = _get_service()

    try:
        # 1. Extract structured grievance data
        grievance_data = await service.intent.extract_grievance_from_voice(
            text=request.transcription, language=request.language
        )

        # 2. Route using the grievance system. CRITICAL: do NOT silently
        # fall back to ("general", "medium") on classification failure —
        # that hides routing bugs and dumps high-priority grievances into
        # the wrong queue. Surface a 422 so the citizen UI can prompt them
        # to file via the regular web form.
        try:
            from src.api.dependencies import get_grievance_router as get_gr
            grievance_router_instance = get_gr()
            route_result = grievance_router_instance.route_grievance(
                grievance_text=grievance_data.description,
                language=request.language,
            )
            if not route_result:
                raise RuntimeError("router returned None")

            department = (
                route_result.department.value
                if hasattr(route_result.department, "value")
                else str(route_result.department)
            )
            priority = (
                route_result.priority.value
                if hasattr(route_result.priority, "value")
                else str(route_result.priority)
            )
            category = (
                route_result.category.value
                if hasattr(route_result.category, "value")
                else str(route_result.category)
            )
        except Exception as route_err:
            logger.error(f"Voice grievance routing failed: {route_err}")
            raise HTTPException(
                status_code=422,
                detail=(
                    "We couldn't auto-route your voice grievance. "
                    "Please file via the web form so a human officer can assign it."
                ),
            )

        # 3. Save to database
        grievance_id = f"GR-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"

        try:
            from src.api.database import get_db
            with get_db() as db:
                cursor = db.cursor()
                cursor.execute(
                    """INSERT INTO grievances
                       (grievance_id, citizen_name, citizen_phone, citizen_location,
                        title, description, category, department, priority, status, language, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, datetime('now'))""",
                    (
                        grievance_id,
                        request.citizen_name or "Voice Citizen",
                        request.citizen_phone or "",
                        request.citizen_location or grievance_data.citizen_location or "",
                        grievance_data.title,
                        grievance_data.description,
                        category,
                        department,
                        priority,
                        request.language,
                    ),
                )
        except Exception as db_err:
            logger.error(f"Failed to save grievance to DB: {db_err}")

        # 4. Generate acknowledgement
        ack_text = None
        ack_audio_url = None
        try:
            ack_text = await service.cross_lingual.generate_grievance_acknowledgement(
                grievance_text=grievance_data.description,
                grievance_id=grievance_id,
                department=department,
                language=request.language,
            )
            if ack_text:
                tts_result = await service.tts.synthesize(
                    text=ack_text, language_code=request.language
                )
                # Acknowledgement audio is PII-bearing (mentions grievance ID
                # and citizen-specific details). Register as private to the
                # caller so /audio/<filename> ACL-checks against owner.
                _register_audio_file(
                    filename=tts_result.audio_path.name,
                    owner_id=current_user.get("id") if current_user else None,
                    scope="private",
                )
                ack_audio_url = f"/api/v1/nyayavaani/audio/{tts_result.audio_path.name}"
        except Exception as e:
            logger.warning(f"Acknowledgement generation failed: {e}")

        return VoiceGrievanceResponse(
            grievance_id=grievance_id,
            title=grievance_data.title,
            description=grievance_data.description,
            category=category,
            department=department,
            priority=priority,
            language=request.language,
            acknowledgement_text=ack_text,
            acknowledgement_audio_url=ack_audio_url,
        )

    except Exception as e:
        logger.error(f"Voice grievance submission failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Voice grievance failed: {str(e)}")


# ============================================================================
# AUDIO FILE SERVING
# ============================================================================

@router.get("/audio/{filename}")
async def serve_audio(
    filename: str,
    current_user: dict = Depends(_get_current_user()),
):
    """Serve generated audio files. Requires authentication; enforces ACL.

    Without this guard any authenticated user could iterate filenames and
    listen to other citizens' grievance acknowledgements (PII leak).
    """
    # Path-traversal hardening: reject parent refs, separators, and any
    # absolute-prefix indicators (Windows drive letters, leading slash).
    if (
        ".." in filename
        or "/" in filename
        or "\\" in filename
        or filename.startswith(("~", "."))
        or (len(filename) > 1 and filename[1] == ":")  # e.g. "C:..."
    ):
        raise HTTPException(status_code=400, detail="Invalid filename")

    service = _get_service()
    audio_path = service.config.audio_output_dir / filename

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    # ACL: public scope OR owner OR admin.
    acl = _audio_file_acl(filename)
    user_id = current_user.get("id") if current_user else None
    user_role = current_user.get("role") if current_user else None

    if acl is None:
        # No row — file is older than the audit table or was created without
        # registration. Default-deny for non-admins to keep the policy strict.
        if user_role != "admin":
            raise HTTPException(status_code=403, detail="Audio access denied")
    else:
        scope = acl.get("scope") or "private"
        owner_id = acl.get("owner_id")
        if not (
            scope == "public"
            or (owner_id is not None and owner_id == user_id)
            or user_role == "admin"
        ):
            raise HTTPException(status_code=403, detail="Audio access denied")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        filename=filename,
    )


# ============================================================================
# NOTICE & SCHEME TTS
# ============================================================================

@router.get("/notice/{notice_id}/audio")
async def get_notice_audio(notice_id: str, language: str = "hi"):
    """Generate TTS audio for a published notice, translated to the requested language."""
    service = _get_service()

    # Check cache first
    cache_path = service.config.audio_output_dir / f"notice_{notice_id}_{language}.wav"
    if cache_path.exists():
        return FileResponse(path=str(cache_path), media_type="audio/wav")

    # Fetch notice from DB
    from src.api.database import get_db
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute(
            "SELECT subject, body, scheme_name, language FROM notices WHERE notice_id = ? AND status = 'published'",
            (notice_id,),
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Notice not found")

    notice = dict(row)
    original_lang = notice.get("language", "en") or "en"
    subject = notice["subject"]
    body = notice["body"]
    text = f"{subject}. {body}"

    # Translate if requested language differs from notice's original language
    if original_lang != language:
        try:
            result = await service.cross_lingual.translate_and_adapt(
                text=text,
                source_lang=original_lang,
                target_lang=language,
                content_type="notice",
            )
            text = result.translated_text
            # Also translate subject for the intro
            subj_result = await service.cross_lingual.translate_and_adapt(
                text=subject,
                source_lang=original_lang,
                target_lang=language,
                content_type="notice",
            )
            subject = subj_result.translated_text
        except Exception as e:
            logger.warning(f"Notice translation to {language} failed, using original: {e}")

    # Generate intro + body TTS
    try:
        intro = await service.cross_lingual.generate_voice_notice_intro(
            notice_subject=subject,
            scheme_name=notice.get("scheme_name", ""),
            language=language,
        )
        full_text = f"{intro} {text}" if intro else text
    except Exception:
        full_text = text

    tts_result = await service.tts.synthesize(text=full_text, language_code=language)

    # Cache
    import shutil
    shutil.copy2(str(tts_result.audio_path), str(cache_path))

    # Notices are public — any citizen can stream them. Register both the
    # raw TTS file and the cached copy so /audio/<name> can ACL-pass.
    _register_audio_file(filename=tts_result.audio_path.name, owner_id=None, scope="public")
    _register_audio_file(filename=cache_path.name, owner_id=None, scope="public")

    return FileResponse(path=str(cache_path), media_type="audio/wav")


@router.get("/schemes")
async def list_nyayavaani_schemes():
    """Return all active schemes with IDs, names, departments, and short descriptions."""
    from src.api.database import get_db

    try:
        with get_db() as db:
            cursor = db.cursor()
            # Use DISTINCT ON (Postgres) / subquery (SQLite) to collapse dupes.
            # Original used GROUP BY sm.scheme_id which works in SQLite (lax)
            # but Postgres requires every non-aggregate column in GROUP BY.
            # Subquery approach is dialect-agnostic.
            cursor.execute("""
                SELECT
                    sm.scheme_id,
                    sm.scheme_name,
                    COALESCE(s.department, sm.department, 'Government of India') AS department,
                    COALESCE(sm.description, s.eligibility, '') AS short_description,
                    s.benefits,
                    s.process
                FROM schemes_metadata sm
                LEFT JOIN (
                    SELECT scheme_name,
                           MAX(department)  AS department,
                           MAX(eligibility) AS eligibility,
                           MAX(benefits)    AS benefits,
                           MAX(process)     AS process
                    FROM schemes
                    GROUP BY scheme_name
                ) s ON LOWER(sm.scheme_name) = LOWER(s.scheme_name)
                WHERE sm.status = 'active'
                ORDER BY sm.scheme_name
            """)
            rows = cursor.fetchall()

        schemes = []
        for row in rows:
            r = dict(row)
            desc = r.get("short_description") or ""
            if not desc and r.get("benefits"):
                desc = str(r["benefits"])
            if not desc and r.get("process"):
                # Extract a meaningful snippet from the full document text
                proc = str(r["process"]).strip()
                # Skip BOM and try to find the overview/description part
                proc = proc.lstrip('\ufeff').strip()
                desc = proc
            short_desc = desc[:200].rstrip() + ("..." if len(desc) > 200 else "")

            schemes.append({
                "scheme_id": r["scheme_id"],
                "scheme_name": r["scheme_name"],
                "department": r["department"],
                "short_description": short_desc,
            })

        return {"schemes": schemes, "count": len(schemes)}

    except Exception as e:
        logger.error(f"List NyayaVaani schemes failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch schemes")


@router.get("/scheme/{scheme_id}/audio")
async def get_scheme_audio(scheme_id: str, language: str = "hi"):
    """Generate high-quality TTS audio for a scheme using AI summarizer."""
    service = _get_service()

    cache_path = service.config.audio_output_dir / f"scheme_summary_{scheme_id}_{language}.wav"
    if cache_path.exists():
        return FileResponse(path=str(cache_path), media_type="audio/wav")

    # Step 1: Look up scheme name
    from src.api.database import get_db
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute(
            "SELECT scheme_name FROM schemes_metadata WHERE scheme_id = ? AND status = 'active'",
            (scheme_id,),
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Scheme not found")

    scheme_name = dict(row)["scheme_name"]

    # Step 2: Fetch scheme document text from DB
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute(
            "SELECT eligibility, benefits, process FROM schemes WHERE LOWER(scheme_name) = LOWER(?) LIMIT 1",
            (scheme_name,),
        )
        scheme_row = cursor.fetchone()

    scheme_data = dict(scheme_row) if scheme_row else {}
    eligibility = (scheme_data.get("eligibility") or "").strip()
    benefits = (scheme_data.get("benefits") or "").strip()
    process_text = (scheme_data.get("process") or "").strip()

    # Step 3: Generate AI summary using LLM
    narration_text = None

    # Try RAG summarizer first
    try:
        from src.api.dependencies import get_summarizer
        summarizer = get_summarizer()
        summary = summarizer.summarize(scheme_name=scheme_name, language="en")

        parts = [f"{summary.scheme_name}."]
        if summary.one_line_purpose:
            parts.append(summary.one_line_purpose + ".")
        if summary.eligibility:
            parts.append("Eligibility: " + ". ".join(summary.eligibility[:4]) + ".")
        if summary.benefits:
            parts.append("Key benefits include: " + ". ".join(summary.benefits[:4]) + ".")
        if summary.application_steps:
            parts.append("To apply: " + ". ".join(summary.application_steps[:3]) + ".")
        if summary.contact_info:
            parts.append("For help, contact: " + summary.contact_info + ".")

        narration_text = " ".join(parts)
    except Exception as e:
        logger.warning(f"RAG summarizer failed for scheme audio: {e}")

    # LLM fallback — feed the actual document text to the LLM for summarization
    if not narration_text:
        try:
            from src.api.dependencies import get_answer_generator
            import json as _json

            generator = get_answer_generator()
            # Build context from available scheme data
            doc_context = process_text[:3000] if process_text else ""
            if eligibility:
                doc_context = f"Eligibility: {eligibility}\nBenefits: {benefits}\n\n{doc_context}"

            prompt = (
                f"Based on the following document about the '{scheme_name}' Indian government scheme, "
                f"create a detailed spoken summary in English suitable for audio narration.\n\n"
                f"Document:\n{doc_context}\n\n"
                f"Return ONLY valid JSON in this exact format:\n"
                f'{{"one_line_purpose": "one sentence about the scheme purpose", '
                f'"eligibility": ["criterion 1", "criterion 2", "criterion 3"], '
                f'"benefits": ["benefit 1", "benefit 2", "benefit 3"], '
                f'"application_steps": ["step 1", "step 2", "step 3"], '
                f'"contact_info": "helpline or website"}}'
            )
            response = generator.llm_client.generate(prompt=prompt, temperature=0.3, max_tokens=1000)

            if response and response.get("success"):
                text = response.get("response", "")
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    data = _json.loads(text[start:end])
                    parts = [f"{scheme_name}."]
                    if data.get("one_line_purpose"):
                        parts.append(data["one_line_purpose"] + ".")
                    if data.get("eligibility"):
                        items = data["eligibility"] if isinstance(data["eligibility"], list) else [data["eligibility"]]
                        parts.append("Eligibility: " + ". ".join(items[:4]) + ".")
                    if data.get("benefits"):
                        items = data["benefits"] if isinstance(data["benefits"], list) else [data["benefits"]]
                        parts.append("Key benefits include: " + ". ".join(items[:4]) + ".")
                    if data.get("application_steps"):
                        items = data["application_steps"] if isinstance(data["application_steps"], list) else [data["application_steps"]]
                        parts.append("To apply: " + ". ".join(items[:3]) + ".")
                    if data.get("contact_info"):
                        parts.append("For help, contact: " + data["contact_info"] + ".")
                    narration_text = " ".join(parts)
        except Exception as e:
            logger.warning(f"LLM fallback also failed for scheme audio: {e}")

    # Final fallback: use raw document text
    if not narration_text:
        if process_text:
            narration_text = f"{scheme_name}. {process_text[:1500]}"
        elif eligibility or benefits:
            narration_text = f"{scheme_name}. {eligibility} {benefits}"
        else:
            narration_text = scheme_name

    # Step 3: Translate to target language
    final_text = narration_text
    if language != "en":
        try:
            tr = await service.cross_lingual.translate_and_adapt(
                text=narration_text,
                source_lang="en",
                target_lang=language,
                content_type="scheme",
            )
            final_text = tr.translated_text
        except Exception as e:
            logger.warning(f"Scheme translation to {language} failed, using English: {e}")

    # Step 4: TTS
    result = await service.tts.synthesize(text=final_text, language_code=language)

    import shutil
    shutil.copy2(str(result.audio_path), str(cache_path))

    # Scheme summaries are public.
    _register_audio_file(filename=result.audio_path.name, owner_id=None, scope="public")
    _register_audio_file(filename=cache_path.name, owner_id=None, scope="public")

    return FileResponse(path=str(cache_path), media_type="audio/wav")


# ============================================================================
# SUPPORTED LANGUAGES
# ============================================================================

@router.get("/languages")
async def get_supported_languages():
    """List all supported languages."""
    return {
        "languages": [
            {
                "code": code,
                "english_name": info.english_name,
                "native_name": info.native_name,
                "script": info.script,
            }
            for code, info in SUPPORTED_LANGUAGES.items()
        ],
        "total": len(SUPPORTED_LANGUAGES),
    }
