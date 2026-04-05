"""
API Error Handling

Custom exceptions and error handlers for NyayaSetu API.
Provides structured error responses with proper HTTP status codes.

Author: NyayaSetu Team
Version: 1.0.0
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime
from typing import Union
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class NyayaSetuAPIError(HTTPException):
    """Base exception for API errors."""
    
    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        detail: str = None
    ):
        self.status_code = status_code
        self.error = error
        self.message = message
        self.detail = detail
        super().__init__(status_code=status_code, detail=message)


class SchemeNotFoundError(NyayaSetuAPIError):
    """Raised when scheme is not found in database."""
    
    def __init__(self, scheme_name: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error="SchemeNotFound",
            message=f"Scheme '{scheme_name}' not found",
            detail="The requested scheme does not exist in the database"
        )


class InvalidInputError(NyayaSetuAPIError):
    """Raised when input validation fails."""
    
    def __init__(self, field: str, reason: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="InvalidInput",
            message=f"Invalid input for field '{field}'",
            detail=reason
        )


class LLMUnavailableError(NyayaSetuAPIError):
    """Raised when LLM service is unavailable."""
    
    def __init__(self, details: str = None):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error="LLMUnavailable",
            message="LLM service is currently unavailable",
            detail=details or "The language model service is not responding"
        )


class TranslationError(NyayaSetuAPIError):
    """Raised when translation fails."""
    
    def __init__(self, details: str = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="TranslationFailed",
            message="Translation service failed",
            detail=details or "Unable to translate the provided text"
        )


class RoutingError(NyayaSetuAPIError):
    """Raised when grievance routing fails."""
    
    def __init__(self, details: str = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="RoutingFailed",
            message="Grievance routing failed",
            detail=details or "Unable to route the grievance to a department"
        )


class ServiceUnavailableError(NyayaSetuAPIError):
    """Raised when a service is temporarily unavailable."""
    
    def __init__(self, service: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error="ServiceUnavailable",
            message=f"{service} service is unavailable",
            detail=f"The {service} is temporarily unavailable. Please try again later."
        )


# ============================================================================
# ERROR RESPONSE BUILDER
# ============================================================================

def build_error_response(
    error: str,
    message: str,
    detail: Union[str, None] = None,
    status_code: int = 500
) -> JSONResponse:
    """
    Build standardized error response.
    
    Args:
        error: Error type/code
        message: Error message
        detail: Detailed error information
        status_code: HTTP status code
    
    Returns:
        JSONResponse with error details
    """
    response_data = {
        "error": error,
        "message": message,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

async def nyayasetu_error_handler(
    request: Request,
    exc: NyayaSetuAPIError
) -> JSONResponse:
    """
    Handle custom NyayaSetu API errors.
    
    Args:
        request: FastAPI request
        exc: NyayaSetuAPIError instance
    
    Returns:
        JSONResponse with error details
    """
    logger.error(
        f"API Error: {exc.error} - {exc.message} "
        f"(Path: {request.url.path})"
    )
    
    return build_error_response(
        error=exc.error,
        message=exc.message,
        detail=exc.detail,
        status_code=exc.status_code
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    
    Args:
        request: FastAPI request
        exc: RequestValidationError instance
    
    Returns:
        JSONResponse with validation error details
    """
    # Extract first validation error for cleaner message
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    
    field = " -> ".join(str(loc) for loc in first_error.get("loc", []))
    message = first_error.get("msg", "Validation failed")
    
    logger.warning(
        f"Validation Error: {field} - {message} "
        f"(Path: {request.url.path})"
    )
    
    return build_error_response(
        error="ValidationError",
        message=f"Invalid request data: {field}",
        detail=message,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """
    Handle standard HTTPException.
    
    Args:
        request: FastAPI request
        exc: HTTPException instance
    
    Returns:
        JSONResponse with error details
    """
    logger.error(
        f"HTTP Error {exc.status_code}: {exc.detail} "
        f"(Path: {request.url.path})"
    )
    
    return build_error_response(
        error="HTTPError",
        message=str(exc.detail),
        detail=None,
        status_code=exc.status_code
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions.
    
    Args:
        request: FastAPI request
        exc: Exception instance
    
    Returns:
        JSONResponse with generic error message
    """
    logger.exception(
        f"Unexpected Error: {type(exc).__name__} - {str(exc)} "
        f"(Path: {request.url.path})"
    )
    
    return build_error_response(
        error="InternalServerError",
        message="An unexpected error occurred",
        detail="Please contact support if this persists",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


# ============================================================================
# MODULE ERROR MAPPING
# ============================================================================

def map_module_error(exc: Exception, module_name: str) -> NyayaSetuAPIError:
    """
    Map module-specific errors to API errors.
    
    Args:
        exc: Original module exception
        module_name: Name of the module
    
    Returns:
        NyayaSetuAPIError instance
    """
    error_name = type(exc).__name__
    
    # Scheme Summarizer errors
    if "SchemeNotFound" in error_name:
        return SchemeNotFoundError(str(exc))
    
    # Grievance Router errors
    if "InvalidGrievance" in error_name:
        return InvalidInputError("grievance_text", str(exc))
    
    if "DepartmentUnavailable" in error_name:
        return RoutingError(str(exc))
    
    # Translator errors
    if "TranslationLength" in error_name:
        return InvalidInputError("text", str(exc))
    
    if "ModelLoad" in error_name:
        return TranslationError("Translation model failed to load")
    
    # LLM errors
    if "LLMUnavailable" in error_name or "Ollama" in error_name:
        return LLMUnavailableError(str(exc))
    
    # Validation errors
    if "Validation" in error_name:
        # Try to extract field name from error
        error_msg = str(exc)
        if "'" in error_msg:
            field = error_msg.split("'")[1]
            return InvalidInputError(field, error_msg)
        return InvalidInputError("unknown", error_msg)
    
    # Generic module error
    return NyayaSetuAPIError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error=f"{module_name}Error",
        message=f"Error in {module_name} module",
        detail=str(exc)
    )


# ============================================================================
# RESPONSE WRAPPERS
# ============================================================================

def success_response(data: dict, status_code: int = 200) -> JSONResponse:
    """
    Build standardized success response.
    
    Args:
        data: Response data
        status_code: HTTP status code
    
    Returns:
        JSONResponse with data
    """
    return JSONResponse(
        status_code=status_code,
        content=data
    )
