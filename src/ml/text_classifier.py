"""
Fine-tuned transformer classifier for governance text.

Loads a locally fine-tuned model (IndicBERT/MuRIL) + its label map and predicts
the category of a piece of governance text (scheme description, grievance body).
This is the learned model that backs the grievance router; the existing
LLM-prompt + keyword path remains as a fallback when the model isn't present.

Degrades gracefully: if transformers/torch or the model dir is missing, the
classifier reports unavailable and callers fall back.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_MODEL_DIR = os.getenv(
    "GOV_CLASSIFIER_DIR",
    str(Path(__file__).resolve().parents[2] / "models" / "classifier"),
)


class TextClassifier:
    """Wraps a fine-tuned sequence-classification model + label map."""

    def __init__(self, model_dir: str = DEFAULT_MODEL_DIR):
        self.model_dir = model_dir
        self._model = None
        self._tokenizer = None
        self._labels: List[str] = []
        self._load_attempted = False

    def is_available(self) -> bool:
        return Path(self.model_dir, "config.json").exists()

    def _ensure_loaded(self) -> bool:
        if self._model is not None:
            return True
        if self._load_attempted:
            return False
        self._load_attempted = True
        try:
            import torch  # noqa: F401,WPS433
            from transformers import (  # noqa: WPS433
                AutoModelForSequenceClassification,
                AutoTokenizer,
            )

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_dir)
            self._model.eval()
            labels_path = Path(self.model_dir) / "labels.json"
            if labels_path.exists():
                self._labels = json.loads(labels_path.read_text(encoding="utf-8"))
            else:
                self._labels = [
                    self._model.config.id2label[i]
                    for i in range(self._model.config.num_labels)
                ]
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning("Text classifier unavailable (%s)", e)
            return False

    def predict(self, text: str) -> Optional[Tuple[str, float]]:
        """Return (label, confidence) for ``text``, or None if unavailable."""
        if not self._ensure_loaded():
            return None
        import torch

        enc = self._tokenizer(
            text, truncation=True, max_length=128, return_tensors="pt"
        )
        with torch.no_grad():
            logits = self._model(**enc).logits[0]
            probs = torch.softmax(logits, dim=-1)
            idx = int(torch.argmax(probs))
        return self._labels[idx], float(probs[idx])

    def predict_topk(self, text: str, k: int = 3) -> List[Tuple[str, float]]:
        """Return the top-k (label, confidence) pairs."""
        if not self._ensure_loaded():
            return []
        import torch

        enc = self._tokenizer(text, truncation=True, max_length=128, return_tensors="pt")
        with torch.no_grad():
            probs = torch.softmax(self._model(**enc).logits[0], dim=-1)
            top = torch.topk(probs, min(k, len(self._labels)))
        return [(self._labels[int(i)], float(p)) for p, i in zip(top.values, top.indices)]


_classifier: Optional[TextClassifier] = None


def get_classifier() -> TextClassifier:
    global _classifier
    if _classifier is None:
        _classifier = TextClassifier()
    return _classifier
