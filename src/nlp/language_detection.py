"""
Offline language detection for the 12 supported Indian languages.

Primary engine: **fastText lid.176** (bundled at models/fasttext/lid.176.bin),
a compact, fully-offline model. Because several supported languages share a
Unicode script (Hindi/Marathi → Devanagari; Bengali/Assamese → Bengali), we
combine two signals:

1. **Script narrowing** — the Unicode block of a text's characters restricts the
   candidate languages (unambiguous for Tamil, Telugu, Kannada, Malayalam,
   Gujarati, Odia, Gurmukhi).
2. **fastText** — decides within a shared script (hi vs mr, bn vs as) and gives
   a calibrated confidence, and handles Latin/English.

Degrades gracefully: if fastText or the model is unavailable (e.g. the API
backend's Python has no wheel), it falls back to script detection, then
``langdetect``, then English — so the service never crashes.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SUPPORTED = {"hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa", "or", "as", "en"}

DEFAULT_MODEL_PATH = os.getenv(
    "FASTTEXT_LID_PATH",
    str(Path(__file__).resolve().parents[2] / "models" / "fasttext" / "lid.176.bin"),
)

# Unicode block → candidate supported languages sharing that script.
_SCRIPT_RANGES: List[Tuple[int, int, Tuple[str, ...]]] = [
    (0x0900, 0x097F, ("hi", "mr")),      # Devanagari
    (0x0980, 0x09FF, ("bn", "as")),      # Bengali/Assamese
    (0x0A00, 0x0A7F, ("pa",)),           # Gurmukhi
    (0x0A80, 0x0AFF, ("gu",)),           # Gujarati
    (0x0B00, 0x0B7F, ("or",)),           # Odia
    (0x0B80, 0x0BFF, ("ta",)),           # Tamil
    (0x0C00, 0x0C7F, ("te",)),           # Telugu
    (0x0C80, 0x0CFF, ("kn",)),           # Kannada
    (0x0D00, 0x0D7F, ("ml",)),           # Malayalam
]

_WS = re.compile(r"\s+")


@dataclass
class DetectionResult:
    lang: str            # short code in SUPPORTED
    confidence: float    # 0..1
    method: str          # 'fasttext' | 'script' | 'langdetect' | 'fallback'


def _dominant_script(text: str) -> Optional[Tuple[str, ...]]:
    """Return the candidate languages for the most common Indic script in text."""
    counts: Dict[Tuple[str, ...], int] = {}
    for ch in text:
        cp = ord(ch)
        for lo, hi, langs in _SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[langs] = counts.get(langs, 0) + 1
                break
    if not counts:
        return None
    return max(counts, key=counts.get)


class FastTextLanguageDetector:
    """fastText-based detector with script narrowing and safe fallbacks."""

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        self.model_path = model_path
        self._model = None
        self._load_attempted = False

    def _ensure_model(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True
        try:
            import fasttext  # noqa: WPS433

            if Path(self.model_path).exists():
                # fasttext prints a load warning to stderr; harmless.
                self._model = fasttext.load_model(self.model_path)
                logger.info("Loaded fastText lid.176 from %s", self.model_path)
            else:
                logger.warning("fastText model not found at %s", self.model_path)
        except Exception as e:  # noqa: BLE001
            logger.warning("fastText unavailable (%s); using fallback detection", e)

    def detect(self, text: str) -> DetectionResult:
        """Detect the language of ``text`` → :class:`DetectionResult`."""
        text = (text or "").strip()
        if not text:
            return DetectionResult("en", 0.0, "fallback")

        self._ensure_model()
        script_langs = _dominant_script(text)

        if self._model is not None:
            clean = _WS.sub(" ", text)
            try:
                labels, probs = self._model.predict(clean, k=5)
            except Exception as e:  # noqa: BLE001
                logger.debug("fastText predict failed: %s", e)
                labels, probs = [], []
            ranked = [
                (lab.replace("__label__", ""), min(1.0, max(0.0, float(p))))
                for lab, p in zip(labels, probs)
            ]
            # Prefer the top prediction that is (a) supported and (b) consistent
            # with the dominant script, if any.
            if script_langs:
                for code, prob in ranked:
                    if code in script_langs:
                        return DetectionResult(code, prob, "fasttext")
                # fastText disagreed with script → trust the script, pick its
                # first candidate but keep fastText's top prob as a soft score.
                top_prob = ranked[0][1] if ranked else 0.5
                return DetectionResult(script_langs[0], top_prob, "script")
            for code, prob in ranked:
                if code in SUPPORTED:
                    return DetectionResult(code, prob, "fasttext")

        # ---- fallbacks (no model) ----
        if script_langs:
            return DetectionResult(script_langs[0], 0.6, "script")
        try:
            from langdetect import detect  # noqa: WPS433

            code = detect(text)
            if code in SUPPORTED:
                return DetectionResult(code, 0.5, "langdetect")
        except Exception:  # noqa: BLE001
            pass
        return DetectionResult("en", 0.3, "fallback")


# ---- module-level singleton ------------------------------------------------

_detector: Optional[FastTextLanguageDetector] = None


def get_detector() -> FastTextLanguageDetector:
    global _detector
    if _detector is None:
        _detector = FastTextLanguageDetector()
    return _detector


def detect_language(text: str) -> str:
    """Convenience: return just the short language code (drop-in replacement)."""
    return get_detector().detect(text).lang
