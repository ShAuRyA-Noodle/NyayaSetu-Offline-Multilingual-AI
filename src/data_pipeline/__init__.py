"""
Data pipeline package — real government scheme ingestion.

Scrapes the National myScheme portal (https://www.myscheme.gov.in), normalizes
each scheme into the RAG-ready shape (eligibility / benefits / process), and
upserts into the `schemes` and `schemes_metadata` tables. A daily refresh keeps
the knowledge base current.

100% real data. No synthetic or simulated content.
"""

from .myscheme_client import MySchemeClient, MySchemeError
from .normalizer import normalize_scheme, NormalizedScheme

__all__ = [
    "MySchemeClient",
    "MySchemeError",
    "normalize_scheme",
    "NormalizedScheme",
]
