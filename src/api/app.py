"""
NyayaSetu FastAPI Application

Production-grade REST API for rural Indian governance services.
"""

import os
import time
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .errors import (
    NyayaSetuAPIError, nyayasetu_error_handler,
    validation_error_handler, general_exception_handler,
    http_exception_handler,
)
from .dependencies import initialize_services, shutdown_services
from .middleware import (
    RequestLoggingMiddleware, SecurityHeadersMiddleware, RateLimitMiddleware,
)
from .database import init_core_tables
from .migrations.runner import run_all_pending
from .sla_service import start_sla_scheduler, stop_sla_scheduler

# Route modules
from .auth_routes import router as auth_router
from .core_routes import router as core_router
from .scheme_routes import router as scheme_router
from .grievance_routes import router as grievance_router
from .notice_routes import router as notice_router
from .admin_routes import router as admin_router
from src.modules.nyayavaani.router import router as nyayavaani_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# APPLICATION LIFECYCLE
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("=" * 80)
    logger.info("NyayaSetu API - Starting up...")
    logger.info("=" * 80)

    try:
        # Suppress asyncio ConnectionResetError spam on Windows
        loop = asyncio.get_event_loop()
        _default_handler = loop.get_exception_handler()

        def _quiet_exception_handler(loop, context):
            exc = context.get("exception")
            if exc and isinstance(exc, ConnectionResetError):
                return  # Silently ignore connection resets
            if _default_handler:
                _default_handler(loop, context)
            else:
                loop.default_exception_handler(context)

        loop.set_exception_handler(_quiet_exception_handler)

        # Initialize database tables and run migrations
        init_core_tables()
        run_all_pending()

        # Initialize ML services
        await initialize_services()

        # Start SLA breach scheduler (5-min interval, advisory-lock leader election)
        try:
            start_sla_scheduler()
        except Exception as exc:
            logger.warning(f"SLA scheduler failed to start: {exc}")

        # Start daily scheme-refresh scheduler (re-scrapes myScheme.gov.in + rebuilds FAISS)
        try:
            from src.data_pipeline.refresh_scheduler import start_scheme_refresh_scheduler
            start_scheme_refresh_scheduler()
        except Exception as exc:
            logger.warning(f"Scheme refresh scheduler failed to start: {exc}")

        app.state.startup_time = time.time()
        app.state.request_count = 0
        app.state.requests_by_endpoint = {}

        logger.info("NyayaSetu API is ready! Visit /docs for documentation")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    yield

    logger.info("NyayaSetu API - Shutting down...")
    try:
        stop_sla_scheduler()
    except Exception as exc:
        logger.warning(f"SLA scheduler failed to stop cleanly: {exc}")
    try:
        from src.data_pipeline.refresh_scheduler import stop_scheme_refresh_scheduler
        stop_scheme_refresh_scheduler()
    except Exception as exc:
        logger.warning(f"Scheme refresh scheduler failed to stop cleanly: {exc}")
    await shutdown_services()
    logger.info("All services shut down successfully")


# ============================================================================
# CREATE APPLICATION
# ============================================================================

_ENV = os.environ.get("ENV", "development").strip().lower()
_IS_PROD = _ENV == "production"

# In production, hide /docs, /redoc, and the OpenAPI schema entirely.
_docs_url = None if _IS_PROD else "/docs"
_redoc_url = None if _IS_PROD else "/redoc"
_openapi_url = None if _IS_PROD else "/openapi.json"

app = FastAPI(
    title="NyayaSetu API",
    description=(
        "# NyayaSetu Governance Platform API\n\n"
        "Production-grade REST API for rural Indian governance services.\n\n"
        "## Features\n"
        "- **RAG Q&A**: Ask questions about government schemes\n"
        "- **Scheme Summarizer**: Get structured summaries\n"
        "- **Notice Drafter**: Generate official notices\n"
        "- **NyayaVaani**: Voice-native cross-lingual governance\n"
        "- **Grievance Router**: Route citizen complaints\n"
        "- **Admin Upload**: Upload new schemes\n"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    openapi_tags=[
        {"name": "Health", "description": "Health checks and monitoring"},
        {"name": "Authentication", "description": "User authentication"},
        {"name": "RAG Q&A", "description": "Question answering using RAG"},
        {"name": "Scheme Summarizer", "description": "Scheme summarization"},
        {"name": "Notice Drafter", "description": "Notice generation"},
        {"name": "NyayaVaani", "description": "Voice-native cross-lingual governance"},
        {"name": "Grievances", "description": "Grievance management"},
        {"name": "Statistics", "description": "API usage statistics"},
        {"name": "Admin", "description": "Admin operations"},
    ],
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS configuration.
# - In production (ENV=production): ONLY the entries from CORS_ORIGINS env
#   var are allowed. Localhost, app://, and file:// origins are dropped.
# - Otherwise: dev defaults (localhost + Electron) plus any CORS_ORIGINS
#   entries are allowed.
_cors_env = os.environ.get("CORS_ORIGINS", "").strip()
_cors_extra = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else []

if _IS_PROD:
    _cors_origins = list(dict.fromkeys(_cors_extra))
    if not _cors_origins:
        logger.warning(
            "CORS: production mode but CORS_ORIGINS is empty. No browser origin will be allowed."
        )
else:
    _cors_dev_base = [
        "http://localhost:5173",
        "http://localhost:8001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8001",
        "app://.",
        "file://",
    ]
    _cors_origins = list(dict.fromkeys(_cors_dev_base + _cors_extra))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Accept-Language"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, default_limit=100, window_seconds=60)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

app.add_exception_handler(NyayaSetuAPIError, nyayasetu_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
# Catch raw HTTPException (FastAPI + Starlette flavors) so str(e) leaks
# from `raise HTTPException(500, str(e))` patterns are handled uniformly.
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# ============================================================================
# REGISTER ROUTERS
# ============================================================================

app.include_router(auth_router)
app.include_router(core_router)
app.include_router(scheme_router)
app.include_router(grievance_router)
app.include_router(notice_router)
app.include_router(admin_router)
app.include_router(nyayavaani_router)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8001, reload=True)
