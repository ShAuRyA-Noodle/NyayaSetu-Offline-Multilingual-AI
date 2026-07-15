"""
ML package — trained models for governance text understanding.

- ``text_classifier`` : a fine-tuned transformer (IndicBERT/MuRIL) that classifies
  governance text into departments/categories, backing the grievance router with
  a learned model (the LLM + keyword path remains as fallback).
"""

from .text_classifier import TextClassifier, get_classifier

__all__ = ["TextClassifier", "get_classifier"]
