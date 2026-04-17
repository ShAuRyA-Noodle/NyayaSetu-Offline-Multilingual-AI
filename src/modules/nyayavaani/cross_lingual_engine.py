"""
Cross-Lingual Engine — Translation using Sarvam Translate API (online) + LLM fallback.
"""

import json
import logging
import re
from dataclasses import dataclass

import httpx

from .config import NyayaVaaniConfig
from .language_registry import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    content_type: str
    method: str


class CrossLingualEngine:
    """Cross-lingual translation and cultural adaptation engine."""

    def __init__(self, config: NyayaVaaniConfig):
        self.config = config

    async def translate_and_adapt(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        content_type: str = "general",
    ) -> TranslationResult:
        """Translate text with cultural adaptation."""
        # Try Sarvam Translate API first (online)
        if self.config.is_online_mode:
            try:
                translated = await self._translate_sarvam(text, source_lang, target_lang, content_type)
                return TranslationResult(
                    original_text=text,
                    translated_text=translated,
                    source_language=source_lang,
                    target_language=target_lang,
                    content_type=content_type,
                    method="sarvam-translate",
                )
            except Exception as e:
                logger.warning(f"Sarvam Translate failed, falling back to LLM: {e}")

        # Fallback to LLM (Groq or Ollama depending on config)
        translated = await self._translate_llm(text, source_lang, target_lang, content_type)
        return TranslationResult(
            original_text=text,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
            content_type=content_type,
            method="llm-fallback",
        )

    async def _translate_sarvam(
        self, text: str, source_lang: str, target_lang: str, content_type: str
    ) -> str:
        """Translate using Sarvam Translate API (Mayura model)."""
        src_code = "en-IN"
        tgt_code = "hi-IN"
        if source_lang in SUPPORTED_LANGUAGES:
            src_code = SUPPORTED_LANGUAGES[source_lang].sarvam_tts_code  # BCP-47 format
        if target_lang in SUPPORTED_LANGUAGES:
            tgt_code = SUPPORTED_LANGUAGES[target_lang].sarvam_tts_code

        # Map content_type to Sarvam mode
        mode_map = {
            "notice": "formal",
            "grievance": "formal",
            "scheme": "modern-colloquial",
            "general": "modern-colloquial",
        }
        mode = mode_map.get(content_type, "formal")

        # Sarvam translate has 1000 char limit per request
        if len(text) > 1000:
            # Chunk and translate
            chunks = self._chunk_text(text, max_chars=900)
            translated_parts = []
            for chunk in chunks:
                result = await self._sarvam_translate_request(chunk, src_code, tgt_code, mode)
                translated_parts.append(result)
            return " ".join(translated_parts)

        return await self._sarvam_translate_request(text, src_code, tgt_code, mode)

    async def _sarvam_translate_request(
        self, text: str, src_code: str, tgt_code: str, mode: str
    ) -> str:
        """Single Sarvam translate API call."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.config.sarvam_base_url}/translate",
                headers={
                    "api-subscription-key": self.config.sarvam_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "input": text,
                    "source_language_code": src_code,
                    "target_language_code": tgt_code,
                    "mode": mode,
                    "model": "mayura:v1",
                    "enable_preprocessing": True,
                },
            )
            response.raise_for_status()
            data = response.json()

        translated = data.get("translated_text", "")
        if not translated:
            raise RuntimeError(f"Sarvam Translate returned empty result. Response: {data}")
        return translated

    async def _translate_llm(
        self, text: str, source_lang: str, target_lang: str, content_type: str
    ) -> str:
        """Translate using the shared LLM client (Groq or Ollama)."""
        source_name = SUPPORTED_LANGUAGES.get(source_lang, SUPPORTED_LANGUAGES["en"]).english_name
        target_name = SUPPORTED_LANGUAGES.get(target_lang, SUPPORTED_LANGUAGES["hi"]).english_name
        target_native = SUPPORTED_LANGUAGES.get(target_lang, SUPPORTED_LANGUAGES["hi"]).native_name

        style_instructions = self._get_style_instructions(content_type)

        prompt = f"""Translate the following text from {source_name} to {target_name} ({target_native}).

{style_instructions}

IMPORTANT: Return ONLY a JSON object with this exact format:
{{"translated_text": "your translation here"}}

Text to translate:
{text}"""

        return await self._call_llm(prompt)

    async def generate_grievance_acknowledgement(
        self,
        grievance_text: str,
        grievance_id: str,
        department: str,
        language: str = "hi",
    ) -> str:
        """Generate a personalized grievance acknowledgement in the target language."""
        lang_name = SUPPORTED_LANGUAGES.get(language, SUPPORTED_LANGUAGES["hi"]).native_name

        prompt = f"""Generate a brief, empathetic grievance acknowledgement in {lang_name}.

Grievance ID: {grievance_id}
Department: {department}
Citizen's complaint: {grievance_text[:200]}

The acknowledgement should:
1. Thank the citizen for reporting
2. Mention the grievance ID
3. State which department will handle it
4. Be warm and reassuring
5. Be 2-3 sentences max

Return ONLY a JSON object: {{"acknowledgement": "your text here"}}"""

        return await self._call_llm(prompt)

    async def generate_voice_notice_intro(
        self, notice_subject: str, scheme_name: str, language: str = "hi"
    ) -> str:
        """Generate a spoken intro for audio notices."""
        lang_name = SUPPORTED_LANGUAGES.get(language, SUPPORTED_LANGUAGES["hi"]).native_name

        prompt = f"""Generate a brief spoken introduction for a government notice in {lang_name}.

Notice subject: {notice_subject}
Related scheme: {scheme_name}

The intro should be suitable for text-to-speech (natural spoken style, no formatting).
Keep it to 1-2 sentences.

Return ONLY a JSON object: {{"intro": "your text here"}}"""

        return await self._call_llm(prompt)

    async def _call_llm(self, prompt: str, retries: int = 2) -> str:
        """Call the shared LLM client (Groq or Ollama) and parse JSON response."""
        from src.generation.llm_client import create_client

        for attempt in range(retries + 1):
            try:
                client = create_client()
                result = client.generate(
                    prompt=prompt,
                    system_prompt="You are a multilingual translator for Indian government services. Return ONLY valid JSON.",
                    temperature=0.2,
                    max_tokens=500,
                )

                if not result.get("success"):
                    raise RuntimeError(result.get("error", "LLM failed"))

                raw_text = result["response"].strip()

                # Try to parse as JSON
                try:
                    parsed = json.loads(raw_text)
                    for key in ["translated_text", "acknowledgement", "intro"]:
                        if key in parsed:
                            return parsed[key]
                    for v in parsed.values():
                        if isinstance(v, str):
                            return v
                except json.JSONDecodeError:
                    json_match = re.search(r'\{[^}]+\}', raw_text)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            for key in ["translated_text", "acknowledgement", "intro"]:
                                if key in parsed:
                                    return parsed[key]
                        except json.JSONDecodeError:
                            pass
                    return raw_text

            except Exception as e:
                if attempt < retries:
                    logger.warning(f"LLM call failed (attempt {attempt + 1}): {e}")
                    continue
                logger.error(f"LLM call failed after {retries + 1} attempts: {e}")
                raise RuntimeError(f"Cross-lingual engine unavailable: {e}")

        return ""

    @staticmethod
    def _get_style_instructions(content_type: str) -> str:
        styles = {
            "grievance": "Use an empathetic, supportive tone. Simplify legal/bureaucratic terms. Keep sentences short.",
            "notice": "Use formal, official language suitable for government communications. Maintain bureaucratic terminology.",
            "scheme": "Use simple, accessible language. Explain technical terms. Target semi-literate audience.",
            "general": "Use natural, conversational language. Mix in common English terms where appropriate (Hinglish style for Hindi).",
        }
        return styles.get(content_type, styles["general"])

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 900) -> list[str]:
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
