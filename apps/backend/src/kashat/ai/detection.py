"""
AI Detection Module - Transfer, P2P, and recurring detection

This module consolidates detection functionality:
- Transfer detection (internal, external)
- P2P payment detection (Zelle, Venmo, etc.)
- Recurring transaction detection
"""

# Re-export from existing modules

from ..ai_transfer_detection import (
    get_transfer_detection_service,
    AITransferDetectionService,
    TransferCandidate,
)

from ..transfers import (
    suggest_transfers,
)

from ..recurring import (
    detect_recurring_candidates,
    suggest_recurring,
)

__all__ = [
    # Transfer detection
    "get_transfer_detection_service",
    "AITransferDetectionService",
    "TransferCandidate",
    "suggest_transfers",
    # Recurring detection
    "detect_recurring_candidates",
    "suggest_recurring",
]
