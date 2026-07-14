"""
Offline translation for the 12 supported languages.

Runs fully on-device by reusing the bundled compact LLM (M3, llama.cpp) with a
strict translation prompt — no cloud, no separate NMT service, no extra model
download. This is the offline counterpart to the cloud Sarvam ``mayura``
translator, and the default when no network is available.

A dedicated NMT backend (e.g. IndicTrans2) can be plugged in behind the same
``translate()`` interface later; the LLM backend is the always-available floor.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

LANG_NAMES = {
    "hi": "Hindi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
    "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam",
    "pa": "Punjabi", "or": "Odia", "as": "Assamese", "en": "English",
}

# Strip common LLM preambles like "Translation:" / "Sure, here is...".
_PREAMBLE = re.compile(
    r"^\s*(translation|here('?s| is)[^:]*|sure[^:]*|output)\s*:?\s*",
    re.IGNORECASE,
)


class OfflineTranslator:
    """LLM-backed offline translator with the same call shape as the cloud one."""

    def __init__(self, llm=None):
        self._llm = llm  # injectable for tests

    def _client(self):
        if self._llm is None:
            from src.generation.local_llm import get_local_llm
            self._llm = get_local_llm()
        return self._llm

    def is_available(self) -> bool:
        try:
            return self._client().is_available()
        except Exception:  # noqa: BLE001
            return False

    def translate(self, text: str, src: str, tgt: str) -> str:
        """
        Translate ``text`` from ``src`` to ``tgt`` (short codes, e.g. 'en','hi').

        Returns the translated string, or the original text on failure (so a
        caller never ends up with an empty message).
        """
        text = (text or "").strip()
        if not text or src == tgt:
            return text
        src_name = LANG_NAMES.get(src, src)
        tgt_name = LANG_NAMES.get(tgt, tgt)

        system = (
            f"You are a professional translator for Indian government services. "
            f"Translate the user's {src_name} text into {tgt_name}. "
            f"Preserve numbers, dates, scheme names and amounts exactly. "
            f"Output ONLY the {tgt_name} translation with no preamble, quotes, "
            f"or explanation."
        )
        result = self._client().generate(
            text, system_prompt=system, temperature=0.1, max_tokens=512
        )
        if not result.get("success"):
            logger.warning("Offline translation failed: %s", result.get("error"))
            return text
        out = result["response"].strip()
        out = _PREAMBLE.sub("", out).strip().strip('"').strip()
        return out or text


_translator: Optional[OfflineTranslator] = None


def get_translator() -> OfflineTranslator:
    global _translator
    if _translator is None:
        _translator = OfflineTranslator()
    return _translator


def translate(text: str, src: str, tgt: str) -> str:
    return get_translator().translate(text, src, tgt)
