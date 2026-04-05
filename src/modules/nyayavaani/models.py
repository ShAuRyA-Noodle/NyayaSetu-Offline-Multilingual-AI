"""
NyayaVaani Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal


# ============================================================================
# REQUEST MODELS
# ============================================================================

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    language: str = Field(default="hi", description="Language code (hi, bn, ta, etc.)")
    voice_gender: Literal["female", "male"] = Field(default="female")


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to translate")
    source_language: str = Field(..., description="Source language code")
    target_language: str = Field(..., description="Target language code")
    content_type: Literal["general", "grievance", "notice", "scheme"] = Field(default="general")


class IntentClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text to classify")
    language: str = Field(default="hi", description="Language code")


class VoiceGrievanceSubmitRequest(BaseModel):
    transcription: str = Field(..., min_length=10, description="Voice transcription text")
    language: str = Field(default="hi", description="Detected language")
    citizen_name: Optional[str] = None
    citizen_phone: Optional[str] = None
    citizen_location: Optional[str] = None


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float
    method: str


class TTSResponse(BaseModel):
    audio_url: str
    duration_seconds: float
    language: str
    method: str


class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    content_type: str
    method: str


class IntentResponse(BaseModel):
    intent: str
    confidence: float
    entities: Dict[str, Any] = {}
    language: str


class VoiceGrievanceResponse(BaseModel):
    grievance_id: str
    title: str
    description: str
    category: str
    department: str
    priority: str
    language: str
    acknowledgement_text: Optional[str] = None
    acknowledgement_audio_url: Optional[str] = None


class NyayaVaaniStatusResponse(BaseModel):
    status: str
    mode: str  # "online" or "offline"
    sarvam_api: bool
    ollama_available: bool
    ollama_models: List[str] = []
    supported_languages: int
    audio_cleanup_enabled: bool


class NyayaVaaniErrorResponse(BaseModel):
    error: str
    message: str
    message_hindi: Optional[str] = None
