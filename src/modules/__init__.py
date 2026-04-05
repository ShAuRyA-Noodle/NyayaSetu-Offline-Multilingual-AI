"""
NyayaSetu Modules Package

Production-grade modules for government scheme operations.

Modules:
    - Summarizer: Extract structured scheme summaries
    - NoticeDrafter: Generate official government notices
    - GrievanceRouter: AI-powered grievance routing
    - NyayaVaani: Voice-native cross-lingual governance
"""

# Module 1: Summarizer
from .summarizer import (
    SchemeSummarizer,
    SchemeSummary,
    SummarizerError,
    SchemeNotFoundError,
    LowConfidenceError,
    LLMUnavailableError,
    ValidationError as SummarizerValidationError
)

# Module 2: Notice Drafter
from .notice_drafter import (
    NoticeDrafter,
    GovernmentNotice,
    NoticeDrafterError,
    SchemeNotFoundError as NoticeDrafterSchemeNotFoundError,
    LLMUnavailableError as NoticeDrafterLLMUnavailableError,
    ValidationError as NoticeDrafterValidationError
)

# Module 3: Grievance Router
from .grievance_router import (
    GrievanceRouter,
    GrievanceRoute,
    GrievanceRouterError,
    InvalidGrievanceError,
    DepartmentUnavailableError,
    LowConfidenceError as RouterLowConfidenceError,
    LLMUnavailableError as RouterLLMUnavailableError,
    ValidationError as RouterValidationError,
    Department,
    Priority,
    Category
)

__all__ = [
    # Summarizer
    "SchemeSummarizer",
    "SchemeSummary",
    "SummarizerError",
    "SchemeNotFoundError",
    "LowConfidenceError",
    "LLMUnavailableError",
    "SummarizerValidationError",

    # Notice Drafter
    "NoticeDrafter",
    "GovernmentNotice",
    "NoticeDrafterError",
    "NoticeDrafterSchemeNotFoundError",
    "NoticeDrafterLLMUnavailableError",
    "NoticeDrafterValidationError",

    # Grievance Router
    "GrievanceRouter",
    "GrievanceRoute",
    "GrievanceRouterError",
    "InvalidGrievanceError",
    "DepartmentUnavailableError",
    "Department",
    "Priority",
    "Category"
]

__version__ = "1.0.0"
