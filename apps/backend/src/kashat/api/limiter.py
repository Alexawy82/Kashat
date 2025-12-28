"""
Rate limiting configuration for Kashat API.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global rate limiter instance
# Uses remote address (IP) as the key for rate limiting
limiter = Limiter(key_func=get_remote_address)

# Default limits for different endpoint types
DEFAULT_LIMIT = "1000/minute"
AI_LIMIT = "30/minute"           # AI analysis endpoints
AI_BULK_LIMIT = "10/minute"      # Bulk AI operations
IMPORT_LIMIT = "10/minute"       # File import operations
EXPORT_LIMIT = "30/minute"       # Export operations
