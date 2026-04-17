"""
NyayaSetu FastAPI Application

Production-grade REST API for rural Indian governance services.
"""

import time
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from .errors import (
    NyayaSetuAPIError, nyayasetu_error_handler,
    validation_error_handler, general_exception_handler,
)
from .dependencies import initialize_services, shutdown_services
from .middleware import (
    RequestLoggingMiddleware, SecurityHeadersMiddleware, RateLimitMiddleware,
)
from .database import init_core_tables
from .migrations.runner import run_all_pending

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
    await shutdown_services()
    logger.info("All services shut down successfully")


# ============================================================================
# CREATE APPLICATION
# ============================================================================

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
    docs_url="/docs",
    redoc_url="/redoc",
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

import os as _os

# Base set - always allowed (local dev + Electron)
_cors_base = [
    "http://localhost:5173",
    "http://localhost:8001",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8001",
    "app://.",
    "file://",
]

# Production: additional origins from CORS_ORIGINS env var (comma-separated)
_cors_env = _os.environ.get("CORS_ORIGINS", "").strip()
_cors_extra = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else []

_cors_origins = list(dict.fromkeys(_cors_base + _cors_extra))  # de-duplicate

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
