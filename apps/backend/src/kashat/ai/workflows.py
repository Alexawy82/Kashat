"""
AI Workflows Module - Pipeline orchestration

This module consolidates workflow functionality:
- Import workflow orchestration
- Insights workflow
- Recurring detection workflow
- Full detection pipeline
"""

# Re-export from existing modules

from ..ai_integration import (
    TransactionProcessor,
    process_transactions_batch,
    process_all_uncategorized_transactions,
    run_full_detection_workflow,
)

__all__ = [
    # Integration
    "TransactionProcessor",
    "process_transactions_batch",
    "process_all_uncategorized_transactions",
    "run_full_detection_workflow",
]
