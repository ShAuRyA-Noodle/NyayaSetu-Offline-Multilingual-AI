"""
NyayaVaani — Voice-native cross-lingual governance module.

Powered by Sarvam AI for ASR/TTS and Ollama for cross-lingual intelligence.
Supports 12 Indian languages with online/offline dual-mode architecture.
"""

from .config import NyayaVaaniConfig
from .language_registry import LanguageRegistry, SUPPORTED_LANGUAGES
from .asr_engine import ASREngine
from .tts_engine import TTSEngine
from .cross_lingual_engine import CrossLingualEngine
from .intent_engine import IntentEngine

__all__ = [
    "NyayaVaaniConfig",
    "LanguageRegistry",
    "SUPPORTED_LANGUAGES",
    "ASREngine",
    "TTSEngine",
    "CrossLingualEngine",
    "IntentEngine",
]
