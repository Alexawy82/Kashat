"""
AI Quality Module - Data quality and deduplication

This module consolidates quality-related functionality:
- Data quality scoring and analysis
- Duplicate detection
- Intelligent deduplication
"""

# Re-export from existing modules

from ..ai_dedup import (
    get_ai_deduplicator,
)

__all__ = [
    # Deduplication
    "get_ai_deduplicator",
]
