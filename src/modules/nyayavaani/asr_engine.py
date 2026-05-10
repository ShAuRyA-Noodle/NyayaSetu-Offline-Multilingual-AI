"""
ASR Engine — Speech-to-Text using Sarvam AI (online) or faster-whisper (offline).
"""

import logging
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import httpx

from .config import NyayaVaaniConfig
from .language_registry import SUPPORTED_LANGUAGES
from .audio_utils import convert_to_wav, validate_audio_file

# Stable language detection. Without this seed, langdetect's results vary
# between runs which breaks deterministic transcription routing.
try:
    from langdetect import DetectorFactory
    DetectorFactory.seed = 0
except ImportError:
    # langdetect is optional — Sarvam returns its own language code, and
    # whisper has its own detector. Just log and continue.
    logging.getLogger(__name__).debug("langdetect unavailable — skipping seed")

logger = logging.getLogger(__name__)


def _sarvam_timeout() -> float:
    """Configurable Sarvam ASR timeout. Defaults to 30s."""
    try:
        return float(os.environ.get("SARVAM_TIMEOUT_SEC", "30"))
    except ValueError:
        return 30.0


@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    method: str  # "sarvam" or "whisper"


class ASREngine:
    """Speech-to-text engine with online/offline dual mode."""

    def __init__(self, config: NyayaVaaniConfig):
        self.config = config
        self._whisper_model = None

    async def transcribe(
        self, audio_path: Path, language_hint: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe audio file to text."""
        # Validate
        error = validate_audio_file(
            audio_path, self.config.max_audio_size_bytes, self.config.max_audio_duration_seconds
        )
        if error:
            raise ValueError(error)

        # Try Sarvam API first if online
        if self.config.is_online_mode:
            try:
                return await self._transcribe_sarvam(audio_path, language_hint)
            except Exception as e:
                logger.warning(f"Sarvam ASR failed, falling back to Whisper: {e}")

        # Offline fallback
        return await self._transcribe_whisper(audio_path, language_hint)

    async def _transcribe_sarvam(
        self, audio_path: Path, language_hint: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe using Sarvam AI Saarika/Saaras API (multipart file upload).

        language_hint policy: if the caller explicitly supplies a supported
        language, honour it. Otherwise we let Sarvam auto-detect rather than
        biasing every transcription to hi-IN — that mis-routed Tamil and
        Bengali speakers in the field.
        """
        if language_hint and language_hint in SUPPORTED_LANGUAGES:
            lang_code = SUPPORTED_LANGUAGES[language_hint].sarvam_asr_code
        else:
            lang_code = "auto"

        audio_bytes = audio_path.read_bytes()
        filename = audio_path.name

        async with httpx.AsyncClient(timeout=_sarvam_timeout()) as client:
            response = await client.post(
                f"{self.config.sarvam_base_url}/speech-to-text",
                headers={
                    "api-subscription-key": self.config.sarvam_api_key,
                },
                files={
                    "file": (filename, audio_bytes, "audio/webm"),
                },
                data={
                    "language_code": lang_code,
                    "model": "saarika:v2.5",
                },
            )
            response.raise_for_status()
            data = response.json()

        # Sarvam response: {"transcript": "...", "language_code": "hi-IN", ...}
        transcript = data.get("transcript", "")
        if not transcript:
            # Fallback to other possible response keys
            transcript = data.get("text", "")

        if not transcript:
            raise RuntimeError(f"Sarvam ASR returned empty transcript. Response: {data}")

        detected_lang = language_hint or "hi"
        return TranscriptionResult(
            text=transcript.strip(),
            language=detected_lang,
            confidence=0.9,
            method="sarvam",
        )

    async def _transcribe_whisper(
        self, audio_path: Path, language_hint: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe using faster-whisper (offline)."""
        import asyncio

        def _run_whisper():
            if self._whisper_model is None:
                try:
                    from faster_whisper import WhisperModel
                    self._whisper_model = WhisperModel(
                        self.config.whisper_model_size,
                        compute_type=self.config.whisper_compute_type,
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to load Whisper model: {e}")

            # Convert to WAV for best compatibility
            wav_path = convert_to_wav(audio_path, self.config.audio_output_dir)

            whisper_lang = None
            if language_hint and language_hint in SUPPORTED_LANGUAGES:
                whisper_lang = SUPPORTED_LANGUAGES[language_hint].whisper_code

            segments, info = self._whisper_model.transcribe(
                str(wav_path),
                beam_size=5,
                language=whisper_lang,
            )

            text_parts = [seg.text for seg in segments]
            full_text = " ".join(text_parts).strip()
            detected = info.language if hasattr(info, "language") else (language_hint or "hi")

            return TranscriptionResult(
                text=full_text,
                language=detected,
                confidence=round(info.language_probability, 2) if hasattr(info, "language_probability") else 0.7,
                method="whisper",
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run_whisper)
