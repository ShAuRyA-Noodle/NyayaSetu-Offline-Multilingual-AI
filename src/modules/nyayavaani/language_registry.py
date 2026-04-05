"""
Language Registry — 12 Indian languages supported by NyayaVaani.
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class LanguageInfo:
    """Metadata for a supported language."""
    bcp47: str
    english_name: str
    native_name: str
    script: str
    sarvam_asr_code: str
    sarvam_tts_code: str
    whisper_code: str


SUPPORTED_LANGUAGES: dict[str, LanguageInfo] = {
    "hi": LanguageInfo("hi-IN", "Hindi", "हिन्दी", "Devanagari", "hi-IN", "hi-IN", "hi"),
    "bn": LanguageInfo("bn-IN", "Bengali", "বাংলা", "Bengali", "bn-IN", "bn-IN", "bn"),
    "ta": LanguageInfo("ta-IN", "Tamil", "தமிழ்", "Tamil", "ta-IN", "ta-IN", "ta"),
    "te": LanguageInfo("te-IN", "Telugu", "తెలుగు", "Telugu", "te-IN", "te-IN", "te"),
    "mr": LanguageInfo("mr-IN", "Marathi", "मराठी", "Devanagari", "mr-IN", "mr-IN", "mr"),
    "gu": LanguageInfo("gu-IN", "Gujarati", "ગુજરાતી", "Gujarati", "gu-IN", "gu-IN", "gu"),
    "kn": LanguageInfo("kn-IN", "Kannada", "ಕನ್ನಡ", "Kannada", "kn-IN", "kn-IN", "kn"),
    "ml": LanguageInfo("ml-IN", "Malayalam", "മലയാളം", "Malayalam", "ml-IN", "ml-IN", "ml"),
    "pa": LanguageInfo("pa-IN", "Punjabi", "ਪੰਜਾਬੀ", "Gurmukhi", "pa-IN", "pa-IN", "pa"),
    "or": LanguageInfo("or-IN", "Odia", "ଓଡ଼ିଆ", "Odia", "od-IN", "od-IN", "or"),
    "as": LanguageInfo("as-IN", "Assamese", "অসমীয়া", "Bengali", "as-IN", "as-IN", "as"),
    "en": LanguageInfo("en-IN", "English", "English", "Latin", "en-IN", "en-IN", "en"),
}


class LanguageRegistry:
    """Language detection and lookup."""

    @staticmethod
    def get(code: str) -> Optional[LanguageInfo]:
        """Get language info by short code (hi, en, etc.)."""
        return SUPPORTED_LANGUAGES.get(code)

    @staticmethod
    def get_all() -> dict[str, LanguageInfo]:
        return SUPPORTED_LANGUAGES

    @staticmethod
    def detect_language(text: str) -> str:
        """Detect language of text, return short code."""
        try:
            from langdetect import detect
            detected = detect(text)
            # langdetect returns ISO 639-1 codes
            if detected in SUPPORTED_LANGUAGES:
                return detected
            # Map common variants
            lang_map = {"hi": "hi", "bn": "bn", "ta": "ta", "te": "te",
                        "mr": "mr", "gu": "gu", "kn": "kn", "ml": "ml",
                        "pa": "pa", "or": "or", "as": "as", "en": "en"}
            return lang_map.get(detected, "hi")
        except Exception:
            # If langdetect fails, check for Devanagari script
            for ch in text:
                if "\u0900" <= ch <= "\u097F":
                    return "hi"
            return "en"

    @staticmethod
    def is_supported(code: str) -> bool:
        return code in SUPPORTED_LANGUAGES
