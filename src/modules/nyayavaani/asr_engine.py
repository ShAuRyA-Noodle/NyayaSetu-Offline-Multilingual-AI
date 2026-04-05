"""
ASR Engine — Speech-to-Text using Sarvam AI (online) or faster-whisper (offline).
"""

import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import httpx

from .config import NyayaVaaniConfig
from .language_registry import SUPPORTED_LANGUAGES
from .audio_utils import convert_to_wav, validate_audio_file

logger = logging.getLogger(__name__)


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
        """Transcribe using Sarvam AI Saarika/Saaras API (multipart file upload)."""
        lang_code = "hi-IN"
        if language_hint and language_hint in SUPPORTED_LANGUAGES:
            lang_code = SUPPORTED_LANGUAGES[language_hint].sarvam_asr_code

        audio_bytes = audio_path.read_bytes()
        filename = audio_path.name

        async with httpx.AsyncClient(timeout=30.0) as client:
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
