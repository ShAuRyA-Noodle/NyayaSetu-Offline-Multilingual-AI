"""
Tests for the fastText-backed language detector (M5).

Split into two groups:
- Script-narrowing + fallback logic — runs anywhere (no model/lib needed).
- fastText disambiguation — runs only where fasttext + the model are present
  (the ML venv); skipped otherwise.
"""

import importlib.util
from pathlib import Path

import pytest

from src.nlp.language_detection import (
    FastTextLanguageDetector,
    _dominant_script,
    detect_language,
)

MODEL_PATH = Path("models/fasttext/lid.176.bin")
_HAS_FASTTEXT = importlib.util.find_spec("fasttext") is not None
_HAS_MODEL = MODEL_PATH.exists()
_FT_READY = _HAS_FASTTEXT and _HAS_MODEL


# ---- script narrowing (no model needed) ------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("எனக்கு உதவி வேண்டும்", ("ta",)),          # Tamil
        ("నాకు సహాయం కావాలి", ("te",)),             # Telugu
        ("ನನಗೆ ಸಹಾಯ ಬೇಕು", ("kn",)),               # Kannada
        ("എനിക്ക് സഹായം വേണം", ("ml",)),           # Malayalam
        ("મને મદદ જોઈએ", ("gu",)),                 # Gujarati
        ("ମୋତେ ସାହାଯ୍ୟ ଦରକାର", ("or",)),           # Odia
        ("ਮੈਨੂੰ ਮਦਦ ਚਾਹੀਦੀ ਹੈ", ("pa",)),          # Gurmukhi
        ("किसान को पैसा नहीं मिला", ("hi", "mr")),  # Devanagari (hi/mr)
        ("আমার সাহায্য দরকার", ("bn", "as")),       # Bengali (bn/as)
    ],
)
def test_dominant_script(text, expected):
    assert _dominant_script(text) == expected


def test_distinct_script_langs_detected_without_model():
    """Unique-script languages resolve correctly via script narrowing alone."""
    det = FastTextLanguageDetector(model_path="/nonexistent/model.bin")
    assert det.detect("எனக்கு உதவி வேண்டும்").lang == "ta"
    assert det.detect("ನನಗೆ ಸಹಾಯ ಬೇಕು").lang == "kn"
    assert det.detect("ମୋତେ ସାହାଯ୍ୟ ଦରକାର").lang == "or"


def test_empty_text_defaults_english():
    det = FastTextLanguageDetector(model_path="/nonexistent/model.bin")
    assert det.detect("").lang == "en"


# ---- fastText disambiguation (ML venv only) --------------------------------


@pytest.mark.skipif(not _FT_READY, reason="fastText model not available in this env")
def test_fasttext_disambiguates_shared_script():
    det = FastTextLanguageDetector()
    # Hindi vs Marathi (both Devanagari) — needs fastText, not just script.
    assert det.detect("मुझे मदद चाहिए").lang == "hi"
    # English via fastText.
    assert det.detect("I need help with my pension application").lang == "en"


@pytest.mark.skipif(not _FT_READY, reason="fastText model not available in this env")
def test_confidence_returned():
    det = FastTextLanguageDetector()
    res = det.detect("எனக்கு உதவி வேண்டும்")
    assert 0.0 < res.confidence <= 1.0
    assert res.method in ("fasttext", "script")


def test_detect_language_convenience_returns_supported_code():
    assert detect_language("எனக்கு உதவி வேண்டும்") == "ta"
