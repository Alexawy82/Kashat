"""
AI category acceptance schemas.

Single source of truth for request models used by both API routes and
internal acceptance logic to prevent schema drift.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class SingleAcceptanceRequest(BaseModel):
    """Request to accept a single AI category suggestion."""
    transaction_id: str
    suggested_category_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    create_if_missing: bool = True
    auto_merge_similar: bool = True
    provider: Optional[str] = None


class BatchAcceptanceRequest(BaseModel):
    """Request to accept multiple AI category suggestions."""
    acceptances: List[SingleAcceptanceRequest]
    create_missing_categories: bool = True
    auto_merge_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    create_parent_hierarchy: bool = True
