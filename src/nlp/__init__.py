"""
NLP package — offline-capable language tooling.

- ``language_detection`` : fastText lid.176 language identification across the
  12 supported Indian languages, with Unicode-script narrowing and graceful
  fallback when the model/library is unavailable.
"""

from .language_detection import (
    DetectionResult,
    FastTextLanguageDetector,
    detect_language,
    get_detector,
)

__all__ = [
    "DetectionResult",
    "FastTextLanguageDetector",
    "detect_language",
    "get_detector",
]
