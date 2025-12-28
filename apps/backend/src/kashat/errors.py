"""
Kashat Error Classes - Standardized error handling

This module provides consistent error types for the Kashat API.
All errors inherit from KashatError and provide structured responses.
"""

from typing import Optional


class KashatError(Exception):
    """Base exception class for all Kashat errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        details: Optional[dict] = None
    ):
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}
        super().__init__(message)


class NotFoundError(KashatError):
    """Resource not found error (404)."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} not found: {resource_id}",
            status=404,
            details={"resource": resource, "id": resource_id}
        )


class ValidationError(KashatError):
    """Request validation error (400)."""

    def __init__(self, field: str, message: str):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status=400,
            details={"field": field}
        )


class DuplicateError(KashatError):
    """Duplicate resource error (409)."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="DUPLICATE",
            message=f"{resource} already exists: {identifier}",
            status=409,
            details={"resource": resource, "identifier": identifier}
        )


class AIError(KashatError):
    """AI service error (503)."""

    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(
            code="AI_ERROR",
            message=message,
            status=503,
            details={"provider": provider} if provider else {}
        )


class ImportError(KashatError):
    """File import error (400)."""

    def __init__(self, message: str, filename: Optional[str] = None):
        super().__init__(
            code="IMPORT_ERROR",
            message=message,
            status=400,
            details={"filename": filename} if filename else {}
        )


class AuthenticationError(KashatError):
    """Authentication error (401)."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            code="AUTHENTICATION_ERROR",
            message=message,
            status=401
        )


class AuthorizationError(KashatError):
    """Authorization error (403)."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            code="AUTHORIZATION_ERROR",
            message=message,
            status=403
        )


class RateLimitError(KashatError):
    """Rate limit exceeded error (429)."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status=429,
            details=details
        )


class DatabaseError(KashatError):
    """Database operation error (500)."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            code="DATABASE_ERROR",
            message=message,
            status=500
        )


# Export all error classes
__all__ = [
    "KashatError",
    "NotFoundError",
    "ValidationError",
    "DuplicateError",
    "AIError",
    "ImportError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    "DatabaseError",
]
