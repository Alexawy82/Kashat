"""
Kashat API Response Schemas - Standardized response models

This module provides consistent response structures for the API.
"""

from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response with metadata."""

    items: List[T]
    total: int = Field(description="Total number of items available")
    offset: int = Field(default=0, description="Current offset")
    limit: int = Field(default=100, description="Items per page")
    has_more: bool = Field(description="Whether more items are available")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "offset": 0,
                "limit": 20,
                "has_more": True
            }
        }


class ListResponse(BaseModel, Generic[T]):
    """Simple list response without pagination."""

    items: List[T]
    count: int = Field(description="Number of items returned")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "count": 0
            }
        }


class SuccessResponse(BaseModel):
    """Success response for operations that don't return data."""

    success: bool = True
    message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully"
            }
        }


class ErrorResponse(BaseModel):
    """Error response structure."""

    error: str = Field(description="Error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[dict] = Field(default=None, description="Additional error context")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "NOT_FOUND",
                "message": "Transaction not found: abc123",
                "details": {"resource": "transaction", "id": "abc123"}
            }
        }


class StatusResponse(BaseModel):
    """Status response for health checks and status endpoints."""

    status: str = Field(description="Current status")
    version: Optional[str] = None
    uptime: Optional[float] = None
    details: Optional[dict] = None


class CountResponse(BaseModel):
    """Response for count-only queries."""

    count: int


class IdResponse(BaseModel):
    """Response for create operations returning an ID."""

    id: str
    created: bool = True


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""

    processed: int = Field(description="Number of items processed")
    succeeded: int = Field(description="Number of successful operations")
    failed: int = Field(description="Number of failed operations")
    errors: Optional[List[dict]] = Field(default=None, description="Details of failures")


# Export all
__all__ = [
    "PaginatedResponse",
    "ListResponse",
    "SuccessResponse",
    "ErrorResponse",
    "StatusResponse",
    "CountResponse",
    "IdResponse",
    "BulkOperationResponse",
]
