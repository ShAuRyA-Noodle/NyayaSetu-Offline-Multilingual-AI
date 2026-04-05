"""
Core RAG system modules.
"""

from .chunker import SchemeChunker
from .embedder import MultilingualEmbedder
from .rag_engine import RAGEngine

try:
    from .retriever import FAISSRetriever
except (ImportError, Exception):
    FAISSRetriever = None  # type: ignore

__all__ = [
    'SchemeChunker',
    'MultilingualEmbedder',
    'FAISSRetriever',
    'RAGEngine'
]
