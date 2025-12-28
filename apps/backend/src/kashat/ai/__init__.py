"""
Kashat AI Module - Consolidated AI functionality

This package consolidates all AI functionality into a clean, organized structure:
- core: AIService, AIConfig, providers
- categorization: Transaction categorization pipeline
- detection: Transfer, P2P, recurring detection
- quality: Data quality and deduplication
- workflows: Pipeline orchestration
- prompts: All prompt templates
- merchant: Merchant intelligence

For backward compatibility, key exports are re-exported from existing modules.
"""

# Re-export from existing modules for backward compatibility
# Note: ai.py was renamed to ai_service.py to avoid conflict with this package
from ..ai_service import (
    AIService,
    get_ai_service,
    TransactionInsights,
    CategorySuggestion,
    MerchantInfo,
    ping_ai,
    reset_ai_service,
)

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

from ..ai_dedup import get_ai_deduplicator

from ..ai_integration import (
    TransactionProcessor,
    process_transactions_batch,
    process_all_uncategorized_transactions,
    run_full_detection_workflow,
)

from ..ai_transfer_detection import (
    get_transfer_detection_service,
    AITransferDetectionService,
    TransferCandidate,
)

from ..merchant_intelligence import MerchantIntelligence

# Export all for convenience
__all__ = [
    # Core
    "AIService",
    "get_ai_service",
    "TransactionInsights",
    "CategorySuggestion",
    "MerchantInfo",
    "ping_ai",
    "reset_ai_service",
    # Categorization
    "get_category_matcher",
    "auto_create_category",
    "SmartCategorySuggestion",
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
    # Detection
    "get_transfer_detection_service",
    "AITransferDetectionService",
    "TransferCandidate",
    # Quality
    "get_ai_deduplicator",
    # Integration
    "TransactionProcessor",
    "process_transactions_batch",
    "process_all_uncategorized_transactions",
    "run_full_detection_workflow",
    # Merchant
    "MerchantIntelligence",
]
