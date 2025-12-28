"""
Standardized Error Handling for LedgerLoop API

Provides consistent error response format across all API endpoints:
- ErrorResponse model for uniform JSON structure
- Custom exception classes for different error types
- Exception handlers for FastAPI integration
"""

from __future__ import annotations

from typing import Any, Optional, Dict, List
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import traceback

logger = logging.getLogger(__name__)


# =============================================================================
# Error Response Models
# =============================================================================

class ErrorDetail(BaseModel):
    """Detail about a specific error or validation issue."""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standardized error response format for all API errors.

    Example:
    {
        "error": {
            "type": "validation_error",
            "message": "Invalid request data",
            "code": "VALIDATION_ERROR",
            "details": [
                {"field": "amount", "message": "Amount must be positive", "code": "POSITIVE_REQUIRED"}
            ],
            "request_id": "abc123"
        }
    }
    """
    type: str
    message: str
    code: str
    details: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None


class ErrorWrapper(BaseModel):
    """Wrapper for error response."""
    error: ErrorResponse


# =============================================================================
# Custom Exceptions
# =============================================================================

class AppException(Exception):
    """Base exception class for all application errors.

    Subclass this for specific error types. Each subclass should define:
    - status_code: HTTP status code
    - error_type: Short string identifying the error type
    - error_code: Unique code for this error type
    """
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type: str = "internal_error"
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
        code: Optional[str] = None,
    ):
        self.message = message
        self.details = details
        self.code = code or self.error_code
        super().__init__(message)

    def to_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert exception to ErrorResponse model."""
        return ErrorResponse(
            type=self.error_type,
            message=self.message,
            code=self.code,
            details=self.details,
            request_id=request_id,
        )


class NotFoundError(AppException):
    """Resource not found error (404)."""
    status_code = status.HTTP_404_NOT_FOUND
    error_type = "not_found"
    error_code = "NOT_FOUND"

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        if message is None:
            if resource_id:
                message = f"{resource} with ID '{resource_id}' not found"
            else:
                message = f"{resource} not found"
        super().__init__(message)
        self.resource = resource
        self.resource_id = resource_id


class ValidationError(AppException):
    """Request validation error (400)."""
    status_code = status.HTTP_400_BAD_REQUEST
    error_type = "validation_error"
    error_code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str = "Invalid request data",
        details: Optional[List[ErrorDetail]] = None,
        field_errors: Optional[Dict[str, str]] = None,
    ):
        # Convert field_errors dict to details list if provided
        if field_errors and not details:
            details = [
                ErrorDetail(field=field, message=msg)
                for field, msg in field_errors.items()
            ]
        super().__init__(message, details)


class AuthenticationError(AppException):
    """Authentication failed error (401)."""
    status_code = status.HTTP_401_UNAUTHORIZED
    error_type = "authentication_error"
    error_code = "AUTHENTICATION_FAILED"

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message)


class AuthorizationError(AppException):
    """Authorization/permission denied error (403)."""
    status_code = status.HTTP_403_FORBIDDEN
    error_type = "authorization_error"
    error_code = "PERMISSION_DENIED"

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message)


class ConflictError(AppException):
    """Resource conflict error (409)."""
    status_code = status.HTTP_409_CONFLICT
    error_type = "conflict_error"
    error_code = "CONFLICT"

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message)


class RateLimitError(AppException):
    """Rate limit exceeded error (429)."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_type = "rate_limit_error"
    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(message)


class DatabaseError(AppException):
    """Database operation error (500)."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type = "database_error"
    error_code = "DATABASE_ERROR"

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message)


class ExternalServiceError(AppException):
    """External service (AI, etc.) error (502)."""
    status_code = status.HTTP_502_BAD_GATEWAY
    error_type = "external_service_error"
    error_code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, service: str = "External service", message: Optional[str] = None):
        if message is None:
            message = f"{service} is unavailable or returned an error"
        super().__init__(message)
        self.service = service


class ServiceUnavailableError(AppException):
    """Service temporarily unavailable (503)."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_type = "service_unavailable"
    error_code = "SERVICE_UNAVAILABLE"

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message)


# =============================================================================
# Exception Handlers
# =============================================================================

def get_request_id(request: Request) -> Optional[str]:
    """Extract request ID from request state or headers."""
    # Check request state first (set by middleware)
    if hasattr(request.state, "request_id"):
        return request.state.request_id
    # Check X-Request-ID header
    return request.headers.get("X-Request-ID")


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom AppException and subclasses."""
    request_id = get_request_id(request)
    error_response = exc.to_response(request_id)

    # Log the error
    logger.warning(
        f"AppException: {exc.error_type} - {exc.message}",
        extra={
            "error_type": exc.error_type,
            "error_code": exc.code,
            "status_code": exc.status_code,
            "request_id": request_id,
            "path": request.url.path,
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_response.model_dump()},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException to return consistent format."""
    request_id = get_request_id(request)

    # Map HTTP status codes to error types
    error_type_map = {
        400: ("validation_error", "VALIDATION_ERROR"),
        401: ("authentication_error", "AUTHENTICATION_FAILED"),
        403: ("authorization_error", "PERMISSION_DENIED"),
        404: ("not_found", "NOT_FOUND"),
        405: ("method_not_allowed", "METHOD_NOT_ALLOWED"),
        409: ("conflict_error", "CONFLICT"),
        422: ("validation_error", "UNPROCESSABLE_ENTITY"),
        429: ("rate_limit_error", "RATE_LIMIT_EXCEEDED"),
        500: ("internal_error", "INTERNAL_ERROR"),
        502: ("external_service_error", "BAD_GATEWAY"),
        503: ("service_unavailable", "SERVICE_UNAVAILABLE"),
    }

    error_type, error_code = error_type_map.get(
        exc.status_code,
        ("error", f"HTTP_{exc.status_code}")
    )

    error_response = ErrorResponse(
        type=error_type,
        message=str(exc.detail) if exc.detail else "An error occurred",
        code=error_code,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=exc.status_code,
        # Include FastAPI's conventional shape for compatibility with tests/clients,
        # while keeping the standardized error envelope.
        content={"detail": exc.detail, "error": error_response.model_dump()},
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: Any) -> JSONResponse:
    """Handle Pydantic validation errors from FastAPI."""
    from pydantic import ValidationError as PydanticValidationError

    request_id = get_request_id(request)

    details = []
    if isinstance(exc, PydanticValidationError):
        for error in exc.errors():
            loc = error.get("loc", [])
            field = ".".join(str(l) for l in loc if l != "body")
            details.append(ErrorDetail(
                field=field or None,
                message=error.get("msg", "Validation error"),
                code=error.get("type"),
            ))

    error_response = ErrorResponse(
        type="validation_error",
        message="Request validation failed",
        code="VALIDATION_ERROR",
        details=details if details else None,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": error_response.model_dump()},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions to prevent exposing internal details."""
    request_id = get_request_id(request)

    # Log the full exception for debugging
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    error_response = ErrorResponse(
        type="internal_error",
        message="An unexpected error occurred",
        code="INTERNAL_ERROR",
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": error_response.model_dump()},
    )


# =============================================================================
# Registration Helper
# =============================================================================

def register_exception_handlers(app: Any) -> None:
    """Register all exception handlers with a FastAPI app.

    Usage in main.py:
        from .errors import register_exception_handlers
        register_exception_handlers(app)
    """
    from fastapi import HTTPException as FastAPIHTTPException
    from fastapi.exceptions import RequestValidationError

    # Register handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(FastAPIHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, generic_exception_handler)
