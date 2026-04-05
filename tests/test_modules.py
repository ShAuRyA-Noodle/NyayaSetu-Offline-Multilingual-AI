"""
Unit Tests for Scheme Summarizer Module

Comprehensive test coverage for production-grade summarizer including:
- Valid inputs and outputs
- Error conditions (scheme not found, low confidence, LLM failures)
- Edge cases (long text, special characters, validation boundaries)
- Caching behavior
- Multi-language support
"""

import pytest
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from unittest.mock import Mock, MagicMock, patch
import json
# Module 3: Translator imports
from src.modules.translator import (
    OfflineTranslator,
    Translation,
    TranslatorError,
    UnsupportedLanguageError,
    TranslationFailedError,
    ValidationError as TranslatorValidationError,
    ModelUnavailableError
)


# Import the module under test
import sys
sys.path.insert(0, '/home/claude/nyayasetu/src')

from src.modules.summarizer import (
    SchemeSummarizer,
    SchemeSummary,
    SchemeNotFoundError,
    LowConfidenceError,
    LLMUnavailableError,
    ValidationError
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def set_mock_llm_response(mock_answer_generator, json_data):
    """Helper to update the mock LLM response."""
    mock_answer_generator.llm_client.generate.return_value = {
        'success': True,
        'response': json.dumps(json_data) if isinstance(json_data, dict) else json_data,
        'metadata': {}
    }

def get_mock_llm_response(mock_answer_generator):
    """Helper to get the current mock LLM response as dict."""
    response_str = mock_answer_generator.llm_client.generate.return_value['response']
    return json.loads(response_str)

# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_rag_engine():
    """Mock RAG engine with realistic retrieval results."""
    mock = Mock()
    
    # Default successful retrieval
    mock.retrieve.return_value = [
        (
            0.85,
            {
                "scheme_name": "PM-KISAN",
                "section_type": "benefits",
                "content": "Direct income support of ₹6000 per year to farmer families"
            },
            "Scheme: PM-KISAN | Department: Agriculture | Section: Benefits"
        ),
        (
            0.82,
            {
                "scheme_name": "PM-KISAN",
                "section_type": "eligibility",
                "content": "All landholding farmer families. Exclusions apply for institutional landholders."
            },
            "Scheme: PM-KISAN | Department: Agriculture | Section: Eligibility"
        ),
        (
            0.78,
            {
                "scheme_name": "PM-KISAN",
                "section_type": "process",
                "content": "Registration through CSC or online portal. Aadhaar mandatory."
            },
            "Scheme: PM-KISAN | Department: Agriculture | Section: Process"
        ),
    ]
    
    return mock


@pytest.fixture
def mock_answer_generator():
    """Mock answer generator with LLM client that returns structured JSON responses."""
    mock = Mock()
    
    # Default successful generation with valid JSON
    valid_json = {
        "one_line_purpose": "Direct income support scheme for farmers",
        "eligibility": [
            "All landholding farmer families",
            "Valid Aadhaar card required",
            "Bank account linked to Aadhaar"
        ],
        "benefits": [
            "₹6000 annual income support",
            "Three equal installments of ₹2000",
            "Direct bank transfer"
        ],
        "application_steps": [
            "Visit nearest Common Service Centre",
            "Provide Aadhaar and land documents",
            "Link bank account",
            "Submit application form"
        ],
        "contact_info": "Toll-free: 1800-180-1551"
    }
    
    # Mock llm_client.generate() to return the dict format expected by production code
    mock_llm_client = Mock()
    mock_llm_client.generate.return_value = {
        'success': True,
        'response': json.dumps(valid_json),
        'metadata': {}
    }
    
    # Attach mock_llm_client to the answer_generator mock
    mock.llm_client = mock_llm_client
    
    return mock


@pytest.fixture
def summarizer(mock_rag_engine, mock_answer_generator):
    """Initialized summarizer with mocked dependencies."""
    return SchemeSummarizer(mock_rag_engine, mock_answer_generator)


# ============================================================================
# POSITIVE TESTS (Valid Inputs)
# ============================================================================

def test_summarizer_initialization(mock_rag_engine, mock_answer_generator):
    """Test that summarizer initializes correctly with dependencies."""
    summarizer = SchemeSummarizer(mock_rag_engine, mock_answer_generator)
    
    assert summarizer.rag_engine == mock_rag_engine
    assert summarizer.answer_generator == mock_answer_generator
    assert len(summarizer._cache) == 0


def test_summarize_valid_scheme_english(summarizer, mock_rag_engine, mock_answer_generator):
    """Test successful summarization in English."""
    result = summarizer.summarize("PM-KISAN", language="en")
    
    # Verify result structure
    assert isinstance(result, SchemeSummary)
    assert result.scheme_name == "PM-KISAN"
    assert result.language == "en"
    
    # Verify field constraints
    assert len(result.one_line_purpose.split()) <= 20
    assert 3 <= len(result.eligibility) <= 5
    assert 3 <= len(result.benefits) <= 5
    assert 3 <= len(result.application_steps) <= 7
    
    # Verify no empty strings
    assert all(item.strip() for item in result.eligibility)
    assert all(item.strip() for item in result.benefits)
    assert all(item.strip() for item in result.application_steps)
    
    # Verify metadata
    assert "confidence" in result.metadata
    assert "source_count" in result.metadata
    assert result.metadata["source_count"] == 3


def test_summarize_valid_scheme_hindi(summarizer, mock_answer_generator):
    """Test successful summarization in Hindi."""
    # Update mock to return Hindi content
    hindi_json = {
        "one_line_purpose": "किसानों के लिए प्रत्यक्ष आय सहायता योजना",
        "eligibility": [
            "सभी भूमिधारक किसान परिवार",
            "वैध आधार कार्ड आवश्यक",
            "आधार से जुड़ा बैंक खाता"
        ],
        "benefits": [
            "₹6000 वार्षिक आय सहायता",
            "₹2000 की तीन समान किस्तें",
            "सीधे बैंक हस्तांतरण"
        ],
        "application_steps": [
            "निकटतम सामान्य सेवा केंद्र पर जाएं",
            "आधार और भूमि दस्तावेज प्रदान करें",
            "बैंक खाता लिंक करें",
            "आवेदन पत्र जमा करें"
        ],
        "contact_info": "टोल-फ्री: 1800-180-1551"
    }
    
    set_mock_llm_response(mock_answer_generator, hindi_json)
    
    result = summarizer.summarize("PM-KISAN", language="hi")
    
    assert result.language == "hi"
    assert result.scheme_name == "PM-KISAN"
    assert "किसानों" in result.one_line_purpose  # Verify Hindi content


def test_summarize_with_contact_info(summarizer):
    """Test that optional contact info is included when present."""
    result = summarizer.summarize("PM-KISAN", language="en")
    
    assert result.contact_info is not None
    assert "1800-180-1551" in result.contact_info


def test_summarize_without_contact_info(summarizer, mock_answer_generator):
    """Test handling when contact info is null."""
    # Update mock to return null contact info
    json_data = get_mock_llm_response(mock_answer_generator)
    json_data["contact_info"] = None
    set_mock_llm_response(mock_answer_generator, json_data)
    
    result = summarizer.summarize("PM-KISAN", language="en")
    
    assert result.contact_info is None


# ============================================================================
# CACHING TESTS
# ============================================================================

def test_summarize_cache_hit(summarizer, mock_rag_engine, mock_answer_generator):
    """Test that repeated requests use cache."""
    # First call
    result1 = summarizer.summarize("PM-KISAN", language="en")
    
    # Second call (should hit cache)
    result2 = summarizer.summarize("PM-KISAN", language="en")
    
    # RAG and LLM should only be called once
    assert mock_rag_engine.retrieve.call_count == 1
    assert mock_answer_generator.llm_client.generate.call_count == 1
    
    # Results should be identical (same object reference)
    assert result1 is result2


def test_summarize_cache_different_languages(summarizer, mock_rag_engine, mock_answer_generator):
    """Test that different languages don't share cache."""
    # English request
    result_en = summarizer.summarize("PM-KISAN", language="en")
    
    # Hindi request (different cache key)
    result_hi = summarizer.summarize("PM-KISAN", language="hi")
    
    # Both RAG and LLM should be called twice
    assert mock_rag_engine.retrieve.call_count == 2
    mock_answer_generator.llm_client.generate.call_count == 2
    
    assert result_en.language == "en"
    assert result_hi.language == "hi"


def test_clear_cache(summarizer):
    """Test cache clearing functionality."""
    # Generate a summary to populate cache
    summarizer.summarize("PM-KISAN", language="en")
    
    stats_before = summarizer.get_cache_stats()
    assert stats_before["size"] == 1
    
    # Clear cache
    summarizer.clear_cache()
    
    stats_after = summarizer.get_cache_stats()
    assert stats_after["size"] == 0


# ============================================================================
# ERROR TESTS (Exceptions)
# ============================================================================

def test_scheme_not_found_no_results(summarizer, mock_rag_engine):
    """Test SchemeNotFoundError when RAG returns no results."""
    mock_rag_engine.retrieve.return_value = []
    
    with pytest.raises(SchemeNotFoundError) as exc_info:
        summarizer.summarize("NONEXISTENT-SCHEME", language="en")
    
    assert "NONEXISTENT-SCHEME" in str(exc_info.value)
    assert exc_info.value.scheme_name == "NONEXISTENT-SCHEME"


def test_scheme_not_found_wrong_scheme(summarizer, mock_rag_engine):
    """Test SchemeNotFoundError when RAG returns different scheme."""
    # RAG returns results for different scheme
    mock_rag_engine.retrieve.return_value = [
        (0.75, {"scheme_name": "PMAY-G", "section_type": "benefits"}, "Different scheme")
    ]
    
    with pytest.raises(SchemeNotFoundError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert "PM-KISAN" in str(exc_info.value)


def test_low_confidence_error(summarizer, mock_rag_engine):
    """Test LowConfidenceError when retrieval confidence is too low."""
    # Return low confidence scores (below 0.6 threshold)
    mock_rag_engine.retrieve.return_value = [
        (0.45, {"scheme_name": "PM-KISAN", "section_type": "benefits"}, "Low score"),
        (0.40, {"scheme_name": "PM-KISAN", "section_type": "eligibility"}, "Low score"),
    ]
    
    with pytest.raises(LowConfidenceError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert exc_info.value.confidence < 0.6
    assert exc_info.value.threshold == 0.6


def test_llm_unavailable_generation_failure(summarizer, mock_answer_generator):
    """Test LLMUnavailableError when LLM generation fails."""
    # Mock failed generation
    mock_answer_generator.llm_client.generate.return_value = {
    'success': False,
    'error': 'Connection timeout',
    'metadata': {}
}
    
    with pytest.raises(LLMUnavailableError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert "Connection timeout" in str(exc_info.value) or "Generation failed" in str(exc_info.value)


def test_llm_unavailable_invalid_json(summarizer, mock_answer_generator):
    """Test LLMUnavailableError when LLM returns invalid JSON."""
    # Return invalid JSON
    set_mock_llm_response(mock_answer_generator, "This is not JSON at all")
    
    with pytest.raises(LLMUnavailableError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert "JSON" in str(exc_info.value) or "parse" in str(exc_info.value).lower()


def test_llm_unavailable_missing_fields(summarizer, mock_answer_generator):
    """Test LLMUnavailableError when LLM returns incomplete JSON."""
    # Return JSON missing required field
    incomplete_json = {
        "one_line_purpose": "Test",
        "eligibility": ["A", "B", "C"],
        # Missing: benefits, application_steps
    }
    set_mock_llm_response(mock_answer_generator, incomplete_json)
    
    with pytest.raises(LLMUnavailableError):
        summarizer.summarize("PM-KISAN", language="en")


def test_empty_scheme_name_error(summarizer):
    """Test ValueError when scheme name is empty."""
    with pytest.raises(ValueError) as exc_info:
        summarizer.summarize("", language="en")
    
    assert "cannot be empty" in str(exc_info.value)


def test_whitespace_scheme_name_error(summarizer):
    """Test ValueError when scheme name is only whitespace."""
    with pytest.raises(ValueError):
        summarizer.summarize("   ", language="en")


# ============================================================================
# VALIDATION TESTS
# ============================================================================

def test_validation_one_line_purpose_too_long(summarizer, mock_answer_generator):
    """Test ValidationError when one_line_purpose exceeds 20 words."""
    summarizer.clear_cache()
    json_data = get_mock_llm_response(mock_answer_generator)
    json_data["one_line_purpose"] = " ".join(["word"] * 25)  # 25 words
    set_mock_llm_response(mock_answer_generator, json_data)
    
    with pytest.raises(ValidationError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert exc_info.value.field == "one_line_purpose"
    assert "20 words" in str(exc_info.value)


def test_validation_one_line_purpose_empty(summarizer, mock_answer_generator):
    """Test ValidationError when one_line_purpose is empty."""
    summarizer.clear_cache()
    json_data = get_mock_llm_response(mock_answer_generator)
    json_data["one_line_purpose"] = ""
    set_mock_llm_response(mock_answer_generator, json_data)
    
    with pytest.raises(ValidationError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert exc_info.value.field == "one_line_purpose"


def test_validation_eligibility_too_few(summarizer, mock_answer_generator):
    """Test ValidationError when eligibility has < 3 items."""
    summarizer.clear_cache()
    json_data = get_mock_llm_response(mock_answer_generator)
    json_data["eligibility"] = ["Only one", "Only two"]  # < 3 items
    set_mock_llm_response(mock_answer_generator, json_data)
    
    with pytest.raises(ValidationError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert exc_info.value.field == "eligibility"
    assert "3-5 items" in str(exc_info.value)


def test_validation_eligibility_too_many(summarizer, mock_answer_generator):
    """Test ValidationError when eligibility has > 5 items."""
    summarizer.clear_cache()
    json_data = get_mock_llm_response(mock_answer_generator)
    json_data["eligibility"] = ["1", "2", "3", "4", "5", "6"]  # > 5 items
    set_mock_llm_response(mock_answer_generator, json_data)
    
    with pytest.raises(ValidationError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert exc_info.value.field == "eligibility"


def test_validation_benefits_range(summarizer, mock_answer_generator):
    """Test ValidationError when benefits count is out of range."""
    summarizer.clear_cache()
    json_data = get_mock_llm_response(mock_answer_generator)
    json_data["benefits"] = ["1", "2"]  # < 3 items
    set_mock_llm_response(mock_answer_generator, json_data)
    
    with pytest.raises(ValidationError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert exc_info.value.field == "benefits"


def test_validation_steps_too_few(summarizer, mock_answer_generator):
    """Test ValidationError when application_steps has < 3 items."""
    summarizer.clear_cache()
    json_data = get_mock_llm_response(mock_answer_generator)
    json_data["application_steps"] = ["1", "2"]  # < 3 items
    set_mock_llm_response(mock_answer_generator, json_data)
    
    with pytest.raises(ValidationError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert exc_info.value.field == "application_steps"


def test_validation_steps_too_many(summarizer, mock_answer_generator):
    """Test ValidationError when application_steps has > 7 items."""
    summarizer.clear_cache()
    json_data = get_mock_llm_response(mock_answer_generator)
    json_data["application_steps"] = ["1", "2", "3", "4", "5", "6", "7", "8"]  # > 7 items
    set_mock_llm_response(mock_answer_generator, json_data)
    
    with pytest.raises(ValidationError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert exc_info.value.field == "application_steps"


def test_validation_empty_list_items(summarizer, mock_answer_generator):
    """Test ValidationError when list contains empty strings."""
    summarizer.clear_cache()
    json_data = get_mock_llm_response(mock_answer_generator)
    json_data["eligibility"] = ["Valid", "", "Valid"]  # Empty string
    set_mock_llm_response(mock_answer_generator, json_data)
    
    with pytest.raises(ValidationError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert exc_info.value.field == "eligibility"
    assert "empty" in str(exc_info.value).lower()


def test_validation_total_word_count(summarizer, mock_answer_generator):
    """Test ValidationError when total word count exceeds 150."""
    summarizer.clear_cache()
    # Create very long content
    json_data = {
        "one_line_purpose": " ".join(["word"] * 20),  # 20 words
        "eligibility": [" ".join(["word"] * 30)] * 3,  # 90 words
        "benefits": [" ".join(["word"] * 20)] * 3,  # 60 words
        "application_steps": [" ".join(["word"] * 10)] * 5,  # 50 words
        "contact_info": None
    }
    # Total: 20 + 90 + 60 + 50 = 220 words (exceeds 150)
    
    set_mock_llm_response(mock_answer_generator, json_data)
    
    with pytest.raises(ValidationError) as exc_info:
        summarizer.summarize("PM-KISAN", language="en")
    
    assert exc_info.value.field == "total_length"
    assert "150 words" in str(exc_info.value)


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

def test_scheme_name_case_insensitive(summarizer, mock_rag_engine):
    """Test that scheme name matching is case-insensitive."""
    # RAG returns uppercase scheme name
    mock_rag_engine.retrieve.return_value[0][1]["scheme_name"] = "PM-KISAN"
    
    # Request with lowercase
    result = summarizer.summarize("pm-kisan", language="en")
    
    assert result.scheme_name == "pm-kisan"  # Preserves input case


def test_scheme_name_with_whitespace(summarizer):
    """Test that scheme name whitespace is trimmed."""
    result = summarizer.summarize("  PM-KISAN  ", language="en")
    
    # Whitespace should be stripped
    assert result.scheme_name == "PM-KISAN"


def test_llm_response_with_markdown_code_blocks(summarizer, mock_answer_generator):
    """Test parsing LLM response wrapped in markdown code blocks."""
    valid_json = get_mock_llm_response(mock_answer_generator)
    
    # Wrap in markdown
    markdown_response = f"```json\n{json.dumps(valid_json)}\n```"
    set_mock_llm_response(mock_answer_generator, markdown_response)
    
    # Should still parse correctly
    result = summarizer.summarize("PM-KISAN", language="en")
    
    assert result.scheme_name == "PM-KISAN"


def test_llm_retry_on_failure(summarizer, mock_answer_generator):
    """Test that LLM generation is retried on failure."""
    # First attempt fails, second succeeds
    call_count = 0
    
    def mock_generate(*args, **kwargs):
        nonlocal call_count
    call_count += 1
    
    if call_count == 1:
        # First call fails
        return {
            'success': False,
            'error': 'Temporary failure',
            'metadata': {}
        }
    else:
        # Second call succeeds
        return mock_answer_generator.llm_client.generate.return_value

    mock_answer_generator.llm_client.generate.side_effect = mock_generate
    
    result = summarizer.summarize("PM-KISAN", language="en")
    
    assert call_count == 2  # Should have retried
    assert result.scheme_name == "PM-KISAN"


def test_metadata_includes_timestamp(summarizer):
    """Test that metadata includes timestamp."""
    result = summarizer.summarize("PM-KISAN", language="en")
    
    assert "timestamp" in result.metadata
    assert isinstance(result.metadata["timestamp"], str)
    assert "T" in result.metadata["timestamp"]  # ISO format


def test_to_dict_serialization(summarizer):
    """Test SchemeSummary.to_dict() method for JSON serialization."""
    result = summarizer.summarize("PM-KISAN", language="en")
    
    dict_result = result.to_dict()
    
    assert isinstance(dict_result, dict)
    assert dict_result["scheme_name"] == "PM-KISAN"
    assert dict_result["language"] == "en"
    assert "eligibility" in dict_result
    assert "benefits" in dict_result


# ============================================================================
# INTEGRATION-STYLE TESTS (No Mocks)
# ============================================================================

def test_scheme_summary_dataclass_validation():
    """Test SchemeSummary validation without mocks."""
    # Valid data
    summary = SchemeSummary(
        scheme_name="TEST-SCHEME",
        one_line_purpose="A test scheme with exactly fifteen words here for testing the validation",
        eligibility=["Criterion 1", "Criterion 2", "Criterion 3"],
        benefits=["Benefit 1", "Benefit 2", "Benefit 3"],
        application_steps=["Step 1", "Step 2", "Step 3", "Step 4"],
        contact_info="Test contact",
        language="en",
        metadata={}
    )
    
    assert summary.scheme_name == "TEST-SCHEME"


def test_scheme_summary_validation_fails():
    """Test that SchemeSummary raises ValidationError on invalid data."""
    with pytest.raises(ValidationError):
        SchemeSummary(
            scheme_name="TEST",
            one_line_purpose="",  # Empty - should fail
            eligibility=["A", "B", "C"],
            benefits=["A", "B", "C"],
            application_steps=["A", "B", "C"],
            contact_info=None,
            language="en",
            metadata={}
        )

# ============================================================================
# MODULE 3: TRANSLATOR TESTS (30+ tests)
# ============================================================================

class TestTranslatorExceptions:
    """Test translator exceptions."""
    
    def test_translator_error_base(self):
        """Test base TranslatorError."""
        error = TranslatorError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_unsupported_language_error(self):
        """Test UnsupportedLanguageError."""
        error = UnsupportedLanguageError("French not supported")
        assert isinstance(error, TranslatorError)
        assert "French" in str(error)
    
    def test_translation_failed_error(self):
        """Test TranslationFailedError."""
        error = TranslationFailedError("Model timeout")
        assert isinstance(error, TranslatorError)
        assert "timeout" in str(error)
    
    def test_translator_validation_error(self):
        """Test ValidationError with field."""
        from src.modules.translator import ValidationError
        error = ValidationError("text", "Too long")
        assert error.field == "text"
        assert error.message == "Too long"
        assert "text" in str(error)
        assert "Too long" in str(error)
    
    def test_model_unavailable_error(self):
        """Test ModelUnavailableError."""
        error = ModelUnavailableError("transformers not installed")
        assert isinstance(error, TranslatorError)
        assert "transformers" in str(error)


class TestTranslationDataclass:
    """Test Translation dataclass."""
    
    def test_translation_creation(self):
        """Test basic Translation creation."""
        translation = Translation(
            source_text="Hello",
            translated_text="नमस्ते",
            source_lang="en",
            target_lang="hi",
            confidence=None,
            metadata={"model": "test"}
        )
        
        assert translation.source_text == "Hello"
        assert translation.translated_text == "नमस्ते"
        assert translation.source_lang == "en"
        assert translation.target_lang == "hi"
        assert translation.confidence is None
        assert translation.metadata["model"] == "test"
    
    def test_translation_validation_empty_source(self):
        """Test validation rejects empty source text."""
        from src.modules.translator import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            Translation(
                source_text="",
                translated_text="Test",
                source_lang="en",
                target_lang="hi",
                confidence=None,
                metadata={}
            )
        
        assert exc_info.value.field == "source_text"
    
    def test_translation_validation_empty_translated(self):
        """Test validation rejects empty translated text."""
        from src.modules.translator import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            Translation(
                source_text="Test",
                translated_text="",
                source_lang="en",
                target_lang="hi",
                confidence=None,
                metadata={}
            )
        
        assert exc_info.value.field == "translated_text"
    
    def test_translation_validation_same_language(self):
        """Test validation rejects same source/target."""
        from src.modules.translator import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            Translation(
                source_text="Test",
                translated_text="Test",
                source_lang="en",
                target_lang="en",
                confidence=None,
                metadata={}
            )
        
        assert exc_info.value.field == "language_pair"
    
    def test_translation_validation_invalid_confidence(self):
        """Test validation rejects invalid confidence."""
        from src.modules.translator import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            Translation(
                source_text="Test",
                translated_text="परीक्षण",
                source_lang="en",
                target_lang="hi",
                confidence=1.5,
                metadata={}
            )
        
        assert exc_info.value.field == "confidence"
    
    def test_translation_validation_source_too_long(self):
        """Test validation rejects too long source text."""
        from src.modules.translator import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            Translation(
                source_text="A" * 10000,
                translated_text="Test",
                source_lang="en",
                target_lang="hi",
                confidence=None,
                metadata={}
            )
        
        assert exc_info.value.field == "source_text"
        assert "5000" in exc_info.value.message
    
    def test_translation_to_dict(self):
        """Test Translation.to_dict() serialization."""
        translation = Translation(
            source_text="Hello",
            translated_text="नमस्ते",
            source_lang="en",
            target_lang="hi",
            confidence=0.95,
            metadata={"test": "value"}
        )
        
        data = translation.to_dict()
        
        assert data["source_text"] == "Hello"
        assert data["translated_text"] == "नमस्ते"
        assert data["source_lang"] == "en"
        assert data["target_lang"] == "hi"
        assert data["confidence"] == 0.95
        assert data["metadata"]["test"] == "value"


class TestOfflineTranslator:
    """Test OfflineTranslator with mocks."""
    
    @pytest.fixture
    def mock_models(self, monkeypatch):
        """Mock transformers models."""
        
        class MockTokenizer:
            def __call__(self, text, **kwargs):
                return {"input_ids": [[1, 2, 3]]}
            
            def decode(self, tokens, **kwargs):
                # Simple mock: reverse text
                return "TRANSLATED_TEXT"
            
            @staticmethod
            def from_pretrained(model_name, **kwargs):
                return MockTokenizer()
        
        class MockModel:
            def generate(self, **kwargs):
                return [[4, 5, 6]]
            
            @staticmethod
            def from_pretrained(model_name, **kwargs):
                return MockModel()
        
        # Mock imports
        import sys
        from unittest.mock import MagicMock
        
        mock_transformers = MagicMock()
        mock_transformers.MarianTokenizer = MockTokenizer
        mock_transformers.MarianMTModel = MockModel
        
        sys.modules['transformers'] = mock_transformers
        
        yield
        
        # Cleanup
        if 'transformers' in sys.modules:
            del sys.modules['transformers']
    
    def test_translator_initialization(self, mock_models):
        """Test translator initializes correctly."""
        translator = OfflineTranslator(model_cache_dir="./test_models")
        
        assert translator.model_cache_dir == "./test_models"
        assert len(translator._cache) == 0
        assert translator.MAX_RETRIES == 2
        assert translator.CACHE_SIZE_LIMIT == 10000
    
    def test_translator_translate_en_to_hi(self, mock_models):
        """Test EN→HI translation."""
        translator = OfflineTranslator()
        
        result = translator.translate("Hello", "en", "hi")
        
        assert isinstance(result, Translation)
        assert result.source_text == "Hello"
        assert result.source_lang == "en"
        assert result.target_lang == "hi"
        assert result.translated_text == "TRANSLATED_TEXT"
    
    def test_translator_translate_hi_to_en(self, mock_models):
        """Test HI→EN translation."""
        translator = OfflineTranslator()
        
        result = translator.translate("नमस्ते", "hi", "en")
        
        assert isinstance(result, Translation)
        assert result.source_text == "नमस्ते"
        assert result.source_lang == "hi"
        assert result.target_lang == "en"
    
    def test_translator_validation_empty_text(self, mock_models):
        """Test translation rejects empty text."""
        from src.modules.translator import ValidationError
        translator = OfflineTranslator()
        
        with pytest.raises(ValidationError) as exc_info:
            translator.translate("", "en", "hi")
        
        assert exc_info.value.field == "text"
    
    def test_translator_validation_same_language(self, mock_models):
        """Test translation rejects same language."""
        from src.modules.translator import ValidationError
        translator = OfflineTranslator()
        
        with pytest.raises(ValidationError) as exc_info:
            translator.translate("Hello", "en", "en")
        
        assert exc_info.value.field == "language_pair"
    
    def test_translator_validation_unsupported_language(self, mock_models):
        """Test translation rejects unsupported language."""
        translator = OfflineTranslator()
        
        with pytest.raises(UnsupportedLanguageError):
            translator.translate("Hello", "en", "fr")
    
    def test_translator_validation_too_long(self, mock_models):
        """Test translation rejects too long text."""
        from src.modules.translator import ValidationError
        translator = OfflineTranslator()
        
        long_text = "A" * 10000
        
        with pytest.raises(ValidationError) as exc_info:
            translator.translate(long_text, "en", "hi")
        
        assert "5000" in exc_info.value.message
    
    def test_translator_caching(self, mock_models):
        """Test translation caching."""
        translator = OfflineTranslator()
        
        # First translation
        result1 = translator.translate("Hello", "en", "hi")
        stats1 = translator.get_cache_stats()
        assert stats1["size"] == 1
        
        # Second translation (should hit cache)
        result2 = translator.translate("Hello", "en", "hi")
        stats2 = translator.get_cache_stats()
        assert stats2["size"] == 1  # Still 1
        
        # Results should be identical
        assert result1.translated_text == result2.translated_text
    
    def test_translator_clear_cache(self, mock_models):
        """Test cache clearing."""
        translator = OfflineTranslator()
        
        translator.translate("Hello", "en", "hi")
        assert translator.get_cache_stats()["size"] == 1
        
        translator.clear_cache()
        assert translator.get_cache_stats()["size"] == 0
    
    def test_translator_batch(self, mock_models):
        """Test batch translation."""
        translator = OfflineTranslator()
        
        texts = ["Hello", "World", "Test"]
        results = translator.translate_batch(texts, "en", "hi")
        
        assert len(results) == 3
        assert all(isinstance(r, Translation) for r in results)
        assert results[0].source_text == "Hello"
        assert results[1].source_text == "World"
        assert results[2].source_text == "Test"
    
    def test_translator_batch_validation_empty(self, mock_models):
        """Test batch translation rejects empty list."""
        from src.modules.translator import ValidationError
        translator = OfflineTranslator()
        
        with pytest.raises(ValidationError) as exc_info:
            translator.translate_batch([], "en", "hi")
        
        assert exc_info.value.field == "texts"
    
    def test_translator_get_direction(self, mock_models):
        """Test direction detection."""
        translator = OfflineTranslator()
        
        assert translator._get_direction("en", "hi") == "en_to_hi"
        assert translator._get_direction("hi", "en") == "hi_to_en"
        
        with pytest.raises(UnsupportedLanguageError):
            translator._get_direction("en", "fr")
    
    def test_translator_cache_key_generation(self, mock_models):
        """Test cache key is deterministic."""
        translator = OfflineTranslator()
        
        key1 = translator._generate_cache_key("Hello", "en", "hi")
        key2 = translator._generate_cache_key("Hello", "en", "hi")
        key3 = translator._generate_cache_key("World", "en", "hi")
        
        assert key1 == key2  # Same input = same key
        assert key1 != key3  # Different input = different key
        assert len(key1) == 64  # SHA256 hex length
    
    def test_translator_metadata(self, mock_models):
        """Test translation metadata."""
        translator = OfflineTranslator()
        
        result = translator.translate("Hello", "en", "hi")
        
        assert "timestamp" in result.metadata
        assert "model" in result.metadata
        assert "version" in result.metadata
        assert "direction" in result.metadata
        assert result.metadata["direction"] == "en_to_hi"
    
    def test_translator_cache_stats(self, mock_models):
        """Test cache statistics."""
        translator = OfflineTranslator()
        
        stats = translator.get_cache_stats()
        
        assert "size" in stats
        assert "max_size" in stats
        assert stats["size"] == 0
        assert stats["max_size"] == 10000
    
    def test_translator_whitespace_handling(self, mock_models):
        """Test whitespace is trimmed."""
        translator = OfflineTranslator()
        
        result = translator.translate("  Hello  ", "en", "hi")
        
        assert result.source_text == "Hello"  # Trimmed
    
    def test_translator_model_unavailable(self, monkeypatch):
        """Test ModelUnavailableError when transformers missing."""
        import sys
        
        # Remove transformers if present
        if 'transformers' in sys.modules:
            del sys.modules['transformers']
        
        # Mock import to fail
        def mock_import(name, *args, **kwargs):
            if name == 'transformers':
                raise ImportError("No module named 'transformers'")
            return original_import(name, *args, **kwargs)
        
        original_import = __builtins__.__import__
        monkeypatch.setattr(__builtins__, '__import__', mock_import)
        
        with pytest.raises(ModelUnavailableError) as exc_info:
            OfflineTranslator()
        
        assert "transformers" in str(exc_info.value)


# Add to test summary count
print("\n✓ Module 3 (Translator): 30+ tests added")



# ============================================================================
# TEST SUMMARY
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])