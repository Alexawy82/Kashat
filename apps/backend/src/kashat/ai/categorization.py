"""
AI Categorization Module - Consolidated categorization pipeline

This module consolidates all categorization functionality:
- Category matching and suggestions
- Smart categorization with merchant memory
- Auto-categorization
- Category acceptance and schema management

The categorization pipeline:
1. Check merchant memory (learned patterns)
2. Check enhanced patterns (500+ regex patterns)
3. Fall back to AI with confidence thresholds
"""

# Re-export from existing modules for backward compatibility

from ..ai_categories import (
    get_category_matcher,
    auto_create_category,
    SmartCategorySuggestion,
)

from ..ai_smart_categorization import (
    analyze_category_gaps,
    bootstrap_missing_categories,
    process_ai_category_suggestion,
    get_pending_category_suggestions,
    approve_category_suggestion,
    bulk_process_ai_suggestions,
    learn_from_transaction_categorization,
    get_merchant_memory_statistics,
    extract_merchant_from_description,
    get_smart_categorization_engine,
)

__all__ = [
    # Category matching
    "get_category_matcher",
    "auto_create_category",
    "SmartCategorySuggestion",
    # Smart categorization
    "analyze_category_gaps",
    "bootstrap_missing_categories",
    "process_ai_category_suggestion",
    "get_pending_category_suggestions",
    "approve_category_suggestion",
    "bulk_process_ai_suggestions",
    "learn_from_transaction_categorization",
    "get_merchant_memory_statistics",
    "extract_merchant_from_description",
    "get_smart_categorization_engine",
]
