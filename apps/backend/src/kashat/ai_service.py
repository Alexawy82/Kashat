"""
AI Service Module for LedgerLoop

Provides AI-powered transaction analysis, merchant normalization,
and category suggestions using local models and optional OpenAI integration.

Enhanced with best practices (2025):
- Exponential backoff with jitter for rate limit handling
- Configurable timeouts and retry settings
- Robust error handling with specific exception types
- Connection validation and health checks
"""

from __future__ import annotations

import json
import re
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
import os
import time

# Prometheus metrics (optional)
try:
    from prometheus_client import Counter, Histogram  # type: ignore
    AI_CALLS = Counter("ai_calls_total", "AI calls", ["provider"])  # type: ignore
    AI_ERRORS = Counter("ai_errors_total", "AI errors", ["provider", "error_type"])  # type: ignore
    AI_LATENCY = Histogram("ai_latency_seconds", "AI latency (seconds)", ["provider"])  # type: ignore
    AI_RETRIES = Counter("ai_retries_total", "AI retry attempts", ["provider"])  # type: ignore
except Exception:  # pragma: no cover - metrics optional
    class _Noop:
        def labels(self, **kwargs):
            return self
        def inc(self, *a, **k):
            return None
        def observe(self, *a, **k):
            return None
    AI_CALLS = _Noop()
    AI_ERRORS = _Noop()
    AI_LATENCY = _Noop()
    AI_RETRIES = _Noop()

# OpenAI/compatible client (supports LM Studio via base_url)
#
# IMPORTANT: keep OpenAI import lazy.
# Importing `openai` pulls in httpx/httpcore and can be very slow on some filesystems
# (e.g., WSL/OneDrive), which blocks API startup. We only import when a provider is
# actually configured.
OPENAI_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from .config import data_dir


# =============================================================================
# AI Configuration with Best Practices
# =============================================================================

@dataclass
class AIConfig:
    """
    AI configuration with sensible defaults based on OpenAI best practices.

    References:
    - https://platform.openai.com/docs/guides/rate-limits
    - https://cookbook.openai.com/examples/how_to_handle_rate_limits
    """
    # Provider settings
    provider: str = "auto"  # local, openai, lmstudio, auto

    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    # LM Studio settings
    lmstudio_base_url: str = "http://127.0.0.1:1234/v1"
    lmstudio_api_key: str = "lm-studio"
    lmstudio_model: Optional[str] = None

    # Timeout settings (in seconds)
    timeout: float = 30.0  # Request timeout (reduced from 90s to prevent hanging)
    connect_timeout: float = 5.0  # Connection timeout (reduced from 10s)

    # Retry settings with exponential backoff
    max_retries: int = 2  # Reduced from 3 to fail faster
    retry_min_wait: float = 0.5  # Minimum wait between retries (seconds)
    retry_max_wait: float = 10.0  # Maximum wait between retries (reduced from 30s)
    retry_multiplier: float = 2.0  # Exponential multiplier
    retry_jitter: bool = True  # Add randomness to prevent thundering herd

    # Rate limiting
    max_concurrency: int = 2  # Maximum concurrent requests
    requests_per_minute: int = 60  # Rate limit (for self-throttling)

    # Processing settings
    batch_size: int = 5
    confidence_threshold: float = 0.7
    temperature: float = 0.1

    # Debug
    debug: bool = False

    # Model overrides for specific tasks
    model_overrides: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "AIConfig":
        """Load configuration from environment variables and settings file."""
        from .settings import load_settings
        s = load_settings()

        return cls(
            provider=os.getenv("KASHAT_AI_PROVIDER", str(s.get("ai_provider", "auto"))).lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY", str(s.get("ai_openai_api_key", ""))) or None,
            openai_base_url=os.getenv("KASHAT_AI_OPENAI_BASE_URL", str(s.get("ai_openai_base_url", ""))) or None,
            openai_model=os.getenv("KASHAT_AI_OPENAI_MODEL", str(s.get("ai_openai_model", "gpt-4o-mini"))),
            lmstudio_base_url=os.getenv("KASHAT_AI_LMSTUDIO_BASE_URL", str(s.get("ai_lmstudio_base_url", "http://127.0.0.1:1234/v1"))),
            lmstudio_api_key=os.getenv("KASHAT_AI_LMSTUDIO_API_KEY", "lm-studio"),
            lmstudio_model=os.getenv("KASHAT_AI_LMSTUDIO_MODEL", str(s.get("ai_lmstudio_model", ""))) or None,
            timeout=float(os.getenv("KASHAT_AI_TIMEOUT", str(s.get("ai_timeout", "30")))),
            connect_timeout=float(os.getenv("KASHAT_AI_CONNECT_TIMEOUT", str(s.get("ai_connect_timeout", "5")))),
            max_retries=int(os.getenv("KASHAT_AI_MAX_RETRIES", str(s.get("ai_max_retries", "2")))),
            retry_min_wait=float(os.getenv("KASHAT_AI_RETRY_MIN_WAIT", str(s.get("ai_retry_min_wait", "0.5")))),
            retry_max_wait=float(os.getenv("KASHAT_AI_RETRY_MAX_WAIT", str(s.get("ai_retry_max_wait", "10")))),
            retry_multiplier=float(os.getenv("KASHAT_AI_RETRY_MULTIPLIER", str(s.get("ai_retry_multiplier", "2")))),
            retry_jitter=os.getenv("KASHAT_AI_RETRY_JITTER", str(s.get("ai_retry_jitter", "true"))).lower() == "true",
            max_concurrency=int(os.getenv("KASHAT_AI_MAX_CONCURRENCY", str(s.get("ai_max_concurrency", "2")))),
            requests_per_minute=int(os.getenv("KASHAT_AI_REQUESTS_PER_MINUTE", str(s.get("ai_requests_per_minute", "60")))),
            batch_size=int(os.getenv("KASHAT_AI_BATCH_SIZE", str(s.get("ai_batch_size", "5")))),
            confidence_threshold=float(os.getenv("KASHAT_AI_CONFIDENCE_THRESHOLD", str(s.get("ai_confidence_threshold", "0.7")))),
            temperature=float(os.getenv("KASHAT_AI_TEMPERATURE", str(s.get("ai_temperature", "0.1")))),
            debug=os.getenv("KASHAT_AI_DEBUG", str(s.get("ai_debug", "false"))).lower() == "true",
            model_overrides={
                "categorize": os.getenv("KASHAT_AI_MODEL_CATEGORIZE", str(s.get("ai_model_categorize", ""))) or "",
                "merchant": os.getenv("KASHAT_AI_MODEL_MERCHANT", str(s.get("ai_model_merchant", ""))) or "",
                "anomaly": os.getenv("KASHAT_AI_MODEL_ANOMALY", str(s.get("ai_model_anomaly", ""))) or "",
            }
        )


# =============================================================================
# Custom Exceptions for AI Errors
# =============================================================================

class AIError(Exception):
    """Base exception for AI service errors."""
    pass


class AIConnectionError(AIError):
    """Failed to connect to AI provider."""
    pass


class AIRateLimitError(AIError):
    """Rate limit exceeded."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class AITimeoutError(AIError):
    """Request timed out."""
    pass


class AIAuthenticationError(AIError):
    """Authentication failed (invalid API key)."""
    pass


class AIQuotaExceededError(AIError):
    """API quota/credits exceeded."""
    pass


# =============================================================================
# Exponential Backoff with Jitter
# =============================================================================

def calculate_backoff(
    attempt: int,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    multiplier: float = 2.0,
    jitter: bool = True
) -> float:
    """
    Calculate wait time using exponential backoff with optional jitter.

    Based on OpenAI's recommended retry strategy:
    https://platform.openai.com/docs/guides/rate-limits/retrying-with-exponential-backoff

    Args:
        attempt: Current attempt number (0-indexed)
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        multiplier: Exponential multiplier
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Wait time in seconds
    """
    # Calculate base exponential wait: min_wait * (multiplier ^ attempt)
    wait = min_wait * (multiplier ** attempt)

    # Cap at max_wait
    wait = min(wait, max_wait)

    # Add jitter: random value between 0 and wait
    if jitter:
        wait = wait * (0.5 + random.random())  # 50% to 150% of calculated wait

    return wait


async def retry_with_backoff(
    func,
    *args,
    max_retries: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    multiplier: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (AIRateLimitError, AIConnectionError, AITimeoutError),
    provider: str = "unknown",
    **kwargs
):
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        min_wait: Minimum wait between retries
        max_wait: Maximum wait between retries
        multiplier: Exponential multiplier
        jitter: Add randomness to wait times
        retryable_exceptions: Tuple of exception types to retry on
        provider: Provider name for metrics

    Returns:
        Result of the function call

    Raises:
        The last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e

            if attempt == max_retries:
                # No more retries
                logger.error(f"All {max_retries} retries exhausted for {provider}: {e}")
                raise

            # Check for rate limit with retry-after header
            wait_time = calculate_backoff(attempt, min_wait, max_wait, multiplier, jitter)
            if isinstance(e, AIRateLimitError) and e.retry_after:
                wait_time = max(wait_time, e.retry_after)

            AI_RETRIES.labels(provider=provider).inc()
            logger.warning(f"Retry {attempt + 1}/{max_retries} for {provider} after {wait_time:.1f}s: {e}")

            await asyncio.sleep(wait_time)
        except (AIAuthenticationError, AIQuotaExceededError) as e:
            # Don't retry auth or quota errors
            logger.error(f"Non-retryable error for {provider}: {e}")
            raise

    raise last_exception


logger = logging.getLogger(__name__)


@dataclass
class MerchantInfo:
    """Extracted merchant information from transaction description"""
    normalized_name: str
    confidence: float
    original_description: str
    merchant_type: Optional[str] = None
    location: Optional[str] = None


@dataclass
class CategorySuggestion:
    """AI-powered category suggestion"""
    category_id: Optional[str]
    category_name: str
    confidence: float
    reasoning: str
    merchant_name: Optional[str] = None  # Clean extracted merchant name


@dataclass
class TransactionInsights:
    """AI analysis results for a transaction"""
    merchant_info: Optional[MerchantInfo]
    category_suggestions: List[CategorySuggestion]
    anomaly_flags: List[str]
    confidence_score: float
    processing_method: str  # 'local', 'openai', 'fallback'
    provider_name: Optional[str] = None
    model_name: Optional[str] = None
    latency_ms: Optional[int] = None


class LocalAIService:
    """Local AI service using simple heuristics and pattern matching"""
    
    def __init__(self):
        self.merchant_patterns = self._load_merchant_patterns()
        self.category_keywords = self._load_category_keywords()
        self.merchant_category_map = self._load_merchant_category_map()
    
    def _load_merchant_patterns(self) -> Dict[str, str]:
        """Load common merchant normalization patterns"""
        return {
            r'STARBUCKS.*': 'Starbucks',
            r'AMAZON.*MKTP.*': 'Amazon',
            r'AMAZON\.COM.*': 'Amazon',
            r'AMZ\*.*': 'Amazon',
            r'SQ\s*\*.*': 'Square Payment',
            r'PAYPAL.*': 'PayPal',
            r'VENMO.*': 'Venmo',
            r'UBER.*': 'Uber',
            r'LYFT.*': 'Lyft',
            r'NETFLIX.*': 'Netflix',
            r'SPOTIFY.*': 'Spotify',
            r'APPLE.*': 'Apple',
            r'GOOGLE.*': 'Google',
            r'MICROSOFT.*': 'Microsoft',
            r'WALMART.*': 'Walmart',
            r'TARGET.*': 'Target',
            r'COSTCO.*': 'Costco',
            r'SHELL.*': 'Shell',
            r'EXXON.*': 'Exxon',
            r'CHEVRON.*': 'Chevron',
            r'MCDONALD.*': 'McDonald\'s',
            r'BURGER KING.*': 'Burger King',
            r'SUBWAY.*': 'Subway',
            r'WHOLE FOODS.*': 'Whole Foods',
            r'SAFEWAY.*': 'Safeway',
            r'KROGER.*': 'Kroger',
        }
    
    def _load_category_keywords(self) -> Dict[str, List[str]]:
        """Load category classification keywords"""
        return {
            'Income': [
                'payroll', 'salary', 'wages', 'direct deposit', 'paycheck',
                'freelance', 'contractor', 'consulting', '1099', 'invoice payment',
                'transfer from', 'deposit from', 'income', 'earnings', 'cashback', 'bankamerideals'
            ],
            'Internal Transfer': [
                'transfer from sav', 'transfer from chk', 'transfer to sav', 'transfer to chk',
                'automatic transfer to savings', 'auto transfer to savings',
                'keep the change', 'savings transfer', 'checking transfer',
                'account transfer', 'internal transfer'
            ],
            'Zelle': [
                'zelle from', 'zelle to', 'zelle payment', 'zelle transfer'
            ],
            'Transfers': [
                'paypal to', 'cash app to', 'venmo to', 'auto pay to', 'autopay to'
            ],
            'Food & Dining': [
                'restaurant', 'cafe', 'coffee', 'pizza', 'burger', 'food',
                'dining', 'lunch', 'dinner', 'breakfast', 'starbucks',
                'mcdonald', 'subway', 'chipotle', 'domino', 'kitchen',
                'chick-fil-a', 'taco bell', 'kfc', 'wendy', 'popeyes',
                'panera', 'bojangles', 'lobster', 'pepper asian', 'alaboud', 'red pepper asian'
            ],
            'Gas & Automotive': [
                'shell', 'exxon', 'chevron', 'bp', 'mobil', 'gas station',
                'fuel', 'gas pump', 'automotive', 'auto repair', 'car wash', 'sheetz'
            ],
            'Shopping': [
                'amazon', 'walmart', 'target', 'costco', 'store',
                'shopping', 'retail', 'purchase', 'buy', 'google store'
            ],
            'Grocery': [
                'market', 'grocery', 'groceries', 'harris teeter', 'al-basha'
            ],
            'Transportation': [
                'uber', 'lyft', 'taxi', 'transport', 'metro', 'bus',
                'train', 'flight', 'airline', 'parking'
            ],
            'Entertainment': [
                'netflix', 'spotify', 'movie', 'theater', 'game',
                'entertainment', 'streaming', 'music', 'concert',
                'youtube', 'plex', 'ground news', 'nebula', 'curiositystream', 'midjourney', 'steam games', 'giganews', 'ea inc'
            ],
            'Bills & Utilities': [
                'electric', 'gas', 'water', 'internet', 'phone',
                'cable', 'utility', 'bill', 'service', 'duke energy', 'dominion energy', 'google fiber', 'google fi', 'roadrunner', 'spectrum'
            ],
            'Healthcare': [
                'doctor', 'dentist', 'pharmacy', 'medical', 'health',
                'hospital', 'clinic', 'medicine', 'prescription'
            ],
            'Financial': [
                'bank', 'fee', 'interest', 'loan', 'credit',
                'investment', 'financial', 'insurance', 'identityiq'
            ],
            'Loans & Credit': [
                'auto payment', 'autopay', 'best buy auto', 'ally auto', 'avant llc', 'citi card auto pay', 'bank of america auto pay'
            ],
            'Housing & Mortgage': [
                'mortgage', 'carrington mortgage'
            ],
            'Technology': [
                'openai', 'claude.ai', 'cursor ai', 'midjourney', 'microsoft', 'google', 'apple', 'software', 'subscription'
            ],
            'Professional Services': [
                'inventorylab', 'identityiq', 'teikametrics', 'vidiq'
            ]
        }

    def _load_merchant_category_map(self) -> Dict[str, str]:
        """Curated merchant -> category mapping (regex -> category).

        This increases specificity over generic keyword categories and is derived from
        the observed dataset (fixtures) and common US merchants. Patterns are case-insensitive.
        """
        return {
            r"HARRIS\s+TE": "Grocery",
            r"AL[- ]?BASHA": "Grocery",
            r"MECCA\s+MARKET": "Grocery",
            r"SHEETZ": "Gas & Automotive",
            r"GOOGLE\s*\*?\s*FIBER|GOOGLE\s+FIBER": "Bills & Utilities",
            r"CARRINGTON.*MORTGAGE|MORTGAGE": "Housing & Mortgage",
            r"GEICO": "Bills & Utilities",
            r"DOMINION\s+ENERGY|DUKE\s+ENERGY": "Bills & Utilities",
            r"NETFLIX": "Entertainment",
            r"SPOTIFY": "Entertainment",
            r"OPENAI": "Technology",
            r"GODADDY": "Professional Services",
            r"GIGANEWS|PLEX|NEBULA|CURIOSITYSTREAM|YOUTUBE": "Entertainment",
            r"WINGSTOP|PIZZA\s*HUT|MCDONALD|STARBUCKS|OUTBACK|KANKI|TACO\s*BELL|PANADERIA": "Food & Dining",
            r"HOME\s+DEPOT|WAL[- ]?MART|TARGET|COSTCO": "Shopping",
            r"AMAZON": "Shopping",
            r"LYFT|UBER": "Transportation",
            r"MICROSOFT|GOOGLE\s+(?!FIBER)": "Technology",
        }
    
    def normalize_merchant(self, description: str) -> MerchantInfo:
        """Extract and normalize merchant name from transaction description"""
        description = description.strip().upper()
        
        # Try pattern matching
        for pattern, normalized_name in self.merchant_patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                return MerchantInfo(
                    normalized_name=normalized_name,
                    confidence=0.9,
                    original_description=description,
                    merchant_type=self._guess_merchant_type(normalized_name)
                )
        
        # Fallback: clean up the description
        cleaned = self._clean_description(description)
        return MerchantInfo(
            normalized_name=cleaned,
            confidence=0.6,
            original_description=description,
            merchant_type=self._guess_merchant_type(cleaned)
        )
    
    def _clean_description(self, description: str) -> str:
        """Clean up transaction description to extract merchant name"""
        # Remove common prefixes and suffixes
        description = re.sub(r'^(DEBIT|CREDIT|PURCHASE|PAYMENT|POS|ACH|TRANSFER)\s*', '', description)
        description = re.sub(r'\s*(PAYMENT|PURCHASE|DEBIT|CREDIT)$', '', description)
        
        # Remove numbers and special characters at the end
        description = re.sub(r'\s*\d+\s*$', '', description)
        description = re.sub(r'\s*[#*]\w*\s*$', '', description)
        
        # Take first few words (likely merchant name)
        words = description.split()[:3]
        return ' '.join(words).title()
    
    def _guess_merchant_type(self, merchant_name: str) -> Optional[str]:
        """Guess merchant type from name"""
        merchant_lower = merchant_name.lower()
        
        if any(keyword in merchant_lower for keyword in ['coffee', 'cafe', 'restaurant', 'food']):
            return 'restaurant'
        elif any(keyword in merchant_lower for keyword in ['gas', 'shell', 'exxon', 'fuel']):
            return 'gas_station'
        elif any(keyword in merchant_lower for keyword in ['store', 'market', 'shop']):
            return 'retail'
        elif any(keyword in merchant_lower for keyword in ['bank', 'credit', 'financial']):
            return 'financial'
        
        return None
    
    def suggest_categories(self, description: str, amount: float) -> List[CategorySuggestion]:
        """Suggest categories based on transaction description and amount"""
        # Use enhanced categorization service for better accuracy
        try:
            from .ai_enhanced_categorization import categorize_transaction_enhanced
            enhanced_suggestions = categorize_transaction_enhanced(description, amount)
            if enhanced_suggestions:
                return enhanced_suggestions
        except ImportError:
            logger.warning("Enhanced categorization service not available, falling back to basic service")
        
        # Fallback to original logic
        suggestions = []
        description_lower = description.lower()

        # 0) Extract PayPal vendor if present to gain specificity
        paypal_vendor = None
        m = re.search(r"paypal\s*\*\s*([a-z0-9\-\s\.'&]+)", description_lower, re.IGNORECASE)
        if m:
            paypal_vendor = m.group(1).strip().upper()

        # 1) Merchant-specific mapping first (high confidence)
        desc_upper = description.strip().upper()
        for pattern, cat in self.merchant_category_map.items():
            if re.search(pattern, desc_upper, re.IGNORECASE) or (paypal_vendor and re.search(pattern, paypal_vendor, re.IGNORECASE)):
                suggestions.append(CategorySuggestion(
                    category_id=None,
                    category_name=cat,
                    confidence=0.92,
                    reasoning=f"Merchant mapping matched: pattern '{pattern}'"
                ))
                break  # favor first specific match
        
        # Enhanced logic for income detection
        if amount > 0:  # Credits only
            # Check for explicit income patterns
            if self._is_income_transaction(description_lower):
                suggestions.append(CategorySuggestion(
                    category_id=None,
                    category_name="Income",
                    confidence=0.95,
                    reasoning="Income pattern detected in credit transaction"
                ))
            
            # Check for internal transfer patterns  
            elif self._is_internal_transfer(description_lower):
                suggestions.append(CategorySuggestion(
                    category_id=None,
                    category_name="Internal Transfer",
                    confidence=0.9,
                    reasoning="Internal account transfer pattern detected"
                ))
            
            # Check for Zelle patterns
            elif self._is_zelle_transaction(description_lower):
                suggestions.append(CategorySuggestion(
                    category_id=None,
                    category_name="Zelle",
                    confidence=0.95,
                    reasoning="Zelle payment pattern detected"
                ))
        
        # Standard category matching for all other transactions
        for category, keywords in self.category_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in description_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                confidence = min(0.9, score / len(keywords) * 2)  # Scale confidence
                reasoning = f"Matched keywords: {', '.join(matched_keywords)}"
                
                suggestions.append(CategorySuggestion(
                    category_id=None,  # Will be resolved later
                    category_name=category,
                    confidence=confidence,
                    reasoning=reasoning
                ))
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:3]  # Return top 3 suggestions
    
    def _is_income_transaction(self, description: str) -> bool:
        """Check if transaction matches income patterns"""
        income_patterns = [
            r'transfer from [a-z]{2,}[\s\d]*(?:(?!sav|chk|savings|checking)\w)*',  # Transfer from business (not account)
            r'deposit from',
            r'payroll',
            r'salary',
            r'direct deposit',
            r'freelance',
            r'contractor',
            r'consulting'
        ]
        
        for pattern in income_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                # Extra check: if it says "transfer from" make sure it's not from sav/chk
                if 'transfer from' in pattern:
                    if not re.search(r'transfer from (sav|chk|savings|checking)', description, re.IGNORECASE):
                        return True
                else:
                    return True
        return False
    
    def _is_internal_transfer(self, description: str) -> bool:
        """Check if transaction is internal transfer between accounts"""
        internal_patterns = [
            r'transfer from (sav|chk|savings|checking)',
            r'transfer to (sav|chk|savings|checking)',
            r'keep the change',
            r'automatic transfer to savings',
            r'account transfer',
            r'internal transfer'
        ]
        
        for pattern in internal_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return True
        return False
    
    def _is_zelle_transaction(self, description: str) -> bool:
        """Check if transaction is a Zelle payment"""
        return 'zelle' in description
    
    def detect_anomalies(self, description: str, amount: float) -> List[str]:
        """Detect potential anomalies in transactions"""
        anomalies = []
        
        # Large amount anomaly
        if abs(amount) > 1000:
            anomalies.append('large_amount')
        
        # Unusual description patterns
        if len(description) < 5:
            anomalies.append('short_description')
        
        if re.search(r'\d{10,}', description):
            anomalies.append('long_number_sequence')
        
        # International transaction indicators
        if re.search(r'(FOREIGN|INTERNATIONAL|CONVERSION)', description, re.IGNORECASE):
            anomalies.append('international_transaction')
        
        return anomalies


class OpenAIService:
    """
    OpenAI and OpenAI-compatible integration (LM Studio via base_url).

    Enhanced with best practices:
    - Configurable timeout and connection timeout
    - Built-in retry logic with exponential backoff
    - Proper error classification (rate limit, auth, timeout, etc.)
    - Connection validation
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        config: Optional[AIConfig] = None
    ):
        try:
            from openai import AsyncOpenAI  # type: ignore
            import httpx
        except Exception as e:
            raise ImportError("OpenAI package not available") from e

        self.config = config or AIConfig()

        # Configure timeout with both connect and request timeouts
        timeout = httpx.Timeout(
            timeout=self.config.timeout,
            connect=self.config.connect_timeout
        )

        # Async client with proper timeout configuration
        # Note: OpenAI client has built-in retry, but we add our own for more control
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=0  # We handle retries ourselves for better control
        )

        # Model configuration
        self.default_model = default_model or self.config.openai_model
        self.base_url = base_url
        self._debug = self.config.debug
        self._validated = False  # Track if connection has been validated

    def _classify_error(self, e: Exception) -> AIError:
        """Classify an OpenAI exception into our custom error types."""
        error_str = str(e).lower()
        error_type = type(e).__name__

        # Check for specific error types
        if "authentication" in error_str or "api key" in error_str or "401" in error_str:
            return AIAuthenticationError(f"Authentication failed: {e}")
        elif "rate limit" in error_str or "429" in error_str or "too many requests" in error_str:
            # Try to extract retry-after
            retry_after = None
            import re
            match = re.search(r'retry.after[:\s]*(\d+)', error_str)
            if match:
                retry_after = float(match.group(1))
            return AIRateLimitError(f"Rate limit exceeded: {e}", retry_after=retry_after)
        elif "quota" in error_str or "insufficient" in error_str or "billing" in error_str:
            return AIQuotaExceededError(f"Quota exceeded: {e}")
        elif "timeout" in error_str or "timed out" in error_str:
            return AITimeoutError(f"Request timed out: {e}")
        elif "connection" in error_str or "connect" in error_str or "refused" in error_str:
            return AIConnectionError(f"Connection failed: {e}")
        else:
            return AIError(f"AI error: {e}")

    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 300
    ) -> Any:
        """Make a request to the OpenAI API with proper error handling."""
        try:
            resp = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=max_tokens,
            )
            return resp
        except Exception as e:
            # Classify and re-raise with our custom exception type
            raise self._classify_error(e) from e

    async def analyze_transaction(self, description: str, amount: float, *, model: Optional[str] = None, categories: Optional[List[str]] = None) -> TransactionInsights:
        """Analyze transaction using chat.completions with JSON-style output."""
        # Build category list for prompt
        if categories:
            cat_list = ", ".join(categories)
        else:
            # Fetch from database if not provided
            try:
                from .db import get_conn
                conn = get_conn()
                rows = conn.execute("SELECT name FROM category ORDER BY name").fetchall()
                cat_list = ", ".join([r[0] for r in rows]) if rows else "Food & Dining, Shopping, Bills & Utilities, Transportation, Entertainment, Income, Transfers, Zelle, Grocery, Gas & Automotive"
            except:
                cat_list = "Food & Dining, Shopping, Bills & Utilities, Transportation, Entertainment, Income, Transfers, Zelle, Grocery, Gas & Automotive"

        # Simpler prompt for smaller LLMs with merchant hints
        prompt = f"""Categorize this bank transaction.

AVAILABLE CATEGORIES: {cat_list}

MERCHANT HINTS (use these to help categorize):
- Gas & Auto: Sheetz, Shell, Exxon, Chevron, BP, car wash, auto spa, Jiffy Lube, AutoZone → Gas & Automotive
- Grocery: Harris Teeter, Walmart Grocery, Kroger, Safeway, Aldi, Al-Basha, Sams Club, Mecca Market → Grocery
- Restaurants/Food: Starbucks, McDonald's, Chipotle, DoorDash, Wingstop, Bojangles, Sonic → Food & Dining
- Entertainment: Netflix, Spotify, YouTube, Hulu, Plex, F1.com, F1 TV, ESPN+, Disney+, Nebula, HBO Max, Peacock, Steam, PlayStation, Xbox, EA Sports → Entertainment
- Tech/Software: OpenAI, Microsoft, Google Ads, Canva, Replit, Leonardo.ai, Midjourney, Cursor AI, Shopify, GoDaddy, Teikametrics → Technology or Software
- Shopping: Amazon, Walmart, Target, tobacco shop, Maxx Tobacco, smoke shop, vape, Dollar General, 7-Eleven, convenience store → Shopping
- Salons/Personal Care: salon, barber, hair cut, nail salon, spa → Personal Care
- Mortgage: Carrington, mortgage payment → Mortgage Payment
- Insurance: Geico, Progressive, State Farm → Insurance
- Utilities: Duke Energy, Google Fiber, Spectrum, Verizon, AT&T → Bills & Utilities
- P2P Transfers: Cash App, Venmo, PayPal transfer, "pmnt sent" → Transfers
- Financial: Avant, Citi Autopay, Rocket Money, Albert Genius, IRS, loan payment → Financial Services

RULES:
- For credits (positive amounts > $500 with DES: pattern): likely Income (payroll/salary)
- Bank rewards, cashback, rebates = Income
- "zelle from/to" = Zelle
- "transfer from sav/chk/brk" = Internal Transfer
- Cash App, Venmo payments = Transfers (NOT Financial Services)
- Payroll, salary, direct deposit, employer DES: = Income
- For debits: match merchant to category using hints above

Transaction: {description}
Amount: ${amount:.2f}

Respond with ONLY valid JSON:
{{"merchant_name": "extracted merchant", "category": "one category from list", "confidence": 0.8, "reasoning": "brief reason"}}"""

        if self._debug:
            logger.info(f"[AI DEBUG] Sending prompt:\n{prompt}")

        mdl = model or self.default_model
        _t0 = time.perf_counter()

        try:
            # Use retry with backoff for resilient API calls
            async def make_call():
                return await self._make_request(
                    messages=[{"role": "user", "content": prompt}],
                    model=mdl,
                    max_tokens=300
                )

            resp = await retry_with_backoff(
                make_call,
                max_retries=self.config.max_retries,
                min_wait=self.config.retry_min_wait,
                max_wait=self.config.retry_max_wait,
                multiplier=self.config.retry_multiplier,
                jitter=self.config.retry_jitter,
                provider=self.base_url or "openai"
            )

            latency_ms = int((time.perf_counter() - _t0) * 1000)

            content = resp.choices[0].message.content if resp and resp.choices else None

            if self._debug:
                logger.info(f"[AI DEBUG] Raw response ({latency_ms}ms):\n{content}")

            result: Dict[str, Any] = {}
            if content:
                try:
                    # Try to extract JSON from response (handle markdown code blocks)
                    json_str = content.strip()
                    # Remove markdown code blocks if present
                    if "```json" in json_str:
                        json_str = json_str.split("```json")[1].split("```")[0].strip()
                    elif "```" in json_str:
                        json_str = json_str.split("```")[1].split("```")[0].strip()
                    # Find JSON object in response
                    if "{" in json_str:
                        start = json_str.find("{")
                        end = json_str.rfind("}") + 1
                        json_str = json_str[start:end]
                    result = json.loads(json_str)
                    if self._debug:
                        logger.info(f"[AI DEBUG] Parsed result: {result}")
                except Exception as parse_err:
                    if self._debug:
                        logger.warning(f"[AI DEBUG] JSON parse failed: {parse_err}, raw: {content}")
                    # Extract rough key/value via regex fallback
                    cat_match = re.search(r'"category"\s*:\s*"([^"]+)"', content or "")
                    merchant_match = re.search(r'"merchant_name"\s*:\s*"([^"]+)"', content or "")
                    result = {
                        "merchant_name": merchant_match.group(1) if merchant_match else description[:50],
                        "category": cat_match.group(1) if cat_match else "Uncategorized",
                        "confidence": 0.6,
                        "anomalies": [],
                    }

            merchant_name = result.get("merchant_name") or description
            category = result.get("category") or "Uncategorized"
            confidence = float(result.get("confidence", 0.7))
            anomalies = result.get("anomalies") or []
            reasoning = result.get("reasoning") or "LLM analysis"

            self._validated = True  # Mark as validated after successful call

            return TransactionInsights(
                merchant_info=MerchantInfo(
                    normalized_name=merchant_name,
                    confidence=confidence,
                    original_description=description,
                ),
                category_suggestions=[
                    CategorySuggestion(
                        category_id=None,
                        category_name=category,
                        confidence=confidence,
                        reasoning=reasoning,
                    )
                ],
                anomaly_flags=anomalies,
                confidence_score=confidence,
                processing_method="openai",
                provider_name="openai-compatible",
                model_name=mdl,
                latency_ms=latency_ms,
            )

        except AIAuthenticationError as e:
            AI_ERRORS.labels(provider=self.base_url or "openai", error_type="auth").inc()
            logger.error(f"Authentication failed: {e}")
            raise
        except AIQuotaExceededError as e:
            AI_ERRORS.labels(provider=self.base_url or "openai", error_type="quota").inc()
            logger.error(f"Quota exceeded: {e}")
            raise
        except AIRateLimitError as e:
            AI_ERRORS.labels(provider=self.base_url or "openai", error_type="rate_limit").inc()
            logger.warning(f"Rate limit after retries: {e}")
            # Fall back to local
            local_service = LocalAIService()
            return await local_service.analyze_transaction(description, amount)
        except (AIConnectionError, AITimeoutError) as e:
            AI_ERRORS.labels(provider=self.base_url or "openai", error_type="connection").inc()
            logger.warning(f"Connection/timeout error: {e}")
            # Fall back to local
            local_service = LocalAIService()
            return await local_service.analyze_transaction(description, amount)
        except Exception as e:
            AI_ERRORS.labels(provider=self.base_url or "openai", error_type="unknown").inc()
            logger.error(f"OpenAI-compatible analysis failed: {e}")
            # Fallback to local analysis
            local_service = LocalAIService()
            return await local_service.analyze_transaction(description, amount)

    async def analyze_with_prompt(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: int = 500,
        task_type: str = "custom"
    ) -> str:
        """
        Analyze using a custom prompt and return raw response.

        Useful for specialized analysis like transfer detection.
        """
        mdl = model or self.default_model
        _t0 = time.perf_counter()

        try:
            async def make_call():
                return await self._make_request(
                    messages=[{"role": "user", "content": prompt}],
                    model=mdl,
                    max_tokens=max_tokens
                )

            resp = await retry_with_backoff(
                make_call,
                max_retries=self.config.max_retries,
                min_wait=self.config.retry_min_wait,
                max_wait=self.config.retry_max_wait,
                multiplier=self.config.retry_multiplier,
                jitter=self.config.retry_jitter,
                provider=self.base_url or "openai"
            )

            latency_ms = int((time.perf_counter() - _t0) * 1000)
            content = resp.choices[0].message.content if resp and resp.choices else ""

            if self._debug:
                logger.info(f"[AI DEBUG] Custom prompt response ({latency_ms}ms):\n{content}")

            return content

        except Exception as e:
            logger.error(f"Custom prompt analysis failed: {e}")
            raise

    async def ping(self, *, model: Optional[str] = None) -> Dict[str, Any]:
        """Send a tiny request to validate connectivity and measure latency."""
        mdl = model or self.default_model
        start = time.perf_counter()

        try:
            resp = await self._make_request(
                messages=[{"role": "user", "content": "Reply with OK"}],
                model=mdl,
                max_tokens=3
            )
            ms = int((time.perf_counter() - start) * 1000)
            ok = bool(resp and resp.choices)
            self._validated = ok
            return {
                "ok": ok,
                "latency_ms": ms,
                "model": mdl,
                "base_url": self.base_url,
                "config": {
                    "timeout": self.config.timeout,
                    "max_retries": self.config.max_retries,
                    "retry_jitter": self.config.retry_jitter
                }
            }
        except AIAuthenticationError as e:
            return {
                "ok": False,
                "error": str(e),
                "error_type": "authentication",
                "model": mdl,
                "base_url": self.base_url,
                "suggestion": "Check your API key in settings"
            }
        except AIQuotaExceededError as e:
            return {
                "ok": False,
                "error": str(e),
                "error_type": "quota",
                "model": mdl,
                "base_url": self.base_url,
                "suggestion": "Check your API billing/credits"
            }
        except AIConnectionError as e:
            return {
                "ok": False,
                "error": str(e),
                "error_type": "connection",
                "model": mdl,
                "base_url": self.base_url,
                "suggestion": "Check if the AI service is running and accessible"
            }
        except AITimeoutError as e:
            return {
                "ok": False,
                "error": str(e),
                "error_type": "timeout",
                "model": mdl,
                "base_url": self.base_url,
                "suggestion": f"Request timed out after {self.config.timeout}s. Try increasing timeout."
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "error_type": "unknown",
                "model": mdl,
                "base_url": self.base_url
            }


class AIService:
    """
    Main AI service that coordinates local and cloud AI capabilities.

    Enhanced with:
    - Centralized configuration via AIConfig
    - Rate limiting via semaphore
    - Configurable retry and timeout settings
    """

    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or AIConfig.from_env()
        self.provider = self.config.provider
        self.local_service = LocalAIService()
        self.model_overrides = {k: v for k, v in self.config.model_overrides.items() if v}

        # Concurrency control via semaphore
        self._sem = asyncio.Semaphore(self.config.max_concurrency)

        # We may have both LM Studio and OpenAI clients for 'auto' escalation
        self.lmstudio_service: Optional[OpenAIService] = None
        self.openai_service: Optional[OpenAIService] = None

        try:
            # LM Studio client (OpenAI-compatible, local server)
            if self.config.lmstudio_base_url:
                self.lmstudio_service = OpenAIService(
                    api_key=self.config.lmstudio_api_key,
                    base_url=self.config.lmstudio_base_url,
                    default_model=self.config.lmstudio_model,
                    config=self.config,
                )
                logger.info(f"LM Studio client initialized: {self.config.lmstudio_base_url}")

            # OpenAI client (cloud)
            if self.config.openai_api_key:
                self.openai_service = OpenAIService(
                    api_key=self.config.openai_api_key,
                    base_url=self.config.openai_base_url,
                    default_model=self.config.openai_model,
                    config=self.config,
                )
                logger.info(f"OpenAI client initialized: {self.config.openai_base_url or 'api.openai.com'}")
        except Exception as e:
            logger.warning(f"Failed to initialize AI provider client(s): {e}")
    
    async def analyze_transaction(self, description: str, amount: float, *, task: str = "categorize") -> TransactionInsights:
        """Analyze a transaction using configured AI provider strategy with confidence-based escalation in 'auto'."""
        provider = self.provider
        model = self.model_overrides.get(task)
        threshold = self.config.confidence_threshold
        timeout_s = self.config.timeout

        # Provider: OpenAI only
        if provider == "openai" and self.openai_service:
            try:
                async with self._sem:
                    prov = "openai"
                    AI_CALLS.labels(provider=prov).inc()
                    start = time.perf_counter()
                    res = await asyncio.wait_for(self.openai_service.analyze_transaction(description, amount, model=model), timeout=timeout_s)
                    AI_LATENCY.labels(provider=prov).observe(time.perf_counter() - start)
                    return res
            except Exception as e:
                AI_ERRORS.labels(provider="openai").inc()
                logger.warning(f"OpenAI analysis failed, falling back to local: {e}")
        # Provider: LM Studio only
        if provider == "lmstudio" and self.lmstudio_service:
            try:
                async with self._sem:
                    prov = "lmstudio"
                    AI_CALLS.labels(provider=prov).inc()
                    start = time.perf_counter()
                    res = await asyncio.wait_for(self.lmstudio_service.analyze_transaction(description, amount, model=model), timeout=timeout_s)
                    AI_LATENCY.labels(provider=prov).observe(time.perf_counter() - start)
                    return res
            except Exception as e:
                AI_ERRORS.labels(provider="lmstudio").inc()
                logger.warning(f"LM Studio analysis failed, falling back to local: {e}")
        # Provider: Auto escalation (OpenAI -> LM Studio -> Local)
        # Prioritize OpenAI when configured since it's more reliable than local LM Studio
        if provider == "auto":
            # First try OpenAI if available (cloud = more reliable)
            if self.openai_service:
                try:
                    async with self._sem:
                        prov = "openai"
                        AI_CALLS.labels(provider=prov).inc()
                        start = time.perf_counter()
                        res = await asyncio.wait_for(self.openai_service.analyze_transaction(description, amount, model=model), timeout=timeout_s)
                        AI_LATENCY.labels(provider=prov).observe(time.perf_counter() - start)
                        return res
                except Exception as e:
                    AI_ERRORS.labels(provider="openai").inc()
                    logger.warning(f"OpenAI in auto failed: {e}")
            # Fall back to LM Studio if OpenAI unavailable
            if self.lmstudio_service:
                try:
                    async with self._sem:
                        prov = "lmstudio"
                        AI_CALLS.labels(provider=prov).inc()
                        start = time.perf_counter()
                        res = await asyncio.wait_for(self.lmstudio_service.analyze_transaction(description, amount, model=model), timeout=timeout_s)
                        AI_LATENCY.labels(provider=prov).observe(time.perf_counter() - start)
                    if res.confidence_score >= threshold:
                        return res
                except Exception as e:
                    AI_ERRORS.labels(provider="lmstudio").inc()
                    logger.warning(f"LM Studio in auto failed: {e}")

        # Local heuristics (fallback or explicit 'local')
        merchant_info = self.local_service.normalize_merchant(description)
        category_suggestions = self.local_service.suggest_categories(description, amount)
        anomaly_flags = self.local_service.detect_anomalies(description, amount)

        confidence_score = (
            merchant_info.confidence * 0.4
            + (max([s.confidence for s in category_suggestions], default=0.0) * 0.4)
            + (0.8 if len(anomaly_flags) == 0 else 0.6) * 0.2
        )

        return TransactionInsights(
            merchant_info=merchant_info,
            category_suggestions=category_suggestions,
            anomaly_flags=anomaly_flags,
            confidence_score=confidence_score,
            processing_method="local",
            provider_name="local",
        )

    async def analyze_with_prompt(
        self,
        prompt: str,
        *,
        max_tokens: int = 500,
        task_type: str = "custom"
    ) -> str:
        """
        Analyze using a custom prompt. Delegates to configured provider.

        Used for specialized analysis like transfer detection.
        """
        provider = self.provider
        timeout_s = self.config.timeout

        # Try OpenAI first if in auto mode (more reliable)
        if provider in ("openai", "auto") and self.openai_service:
            try:
                async with self._sem:
                    return await asyncio.wait_for(
                        self.openai_service.analyze_with_prompt(
                            prompt, max_tokens=max_tokens, task_type=task_type
                        ),
                        timeout=timeout_s
                    )
            except Exception as e:
                if provider == "openai":
                    raise
                logger.warning(f"OpenAI custom prompt failed: {e}")

        # Fall back to LM Studio
        if provider in ("lmstudio", "auto") and self.lmstudio_service:
            try:
                async with self._sem:
                    return await asyncio.wait_for(
                        self.lmstudio_service.analyze_with_prompt(
                            prompt, max_tokens=max_tokens, task_type=task_type
                        ),
                        timeout=timeout_s
                    )
            except Exception as e:
                if provider == "lmstudio":
                    raise
                logger.warning(f"LM Studio custom prompt failed: {e}")

        raise ValueError("No AI provider available for custom prompt analysis")

    async def batch_analyze_transactions(self, transactions: List[Tuple[str, float]], batch_size: int = 5) -> List[TransactionInsights]:
        """Analyze multiple transactions using efficient batching (single LLM call for multiple transactions)"""
        results = []

        # Process in batches
        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i + batch_size]
            try:
                # Use true batch processing for LM Studio/OpenAI
                if self.lmstudio_service:
                    batch_results = await self._batch_analyze_with_service(self.lmstudio_service, batch)
                    results.extend(batch_results)
                elif self.openai_service:
                    batch_results = await self._batch_analyze_with_service(self.openai_service, batch)
                    results.extend(batch_results)
                else:
                    # Fallback to single-transaction processing
                    for description, amount in batch:
                        try:
                            result = await self.analyze_transaction(description, amount)
                            results.append(result)
                        except Exception as e:
                            logger.error(f"Failed to analyze transaction '{description}': {e}")
                            results.append(TransactionInsights(
                                merchant_info=None,
                                category_suggestions=[],
                                anomaly_flags=['analysis_failed'],
                                confidence_score=0.0,
                                processing_method='fallback'
                            ))
            except Exception as e:
                logger.error(f"Batch analysis failed: {e}")
                # Add fallback results for the failed batch
                for _ in batch:
                    results.append(TransactionInsights(
                        merchant_info=None,
                        category_suggestions=[],
                        anomaly_flags=['batch_failed'],
                        confidence_score=0.0,
                        processing_method='fallback'
                    ))

        return results

    async def _batch_analyze_with_service(self, service: 'OpenAIService', transactions: List[Tuple[str, float]]) -> List[TransactionInsights]:
        """Analyze multiple transactions in a single LLM call for efficiency"""
        # Fetch categories from database
        try:
            from .db import get_conn
            conn = get_conn()
            rows = conn.execute("SELECT name FROM category ORDER BY name").fetchall()
            cat_list = ", ".join([r[0] for r in rows]) if rows else "Food & Dining, Shopping, Bills & Utilities, Transportation, Entertainment, Income, Transfers, Zelle, Grocery, Gas & Automotive"
        except:
            cat_list = "Food & Dining, Shopping, Bills & Utilities, Transportation, Entertainment, Income, Transfers, Zelle, Grocery, Gas & Automotive"

        # Build batch prompt
        tx_lines = []
        for idx, (description, amount) in enumerate(transactions, 1):
            tx_lines.append(f'{idx}. "{description}" - ${amount:.2f}')

        tx_text = "\n".join(tx_lines)

        prompt = f"""Categorize these bank transactions.

AVAILABLE CATEGORIES: {cat_list}

MERCHANT HINTS:
- Gas & Auto (Sheetz, Shell, Exxon, BP, car wash, auto spa) → Gas & Automotive
- Grocery (Harris Teeter, Sams Club, Kroger, Aldi, Mecca Market) → Grocery
- Restaurants (Starbucks, McDonald's, Chipotle, Bojangles, Sonic) → Food & Dining
- Entertainment (Netflix, Spotify, YouTube, Hulu, F1.com, F1 TV, ESPN+, Nebula, Steam, PlayStation) → Entertainment
- Tech (OpenAI, Microsoft, Google Ads, Canva, Replit, Midjourney, Shopify, GoDaddy) → Technology
- Shopping (Amazon, Target, tobacco, Maxx Tobacco, smoke shop, Dollar General) → Shopping
- Utilities (Duke Energy, Google Fiber, Spectrum) → Bills & Utilities
- P2P (Cash App, Venmo, "pmnt sent") → Transfers (NOT Financial Services)
- "zelle from/to" → Zelle
- "transfer from sav/chk/brk" → Internal Transfer
- Credits with DES: pattern, cashback, rebate, payroll → Income

TRANSACTIONS:
{tx_text}

Respond with ONLY a JSON array. One object per transaction in order:
[
  {{"id": 1, "merchant": "name", "category": "from list", "confidence": 0.8}},
  {{"id": 2, "merchant": "name", "category": "from list", "confidence": 0.8}}
]"""

        if service._debug:
            logger.info(f"[AI DEBUG] Batch prompt ({len(transactions)} txs):\n{prompt}")

        try:
            import time
            _t0 = time.perf_counter()
            resp = await service.client.chat.completions.create(
                model=service.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=float(os.getenv("KASHAT_AI_TEMPERATURE", "0.1")),
                max_tokens=800,  # More tokens for batch response
            )
            latency_ms = int((time.perf_counter() - _t0) * 1000)

            content = resp.choices[0].message.content if resp and resp.choices else None

            if service._debug:
                logger.info(f"[AI DEBUG] Batch response ({latency_ms}ms):\n{content}")

            results: List[TransactionInsights] = []

            if content:
                # Parse JSON array response
                json_str = content.strip()
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()

                if "[" in json_str:
                    start = json_str.find("[")
                    end = json_str.rfind("]") + 1
                    json_str = json_str[start:end]

                parsed = json.loads(json_str)

                # Convert each result to TransactionInsights
                for idx, item in enumerate(parsed):
                    cat_name = item.get("category", "Uncategorized")
                    confidence = float(item.get("confidence", 0.7))
                    merchant = item.get("merchant", transactions[idx][0][:30] if idx < len(transactions) else "Unknown")

                    results.append(TransactionInsights(
                        merchant_info=MerchantInfo(
                            normalized_name=merchant,
                            confidence=confidence,
                            original_description=transactions[idx][0] if idx < len(transactions) else "",
                        ),
                        category_suggestions=[
                            CategorySuggestion(
                                category_id=None,  # Will be resolved via category matching
                                category_name=cat_name,
                                confidence=confidence,
                                reasoning=f"Batch analysis: {merchant}",
                            )
                        ],
                        anomaly_flags=[],
                        confidence_score=confidence,
                        processing_method="batch",
                        provider_name=service.base_url or "openai",
                        model_name=service.default_model,
                        latency_ms=latency_ms // len(transactions),  # Per-transaction latency
                    ))

            # Ensure we have results for all transactions
            while len(results) < len(transactions):
                results.append(TransactionInsights(
                    merchant_info=None,
                    category_suggestions=[],
                    anomaly_flags=['missing_from_batch'],
                    confidence_score=0.0,
                    processing_method='fallback'
                ))

            return results[:len(transactions)]

        except Exception as e:
            logger.error(f"Batch LLM call failed: {e}")
            raise


# Global AI service instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create the global AI service instance."""
    global _ai_service

    if _ai_service is None:
        # Load configuration from env and settings file
        config = AIConfig.from_env()
        _ai_service = AIService(config=config)
        logger.info(f"AI service initialized: provider={config.provider}, "
                   f"timeout={config.timeout}s, max_retries={config.max_retries}")

    return _ai_service


def get_ai_config() -> AIConfig:
    """Get the current AI configuration."""
    return get_ai_service().config


async def ping_ai() -> Dict[str, Any]:
    """Ping the configured AI provider(s) to verify connectivity."""
    svc = get_ai_service()
    config = svc.config
    provider = svc.provider

    # Base result with configuration info
    results: Dict[str, Any] = {
        "provider": provider,
        "config": {
            "timeout": config.timeout,
            "max_retries": config.max_retries,
            "retry_jitter": config.retry_jitter,
            "max_concurrency": config.max_concurrency,
        }
    }

    try:
        if provider == "local":
            results.update({
                "ok": True,
                "details": "Local heuristics active (no AI provider configured)",
                "suggestion": "Configure OpenAI API key or LM Studio for AI-powered categorization"
            })
            return results

        if provider == "openai":
            if svc.openai_service is None:
                return {
                    **results,
                    "ok": False,
                    "error": "OpenAI client not configured",
                    "error_type": "configuration",
                    "suggestion": "Set OPENAI_API_KEY environment variable or configure in settings"
                }
            pong = await svc.openai_service.ping()
            pong.update({"client": "openai"})
            return {**results, **pong}

        if provider == "lmstudio":
            if svc.lmstudio_service is None:
                return {
                    **results,
                    "ok": False,
                    "error": "LM Studio client not configured",
                    "error_type": "configuration",
                    "suggestion": f"Ensure LM Studio is running at {config.lmstudio_base_url}"
                }
            pong = await svc.lmstudio_service.ping()
            pong.update({"client": "lmstudio"})
            return {**results, **pong}

        if provider == "auto":
            checks: List[Dict[str, Any]] = []
            # Run pings in parallel for faster status checks
            tasks = []
            if svc.openai_service is not None:
                tasks.append(("openai", svc.openai_service.ping()))
            if svc.lmstudio_service is not None:
                tasks.append(("lmstudio", svc.lmstudio_service.ping()))

            if tasks:
                results_list = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
                for (client_name, _), result in zip(tasks, results_list):
                    if isinstance(result, Exception):
                        checks.append({"ok": False, "error": str(result), "client": client_name})
                    else:
                        result.update({"client": client_name})
                        checks.append(result)

            any_ok = any(c.get("ok") for c in checks)
            return {
                **results,
                "checks": checks,
                "ok": any_ok,
                "suggestion": None if any_ok else "No AI providers available. Configure OpenAI API key or start LM Studio."
            }

    except Exception as e:
        return {
            **results,
            "ok": False,
            "error": str(e),
            "error_type": "unknown"
        }

    return results


def reset_ai_service():
    """Reset the global AI service (useful for testing)"""
    global _ai_service
    _ai_service = None
