"""
AI Core Module - Provider configuration and base service

This module contains:
- AIService: Main AI service class
- AIConfig: Configuration dataclass
- Provider initialization and fallback logic
- Rate limiting for AI endpoints
"""

# Re-export from existing ai_service.py for backward compatibility
from ..ai_service import (
    AIService,
    get_ai_service,
    reset_ai_service,
    ping_ai,
    TransactionInsights,
    CategorySuggestion,
    MerchantInfo,
)

__all__ = [
    "AIService",
    "get_ai_service",
    "reset_ai_service",
    "ping_ai",
    "TransactionInsights",
    "CategorySuggestion",
    "MerchantInfo",
]
