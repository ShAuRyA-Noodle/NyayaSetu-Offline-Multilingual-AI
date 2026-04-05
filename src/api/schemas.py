"""
API Schemas

Pydantic models for request validation and response serialization.
Comprehensive schemas for all NyayaSetu API endpoints.

Author: NyayaSetu Team
Version: 1.0.0
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# ============================================================================
# COMMON SCHEMAS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current timestamp")
    components: Dict[str, str] = Field(..., description="Component health status")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2026-01-05T10:30:00Z",
                "components": {
                    "database": "healthy",
                    "rag_engine": "healthy",
                    "llm": "healthy",
                    "vector_store": "healthy"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(..., description="Error timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid input data",
                "detail": "Field 'text' must be between 20-5000 characters",
                "timestamp": "2026-01-05T10:30:00Z"
            }
        }


# ============================================================================
# RAG Q&A SCHEMAS
# ============================================================================

class AskRequest(BaseModel):
    """Request for RAG-based question answering."""
    question: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Question about government schemes"
    )
    language: Literal["en", "hi"] = Field(
        default="en",
        description="Response language"
    )
    top_k: Optional[int] = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of context chunks to retrieve"
    )
    
    @validator("question")
    def validate_question(cls, v):
        """Validate question is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("Question cannot be empty or whitespace")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "question": "What are the eligibility criteria for PM-KISAN scheme?",
                "language": "en",
                "top_k": 5
            }
        }


class AskResponse(BaseModel):
    """Response for RAG-based question answering."""
    answer: str = Field(..., description="Generated answer")
    sources: List[Dict[str, Any]] = Field(..., description="Source chunks used")
    confidence: float = Field(..., description="Answer confidence score")
    language: str = Field(..., description="Response language")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "answer": "PM-KISAN provides income support of ₹6000 per year...",
                "sources": [
                    {
                        "scheme": "PM-KISAN",
                        "section": "eligibility",
                        "confidence": 0.89
                    }
                ],
                "confidence": 0.87,
                "language": "en",
                "metadata": {
                    "retrieval_time_ms": 45,
                    "generation_time_ms": 2340
                }
            }
        }


# ============================================================================
# SCHEME SUMMARIZER SCHEMAS
# ============================================================================

class SummarizeRequest(BaseModel):
    """Request for scheme summarization."""
    scheme_name: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Name of government scheme"
    )
    language: Literal["en", "hi"] = Field(
        default="en",
        description="Output language"
    )
    
    @validator("scheme_name")
    def validate_scheme_name(cls, v):
        """Validate scheme name."""
        if not v or not v.strip():
            raise ValueError("Scheme name cannot be empty")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "scheme_name": "PM-KISAN",
                "language": "en"
            }
        }


class SchemeSummaryResponse(BaseModel):
    """Response for scheme summarization."""
    scheme_name: str = Field(..., description="Scheme name")
    one_line_purpose: str = Field(..., description="One-line purpose")
    eligibility: List[str] = Field(..., description="Eligibility criteria")
    benefits: List[str] = Field(..., description="Scheme benefits")
    application_steps: List[str] = Field(..., description="Application steps")
    contact_info: Optional[str] = Field(None, description="Contact information")
    language: str = Field(..., description="Response language")
    metadata: Dict[str, Any] = Field(..., description="Summary metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "scheme_name": "PM-KISAN",
                "one_line_purpose": "Direct income support to farmers",
                "eligibility": [
                    "Landholding farmers",
                    "Agricultural land ownership",
                    "Valid Aadhaar card"
                ],
                "benefits": [
                    "₹6000 per year in 3 installments",
                    "Direct bank transfer",
                    "No intermediaries"
                ],
                "application_steps": [
                    "Visit PM-KISAN portal",
                    "Register with Aadhaar",
                    "Upload land documents",
                    "Submit application"
                ],
                "contact_info": "PM-KISAN Helpline: 155261",
                "language": "en",
                "metadata": {
                    "confidence": 0.89,
                    "source_count": 5
                }
            }
        }


# ============================================================================
# NOTICE DRAFTER SCHEMAS
# ============================================================================

class DraftNoticeRequest(BaseModel):
    """Request for notice drafting."""
    scheme_name: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Scheme name"
    )
    notice_type: Literal["circular", "order", "memo", "notification", "advisory", "amendment"] = Field(
        ...,
        description="Type of notice"
    )
    language: Literal["en", "hi"] = Field(
        default="en",
        description="Notice language"
    )
    effective_date: Optional[str] = Field(
        None,
        description="Effective date (YYYY-MM-DD format)"
    )
    
    @validator("scheme_name")
    def validate_scheme_name(cls, v):
        """Validate scheme name."""
        if not v or not v.strip():
            raise ValueError("Scheme name cannot be empty")
        return v.strip()
    
    @validator("effective_date")
    def validate_effective_date(cls, v):
        """Validate date format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "scheme_name": "PM-KISAN",
                "notice_type": "update",
                "language": "en",
                "effective_date": "2026-02-01"
            }
        }


class NoticeResponse(BaseModel):
    """Response for notice drafting."""
    reference_number: str = Field(..., description="Official reference number")
    notice_type: str = Field(..., description="Notice type")
    scheme_name: str = Field(..., description="Scheme name")
    issue_date: str = Field(..., description="Issue date")
    effective_date: Optional[str] = Field(None, description="Effective date")
    subject: str = Field(..., description="Notice subject")
    body: str = Field(..., description="Notice body text")
    formatted_notice: str = Field(..., description="Full formatted notice")
    language: str = Field(..., description="Notice language")
    metadata: Dict[str, Any] = Field(..., description="Notice metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "reference_number": "MoRD/PM-KISAN/UPDATE/2026/00001",
                "notice_type": "update",
                "scheme_name": "PM-KISAN",
                "issue_date": "2026-01-05",
                "effective_date": "2026-02-01",
                "subject": "Important Updates to PM-KISAN Scheme",
                "body": "This notice announces important updates...",
                "formatted_notice": "[Full gazette-formatted notice text]",
                "language": "en",
                "metadata": {
                    "confidence": 0.88,
                    "source_count": 5
                }
            }
        }


# ============================================================================
# GRIEVANCE ROUTER SCHEMAS
# ============================================================================

class RouteGrievanceRequest(BaseModel):
    """Request for grievance routing."""
    grievance_text: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Grievance/complaint description"
    )
    language: Literal["en", "hi"] = Field(
        default="en",
        description="Input language"
    )
    citizen_location: Optional[str] = Field(
        None,
        max_length=200,
        description="Citizen location (optional)"
    )
    
    @validator("grievance_text")
    def validate_grievance(cls, v):
        """Validate grievance text."""
        if not v or not v.strip():
            raise ValueError("Grievance text cannot be empty")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "grievance_text": "I have not received my PM-KISAN payment for the last 3 months. My registration number is ABC123.",
                "language": "en",
                "citizen_location": "Maharashtra"
            }
        }


class GrievanceRouteResponse(BaseModel):
    """Response for grievance routing."""
    grievance_id: str = Field(..., description="Unique grievance ID")
    department: str = Field(..., description="Target department")
    sub_department: Optional[str] = Field(None, description="Sub-department")
    priority: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Priority level"
    )
    category: str = Field(..., description="Grievance category")
    summary: str = Field(..., description="One-line summary")
    reasoning: str = Field(..., description="Routing reasoning")
    estimated_resolution_days: int = Field(..., description="Expected resolution time")
    related_schemes: List[str] = Field(..., description="Related schemes")
    language: str = Field(..., description="Response language")
    metadata: Dict[str, Any] = Field(..., description="Routing metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "grievance_id": "GR-20260105-00001",
                "department": "agriculture",
                "sub_department": "PM-KISAN Division",
                "priority": "high",
                "category": "payment_delay",
                "summary": "PM-KISAN payment delayed for 3 months",
                "reasoning": "The grievance concerns delayed benefit payments...",
                "estimated_resolution_days": 45,
                "related_schemes": ["PM-KISAN"],
                "language": "en",
                "metadata": {
                    "confidence": 0.89,
                    "method": "llm",
                    "source_count": 5
                }
            }
        }


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

class BatchSummarizeRequest(BaseModel):
    """Request for batch scheme summarization."""
    scheme_names: List[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="List of scheme names"
    )
    language: Literal["en", "hi"] = Field(default="en", description="Output language")
    
    @validator("scheme_names")
    def validate_schemes(cls, v):
        """Validate scheme names."""
        for name in v:
            if not name or not name.strip():
                raise ValueError("All scheme names must be non-empty")
        return [n.strip() for n in v]
    
    class Config:
        schema_extra = {
            "example": {
                "scheme_names": ["PM-KISAN", "PMAY", "MGNREGA"],
                "language": "en"
            }
        }


class BatchSummarizeResponse(BaseModel):
    """Response for batch summarization."""
    summaries: List[Dict[str, Any]] = Field(..., description="Scheme summaries")
    language: str = Field(..., description="Response language")
    metadata: Dict[str, Any] = Field(..., description="Batch metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "summaries": [
                    {
                        "scheme_name": "PM-KISAN",
                        "one_line_purpose": "Direct income support...",
                        "status": "success"
                    }
                ],
                "language": "en",
                "metadata": {
                    "total_count": 3,
                    "success_count": 3,
                    "failed_count": 0
                }
            }
        }


# ============================================================================
# STATISTICS & MONITORING
# ============================================================================

class StatsResponse(BaseModel):
    """API statistics response."""
    total_requests: int = Field(..., description="Total API requests")
    requests_by_endpoint: Dict[str, int] = Field(..., description="Requests per endpoint")
    cache_stats: Dict[str, Any] = Field(..., description="Cache statistics")
    uptime_seconds: float = Field(..., description="Service uptime")
    
    class Config:
        schema_extra = {
            "example": {
                "total_requests": 1523,
                "requests_by_endpoint": {
                    "/ask": 456,
                    "/summarize": 234,
                    "/grievances/route": 833
                },
                "cache_stats": {
                    "summarizer": {"size": 45, "hits": 123},
                    "router": {"size": 234, "hits": 567}
                },
                "uptime_seconds": 86400.5
            }
        }


# ============================================================================
# AUTHENTICATION SCHEMAS
# ============================================================================

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: Optional[str] = None
    role: Literal["citizen", "officer", "admin"] = "citizen"
    location: Optional[str] = None
    preferred_language: Literal["en", "hi"] = "en"
    officer_code: Optional[str] = None
    designation: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class RegisterResponse(BaseModel):
    success: bool
    message: str
    user: Dict[str, Any]


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    department: Optional[str] = None
    designation: Optional[str] = None
    location: Optional[str] = None


# ============================================================================
# GRIEVANCE MANAGEMENT SCHEMAS
# ============================================================================

class SubmitGrievanceRequest(BaseModel):
    citizen_name: Optional[str] = None
    citizen_phone: Optional[str] = None
    citizen_email: Optional[str] = None
    citizen_location: Optional[str] = None
    title: Optional[str] = None
    description: str = Field(..., min_length=10)
    category: Optional[str] = None
    language: Literal["en", "hi"] = "en"


class AcceptGrievanceRequest(BaseModel):
    officer_name: str
    notes: Optional[str] = None


class RejectGrievanceRequest(BaseModel):
    officer_name: str
    reason: str


class UpdateStatusRequest(BaseModel):
    new_status: str
    officer_name: str
    notes: Optional[str] = None


class ResolveGrievanceRequest(BaseModel):
    officer_name: str
    resolution_notes: str


# ============================================================================
# NOTICE MANAGEMENT SCHEMAS
# ============================================================================

class SaveDraftRequest(BaseModel):
    scheme_name: str
    notice_type: str = "circular"
    subject: str
    body: str
    formatted_notice: str = ""
    language: str = "en"
    effective_date: Optional[str] = None


class UpdateNoticeRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    formatted_notice: Optional[str] = None
    effective_date: Optional[str] = None


class UpdateSchemeMetadataRequest(BaseModel):
    scheme_name: Optional[str] = None
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_audience: Optional[str] = None
    department: Optional[str] = None
