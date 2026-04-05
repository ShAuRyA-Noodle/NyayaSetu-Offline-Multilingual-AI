"""
NyayaVaani startup — health checks, model verification, background cleanup.
"""

import asyncio
import logging
from typing import Optional

import httpx

from .config import NyayaVaaniConfig
from .asr_engine import ASREngine
from .tts_engine import TTSEngine
from .cross_lingual_engine import CrossLingualEngine
from .intent_engine import IntentEngine
from .audio_utils import cleanup_old_audio

logger = logging.getLogger(__name__)


class NyayaVaaniService:
    """Top-level service that owns all NyayaVaani engines."""

    def __init__(self, config: Optional[NyayaVaaniConfig] = None):
        self.config = config or NyayaVaaniConfig()
        self.asr: Optional[ASREngine] = None
        self.tts: Optional[TTSEngine] = None
        self.cross_lingual: Optional[CrossLingualEngine] = None
        self.intent: Optional[IntentEngine] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._ollama_models: list[str] = []
        self._sarvam_healthy = False

    async def initialize(self) -> None:
        """Initialize all engines and run health checks."""
        logger.info("Initializing NyayaVaani service...")
        self.config.validate()

        # Initialize engines
        self.asr = ASREngine(self.config)
        self.tts = TTSEngine(self.config)
        self.cross_lingual = CrossLingualEngine(self.config)
        self.intent = IntentEngine(self.config)

        # Check Sarvam API health
        if self.config.is_online_mode:
            await self._check_sarvam_health()

        # Check Ollama models
        await self._check_ollama_models()

        # Start background cleanup
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

        logger.info("NyayaVaani service initialized successfully")

    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        cleanup_old_audio(self.config.audio_upload_dir, max_age_hours=0)
        cleanup_old_audio(self.config.audio_output_dir, max_age_hours=0)
        logger.info("NyayaVaani service shut down")

    async def get_status(self) -> dict:
        """Get service status."""
        return {
            "status": "healthy",
            "mode": "online" if self.config.is_online_mode else "offline",
            "sarvam_api": self._sarvam_healthy,
            "ollama_available": len(self._ollama_models) > 0,
            "ollama_models": self._ollama_models,
            "supported_languages": 12,
            "audio_cleanup_enabled": True,
        }

    async def _check_sarvam_health(self) -> None:
        """Test Sarvam API connectivity."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.config.sarvam_base_url}/speech-to-text",
                    headers={"api-subscription-key": self.config.sarvam_api_key},
                )
                # Even a 405 means the API is reachable
                self._sarvam_healthy = response.status_code in (200, 405, 422)
                if self._sarvam_healthy:
                    logger.info("Sarvam AI API is reachable")
                else:
                    logger.warning(f"Sarvam API returned {response.status_code}")
        except Exception as e:
            logger.warning(f"Sarvam API unreachable: {e}. Using offline mode.")
            self._sarvam_healthy = False

    async def _check_ollama_models(self) -> None:
        """Check which Ollama models are available."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.config.ollama_base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    self._ollama_models = [
                        m["name"] for m in data.get("models", [])
                    ]
                    # Check for required models
                    has_sarvam_m = any(
                        self.config.sarvam_m_model in m for m in self._ollama_models
                    )
                    if has_sarvam_m:
                        logger.info(f"Ollama model '{self.config.sarvam_m_model}' available")
                    else:
                        logger.warning(
                            f"Ollama model '{self.config.sarvam_m_model}' not found. "
                            f"Available: {self._ollama_models}"
                        )
        except Exception as e:
            logger.warning(f"Ollama not reachable: {e}")
            self._ollama_models = []

    async def _periodic_cleanup(self) -> None:
        """Clean up old audio files every 30 minutes."""
        while True:
            try:
                await asyncio.sleep(1800)
                cleanup_old_audio(self.config.audio_upload_dir, max_age_hours=1)
                cleanup_old_audio(self.config.audio_output_dir, max_age_hours=2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Audio cleanup error: {e}")
