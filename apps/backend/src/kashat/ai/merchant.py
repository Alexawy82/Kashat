"""
AI Merchant Module - Merchant intelligence

This module provides merchant-related functionality:
- Merchant name extraction and normalization
- Merchant category mapping
- Merchant memory (learning from user categorizations)
"""

# Re-export from existing modules

from ..merchant_intelligence import (
    MerchantIntelligence,
)

from ..ai_smart_categorization import (
    extract_merchant_from_description,
    get_merchant_memory_statistics,
    learn_from_transaction_categorization,
)

__all__ = [
    "MerchantIntelligence",
    "extract_merchant_from_description",
    "get_merchant_memory_statistics",
    "learn_from_transaction_categorization",
]
