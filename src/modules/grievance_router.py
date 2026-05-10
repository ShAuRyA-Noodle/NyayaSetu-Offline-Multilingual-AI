"""
Grievance Router Module

Production-grade router for citizen grievances with department taxonomy
classification, priority assignment, and resolution time estimation.

This module routes citizen complaints to the appropriate government department
using RAG-based context retrieval and LLM classification. It assigns priority
levels based on urgency indicators and estimates resolution times based on
complaint categories.

Author: NyayaSetu Team
Version: 1.0.0
"""

# ============================================================================
# SECTION 1: IMPORTS
# ============================================================================
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, date
import hashlib
import json
import logging
import re

import cachetools

# Sanitizer for citizen-controlled inputs (grievance text flows into the prompt).
try:
    from ..generation.prompt_templates import sanitize_user_input
except ImportError:
    from generation.prompt_templates import sanitize_user_input

# Type aliases for clarity
Language = Literal["en", "hi"]

Department = Literal[
    "agriculture",           # Agriculture & Farmers Welfare
    "rural_development",     # Rural Development
    "urban_development",     # Housing & Urban Affairs
    "social_welfare",        # Social Justice & Empowerment
    "health",               # Health & Family Welfare
    "education",            # Education
    "finance",              # Finance/Banking
    "law_enforcement",      # Police/Justice
    "infrastructure",       # Roads/Transport
    "employment"            # Labour & Employment
]

Priority = Literal["low", "medium", "high", "critical"]

Category = Literal[
    "scheme_eligibility",    # Questions about qualifying for schemes
    "payment_delay",         # Benefit payment not received
    "application_rejected",  # Application denial
    "documentation",         # Missing/incorrect documents
    "corruption",           # Bribery/corruption complaint
    "service_denial",       # Service not provided
    "quality_complaint",    # Poor service quality
    "information_request",  # General information query
    "other"                 # Uncategorized
]

logger = logging.getLogger(__name__)

# ============================================================================
# SECTION 2: EXCEPTIONS
# ============================================================================

class GrievanceRouterError(Exception):
    """Base exception for grievance router module."""
    pass


class InvalidGrievanceError(GrievanceRouterError):
    """Raised when grievance text is invalid or too short."""
    
    def __init__(self, reason: str):
        """
        Initialize exception with reason.
        
        Args:
            reason: Detailed explanation of why grievance is invalid
        """
        self.reason = reason
        super().__init__(f"Invalid grievance: {reason}")


class DepartmentUnavailableError(GrievanceRouterError):
    """Raised when routed department is not supported."""
    
    def __init__(self, department: str):
        """
        Initialize exception with department name.
        
        Args:
            department: Name of unavailable department
        """
        self.department = department
        super().__init__(f"Department '{department}' not available in system")


class LowConfidenceError(GrievanceRouterError):
    """Raised when routing confidence is below acceptable threshold."""
    
    def __init__(self, confidence: float, threshold: float = 0.5):
        """
        Initialize exception with confidence metrics.
        
        Args:
            confidence: Calculated confidence score
            threshold: Minimum required confidence
        """
        self.confidence = confidence
        self.threshold = threshold
        super().__init__(
            f"Routing confidence {confidence:.2f} below threshold {threshold:.2f}"
        )


class LLMUnavailableError(GrievanceRouterError):
    """Raised when LLM classification fails."""
    
    def __init__(self, details: str):
        """
        Initialize exception with error details.
        
        Args:
            details: Detailed error information from LLM
        """
        self.details = details
        super().__init__(f"LLM classification unavailable: {details}")


class ValidationError(GrievanceRouterError):
    """Raised when route validation fails."""
    
    def __init__(self, field: str, reason: str):
        """
        Initialize exception with field context.
        
        Args:
            field: Name of field that failed validation
            reason: Detailed explanation of validation failure
        """
        self.field = field
        self.reason = reason
        super().__init__(f"Validation failed for '{field}': {reason}")


# ============================================================================
# SECTION 3: DATA MODELS
# ============================================================================

@dataclass
class GrievanceRoute:
    """
    Structured routing decision for citizen grievance.
    
    This dataclass encapsulates the complete routing decision including
    target department, priority level, category classification, and
    metadata about the routing process.
    
    Attributes:
        grievance_id: Unique identifier in format GR-YYYYMMDD-XXXXX
        department: Target department for handling grievance
        sub_department: Optional specific division or office
        priority: Urgency level (low/medium/high/critical)
        category: Grievance category classification
        summary: One-line summary (10-100 characters)
        reasoning: Detailed routing explanation (50-200 words)
        estimated_resolution_days: Expected resolution time (1-90 days)
        related_schemes: List of relevant government schemes (0-3)
        language: Input language code
        metadata: Additional context including confidence and timestamps
    
    Example:
        >>> route = GrievanceRoute(
        ...     grievance_id="GR-20260105-00001",
        ...     department="agriculture",
        ...     priority="high",
        ...     category="payment_delay",
        ...     summary="PM-KISAN payment delayed 3 months",
        ...     reasoning="Grievance concerns delayed benefit payment...",
        ...     estimated_resolution_days=45,
        ...     related_schemes=["PM-KISAN"],
        ...     language="en"
        ... )
    """
    grievance_id: str
    department: Department
    sub_department: Optional[str]
    priority: Priority
    category: Category
    summary: str
    reasoning: str
    estimated_resolution_days: int
    related_schemes: List[str]
    language: Language
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate route data after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """
        Perform comprehensive validation of routing decision.
        
        Validation Rules:
        1. grievance_id format: GR-YYYYMMDD-XXXXX
        2. department: Cannot be empty
        3. summary: 10-100 characters
        4. reasoning: 50-200 words
        5. estimated_resolution_days: 1-90 days
        6. related_schemes: Maximum 3 items
        
        Raises:
            ValidationError: If any validation rule fails
        """
        # Validate grievance_id format
        if not re.match(r'^GR-\d{8}-\d{5}$', self.grievance_id):
            raise ValidationError(
                "grievance_id",
                f"Invalid format (expected GR-YYYYMMDD-XXXXX, got {self.grievance_id})"
            )
        
        # Validate department is not empty
        if not self.department or not self.department.strip():
            raise ValidationError("department", "Cannot be empty")
        
        # Validate summary length
        summary_len = len(self.summary)
        if not (10 <= summary_len <= 100):
            raise ValidationError(
                "summary",
                f"Must be 10-100 characters (got {summary_len})"
            )
        
        # Validate summary is not empty/whitespace
        if not self.summary.strip():
            raise ValidationError("summary", "Cannot be empty or whitespace")
        
        # Validate reasoning word count
        word_count = len(self.reasoning.split())
        if not (10 <= word_count <= 200):
            raise ValidationError(
                "reasoning",
                f"Must be 50-200 words (got {word_count})"
            )
        
        # Validate reasoning is not empty
        if not self.reasoning.strip():
            raise ValidationError("reasoning", "Cannot be empty or whitespace")
        
        # Validate estimated resolution days range
        if not (1 <= self.estimated_resolution_days <= 90):
            raise ValidationError(
                "estimated_resolution_days",
                f"Must be 1-90 days (got {self.estimated_resolution_days})"
            )
        
        # Validate related schemes count
        if len(self.related_schemes) > 3:
            raise ValidationError(
                "related_schemes",
                f"Maximum 3 schemes allowed (got {len(self.related_schemes)})"
            )
        
        # Validate related schemes are non-empty strings
        for idx, scheme in enumerate(self.related_schemes):
            if not scheme or not scheme.strip():
                raise ValidationError(
                    "related_schemes",
                    f"Scheme at index {idx} cannot be empty"
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert route to dictionary for serialization.
        
        Returns:
            Dictionary containing all route fields
        """
        return {
            "grievance_id": self.grievance_id,
            "department": self.department,
            "sub_department": self.sub_department,
            "priority": self.priority,
            "category": self.category,
            "summary": self.summary,
            "reasoning": self.reasoning,
            "estimated_resolution_days": self.estimated_resolution_days,
            "related_schemes": self.related_schemes,
            "language": self.language,
            "metadata": self.metadata
        }
    
    def format_ticket(self) -> str:
        """
        Format route as support ticket for display.
        
        Returns:
            Formatted ticket text with all routing details
        """
        ticket = f"""
{'='*70}
GRIEVANCE ROUTING TICKET
{'='*70}

Grievance ID: {self.grievance_id}
Timestamp: {self.metadata.get('timestamp', 'N/A')}

ROUTING DECISION:
  Department: {self.department.upper()}
  Sub-Department: {self.sub_department or 'N/A'}
  Priority: {self.priority.upper()}
  Category: {self.category.replace('_', ' ').title()}

SUMMARY:
  {self.summary}

REASONING:
  {self.reasoning}

RESOLUTION:
  Estimated Days: {self.estimated_resolution_days}

RELATED SCHEMES:
  {', '.join(self.related_schemes) if self.related_schemes else 'None'}

METADATA:
  Confidence: {self.metadata.get('confidence', 'N/A')}
  Source Count: {self.metadata.get('source_count', 0)}
  Method: {self.metadata.get('method', 'N/A')}
  Language: {self.language.upper()}

{'='*70}
"""
        return ticket.strip()


# ============================================================================
# SECTION 4: MAIN CLASS
# ============================================================================

class GrievanceRouter:
    """
    Production-grade grievance router with department classification.
    
    Routes citizen complaints to appropriate government departments using
    RAG retrieval for context and LLM for classification. Assigns priority
    levels based on urgency indicators and estimates resolution time based
    on grievance category.
    
    The router uses a two-stage approach:
    1. Context Retrieval: Uses RAG to find relevant government schemes
    2. LLM Classification: Uses LLM to classify department and category
    
    If LLM fails, falls back to keyword-based classification to ensure
    robustness in production environments.
    
    Example:
        >>> router = GrievanceRouter(rag_engine, answer_generator)
        >>> route = router.route_grievance(
        ...     "My PM-KISAN payment hasn't arrived for 3 months",
        ...     language="en"
        ... )
        >>> print(route.department)
        'agriculture'
        >>> print(route.priority)
        'high'
    """
    
    # Class constants
    CONFIDENCE_THRESHOLD = 0.5  # Lower than summarizer (routing is harder)
    TOP_K_RETRIEVAL = 5
    MAX_RETRIES = 2
    
    # Department taxonomy with keywords for fallback classification
    DEPARTMENT_KEYWORDS = {
        "agriculture": [
            "farm", "crop", "kisan", "agriculture", "irrigation", "land",
            "farmer", "cultivation", "harvest", "seed", "fertilizer"
        ],
        "rural_development": [
            "rural", "village", "gram", "panchayat", "mgnrega", "nrega",
            "employment guarantee", "rural employment", "rural work"
        ],
        "urban_development": [
            "urban", "city", "housing", "pmay", "awas", "slum",
            "municipality", "municipal", "urban housing"
        ],
        "social_welfare": [
            "pension", "disability", "widow", "old age", "welfare",
            "senior citizen", "divyang", "handicapped", "aged"
        ],
        "health": [
            "hospital", "medicine", "doctor", "health", "ayushman",
            "medical", "treatment", "clinic", "healthcare"
        ],
        "education": [
            "school", "scholarship", "student", "education", "teacher",
            "college", "university", "study", "learning"
        ],
        "finance": [
            "bank", "loan", "account", "money", "payment", "subsidy",
            "banking", "finance", "credit", "deposit"
        ],
        "law_enforcement": [
            "police", "fir", "crime", "court", "justice", "legal",
            "law", "complaint", "theft", "assault"
        ],
        "infrastructure": [
            "road", "bridge", "transport", "railway", "highway",
            "infrastructure", "construction", "building"
        ],
        "employment": [
            "job", "employment", "unemployment", "skill", "training",
            "work", "career", "placement", "hiring"
        ]
    }
    
    # Priority keywords for automatic assignment.
    # Includes Hindi-script equivalents so we don't accidentally down-prioritise
    # a life-threatening Hindi grievance just because it lacks English markers.
    CRITICAL_KEYWORDS = [
        # English
        "urgent", "emergency", "immediate", "death", "violence", "threat",
        "danger", "critical", "serious injury", "hospital emergency",
        "life threatening", "grave", "severe",
        # Hindi
        "मरना", "आपातकाल", "जान", "गंभीर", "चोट", "मौत",
    ]
    
    HIGH_PRIORITY_CATEGORIES = ["payment_delay", "corruption", "service_denial"]
    
    # Resolution time estimates (days) by category
    RESOLUTION_ESTIMATES = {
        "information_request": 7,
        "scheme_eligibility": 14,
        "documentation": 21,
        "application_rejected": 30,
        "payment_delay": 45,
        "quality_complaint": 30,
        "service_denial": 21,
        "corruption": 60,
        "other": 30
    }
    
    # Prompt templates for LLM classification
    ROUTING_PROMPT_EN = """You are a government grievance classification expert. Analyze the citizen's complaint and route it to the correct department.

GRIEVANCE:
{grievance_text}

RELEVANT CONTEXT (from knowledge base):
{context}

DEPARTMENT OPTIONS:
{departments}

CATEGORY OPTIONS:
{categories}

Analyze the grievance and provide routing decision in JSON format:

{{
    "department": "[one of the department options]",
    "sub_department": "[optional specific division/office or null]",
    "category": "[one of the category options]",
    "summary": "[one-line summary in 10-100 characters]",
    "reasoning": "[50-200 word explanation of why this routing, referencing specific details from the grievance]",
    "related_schemes": ["scheme1", "scheme2"]
}}

IMPORTANT:
- Be specific in reasoning. Reference exact keywords from the grievance.
- If multiple departments could apply, choose the PRIMARY one.
- Related schemes should be 0-3 relevant schemes if any are mentioned or implied.
- Return ONLY valid JSON, no additional text."""

    ROUTING_PROMPT_HI = """आप एक सरकारी शिकायत वर्गीकरण विशेषज्ञ हैं। नागरिक की शिकायत का विश्लेषण करें और सही विभाग में भेजें।

शिकायत:
{grievance_text}

प्रासंगिक संदर्भ (ज्ञान आधार से):
{context}

विभाग विकल्प:
{departments}

श्रेणी विकल्प:
{categories}

शिकायत का विश्लेषण करें और JSON प्रारूप में रूटिंग निर्णय प्रदान करें:

{{
    "department": "[विभाग विकल्पों में से एक]",
    "sub_department": "[वैकल्पिक विशिष्ट प्रभाग/कार्यालय या null]",
    "category": "[श्रेणी विकल्पों में से एक]",
    "summary": "[10-100 अक्षरों में एक पंक्ति सारांश]",
    "reasoning": "[50-200 शब्दों में इस रूटिंग का स्पष्टीकरण, शिकायत से विशिष्ट विवरण का संदर्भ]",
    "related_schemes": ["योजना1", "योजना2"]
}}

महत्वपूर्ण:
- तर्क में विशिष्ट रहें। शिकायत से सटीक कीवर्ड का संदर्भ दें।
- संबंधित योजनाएं 0-3 प्रासंगिक योजनाएं होनी चाहिए यदि कोई हो।
- केवल मान्य JSON लौटाएं, कोई अतिरिक्त पाठ नहीं।"""
    
    def __init__(self, rag_engine: Any, answer_generator: Any):
        """
        Initialize grievance router with dependencies.
        
        Args:
            rag_engine: RAGEngine instance for context retrieval
            answer_generator: AnswerGenerator instance for LLM classification
        """
        self.rag_engine = rag_engine
        self.answer_generator = answer_generator
        # Bounded LRU — was an unbounded dict.
        self._cache: "cachetools.LRUCache[str, GrievanceRoute]" = cachetools.LRUCache(maxsize=500)
        self._grievance_counter = 0  # For generating unique IDs

        logger.info("GrievanceRouter initialized (LRU cache size=500)")
    
    def invalidate_route_cache(
        self,
        grievance_text: str,
        language: Language = "en",
    ) -> bool:
        """Drop a cached routing decision so a re-route picks fresh context.

        Admin-only callers should use this when they need to reroute a
        grievance (e.g. department reorganisation, mis-classification).
        Returns True if a cache entry was actually evicted.
        """
        cache_key = self._generate_cache_key(grievance_text, language)
        return self._cache.pop(cache_key, None) is not None

    def route_grievance(
        self,
        grievance_text: str,
        language: Language = "en",
        citizen_location: Optional[str] = None,
        force_refresh: bool = False,
    ) -> GrievanceRoute:
        """
        Route citizen grievance to appropriate department.
        
        This method is deterministic: same grievance text produces same route.
        Uses caching to ensure consistency and improve performance.
        
        Process:
        1. Validate input
        2. Check cache for existing route
        3. Retrieve context using RAG
        4. Classify using LLM (with fallback to keywords)
        5. Assign priority based on keywords and category
        6. Estimate resolution time
        7. Build and validate route
        
        Args:
            grievance_text: Citizen's complaint description (20-5000 chars)
            language: Input language (en or hi)
            citizen_location: Optional location for context (not used currently)
        
        Returns:
            GrievanceRoute with validated routing decision
        
        Raises:
            InvalidGrievanceError: If text too short/long/invalid
            LowConfidenceError: If classification confidence too low
            LLMUnavailableError: If LLM fails completely
            ValidationError: If route validation fails
        
        Example:
            >>> route = router.route_grievance(
            ...     "My pension payment is delayed by 2 months",
            ...     language="en"
            ... )
            >>> print(f"{route.department} - {route.priority}")
            'social_welfare - high'
        """
        # Input validation
        if not grievance_text or not grievance_text.strip():
            raise InvalidGrievanceError("Grievance text cannot be empty")
        
        grievance_text = grievance_text.strip()
        
        if len(grievance_text) < 20:
            raise InvalidGrievanceError(
                f"Grievance too short (min 20 chars, got {len(grievance_text)})"
            )
        
        if len(grievance_text) > 5000:
            raise InvalidGrievanceError(
                f"Grievance too long (max 5000 chars, got {len(grievance_text)})"
            )
        
        # Check cache (skip if admin asked for a re-route).
        cache_key = self._generate_cache_key(grievance_text, language)
        if force_refresh:
            self._cache.pop(cache_key, None)
            logger.info("Forced cache refresh for grievance routing")
        elif cache_key in self._cache:
            logger.info("Cache hit for grievance routing")
            return self._cache[cache_key]
        
        logger.info(f"Routing grievance ({language}, {len(grievance_text)} chars)")
        
        # Step 1: Retrieve relevant context using RAG
        context_chunks = self._retrieve_context(grievance_text)
        
        # Step 2: Classify using LLM
        classification = self._classify_grievance(
            grievance_text,
            context_chunks,
            language
        )
        
        # Step 3: Assign priority
        priority = self._assign_priority(grievance_text, classification["category"])
        
        # Step 4: Estimate resolution time
        resolution_days = self._estimate_resolution_time(classification["category"])
        
        # Step 5: Generate grievance ID
        grievance_id = self._generate_grievance_id()
        
        # Step 6: Build and validate route
        route = self._build_route(
            grievance_id,
            grievance_text,
            classification,
            priority,
            resolution_days,
            context_chunks,
            language
        )
        
        # Cache result
        self._cache[cache_key] = route
        
        logger.info(
            f"Grievance routed: {route.department} "
            f"(priority: {route.priority}, category: {route.category})"
        )
        return route
    
    def _retrieve_context(self, grievance_text: str) -> list:
        """
        Retrieve relevant context from knowledge base.
        
        Uses RAG to find relevant government schemes and information
        that might help classify the grievance.
        
        Args:
            grievance_text: Grievance description
        
        Returns:
            List of (score, metadata, explanation) tuples
        """
        try:
            # Use grievance text as query
            results = self.rag_engine.retrieve(
                query=grievance_text,
                top_k=self.TOP_K_RETRIEVAL
            )
            
            if not results:
                # No context available - will classify based on keywords only
                logger.warning("No context retrieved from RAG")
                return []
            
            # Lower confidence threshold for routing (0.5 vs 0.6)
            avg_confidence = sum(score for score, _, _ in results) / len(results)
            
            if avg_confidence < self.CONFIDENCE_THRESHOLD:
                logger.warning(f"Low context confidence: {avg_confidence:.3f}")
                # Don't raise error - proceed with available context
            
            logger.info(
                f"Retrieved {len(results)} context chunks "
                f"(confidence: {avg_confidence:.3f})"
            )
            return results
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            # Proceed without context
            return []
    
    def _classify_grievance(
        self,
        grievance_text: str,
        context_chunks: list,
        language: Language
    ) -> Dict[str, Any]:
        """
        Classify grievance using LLM with keyword fallback.
        
        CRITICAL: This is where LLM routing happens.
        
        Args:
            grievance_text: Grievance description
            context_chunks: RAG context results
            language: Input language
        
        Returns:
            Dictionary with classification fields
        
        Raises:
            LLMUnavailableError: If classification fails completely
        """
        # Prepare context string
        context = self._prepare_context(context_chunks) if context_chunks else \
                  "No specific context available. Classify based on keywords and department taxonomy."
        
        # Prepare department and category lists for prompt
        departments = ", ".join([
            f'"{dept}"' for dept in [
                "agriculture", "rural_development", "urban_development",
                "social_welfare", "health", "education", "finance",
                "law_enforcement", "infrastructure", "employment"
            ]
        ])
        
        categories = ", ".join([
            f'"{cat}"' for cat in [
                "scheme_eligibility", "payment_delay", "application_rejected",
                "documentation", "corruption", "service_denial",
                "quality_complaint", "information_request", "other"
            ]
        ])
        
        # Sanitize the citizen-supplied text BEFORE it interpolates into the
        # prompt. Otherwise an attacker who learns the template can inject
        # `### IGNORE ABOVE...` and re-route grievances.
        safe_grievance = sanitize_user_input(grievance_text, max_len=5000)

        # Select prompt template
        prompt_template = self.ROUTING_PROMPT_HI if language == "hi" else self.ROUTING_PROMPT_EN
        prompt = prompt_template.format(
            grievance_text=safe_grievance,
            context=context,
            departments=departments,
            categories=categories
        )

        # Call LLM with retry logic
        for attempt in range(self.MAX_RETRIES):
            try:
                # CRITICAL: Access LLM client directly
                llm_client = self.answer_generator.llm_client

                # temperature=0.0 — routing must be deterministic. The same
                # grievance text routed twice MUST land in the same dept,
                # else admins lose confidence in the system.
                response_dict = llm_client.generate(
                    prompt=prompt,
                    temperature=0.0,
                    max_tokens=1000
                )
                
                if not response_dict or not response_dict.get('success'):
                    error_msg = response_dict.get('error', 'Unknown') if response_dict else 'Empty'
                    raise LLMUnavailableError(f"Classification failed: {error_msg}")
                
                response_text = response_dict.get('response', '')
                
                if not response_text:
                    raise LLMUnavailableError("No response text")
                
                # Parse JSON
                classification = self._parse_llm_response(response_text)
                
                # Validate department and category are valid
                self._validate_classification(classification)
                
                logger.info(f"Classification successful (attempt {attempt + 1})")
                return classification
                
            except Exception as e:
                logger.warning(f"Classification attempt {attempt + 1} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    # Fallback: Use keyword-based classification
                    logger.error("LLM classification failed, using keyword fallback")
                    return self._keyword_based_classification(grievance_text, language)
        
        raise LLMUnavailableError("Max retries exceeded")
    
    def _keyword_based_classification(
        self,
        grievance_text: str,
        language: Language
    ) -> Dict[str, Any]:
        """
        Fallback classification using keywords when LLM fails.
        
        This ensures the router is always available even when LLM is down.
        
        Args:
            grievance_text: Grievance description
            language: Input language
        
        Returns:
            Basic classification based on keyword matching
        """
        text_lower = grievance_text.lower()
        
        # Score each department by keyword matches
        department_scores = {}
        for dept, keywords in self.DEPARTMENT_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            department_scores[dept] = score
        
        # Select department with highest score
        best_dept = max(department_scores.items(), key=lambda x: x[1])[0]
        
        # Determine category by keywords
        if any(kw in text_lower for kw in ["payment", "money", "received", "pending", "delayed"]):
            category = "payment_delay"
        elif any(kw in text_lower for kw in ["reject", "denied", "refused", "rejection"]):
            category = "application_rejected"
        elif any(kw in text_lower for kw in ["document", "paper", "certificate", "proof"]):
            category = "documentation"
        elif any(kw in text_lower for kw in ["eligible", "qualify", "apply", "application"]):
            category = "scheme_eligibility"
        elif any(kw in text_lower for kw in ["corrupt", "bribe", "illegal", "fraud"]):
            category = "corruption"
        elif any(kw in text_lower for kw in ["not provided", "denied service", "refused"]):
            category = "service_denial"
        elif any(kw in text_lower for kw in ["poor", "bad", "quality", "complaint"]):
            category = "quality_complaint"
        elif any(kw in text_lower for kw in ["information", "details", "tell me", "know"]):
            category = "information_request"
        else:
            category = "other"
        
        # Generate basic summary
        summary = grievance_text[:80] + "..." if len(grievance_text) > 80 else grievance_text
        if len(summary) < 10:
            summary = "Grievance requires attention from " + best_dept
        
        # Generate reasoning
        reasoning = (
            f"Routed to {best_dept} department based on keyword analysis of the grievance text. "
            f"The complaint contains keywords and phrases commonly associated with this department's jurisdiction. "
            f"Classified as {category} based on typical pattern matching. "
            f"This is a fallback classification method used when the primary LLM-based routing system is unavailable. "
            f"The routing should be reviewed by department staff for accuracy."
        )
        
        return {
            "department": best_dept,
            "sub_department": None,
            "category": category,
            "summary": summary[:100],
            "reasoning": reasoning,
            "related_schemes": []
        }
    
    def _validate_classification(self, classification: Dict[str, Any]) -> None:
        """
        Validate classification contains valid values.
        
        Args:
            classification: LLM output
        
        Raises:
            DepartmentUnavailableError: If department invalid
            ValidationError: If category invalid
        """
        valid_departments = [
            "agriculture", "rural_development", "urban_development",
            "social_welfare", "health", "education", "finance",
            "law_enforcement", "infrastructure", "employment"
        ]
        
        valid_categories = [
            "scheme_eligibility", "payment_delay", "application_rejected",
            "documentation", "corruption", "service_denial",
            "quality_complaint", "information_request", "other"
        ]
        
        dept = classification.get("department", "")
        if dept not in valid_departments:
            raise DepartmentUnavailableError(dept)
        
        cat = classification.get("category", "")
        if cat not in valid_categories:
            raise ValidationError("category", f"Invalid category: {cat}")
    
    def _assign_priority(
        self,
        grievance_text: str,
        category: Category
    ) -> Priority:
        """
        Auto-assign priority based on keywords and category.
        
        Priority Assignment Rules:
        - CRITICAL: Emergency keywords OR corruption/service denial
        - HIGH: Payment delays, application rejections, documentation
        - MEDIUM: Quality complaints, scheme eligibility
        - LOW: Information requests, other
        
        Args:
            grievance_text: Grievance description
            category: Classified category
        
        Returns:
            Priority level
        """
        text_lower = grievance_text.lower()

        # Check for critical keywords. Devanagari letters are unaffected by
        # .lower(), so the same haystack works for English + Hindi entries.
        if any(keyword in text_lower for keyword in self.CRITICAL_KEYWORDS):
            return "critical"
        
        # Check category-based priority
        if category in self.HIGH_PRIORITY_CATEGORIES:
            return "high"
        
        # Check for medium priority indicators
        if category in ["application_rejected", "documentation", "quality_complaint"]:
            return "medium"
        
        # Check for high priority payment delays (>30 days mentioned)
        if category == "payment_delay":
            # Look for duration indicators
            if any(str(i) for i in range(2, 13) if f"{i} month" in text_lower):
                return "high"
        
        # Default to low for informational queries
        return "low"
    
    def _estimate_resolution_time(self, category: Category) -> int:
        """
        Estimate resolution time in days based on category.
        
        Args:
            category: Grievance category
        
        Returns:
            Estimated days to resolution
        """
        return self.RESOLUTION_ESTIMATES.get(category, 30)
    
    def _generate_grievance_id(self) -> str:
        """
        Generate unique grievance ID.

        Format: GR-YYYYMMDD-XXXXX
        Example: GR-20260105-00123

        Queries the DB for today's highest counter so the sequence survives
        process restarts (previously counter was purely in-memory and collided
        after any restart).
        """
        today = date.today()
        date_str = today.strftime("%Y%m%d")
        prefix = f"GR-{date_str}-"

        # Resolve the next counter by looking at what's actually in the DB.
        # Works for both SQLite and Postgres.
        try:
            from src.api.database import get_db
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT grievance_id FROM grievances "
                    "WHERE grievance_id LIKE ? "
                    "ORDER BY grievance_id DESC LIMIT 1",
                    (f"{prefix}%",),
                )
                row = cursor.fetchone()
                if row:
                    last_id = row[0] if not hasattr(row, "keys") else row["grievance_id"]
                    try:
                        last_seq = int(last_id.rsplit("-", 1)[-1])
                    except (ValueError, IndexError):
                        last_seq = 0
                    next_seq = max(last_seq + 1, self._grievance_counter + 1)
                else:
                    next_seq = self._grievance_counter + 1
            self._grievance_counter = next_seq
        except Exception:
            # If DB lookup fails, fall back to in-memory counter
            self._grievance_counter += 1
            next_seq = self._grievance_counter

        sequence = str(next_seq).zfill(5)
        return f"{prefix}{sequence}"
    
    def _prepare_context(self, context_chunks: list) -> str:
        """
        Prepare context string from RAG results.
        
        Args:
            context_chunks: List of (score, metadata, explanation) tuples
        
        Returns:
            Formatted context string
        """
        if not context_chunks:
            return "No specific context available."

        context_parts = []
        for _score, metadata, explanation in context_chunks:
            scheme = metadata.get("scheme_name", "Unknown")
            section = metadata.get("section_type", "general")
            # Read embedded chunk text from metadata['content'] (chunker now
            # writes it there). Fall back to explanation for resilience.
            content = metadata.get("content") or explanation
            context_parts.append(f"[{scheme} - {section}]\n{content}\n")

        return "\n".join(context_parts)
    
    def _parse_llm_response(self, response: Any) -> Dict[str, Any]:
        """
        Parse JSON from LLM response with error handling.
        
        CRITICAL: Must handle markdown code blocks, extra text, etc.
        
        Args:
            response: Raw LLM response
        
        Returns:
            Parsed dictionary
        
        Raises:
            LLMUnavailableError: If parsing fails
        """
        try:
            # Handle dict vs string
            if isinstance(response, dict):
                data = response
            else:
                response = response.strip()
                
                # Extract JSON from markdown code blocks
                if "```" in response:
                    lines = response.split("\n")
                    json_lines = []
                    in_json = False
                    
                    for line in lines:
                        if line.startswith("```"):
                            in_json = not in_json
                            continue
                        if in_json or not line.startswith("```"):
                            json_lines.append(line)
                    
                    response = "\n".join(json_lines).strip()
                
                # Find JSON boundaries
                start_idx = response.find('{')
                end_idx = response.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response[start_idx:end_idx+1]
                else:
                    json_str = response
                
                # Parse JSON
                data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ["department", "category", "summary", "reasoning"]
            
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            raise LLMUnavailableError(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            raise LLMUnavailableError(f"Failed to parse response: {e}")
    
    def _build_route(
        self,
        grievance_id: str,
        grievance_text: str,
        classification: Dict[str, Any],
        priority: Priority,
        resolution_days: int,
        context_chunks: list,
        language: Language
    ) -> GrievanceRoute:
        """
        Build and validate GrievanceRoute object.
        
        Args:
            grievance_id: Generated unique ID
            grievance_text: Original grievance text
            classification: LLM classification results
            priority: Assigned priority level
            resolution_days: Estimated resolution days
            context_chunks: RAG context results
            language: Input language
        
        Returns:
            Validated GrievanceRoute instance
        
        Raises:
            ValidationError: If route validation fails
        """
        # Calculate confidence from context
        if context_chunks:
            avg_confidence = sum(s for s, _, _ in context_chunks) / len(context_chunks)
        else:
            avg_confidence = 0.3  # Low confidence without context
        
        # Build metadata
        metadata = {
            "source_count": len(context_chunks),
            "confidence": round(avg_confidence, 3),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "method": "llm" if context_chunks else "keyword_fallback",
            "grievance_length": len(grievance_text)
        }
        
        try:
            # Create GrievanceRoute (validation happens in __post_init__)
            route = GrievanceRoute(
                grievance_id=grievance_id,
                department=classification["department"],
                sub_department=classification.get("sub_department"),
                priority=priority,
                category=classification["category"],
                summary=classification["summary"],
                reasoning=classification["reasoning"],
                estimated_resolution_days=resolution_days,
                related_schemes=classification.get("related_schemes", []),
                language=language,
                metadata=metadata
            )
            return route
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError("route", str(e))
    
    def _generate_cache_key(
        self,
        grievance_text: str,
        language: Language
    ) -> str:
        """
        Generate deterministic cache key using SHA256.
        
        Args:
            grievance_text: Grievance description
            language: Input language
        
        Returns:
            SHA256 hash as cache key
        """
        key_data = f"{grievance_text}:{language}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def clear_cache(self) -> None:
        """Clear the in-memory cache and reset counter."""
        self._cache.clear()
        self._grievance_counter = 0
        logger.info("Grievance router cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache size and routing count
        """
        return {
            "size": len(self._cache),
            "max_size": 1000,
            "total_routed": self._grievance_counter
        }
