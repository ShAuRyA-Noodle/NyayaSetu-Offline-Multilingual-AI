"""
Answer Generator - Main Orchestration Layer
Combines RAG retrieval with LLM generation and strict validation
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from .llm_client import OllamaClient, LLMConfig  # noqa: F401  (LLMConfig kept for back-compat re-export)
from .prompt_templates import (
    SYSTEM_PROMPT,  # noqa: F401  (re-exported via __all__ at module bottom for legacy import paths)
    build_prompt,  # noqa: F401
    format_context_from_chunks,  # noqa: F401
    select_prompt_template,  # noqa: F401
    QueryIntent,  # noqa: F401
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Source:
    """Citation source metadata"""
    scheme: str
    section: str
    confidence: float = 0.0


@dataclass
class GenerationResult:
    """Complete answer generation output"""
    success: bool
    answer: str = ""
    sources: List[Source] = field(default_factory=list)
    intent: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class AnswerGenerator:
    """
    Production answer generation system
    
    Responsibilities:
    1. Receive RAG retrieval results
    2. Build hallucination-resistant prompts
    3. Generate answers via local LLM
    4. Extract and validate citations
    5. Perform quality checks
    6. Return structured results
    """
    
    def __init__(
        self,
        llm_client: Optional[OllamaClient] = None,
        rag_engine: Optional[Any] = None,
        min_context_score: float = 0.3,
        max_answer_length: int = 500,
    ):
        """
        Initialize Answer Generator

        Args:
            llm_client: LLM client (creates default if not provided)
            rag_engine: Optional RAGEngine for the .generate() entry-point that
                does retrieval + prompt + LLM in one call. Can be None for
                callers that pass `context_chunks` directly via legacy paths.
            min_context_score: Minimum similarity score to use context
            max_answer_length: Maximum allowed answer length (chars)
        """
        self.llm_client = llm_client or OllamaClient()
        self.rag_engine = rag_engine
        self.min_context_score = min_context_score
        self.max_answer_length = max_answer_length

        # Verify LLM is available — health check is a soft warning rather than
        # a hard crash because the answer-generator may be constructed during
        # bootstrapping where transient network blips are common. Real
        # production checks live in `assert_groq_reachable()`.
        if not self.llm_client.health_check():
            logger.warning(
                "LLM health check failed at AnswerGenerator init — calls will "
                "still be attempted but may return service_degraded."
            )

        logger.info("AnswerGenerator initialized successfully")

    def generate(
        self,
        query: str,
        language: str = "en",
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """Run RAG: retrieve → prompt → LLM → validate.

        Returns a dict with keys: success, answer, sources, confidence,
        language. On failure: {success: False, error: ...}.
        """
        # Local import keeps module-level imports tidy and avoids cycles.
        from .prompt_templates import (
            MULTILINGUAL_SYSTEM_PROMPT as _MULTILINGUAL_SYSTEM_PROMPT,
            select_prompt_template as _select_prompt_template,
            format_context_from_chunks as _format_context_from_chunks,
            sanitize_user_input as _sanitize_user_input,
        )

        if self.rag_engine is None:
            return {
                "success": False,
                "error": "rag_engine_unavailable",
                "language": language,
            }

        safe_query = _sanitize_user_input(query)
        if not safe_query:
            return {
                "success": False,
                "error": "empty_query",
                "language": language,
            }

        # RAGEngine.retrieve returns List[(score, metadata, explanation)].
        # Normalise into the dict shape the rest of this class expects.
        raw_results = self.rag_engine.retrieve(safe_query, top_k=top_k)
        chunks: List[Dict[str, Any]] = []
        for score, metadata, explanation in raw_results:
            chunks.append({
                "scheme_name": metadata.get("scheme_name", ""),
                "section": metadata.get("section_type", ""),
                "text": metadata.get("content") or explanation,
                "score": float(score),
            })

        if not chunks:
            no_ctx = self._handle_no_context(safe_query)
            return {
                "success": no_ctx.success,
                "answer": no_ctx.answer,
                "sources": [],
                "confidence": 0.0,
                "warnings": no_ctx.warnings,
                "language": language,
            }

        context = _format_context_from_chunks(chunks)
        prompt_text = _select_prompt_template(safe_query, context, language)

        result = self.llm_client.generate(
            prompt=prompt_text,
            system_prompt=_MULTILINGUAL_SYSTEM_PROMPT,
            max_tokens=1000,
            temperature=0.1,
        )
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "LLM unavailable"),
                "language": language,
            }

        answer = result.get("response", "").strip()
        sources = self._extract_sources(answer, chunks)
        is_valid, warnings = self._validate_answer(answer, context, sources, chunks)
        confidence = (
            sum(c["score"] for c in chunks) / len(chunks) if chunks else 0.0
        )
        return {
            "success": True,
            "answer": answer,
            "sources": [s.__dict__ for s in sources],
            "confidence": round(confidence, 3),
            "is_valid": is_valid,
            "warnings": warnings,
            "language": language,
        }

    def _extract_sources(
        self,
        answer: str,
        chunks: List[Dict[str, Any]]
    ) -> List[Source]:
        """
        Extract scheme citations from answer
        
        Looks for scheme names mentioned in the answer and matches
        them to the retrieved chunks to build source list.
        
        Args:
            answer: Generated answer text
            chunks: Retrieved context chunks
            
        Returns:
            List of Source objects with scheme, section, confidence
        """
        sources = []
        seen = set()  # Avoid duplicates
        
        # Build mapping of scheme names from chunks
        scheme_info = {}
        for chunk in chunks:
            scheme = chunk.get('scheme_name', '')
            section = chunk.get('section', '')
            score = chunk.get('score', 0.0)
            
            if scheme:
                key = f"{scheme}:{section}"
                if key not in scheme_info or score > scheme_info[key]['score']:
                    scheme_info[key] = {
                        'scheme': scheme,
                        'section': section,
                        'score': score
                    }
        
        # Find mentioned schemes in answer
        answer_lower = answer.lower()
        
        for key, info in scheme_info.items():
            scheme = info['scheme']
            
            # Check if scheme is mentioned in answer
            # Look for exact name or common abbreviations
            scheme_patterns = [
                scheme.lower(),
                scheme.replace('-', ' ').lower(),
                scheme.replace('-', '').lower()
            ]
            
            for pattern in scheme_patterns:
                if pattern in answer_lower:
                    source_key = (info['scheme'], info['section'])
                    if source_key not in seen:
                        sources.append(Source(
                            scheme=info['scheme'],
                            section=info['section'],
                            confidence=info['score']
                        ))
                        seen.add(source_key)
                    break
        
        # If no explicit mentions found, include top chunks as implicit sources
        if not sources and chunks:
            # Add top 3 chunks as sources
            sorted_chunks = sorted(chunks, key=lambda x: x.get('score', 0), reverse=True)
            for chunk in sorted_chunks[:3]:
                scheme = chunk.get('scheme_name', '')
                section = chunk.get('section', '')
                if scheme:
                    source_key = (scheme, section)
                    if source_key not in seen:
                        sources.append(Source(
                            scheme=scheme,
                            section=section,
                            confidence=chunk.get('score', 0.0)
                        ))
                        seen.add(source_key)
        
        return sources
    
    def _validate_answer(
        self,
        answer: str,
        context: str,
        sources: List[Source],
        chunks: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Multi-stage answer validation
        
        Checks:
        1. Answer length within bounds
        2. Answer is not a refusal when context exists
        3. Sources are valid
        4. No obvious hallucination markers
        
        Args:
            answer: Generated answer
            context: Retrieved context
            sources: Extracted sources
            chunks: Original retrieved chunks
            
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []
        
        # Check 1: Length validation
        if len(answer) > self.max_answer_length:
            warnings.append(f"Answer exceeds max length ({len(answer)} > {self.max_answer_length})")
        
        if len(answer) < 10:
            warnings.append(f"Answer suspiciously short ({len(answer)} chars)")
        
        # Check 2: Inappropriate refusal detection
        refusal_phrases = [
            "don't have sufficient information",
            "don't have information",
            "not available in the current records",
            "cannot answer"
        ]
        
        is_refusal = any(phrase in answer.lower() for phrase in refusal_phrases)
        
        if is_refusal and context and "No relevant information" not in context:
            warnings.append("Model refused to answer despite having context")
        
        # Check 3: Source validation
        if sources:
            chunk_schemes = set(c.get('scheme_name', '') for c in chunks)
            for source in sources:
                if source.scheme not in chunk_schemes:
                    warnings.append(f"Source scheme '{source.scheme}' not in retrieved chunks")
        
        # Check 4: Hallucination markers
        # Look for dates, numbers, or specific details not in context
        # This is heuristic-based and not perfect
        if not is_refusal:
            # Extract potential numeric facts from answer
            numbers_in_answer = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', answer)
            numbers_in_context = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', context)
            
            # Check for numbers in answer not in context (potential hallucination)
            hallucinated_numbers = [n for n in numbers_in_answer if n not in numbers_in_context]
            if hallucinated_numbers and len(hallucinated_numbers) > 2:
                warnings.append(f"Answer contains numbers not in context: {hallucinated_numbers[:3]}")
        
        # Overall validity: no critical warnings
        critical_warnings = [w for w in warnings if "not in retrieved chunks" in w]
        is_valid = len(critical_warnings) == 0
        
        return is_valid, warnings
    
    def _handle_no_context(self, query: str) -> GenerationResult:
        """Handle case where RAG returns no results"""
        logger.warning("No context retrieved for query")
        
        return GenerationResult(
            success=True,  # Not a system failure
            answer="I don't have any relevant information in the available government records to answer this question. Please try rephrasing your question or contact your local Panchayat office for assistance.",
            sources=[],
            intent="no_context",
            metadata={'chunks_used': 0},
            warnings=["No relevant context found"]
        )
    
    def _handle_low_confidence(self, query: str, max_score: float) -> GenerationResult:
        """Handle case where context quality is too low"""
        logger.warning(f"Context confidence too low: {max_score:.3f}")
        
        return GenerationResult(
            success=True,  # Not a system failure
            answer="I found some potentially relevant information, but I'm not confident it fully answers your question. Please try asking more specifically about a particular government scheme (like PM-KISAN, PMAY-G, or MGNREGA), or contact your local Panchayat office.",
            sources=[],
            intent="low_confidence",
            metadata={
                'chunks_used': 0,
                'max_context_score': max_score,
                'confidence_threshold': self.min_context_score
            },
            warnings=[f"Context confidence {max_score:.3f} below threshold {self.min_context_score}"]
        )


def create_generator(**kwargs) -> AnswerGenerator:
    """
    Factory function for creating AnswerGenerator
    
    Args:
        **kwargs: Passed to AnswerGenerator constructor
        
    Returns:
        Configured AnswerGenerator instance
    """
    return AnswerGenerator(**kwargs)


# ============================================================================
# STANDALONE USAGE
# ============================================================================

if __name__ == "__main__":
    # Fix imports for direct execution
    import sys
    import os
    
    # Add parent directory to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)
    
    # Now import with absolute paths
    from generation.llm_client import OllamaClient, LLMConfig
    from generation.prompt_templates import (
        SYSTEM_PROMPT,
        build_prompt,
        format_context_from_chunks,
        select_prompt_template,
        QueryIntent
    )
    from generation.answer_generator import create_generator
    
    print("Testing Answer Generator (Standalone Mode)...\n")
    
    # Create generator
    try:
        generator = create_generator()
        print("✓ Generator created successfully\n")
    except RuntimeError as e:
        print(f"✗ Failed to create generator: {e}")
        print("Make sure Ollama is running: 'ollama serve'")
        exit(1)
    
    # Test with mock RAG results
    test_query = "What is PM-KISAN and who is eligible?"
    
    mock_chunks = [
        {
            'scheme_name': 'PM-KISAN',
            'section': 'Overview',
            'text': 'Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) is a central sector scheme that provides income support to all landholding farmers.',
            'score': 0.92
        },
        {
            'scheme_name': 'PM-KISAN',
            'section': 'Eligibility',
            'text': 'All landholding farmer families are eligible for PM-KISAN. Small and marginal farmers who own cultivable land are covered.',
            'score': 0.88
        },
        {
            'scheme_name': 'PM-KISAN',
            'section': 'Benefits',
            'text': 'Provides financial benefit of Rs 6000 per year, paid in three equal installments of Rs 2000 each every four months.',
            'score': 0.75
        }
    ]
    
    print(f"Query: {test_query}\n")
    print("Generating answer...\n")
    
    result = generator.generate(test_query, mock_chunks)
    
    if result.success:
        print("✓ Generation successful!\n")
        print(f"Intent: {result.intent}\n")
        print(f"Answer:\n{result.answer}\n")
        print(f"Sources:")
        for source in result.sources:
            print(f"  - {source.scheme} ({source.section}) [confidence: {source.confidence:.2f}]")
        print(f"\nMetadata:")
        for key, value in result.metadata.items():
            print(f"  {key}: {value}")
        
        if result.warnings:
            print(f"\nWarnings:")
            for warning in result.warnings:
                print(f"  ! {warning}")
    else:
        print(f"✗ Generation failed: {result.error}")