"""
NyayaSetu-GovAgent Answer Generation Layer

This package provides production-grade answer generation with:
- Local LLM integration (Ollama)
- Hallucination-resistant prompt engineering
- Citation/source tracking
- Multi-stage validation
- Offline-first guarantees
"""

from .llm_client import OllamaClient, LLMConfig, create_client
from .prompt_templates import (
    QueryIntent,
    select_prompt_template,
    build_prompt,
    format_context_from_chunks
)
from .answer_generator import (
    AnswerGenerator,
    GenerationResult,
    Source,
    create_generator
)
__version__ = "1.0.0"

__all__ = [
    # LLM Client
    'OllamaClient',
    'LLMConfig',
    'create_client',
    
    # Prompt Templates
    'QueryIntent',
    'select_prompt_template',
    'build_prompt',
    'format_context_from_chunks',
    
    # Answer Generator
    'AnswerGenerator',
    'GenerationResult',
    'Source',
    'create_generator',
]