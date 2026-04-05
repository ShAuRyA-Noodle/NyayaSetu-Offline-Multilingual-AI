"""
Notice Drafter Module

Production-grade module for generating official government notices in gazette-style
format for scheme announcements, updates, and circulars using RAG+LLM pipeline.

Author: NyayaSetu Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal
from datetime import datetime, date
import hashlib
import json
import logging
import re

# Type aliases for clarity
Language = Literal["en", "hi"]
NoticeType = Literal["circular", "order", "memo", "notification", "advisory", "amendment"]

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPTIONS
# ============================================================================

class NoticeDrafterError(Exception):
    """Base exception for notice drafter module."""
    pass


class SchemeNotFoundError(NoticeDrafterError):
    """Raised when requested scheme doesn't exist in knowledge base."""
    
    def __init__(self, scheme_name: str):
        self.scheme_name = scheme_name
        super().__init__(f"Scheme '{scheme_name}' not found in knowledge base")


class LowConfidenceError(NoticeDrafterError):
    """Raised when retrieval confidence is below acceptable threshold."""
    
    def __init__(self, confidence: float, threshold: float = 0.6):
        self.confidence = confidence
        self.threshold = threshold
        super().__init__(
            f"Retrieval confidence {confidence:.2f} below threshold {threshold:.2f}"
        )


class LLMUnavailableError(NoticeDrafterError):
    """Raised when LLM service is unavailable or fails."""
    
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"LLM unavailable: {details}")


class ValidationError(NoticeDrafterError):
    """Raised when output validation fails."""
    
    def __init__(self, field: str, reason: str):
        self.field = field
        self.reason = reason
        super().__init__(f"Validation failed for '{field}': {reason}")


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class GovernmentNotice:
    """
    Structured government notice in gazette-style format.
    
    Attributes:
        scheme_name: Official name of the scheme
        notice_type: Type of notice (announcement/update/circular/amendment)
        reference_number: Official reference/notification number
        issue_date: Date of notice issuance
        subject: Subject line of the notice
        body: Main content of the notice (structured paragraphs)
        issuing_authority: Department/ministry issuing the notice
        signature_block: Official signature details
        effective_date: Optional date when notice takes effect
        language: Output language code
        metadata: Additional context (confidence, sources, etc.)
    """
    scheme_name: str
    notice_type: NoticeType
    reference_number: str
    issue_date: date
    subject: str
    body: str
    issuing_authority: str
    signature_block: str
    effective_date: Optional[date]
    language: Language
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate data after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """
        Perform comprehensive validation of notice fields.
        
        Raises:
            ValidationError: If any field fails validation
        """
        # Validate reference number format
        if not self.reference_number or not self.reference_number.strip():
            raise ValidationError("reference_number", "Cannot be empty")
        
        # Validate subject length (max 150 characters)
        if len(self.subject) > 150:
            raise ValidationError(
                "subject",
                f"Exceeds 150 characters (got {len(self.subject)})"
            )
        
        if not self.subject.strip():
            raise ValidationError("subject", "Cannot be empty")
        
        # Validate body content (200-2000 words)
        word_count = len(self.body.split())
        if not (200 <= word_count <= 2000):
            raise ValidationError(
                "body",
                f"Must be 200-2000 words (got {word_count})"
            )
        
        # Validate issuing authority
        if not self.issuing_authority or not self.issuing_authority.strip():
            raise ValidationError("issuing_authority", "Cannot be empty")
        
        # Validate signature block
        if not self.signature_block or not self.signature_block.strip():
            raise ValidationError("signature_block", "Cannot be empty")
        
        # Validate dates
        if self.effective_date and self.effective_date < self.issue_date:
            raise ValidationError(
                "effective_date",
                "Cannot be before issue_date"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "scheme_name": self.scheme_name,
            "notice_type": self.notice_type,
            "reference_number": self.reference_number,
            "issue_date": self.issue_date.isoformat(),
            "subject": self.subject,
            "body": self.body,
            "issuing_authority": self.issuing_authority,
            "signature_block": self.signature_block,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "language": self.language,
            "metadata": self.metadata
        }
    
    def format_gazette_style(self) -> str:
        """
        Format notice in official gazette style.
        
        Returns:
            Formatted notice text ready for publication
        """
        separator = "=" * 80
        
        # Header
        header = f"{separator}\n"
        header += f"GOVERNMENT OF INDIA\n"
        header += f"{'MINISTRY OF RURAL DEVELOPMENT' if self.language == 'en' else 'ग्रामीण विकास मंत्रालय'}\n"
        header += f"{separator}\n\n"
        
        # Reference and date
        ref_line = f"Reference No.: {self.reference_number}\n"
        date_line = f"Date: {self.issue_date.strftime('%d-%m-%Y')}\n\n"
        
        # Subject
        subject_label = "SUBJECT:" if self.language == "en" else "विषय:"
        subject_line = f"{subject_label} {self.subject}\n\n"
        
        # Body
        body_section = f"{self.body}\n\n"
        
        # Effective date (if applicable)
        effective_section = ""
        if self.effective_date:
            effective_label = "Effective from:" if self.language == "en" else "प्रभावी तिथि:"
            effective_section = f"{effective_label} {self.effective_date.strftime('%d-%m-%Y')}\n\n"
        
        # Signature
        signature_section = f"{self.signature_block}\n"
        signature_section += f"{self.issuing_authority}\n"
        
        # Footer
        footer = f"\n{separator}\n"
        footer += f"{'END OF NOTICE' if self.language == 'en' else 'सूचना समाप्त'}\n"
        footer += f"{separator}\n"
        
        return header + ref_line + date_line + subject_line + body_section + effective_section + signature_section + footer


# ============================================================================
# NOTICE DRAFTER
# ============================================================================

class NoticeDrafter:
    """
    Production-grade notice drafter with deterministic output.
    
    Generates official government notices in gazette-style format using RAG
    retrieval and LLM-based content generation. Implements confidence
    thresholding, output validation, and comprehensive error handling.
    
    Example:
        >>> drafter = NoticeDrafter(rag_engine, generator)
        >>> notice = drafter.draft_notice("PM-KISAN", "announcement", language="en")
        >>> print(notice.format_gazette_style())
    """
    
    # Class constants
    # CONFIDENCE_THRESHOLD = 0.6
    CONFIDENCE_THRESHOLD = 0.35
    TOP_K_RETRIEVAL = 5
    MAX_RETRIES = 2
    
    # Prompt templates for notice generation
    NOTICE_PROMPT_EN = """You are an official government notice drafter. Generate a formal government notice based on the provided scheme information.

SCHEME DATA:
{retrieved_content}

NOTICE REQUIREMENTS:
- Notice Type: {notice_type}
- Language: English
- Format: Official Government Gazette Style

Generate a structured notice with the following components in JSON format:

1. subject: A formal subject line (max 150 characters) for the notice
2. body: The main notice content (200-2000 words) with:
   - Opening paragraph introducing the scheme/update
   - Key details organized in numbered points or paragraphs
   - Eligibility, benefits, and application process (if applicable)
   - Contact information for queries
   - Professional, formal tone throughout
3. issuing_authority: Full name and title of issuing officer
4. signature_block: Signature line with designation

Return ONLY valid JSON in this exact format:
{{
    "subject": "...",
    "body": "...",
    "issuing_authority": "...",
    "signature_block": "..."
}}

Be formal, factual, and use official government notice language. Extract information only from the provided scheme data."""

    NOTICE_PROMPT_HI = """आप एक आधिकारिक सरकारी नोटिस ड्राफ्टर हैं। प्रदान की गई योजना जानकारी के आधार पर एक औपचारिक सरकारी नोटिस तैयार करें।

योजना डेटा:
{retrieved_content}

नोटिस आवश्यकताएं:
- नोटिस प्रकार: {notice_type}
- भाषा: हिंदी
- प्रारूप: आधिकारिक सरकारी राजपत्र शैली

निम्नलिखित घटकों के साथ JSON प्रारूप में एक संरचित नोटिस तैयार करें:

1. subject: नोटिस के लिए एक औपचारिक विषय पंक्ति (अधिकतम 150 अक्षर)
2. body: मुख्य नोटिस सामग्री (200-2000 शब्द) जिसमें शामिल हो:
   - योजना/अपडेट का परिचय देने वाला प्रारंभिक पैराग्राफ
   - क्रमांकित बिंदुओं या पैराग्राफ में व्यवस्थित मुख्य विवरण
   - पात्रता, लाभ और आवेदन प्रक्रिया (यदि लागू हो)
   - प्रश्नों के लिए संपर्क जानकारी
   - पूरे में पेशेवर, औपचारिक स्वर
3. issuing_authority: जारीकर्ता अधिकारी का पूरा नाम और पदनाम
4. signature_block: पदनाम के साथ हस्ताक्षर पंक्ति

इस सटीक प्रारूप में केवल मान्य JSON लौटाएं:
{{
    "subject": "...",
    "body": "...",
    "issuing_authority": "...",
    "signature_block": "..."
}}

औपचारिक, तथ्यात्मक रहें और आधिकारिक सरकारी नोटिस भाषा का उपयोग करें। केवल प्रदान किए गए योजना डेटा से जानकारी निकालें।"""
    
    def __init__(self, rag_engine: Any, answer_generator: Any):
        """
        Initialize notice drafter with dependencies.
        
        Args:
            rag_engine: RAGEngine instance for retrieval
            answer_generator: AnswerGenerator instance for LLM calls
        """
        self.rag_engine = rag_engine
        self.answer_generator = answer_generator
        self._cache: Dict[str, GovernmentNotice] = {}
        
        logger.info("NoticeDrafter initialized")
    
    def draft_notice(
        self,
        scheme_name: str,
        notice_type: NoticeType,
        language: Language = "en",
        issue_date: Optional[date] = None,
        effective_date: Optional[date] = None
    ) -> GovernmentNotice:
        """
        Generate an official government notice for a scheme.
        
        This method is deterministic: given the same inputs,
        it will produce the same output (assuming the knowledge base hasn't changed).
        
        Args:
            scheme_name: Name of the scheme (e.g., "PM-KISAN")
            notice_type: Type of notice to generate
            language: Output language ("en" or "hi")
            issue_date: Date of notice issuance (defaults to today)
            effective_date: Optional date when notice takes effect
        
        Returns:
            GovernmentNotice object with validated structured data
        
        Raises:
            SchemeNotFoundError: If scheme doesn't exist
            LowConfidenceError: If retrieval confidence < 0.6
            LLMUnavailableError: If LLM fails to generate
            ValidationError: If output fails validation
        
        Example:
            >>> notice = drafter.draft_notice("PM-KISAN", "announcement", "en")
            >>> print(notice.subject)
            'Notification regarding Pradhan Mantri Kisan Samman Nidhi Yojana'
        """
        # Input validation
        if not scheme_name or not scheme_name.strip():
            raise ValueError("scheme_name cannot be empty")
        
        scheme_name = scheme_name.strip()
        
        # Set default dates
        if issue_date is None:
            issue_date = date.today()
        
        # Check cache for deterministic output
        cache_key = self._generate_cache_key(
            scheme_name, notice_type, language, issue_date, effective_date
        )
        if cache_key in self._cache:
            logger.info(f"Cache hit for {scheme_name} notice ({notice_type}, {language})")
            return self._cache[cache_key]
        
        logger.info(f"Generating notice for {scheme_name} ({notice_type}, {language})")
        
        # Step 1: Retrieve scheme data using RAG
        retrieved_chunks = self._retrieve_scheme_data(scheme_name)
        
        # Step 2: Generate notice content using LLM
        generated_content = self._generate_notice_content(
            scheme_name,
            notice_type,
            retrieved_chunks,
            language
        )
        
        # Step 3: Build and validate notice
        notice = self._build_notice(
            scheme_name,
            notice_type,
            generated_content,
            retrieved_chunks,
            language,
            issue_date,
            effective_date
        )
        
        # Cache for future requests
        self._cache[cache_key] = notice
        
        logger.info(f"Successfully generated notice for {scheme_name}")
        return notice
    
    def _retrieve_scheme_data(
        self,
        scheme_name: str
    ) -> list:
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
    
    def _generate_notice_content(
        self,
        scheme_name: str,
        notice_type: NoticeType,
        retrieved_chunks: list,
        language: Language
    ) -> Dict[str, Any]:
        """
        Generate notice content using LLM.
        
        Args:
            scheme_name: Name of scheme
            notice_type: Type of notice
            retrieved_chunks: RAG retrieval results
            language: Target language
        
        Returns:
            Dictionary with generated notice fields
        
        Raises:
            LLMUnavailableError: If LLM fails
        """
        # Prepare context from retrieved chunks
        context = self._prepare_context(retrieved_chunks)
        
        # Select prompt based on language
        prompt_template = (
            self.NOTICE_PROMPT_HI if language == "hi"
            else self.NOTICE_PROMPT_EN
        )
        
        prompt = prompt_template.format(
            retrieved_content=context,
            notice_type=notice_type
        )
        
        # Call LLM directly with retry logic
        for attempt in range(self.MAX_RETRIES):
            try:
                # Access the LLM client directly
                llm_client = self.answer_generator.llm_client
                
                # Generate with higher token limit for notice content
                response_dict = llm_client.generate(
                    prompt=prompt,
                    temperature=0.2,  # Slightly higher for more natural text
                    max_tokens=2000   # Enough for full notice
                )
                
                if not response_dict or not response_dict.get('success'):
                    error_msg = response_dict.get('error', 'Unknown error') if response_dict else 'Empty response'
                    raise LLMUnavailableError(f"LLM generation failed: {error_msg}")
                
                # Extract text from response dict
                response_text = response_dict.get('response', '')
                
                if not response_text:
                    raise LLMUnavailableError("No response text in LLM output")
                
                # Parse JSON from LLM response
                generated = self._parse_llm_response(response_text)
                
                logger.info(f"Successfully generated notice content (attempt {attempt + 1})")
                return generated
                
            except Exception as e:
                logger.warning(f"Generation attempt {attempt + 1} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise LLMUnavailableError(str(e))
        
        raise LLMUnavailableError("Max retries exceeded")
    
    def _prepare_context(
        self,
        retrieved_chunks: list
    ) -> str:
        """
        Prepare context string from retrieved chunks.
        
        Args:
            retrieved_chunks: RAG retrieval results
        
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for score, metadata, explanation in retrieved_chunks:
            section_type = metadata.get("section_type", "general")
            content = metadata.get("content", explanation)
            
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
                "subject",
                "body",
                "issuing_authority",
                "signature_block"
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
    
    def _build_notice(
        self,
        scheme_name: str,
        notice_type: NoticeType,
        generated_content: Dict[str, Any],
        retrieved_chunks: list,
        language: Language,
        issue_date: date,
        effective_date: Optional[date]
    ) -> GovernmentNotice:
        """
        Build and validate GovernmentNotice object.
        
        Args:
            scheme_name: Name of scheme
            notice_type: Type of notice
            generated_content: LLM-generated fields
            retrieved_chunks: Original RAG results
            language: Output language
            issue_date: Date of issuance
            effective_date: Optional effective date
        
        Returns:
            Validated GovernmentNotice
        
        Raises:
            ValidationError: If validation fails
        """
        # Calculate metadata
        avg_confidence = sum(
            score for score, _, _ in retrieved_chunks
        ) / len(retrieved_chunks)
        
        source_count = len(retrieved_chunks)
        
        # Generate reference number
        ref_number = self._generate_reference_number(
            scheme_name, notice_type, issue_date
        )
        
        metadata = {
            "source_count": source_count,
            "confidence": round(avg_confidence, 3),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        # Create notice (validation happens in __post_init__)
        try:
            notice = GovernmentNotice(
                scheme_name=scheme_name,
                notice_type=notice_type,
                reference_number=ref_number,
                issue_date=issue_date,
                subject=generated_content["subject"],
                body=generated_content["body"],
                issuing_authority=generated_content["issuing_authority"],
                signature_block=generated_content["signature_block"],
                effective_date=effective_date,
                language=language,
                metadata=metadata
            )
            
            return notice
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise ValidationError("notice", str(e))
    
    def _generate_reference_number(
        self,
        scheme_name: str,
        notice_type: NoticeType,
        issue_date: date
    ) -> str:
        """
        Generate official reference number for notice.
        
        Args:
            scheme_name: Name of scheme
            notice_type: Type of notice
            issue_date: Date of issuance
        
        Returns:
            Reference number (e.g., "MoRD/PM-KISAN/ANN/2026/001")
        """
        # Extract scheme acronym
        acronym = ''.join([word[0] for word in scheme_name.upper().split('-')])
        
        # Notice type code
        type_codes = {
            "circular": "CIR",
            "order": "ORD",
            "memo": "MEM",
            "notification": "NOT",
            "advisory": "ADV",
            "amendment": "AMD",
        }
        type_code = type_codes.get(notice_type, "NOT")
        
        # Generate sequence number (deterministic based on date)
        sequence = str(issue_date.toordinal() % 1000).zfill(3)
        
        return f"MoRD/{acronym}/{type_code}/{issue_date.year}/{sequence}"
    
    def _generate_cache_key(
        self,
        scheme_name: str,
        notice_type: NoticeType,
        language: Language,
        issue_date: date,
        effective_date: Optional[date]
    ) -> str:
        """
        Generate deterministic cache key.
        
        Args:
            scheme_name: Name of scheme
            notice_type: Type of notice
            language: Language code
            issue_date: Issue date
            effective_date: Optional effective date
        
        Returns:
            SHA256 hash of inputs
        """
        key_data = (
            f"{scheme_name.upper()}:{notice_type}:{language}:"
            f"{issue_date.isoformat()}:{effective_date.isoformat() if effective_date else 'None'}"
        )
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