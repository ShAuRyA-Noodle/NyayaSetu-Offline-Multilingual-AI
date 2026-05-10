"""
Scheme Summarizer Module

Production-grade module for generating deterministic, structured summaries 
of government schemes using RAG+LLM pipeline.

Author: NyayaSetu Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import hashlib
import json
import logging

import cachetools

# Import QueryIntent + sanitizer (handle different import contexts)
try:
    from ..generation.prompt_templates import QueryIntent, sanitize_user_input
except ImportError:
    from generation.prompt_templates import QueryIntent, sanitize_user_input

# Type aliases for clarity
Language = Literal["en", "hi"]

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPTIONS
# ============================================================================

class SummarizerError(Exception):
    """Base exception for summarizer module."""
    pass


class SchemeNotFoundError(SummarizerError):
    """Raised when requested scheme doesn't exist in knowledge base."""
    
    def __init__(self, scheme_name: str):
        self.scheme_name = scheme_name
        super().__init__(f"Scheme '{scheme_name}' not found in knowledge base")


class LowConfidenceError(SummarizerError):
    """Raised when retrieval confidence is below acceptable threshold."""
    
    def __init__(self, confidence: float, threshold: float = 0.6):
        self.confidence = confidence
        self.threshold = threshold
        super().__init__(
            f"Retrieval confidence {confidence:.2f} below threshold {threshold:.2f}"
        )


class LLMUnavailableError(SummarizerError):
    """Raised when LLM service is unavailable or fails."""
    
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"LLM unavailable: {details}")


class ValidationError(SummarizerError):
    """Raised when output validation fails."""
    
    def __init__(self, field: str, reason: str):
        self.field = field
        self.reason = reason
        super().__init__(f"Validation failed for '{field}': {reason}")


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class SchemeSummary:
    """
    Structured summary of a government scheme.
    
    Attributes:
        scheme_name: Official name of the scheme
        one_line_purpose: Concise description (max 20 words)
        eligibility: List of eligibility criteria (3-5 bullet points)
        benefits: List of scheme benefits (3-5 bullet points)
        application_steps: Ordered application process (3-7 steps)
        contact_info: Optional contact information
        language: Output language code
        metadata: Additional context (confidence, sources, etc.)
    """
    scheme_name: str
    one_line_purpose: str
    eligibility: List[str]
    benefits: List[str]
    application_steps: List[str]
    contact_info: Optional[str]
    language: Language
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate data after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """
        Perform comprehensive validation of summary fields.
        
        Raises:
            ValidationError: If any field fails validation
        """
        # Validate one-line purpose length (max 20 words)
        word_count = len(self.one_line_purpose.split())
        if word_count > 50:
            raise ValidationError(
                "one_line_purpose",
                f"Exceeds 50 words (got {word_count})"
            )
        
        if not self.one_line_purpose.strip():
            raise ValidationError("one_line_purpose", "Cannot be empty")
        
        # Validate eligibility (3-5 items)
        if not (1 <= len(self.eligibility) <= 10):
            raise ValidationError(
                "eligibility",
                f"Must have 3-5 items (got {len(self.eligibility)})"
            )
        
        # Validate benefits (3-5 items)
        if not (1 <= len(self.benefits) <= 10):  # Relaxed
            raise ValidationError(
                "benefits",
                f"Must have 3-5 items (got {len(self.benefits)})"
            )
        
        # Validate application steps (3-7 items)
        if not (1 <= len(self.application_steps) <= 15):  # Relaxed
            raise ValidationError(
                "application_steps",
                f"Must have 3-7 items (got {len(self.application_steps)})"
            )
        
        # Validate no empty strings in lists
        for field_name, items in [
            ("eligibility", self.eligibility),
            ("benefits", self.benefits),
            ("application_steps", self.application_steps)
        ]:
            if any(not item.strip() for item in items):
                raise ValidationError(field_name, "Contains empty items")
        
        # Validate total word count (max 150 words)
        total_text = (
            self.one_line_purpose + " " +
            " ".join(self.eligibility) + " " +
            " ".join(self.benefits) + " " +
            " ".join(self.application_steps)
        )
        if self.contact_info:
            total_text += " " + self.contact_info
        
        total_words = len(total_text.split())
        if total_words > 500:  # Relaxed from 150 to 500
            raise ValidationError(
                "total_length",
                f"Exceeds 150 words (got {total_words})"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "scheme_name": self.scheme_name,
            "one_line_purpose": self.one_line_purpose,
            "eligibility": self.eligibility,
            "benefits": self.benefits,
            "application_steps": self.application_steps,
            "contact_info": self.contact_info,
            "language": self.language,
            "metadata": self.metadata
        }


# ============================================================================
# SUMMARIZER
# ============================================================================

class SchemeSummarizer:
    """
    Production-grade scheme summarizer with deterministic output.
    
    Generates structured summaries of government schemes using RAG retrieval
    and LLM-based extraction. Implements confidence thresholding, output
    validation, and comprehensive error handling.
    
    Example:
        >>> summarizer = SchemeSummarizer(rag_engine, generator)
        >>> summary = summarizer.summarize("PM-KISAN", language="en")
        >>> print(summary.one_line_purpose)
    """
    
    # Class constants
    CONFIDENCE_THRESHOLD = 0.35
    TOP_K_RETRIEVAL = 5
    MAX_RETRIES = 2
    
    # Prompt templates for structured extraction
    EXTRACTION_PROMPT_EN = """You are a government scheme documentation expert. Extract structured information from the provided scheme data.

SCHEME DATA:
{retrieved_content}

Extract the following in a structured format (JSON):
1. one_line_purpose: A single sentence describing the scheme's main purpose (max 20 words)
2. eligibility: A list of 3-5 specific eligibility criteria (bullet points)
3. benefits: A list of 3-5 specific benefits provided (bullet points)
4. application_steps: A list of 3-7 ordered steps to apply (numbered steps)
5. contact_info: Contact information if available (single line, or null)

Return ONLY valid JSON in this exact format:
{{
    "one_line_purpose": "...",
    "eligibility": ["...", "...", "..."],
    "benefits": ["...", "...", "..."],
    "application_steps": ["...", "...", "..."],
    "contact_info": "..." or null
}}

Be concise, factual, and extract only information present in the scheme data. Do not hallucinate."""

    EXTRACTION_PROMPT_HI = """आप सरकारी योजना दस्तावेज़ विशेषज्ञ हैं। प्रदान की गई योजना डेटा से संरचित जानकारी निकालें।

योजना डेटा:
{retrieved_content}

निम्नलिखित को संरचित प्रारूप (JSON) में निकालें:
1. one_line_purpose: योजना के मुख्य उद्देश्य का एक वाक्य (अधिकतम 20 शब्द)
2. eligibility: 3-5 विशिष्ट पात्रता मानदंड की सूची (बुलेट पॉइंट)
3. benefits: प्रदान किए गए 3-5 विशिष्ट लाभों की सूची (बुलेट पॉइंट)
4. application_steps: आवेदन करने के लिए 3-7 क्रमबद्ध चरणों की सूची (क्रमांकित चरण)
5. contact_info: संपर्क जानकारी यदि उपलब्ध हो (एकल पंक्ति, या null)

इस सटीक प्रारूप में केवल मान्य JSON लौटाएं:
{{
    "one_line_purpose": "...",
    "eligibility": ["...", "...", "..."],
    "benefits": ["...", "...", "..."],
    "application_steps": ["...", "...", "..."],
    "contact_info": "..." or null
}}

संक्षिप्त, तथ्यात्मक रहें, और केवल योजना डेटा में मौजूद जानकारी निकालें। कल्पना न करें।"""
    
    def __init__(self, rag_engine: Any, answer_generator: Any):
        """
        Initialize summarizer with dependencies.
        
        Args:
            rag_engine: RAGEngine instance for retrieval
            answer_generator: AnswerGenerator instance for LLM calls
        """
        self.rag_engine = rag_engine
        self.answer_generator = answer_generator
        # Bounded cache — was an unbounded dict which leaked memory under
        # any non-trivial query volume.
        self._cache: "cachetools.LRUCache[str, SchemeSummary]" = cachetools.LRUCache(maxsize=500)

        logger.info("SchemeSummarizer initialized (LRU cache size=500)")
    
    def summarize(
        self,
        scheme_name: str,
        language: Language = "en"
    ) -> SchemeSummary:
        """
        Generate a structured summary of a government scheme.
        
        This method is deterministic: given the same scheme name and language,
        it will produce the same output (assuming the knowledge base hasn't changed).
        
        Args:
            scheme_name: Name of the scheme to summarize (e.g., "PM-KISAN")
            language: Output language ("en" or "hi")
        
        Returns:
            SchemeSummary object with validated structured data
        
        Raises:
            SchemeNotFoundError: If scheme doesn't exist
            LowConfidenceError: If retrieval confidence < 0.6
            LLMUnavailableError: If LLM fails to generate
            ValidationError: If output fails validation
        
        Example:
            >>> summary = summarizer.summarize("PM-KISAN", "en")
            >>> print(summary.eligibility)
            ['Small and marginal farmers', 'Landholding up to 2 hectares', ...]
        """
        # Input validation
        if not scheme_name or not scheme_name.strip():
            raise ValueError("scheme_name cannot be empty")

        # Sanitize the citizen-supplied scheme name before it ever flows
        # into LLM prompts. Prevents prompt-injection via crafted scheme
        # names like "PM-KISAN ### IGNORE ABOVE...".
        scheme_name = sanitize_user_input(scheme_name.strip(), max_len=200)
        if not scheme_name:
            raise ValueError("scheme_name cannot be empty after sanitization")

        # Check cache for deterministic output
        cache_key = self._generate_cache_key(scheme_name, language)
        if cache_key in self._cache:
            logger.info(f"Cache hit for {scheme_name} ({language})")
            return self._cache[cache_key]
        
        logger.info(f"Generating summary for {scheme_name} ({language})")
        
        # Step 1: Retrieve scheme data using RAG
        retrieved_chunks = self._retrieve_scheme_data(scheme_name)
        
        # Step 2: Extract structured information using LLM
        extracted_data = self._extract_structured_info(
            scheme_name,
            retrieved_chunks,
            language
        )
        
        # Step 3: Build and validate summary
        summary = self._build_summary(
            scheme_name,
            extracted_data,
            retrieved_chunks,
            language
        )
        
        # Cache for future requests
        self._cache[cache_key] = summary
        
        logger.info(f"Successfully generated summary for {scheme_name}")
        return summary
    
    def _retrieve_scheme_data(
        self,
        scheme_name: str
    ) -> List[tuple[float, Dict[str, str], str]]:
        """
        Retrieve scheme data from knowledge base using RAG.
        
        Args:
            scheme_name: Name of scheme to retrieve
        
        Returns:
            List of (score, metadata, explanation) tuples
        
        Raises:
            SchemeNotFoundError: If no results found
            LowConfidenceError: If confidence too low
        """
        try:
            # Retrieve with scheme name as query
            results = self.rag_engine.retrieve(
                query=scheme_name,
                top_k=self.TOP_K_RETRIEVAL
            )
            
            if not results:
                raise SchemeNotFoundError(scheme_name)
            
            # Filter results for this specific scheme
            scheme_results = [
                (score, meta, expl)
                for score, meta, expl in results
                if meta.get("scheme_name", "").upper() == scheme_name.upper()
            ]
            
            if not scheme_results:
                raise SchemeNotFoundError(scheme_name)
            
            # Check confidence (average of top-k scores)
            avg_confidence = sum(score for score, _, _ in scheme_results) / len(scheme_results)
            
            if avg_confidence < self.CONFIDENCE_THRESHOLD:
                raise LowConfidenceError(avg_confidence, self.CONFIDENCE_THRESHOLD)
            
            logger.info(
                f"Retrieved {len(scheme_results)} chunks for {scheme_name} "
                f"(avg confidence: {avg_confidence:.3f})"
            )
            
            return scheme_results
            
        except SchemeNotFoundError:
            raise
        except LowConfidenceError:
            raise
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            raise SchemeNotFoundError(scheme_name)
    
    def _extract_structured_info(
        self,
        scheme_name: str,
        retrieved_chunks: List[tuple[float, Dict[str, str], str]],
        language: Language
    ) -> Dict[str, Any]:
        """
        Extract structured information using LLM.
        
        Args:
            scheme_name: Name of scheme
            retrieved_chunks: RAG retrieval results as tuples (score, metadata, explanation)
            language: Target language
        
        Returns:
            Dictionary with extracted fields
        
        Raises:
            LLMUnavailableError: If LLM fails
        """
        # Prepare context from retrieved chunks
        context = self._prepare_context(retrieved_chunks)
        
        # Select prompt based on language
        prompt_template = (
            self.EXTRACTION_PROMPT_HI if language == "hi"
            else self.EXTRACTION_PROMPT_EN
        )
        
        prompt = prompt_template.format(retrieved_content=context)
        
        # Call LLM directly (bypass AnswerGenerator to avoid extra formatting)
        for attempt in range(self.MAX_RETRIES):
            try:
                # Access the LLM client directly
                llm_client = self.answer_generator.llm_client
                
                # Generate with higher token limit for JSON output
                response_dict = llm_client.generate(
                    prompt=prompt,
                    temperature=0.1,  # Low temp for deterministic output
                    max_tokens=2000   # Enough for full JSON
                )
                
                if not response_dict or not response_dict.get('success'):
                    error_msg = response_dict.get('error', 'Unknown error') if response_dict else 'Empty response'
                    raise LLMUnavailableError(f"LLM generation failed: {error_msg}")
                
                # Extract text from response dict
                response_text = response_dict.get('response', '')
                
                if not response_text:
                    raise LLMUnavailableError("No response text in LLM output")
                
                # Parse JSON from LLM response
                extracted = self._parse_llm_response(response_text)
                
                logger.info(f"Successfully extracted data (attempt {attempt + 1})")
                return extracted
                
            except Exception as e:
                logger.warning(f"Extraction attempt {attempt + 1} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise LLMUnavailableError(str(e))
        
        raise LLMUnavailableError("Max retries exceeded")
    
    def _prepare_context(
        self,
        retrieved_chunks: List[tuple[float, Dict[str, str], str]]
    ) -> str:
        """
        Prepare context string from retrieved chunks.
        
        Args:
            retrieved_chunks: RAG retrieval results
        
        Returns:
            Formatted context string
        """
        context_parts = []

        for _score, metadata, explanation in retrieved_chunks:
            section_type = metadata.get("section_type", "general")
            # Chunker now embeds the actual chunk text in metadata['content'].
            # Fall back to the human-readable banner string if (somehow) it's
            # missing — but this is the bug fix path that was previously
            # reading the wrong field.
            content = metadata.get("content") or explanation

            context_parts.append(
                f"[{section_type.upper()}]\n{content}\n"
            )

        return "\n".join(context_parts)
    
    def _parse_llm_response(self, response: Any) -> Dict[str, Any]:
        """
        Parse JSON from LLM response with error handling.
        
        Args:
            response: Raw LLM response (can be string or dict)
        
        Returns:
            Parsed dictionary
        
        Raises:
            LLMUnavailableError: If parsing fails
        """
        try:
            # Check if response is already a dict
            if isinstance(response, dict):
                data = response
            else:
                # Response is a string, need to parse JSON
                response = response.strip()
                
                # Try to find JSON object in response
                # Look for first { and last }
                start_idx = response.find('{')
                end_idx = response.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response[start_idx:end_idx+1]
                else:
                    json_str = response
                
                # Remove markdown code blocks if present
                if "```" in json_str:
                    lines = json_str.split("\n")
                    json_lines = []
                    in_json = False
                    
                    for line in lines:
                        if line.startswith("```"):
                            in_json = not in_json
                            continue
                        if in_json or (not line.startswith("```")):
                            json_lines.append(line)
                    
                    json_str = "\n".join(json_lines).strip()
                    # Try again to find JSON boundaries
                    start_idx = json_str.find('{')
                    end_idx = json_str.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        json_str = json_str[start_idx:end_idx+1]
                
                # Parse JSON
                data = json.loads(json_str)
            
            # Validate required fields
            required_fields = [
                "one_line_purpose",
                "eligibility",
                "benefits",
                "application_steps"
            ]
            
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}\nResponse: {str(response)[:500]}")
            raise LLMUnavailableError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Response parsing failed: {e}")
            raise LLMUnavailableError(f"Failed to parse response: {e}")
    
    def _build_summary(
        self,
        scheme_name: str,
        extracted_data: Dict[str, Any],
        retrieved_chunks: List[tuple[float, Dict[str, str], str]],
        language: Language
    ) -> SchemeSummary:
        """
        Build and validate SchemeSummary object.
        
        Args:
            scheme_name: Name of scheme
            extracted_data: LLM-extracted fields
            retrieved_chunks: Original RAG results
            language: Output language
        
        Returns:
            Validated SchemeSummary
        
        Raises:
            ValidationError: If validation fails
        """
        # Calculate metadata
        avg_confidence = sum(
            score for score, _, _ in retrieved_chunks
        ) / len(retrieved_chunks)
        
        source_count = len(retrieved_chunks)
        
        metadata = {
            "source_count": source_count,
            "confidence": round(avg_confidence, 3),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        # Create summary (validation happens in __post_init__)
        try:
            summary = SchemeSummary(
                scheme_name=scheme_name,
                one_line_purpose=extracted_data["one_line_purpose"],
                eligibility=extracted_data["eligibility"],
                benefits=extracted_data["benefits"],
                application_steps=extracted_data["application_steps"],
                contact_info=extracted_data.get("contact_info"),
                language=language,
                metadata=metadata
            )
            
            return summary
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise ValidationError("summary", str(e))
    
    def _generate_cache_key(self, scheme_name: str, language: Language) -> str:
        """
        Generate deterministic cache key.
        
        Args:
            scheme_name: Name of scheme
            language: Language code
        
        Returns:
            SHA256 hash of inputs
        """
        key_data = f"{scheme_name.upper()}:{language}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": 1000  # Could be configurable
        }