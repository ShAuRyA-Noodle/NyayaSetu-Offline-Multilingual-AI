"""
Tests for the fine-tuned governance text classifier (M7).

Skipped where transformers/torch or the trained model dir is absent; run in the
ML venv after scripts/train_classifier.py has produced models/classifier/.
"""

import importlib.util
from pathlib import Path

import pytest

from src.ml.text_classifier import DEFAULT_MODEL_DIR, TextClassifier

_HAS_TF = importlib.util.find_spec("transformers") is not None
_HAS_MODEL = Path(DEFAULT_MODEL_DIR, "config.json").exists()
_READY = _HAS_TF and _HAS_MODEL

pytestmark = pytest.mark.skipif(not _READY, reason="trained classifier not available")


@pytest.fixture(scope="module")
def clf():
    return TextClassifier()


def test_available(clf):
    assert clf.is_available()


def test_predicts_agriculture(clf):
    label, conf = clf.predict(
        "Financial assistance and subsidy for small and marginal farmers under a "
        "central agriculture income-support scheme."
    )
    assert "Agriculture" in label
    assert 0.0 < conf <= 1.0


def test_predicts_education(clf):
    label, _ = clf.predict("Scholarship for SC/ST students pursuing higher education.")
    assert "Education" in label


def test_topk_returns_sorted(clf):
    top = clf.predict_topk("Free health insurance for poor families", k=3)
    assert len(top) == 3
    confs = [c for _, c in top]
    assert confs == sorted(confs, reverse=True)
