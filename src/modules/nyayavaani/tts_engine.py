"""
TTS Engine — Text-to-Speech using Sarvam AI Bulbul (online) or pyttsx3 (offline).
"""

import logging
import base64
import uuid
import time
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import httpx

from .config import NyayaVaaniConfig
from .language_registry import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)


@dataclass
class SynthesisResult:
    audio_path: Path
    duration_seconds: float
    language: str
    method: str  # "sarvam" or "pyttsx3"


class TTSEngine:
    """Text-to-speech engine with online/offline dual mode."""

    def __init__(self, config: NyayaVaaniConfig):
        self.config = config

    async def synthesize(
        self,
        text: str,
        language_code: str = "hi",
        voice_gender: str = "female",
    ) -> SynthesisResult:
        """Synthesize speech from text."""
        # Preprocess text
        clean_text = self._preprocess_text(text)
        if not clean_text:
            raise ValueError("Text is empty after preprocessing")

        # Try Sarvam API first
        if self.config.is_online_mode:
            try:
                return await self._synthesize_sarvam(clean_text, language_code, voice_gender)
            except Exception as e:
                logger.warning(f"Sarvam TTS failed, falling back to pyttsx3: {e}")

        # Offline fallback
        return await self._synthesize_pyttsx3(clean_text, language_code)

    async def _synthesize_sarvam(
        self, text: str, language_code: str, voice_gender: str
    ) -> SynthesisResult:
        """Synthesize using Sarvam AI Bulbul v3 API."""
        tts_lang = "hi-IN"
        if language_code in SUPPORTED_LANGUAGES:
            tts_lang = SUPPORTED_LANGUAGES[language_code].sarvam_tts_code

        # Sarvam Bulbul v3 voice selection
        speaker = "priya" if voice_gender == "female" else "shubh"

        # Chunk text if too long (Sarvam limit 2500 chars for v3)
        chunks = self._chunk_text(text, max_chars=2000)
        all_audio = bytearray()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for chunk in chunks:
                response = await client.post(
                    f"{self.config.sarvam_base_url}/text-to-speech",
                    headers={
                        "api-subscription-key": self.config.sarvam_api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": chunk,
                        "target_language_code": tts_lang,
                        "model": "bulbul:v3",
                        "speaker": speaker,
                        "speech_sample_rate": 22050,
                        "output_audio_codec": "wav",
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Sarvam returns: {"audios": ["base64_encoded_audio"]}
                audios = data.get("audios", [])
                if audios and audios[0]:
                    all_audio.extend(base64.b64decode(audios[0]))

        if not all_audio:
            raise RuntimeError("Sarvam TTS returned empty audio")

        # Save audio
        self.config.audio_output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.config.audio_output_dir / f"tts_{int(time.time())}_{uuid.uuid4().hex[:6]}.wav"
        output_path.write_bytes(bytes(all_audio))

        duration = len(all_audio) / (22050 * 2)  # 22050 Hz, 16-bit mono
        return SynthesisResult(
            audio_path=output_path,
            duration_seconds=round(duration, 1),
            language=language_code,
            method="sarvam",
        )

    async def _synthesize_pyttsx3(self, text: str, language_code: str) -> SynthesisResult:
        """Synthesize using pyttsx3 (offline fallback)."""
        import asyncio

        def _run_pyttsx3():
            import pyttsx3
            engine = pyttsx3.init()

            # Set rate and volume
            engine.setProperty("rate", 150)
            engine.setProperty("volume", 0.9)

            self.config.audio_output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.config.audio_output_dir / f"tts_{int(time.time())}_{uuid.uuid4().hex[:6]}.wav"

            engine.save_to_file(text, str(output_path))
            engine.runAndWait()

            duration = len(text) / 15  # ~15 chars per second rough estimate
            return SynthesisResult(
                audio_path=output_path,
                duration_seconds=round(duration, 1),
                language=language_code,
                method="pyttsx3",
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run_pyttsx3)

    @staticmethod
    def _preprocess_text(text: str) -> str:
        """Clean text for TTS."""
        # Remove markdown
        text = re.sub(r"[#*_`~]", "", text)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 2000) -> list[str]:
        """Split text into chunks at sentence boundaries."""
        if len(text) <= max_chars:
            return [text]

        chunks = []
        current = ""
        sentences = re.split(r"(?<=[।.!?])\s+", text)

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= max_chars:
                current = f"{current} {sentence}".strip()
            else:
                if current:
                    chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return chunks or [text[:max_chars]]
