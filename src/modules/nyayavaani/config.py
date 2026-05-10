"""
NyayaVaani Configuration.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class NyayaVaaniConfig:
    """Configuration for NyayaVaani services."""

    # Sarvam AI
    # SECURITY: Previously this field had a hard-coded API key literal in the
    # source. That literal has been treated as BURNED — it MUST be rotated
    # before any production deploy. The key now comes exclusively from the
    # SARVAM_API_KEY environment variable. Never check secrets into VCS.
    sarvam_api_key: str = field(
        default_factory=lambda: os.environ.get("SARVAM_API_KEY", "")
    )
    sarvam_base_url: str = "https://api.sarvam.ai"

    # Ollama models
    sarvam_m_model: str = field(
        default_factory=lambda: os.getenv("SARVAM_M_MODEL", "mashriram/sarvam-m-tools")
    )
    sarvam_1_model: str = field(
        default_factory=lambda: os.getenv("SARVAM_1_MODEL", "mashriram/sarvam-1")
    )
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )

    # Whisper (offline ASR)
    whisper_model_size: str = "base"
    whisper_compute_type: str = "int8"

    # Audio paths
    audio_upload_dir: Path = field(default_factory=lambda: Path("data/audio/uploads"))
    audio_output_dir: Path = field(default_factory=lambda: Path("data/audio/output"))

    # Limits
    max_audio_size_bytes: int = 25 * 1024 * 1024  # 25 MB
    max_audio_duration_seconds: int = 300  # 5 minutes

    @property
    def is_online_mode(self) -> bool:
        return bool(self.sarvam_api_key and self.sarvam_api_key.startswith("sk_"))

    def validate(self) -> None:
        """Create directories and log configuration."""
        self.audio_upload_dir.mkdir(parents=True, exist_ok=True)
        self.audio_output_dir.mkdir(parents=True, exist_ok=True)

        mode = "ONLINE (Sarvam AI)" if self.is_online_mode else "OFFLINE (local models)"
        logger.info(f"NyayaVaani mode: {mode}")
        logger.info(f"Ollama cross-lingual model: {self.sarvam_m_model}")
        logger.info(f"Audio dirs: uploads={self.audio_upload_dir}, output={self.audio_output_dir}")

        # Production guardrail: missing Sarvam key = no cloud STT/TTS/translate.
        # In production this is a configuration error; warn loudly so ops sees it.
        env = os.environ.get("ENV", "development").lower()
        if not self.sarvam_api_key:
            if env == "production":
                logger.error(
                    "SARVAM_API_KEY is missing in production. Online ASR/TTS/Translate "
                    "will be unavailable and offline fallbacks may not work on this host."
                )
            else:
                logger.warning(
                    "SARVAM_API_KEY not set — running NyayaVaani in OFFLINE mode (dev only)."
                )
