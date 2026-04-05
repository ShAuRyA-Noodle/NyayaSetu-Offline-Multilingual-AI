"""
Core Routes

Health checks, RAG Q&A, and statistics endpoints.
"""

import time
import logging
from datetime import datetime

from fastapi import APIRouter, Request

from .schemas import (
    HealthResponse, StatsResponse,
    AskRequest, AskResponse,
)
from .errors import (
    ServiceUnavailableError, LLMUnavailableError, map_module_error,
)
from .dependencies import (
    get_rag_engine, get_answer_generator,
    get_summarizer,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Core"])

# Health check cache (60s TTL)
_health_cache = {"status": None, "timestamp": 0}
_HEALTH_CACHE_TTL = 60


# ============================================================================
# HEALTH & MONITORING
# ============================================================================

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Comprehensive health check with cached LLM status."""
    now = time.time()
    components = {}

    try:
        get_rag_engine()
        components["database"] = "healthy"
    except Exception:
        components["database"] = "unhealthy"

    try:
        get_rag_engine()
        components["rag_engine"] = "healthy"
    except Exception:
        components["rag_engine"] = "unhealthy"

    # Cache LLM health check (expensive HTTP call to Ollama)
    if now - _health_cache["timestamp"] < _HEALTH_CACHE_TTL and _health_cache["status"] is not None:
        components["llm"] = _health_cache["status"]
    else:
        try:
            generator = get_answer_generator()
            llm_status = "healthy" if generator.llm_client.health_check() else "unhealthy"
        except Exception:
            llm_status = "unavailable"
        components["llm"] = llm_status
        _health_cache["status"] = llm_status
        _health_cache["timestamp"] = now

    all_healthy = all(s == "healthy" for s in components.values())

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        components=components,
    )


@router.get("/", tags=["Health"])
async def root():
    """Root endpoint."""
    return {
        "name": "NyayaSetu API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/stats", response_model=StatsResponse, tags=["Statistics"])
async def get_stats(request: Request):
    """API statistics."""
    uptime = time.time() - request.app.state.startup_time
    cache_stats = {}

    try:
        summarizer = get_summarizer()
        cache_stats["summarizer"] = summarizer.get_cache_stats()
    except Exception:
        pass

    return StatsResponse(
        total_requests=request.app.state.request_count,
        requests_by_endpoint=request.app.state.requests_by_endpoint,
        cache_stats=cache_stats,
        uptime_seconds=uptime,
    )


# ============================================================================
# RAG Q&A
# ============================================================================

@router.post("/api/v1/ask", response_model=AskResponse, tags=["RAG Q&A"])
async def ask_question(request: AskRequest):
    """Ask questions about government schemes using RAG."""
    try:
        start_time = time.time()

        rag_engine = get_rag_engine()
        generator = get_answer_generator()

        # Try RAG retrieval; fall back to direct LLM if embeddings unavailable
        results = []
        try:
            results = rag_engine.retrieve(query=request.question, top_k=request.top_k)
        except Exception as retrieval_err:
            logger.warning(f"RAG retrieval failed, using direct LLM: {retrieval_err}")

        avg_confidence = 0.0
        sources = []
        context = ""

        if results:
            avg_confidence = sum(score for score, _, _ in results) / len(results)
            context_parts = []
            for score, metadata, explanation in results:
                scheme = metadata.get("scheme_name", "Unknown")
                section = metadata.get("section_type", "general")
                content = metadata.get("content", explanation)
                context_parts.append(f"[{scheme} - {section}]\n{content}")
                sources.append({
                    "scheme": scheme,
                    "section": section,
                    "confidence": round(score, 3),
                })
            context = "\n\n".join(context_parts)

        lang_instruction = "Hindi" if request.language == "hi" else "English"
        if context:
            prompt = (
                f"Answer based on context:\n\nContext:\n{context}\n\n"
                f"Question: {request.question}\n\n"
                f"Provide detailed answer in {lang_instruction}."
            )
        else:
            prompt = (
                f"You are NyayaSetu, an expert on Indian government schemes like PM-KISAN, MGNREGA, PMAY-G.\n\n"
                f"Question: {request.question}\n\n"
                f"Provide a helpful, detailed answer in {lang_instruction}."
            )

        llm_client = generator.llm_client
        response_dict = llm_client.generate(
            prompt=prompt, temperature=0.3, max_tokens=800
        )

        if not response_dict or not response_dict.get("success"):
            raise LLMUnavailableError("Failed to generate answer")

        return AskResponse(
            answer=response_dict.get("response", ""),
            sources=sources,
            confidence=round(avg_confidence, 3),
            language=request.language,
            metadata={
                "total_time_ms": round((time.time() - start_time) * 1000, 2)
            },
        )
    except Exception as e:
        logger.error(f"Ask failed: {e}")
        raise map_module_error(e, "RAG Q&A")
