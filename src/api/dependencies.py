"""
API Dependencies

Dependency injection setup and service initialization for FastAPI.
Manages lifecycle of all NyayaSetu services.

Author: NyayaSetu Team
Version: 1.0.0
"""

import sys
import os
from typing import Optional
import logging

# Add src to path
sys.path.insert(0, os.path.abspath('.'))

from src.core.rag_engine import RAGEngine
from src.generation.answer_generator import AnswerGenerator
from src.generation.llm_client import OllamaClient, LLMConfig
from src.modules.summarizer import SchemeSummarizer
from src.modules.notice_drafter import NoticeDrafter
from src.modules.grievance_router import GrievanceRouter
from src.modules.nyayavaani.startup import NyayaVaaniService
from src.modules.nyayavaani.config import NyayaVaaniConfig

from .settings import get_settings  # exposed for other modules

logger = logging.getLogger(__name__)


# ============================================================================
# APPLICATION STATE
# ============================================================================

class AppState:
    """
    Global application state container.
    Holds instances of all services.
    """
    
    def __init__(self):
        self.rag_engine: Optional[RAGEngine] = None
        self.answer_generator: Optional[AnswerGenerator] = None
        self.summarizer: Optional[SchemeSummarizer] = None
        self.notice_drafter: Optional[NoticeDrafter] = None
        self.grievance_router: Optional[GrievanceRouter] = None
        self.nyayavaani: Optional[NyayaVaaniService] = None
        self.initialized = False


# Global state instance
_app_state = AppState()


# ============================================================================
# SERVICE INITIALIZATION
# ============================================================================

async def initialize_services():
    """
    Initialize all NyayaSetu services.
    Called on application startup.
    
    Raises:
        Exception: If any service fails to initialize
    """
    global _app_state

    # Fail fast in production if required env vars are missing/invalid.
    _settings = get_settings()
    _missing = _settings.validate_production()
    if _missing:
        raise RuntimeError(
            f"Missing required env vars in production: {', '.join(_missing)}"
        )

    try:
        logger.info("Initializing services...")

        # 1. Initialize RAG Engine
        logger.info("1/6 Initializing RAG Engine...")
        _app_state.rag_engine = RAGEngine(
            db_path="data/governance.db",
            index_dir="data/",
            model_cache_dir="./models"
        )
        logger.info("✓ RAG Engine initialized")
        
        # 2. Initialize LLM Client and Answer Generator
        logger.info("2/6 Initializing Answer Generator...")
        config = LLMConfig()
        llm_client = OllamaClient(config)

        # Check LLM health
        if not llm_client.health_check():
            logger.warning("⚠ LLM not available - some features will use fallbacks")
        else:
            backend = "Groq Cloud" if llm_client._use_groq else f"Ollama ({config.model})"
            logger.info(f"✓ LLM available: {backend}")
        
        _app_state.answer_generator = AnswerGenerator(llm_client=llm_client)
        logger.info("✓ Answer Generator initialized")
        
        # 3. Initialize Scheme Summarizer
        logger.info("3/6 Initializing Scheme Summarizer...")
        _app_state.summarizer = SchemeSummarizer(
            _app_state.rag_engine,
            _app_state.answer_generator
        )
        logger.info("✓ Scheme Summarizer initialized")
        
        # 4. Initialize Notice Drafter
        logger.info("4/6 Initializing Notice Drafter...")
        _app_state.notice_drafter = NoticeDrafter(
            _app_state.rag_engine,
            _app_state.answer_generator
        )
        logger.info("✓ Notice Drafter initialized")
        
        # 5. Initialize Grievance Router
        logger.info("5/6 Initializing Grievance Router...")
        _app_state.grievance_router = GrievanceRouter(
            _app_state.rag_engine,
            _app_state.answer_generator
        )
        logger.info("✓ Grievance Router initialized")

        # 6. Initialize NyayaVaani
        logger.info("6/6 Initializing NyayaVaani...")
        try:
            nyayavaani_config = NyayaVaaniConfig()
            _app_state.nyayavaani = NyayaVaaniService(nyayavaani_config)
            await _app_state.nyayavaani.initialize()
            logger.info("✓ NyayaVaani initialized")
        except Exception as nve:
            logger.warning(f"⚠ NyayaVaani partially unavailable: {nve}")
            if _app_state.nyayavaani is None:
                _app_state.nyayavaani = NyayaVaaniService(NyayaVaaniConfig())

        _app_state.initialized = True
        logger.info("✓ All services initialized successfully!")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Mark as initialized anyway so auth/grievance/notice routes work
        _app_state.initialized = True
        logger.warning("⚠ Server starting with partial services")


async def shutdown_services():
    """
    Cleanup services on application shutdown.
    Called on application shutdown.
    """
    global _app_state
    
    logger.info("Shutting down services...")
    
    # Clear caches
    if _app_state.summarizer:
        try:
            _app_state.summarizer.clear_cache()
            logger.info("✓ Summarizer cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear summarizer cache: {e}")
    
    if _app_state.grievance_router:
        try:
            _app_state.grievance_router.clear_cache()
            logger.info("✓ Router cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear router cache: {e}")
    
    # Shutdown NyayaVaani
    if _app_state.nyayavaani:
        try:
            await _app_state.nyayavaani.shutdown()
            logger.info("✓ NyayaVaani shut down")
        except Exception as e:
            logger.error(f"Failed to shutdown NyayaVaani: {e}")

    # Close database connections
    if _app_state.rag_engine and hasattr(_app_state.rag_engine, 'db_connection'):
        try:
            _app_state.rag_engine.db_connection.close()
            logger.info("✓ Database connection closed")
        except Exception as e:
            logger.error(f"Failed to close database: {e}")
    
    _app_state.initialized = False
    logger.info("✓ Services shut down successfully")


# ============================================================================
# DEPENDENCY INJECTION FUNCTIONS
# ============================================================================

def get_rag_engine() -> RAGEngine:
    """
    Get RAG Engine instance.
    
    Returns:
        RAGEngine instance
    
    Raises:
        RuntimeError: If services not initialized
    """
    if not _app_state.initialized or not _app_state.rag_engine:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _app_state.rag_engine


def get_answer_generator() -> AnswerGenerator:
    """
    Get Answer Generator instance.
    
    Returns:
        AnswerGenerator instance
    
    Raises:
        RuntimeError: If services not initialized
    """
    if not _app_state.initialized or not _app_state.answer_generator:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _app_state.answer_generator


def get_summarizer() -> SchemeSummarizer:
    """
    Get Scheme Summarizer instance.
    
    Returns:
        SchemeSummarizer instance
    
    Raises:
        RuntimeError: If services not initialized
    """
    if not _app_state.initialized or not _app_state.summarizer:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _app_state.summarizer


def get_notice_drafter() -> NoticeDrafter:
    """
    Get Notice Drafter instance.
    
    Returns:
        NoticeDrafter instance
    
    Raises:
        RuntimeError: If services not initialized
    """
    if not _app_state.initialized or not _app_state.notice_drafter:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _app_state.notice_drafter


def get_grievance_router() -> GrievanceRouter:
    """
    Get Grievance Router instance.
    
    Returns:
        GrievanceRouter instance
    
    Raises:
        RuntimeError: If services not initialized
    """
    if not _app_state.initialized or not _app_state.grievance_router:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _app_state.grievance_router


def get_nyayavaani_service() -> NyayaVaaniService:
    """Get NyayaVaani service instance."""
    if not _app_state.initialized or not _app_state.nyayavaani:
        raise RuntimeError("NyayaVaani not initialized.")
    return _app_state.nyayavaani


def get_app_state() -> AppState:
    """
    Get application state.
    
    Returns:
        AppState instance
    """
    return _app_state
