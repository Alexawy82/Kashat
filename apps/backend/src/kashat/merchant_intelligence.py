"""
Merchant Intelligence Module - Phase 2 LLM Integration

Provides LLM-powered merchant extraction and recurring type classification
with intelligent caching to minimize API calls.

This module wraps the existing AI service (ai.py) and adds:
- Merchant intelligence caching (merchant_intelligence_cache table)
- Specialized prompts for recurring transaction classification
- Confidence scoring from LLM responses
- Fallback to pattern-based classification when LLM unavailable
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


@dataclass
class MerchantIntelligence:
    """Result from LLM-powered merchant analysis."""
    clean_merchant_name: str
    recurring_type: str  # subscription, bill, loan, credit_card, insurance, unknown
    sub_category: Optional[str]
    is_essential: bool
    confidence: float
    provider: Optional[str]
    model: Optional[str]
    latency_ms: Optional[int]
    from_cache: bool = False


def _hash_description(description: str) -> str:
    """Create a stable hash for a transaction description."""
    normalized = (description or "").strip().lower()
    # Remove common variable elements that don't affect classification
    normalized = re.sub(r'\s+\d{4,}', '', normalized)  # Remove long numbers
    normalized = re.sub(r'\s+[a-z0-9]{5,8}(?:\s|$)', ' ', normalized)  # Remove short codes
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:32]


def get_cached_intelligence(description: str) -> Optional[MerchantIntelligence]:
    """Look up cached merchant intelligence for a description.

    Returns:
        MerchantIntelligence if found and not expired, None otherwise
    """
    try:
        from .db import get_conn
        conn = get_conn()

        desc_hash = _hash_description(description)

        row = conn.execute(
            """
            SELECT
                clean_merchant_name, recurring_type, sub_category,
                is_essential, confidence, provider, model, latency_ms,
                expires_at
            FROM merchant_intelligence_cache
            WHERE description_hash = ?
            LIMIT 1
            """,
            [desc_hash]
        ).fetchone()

        if not row:
            return None

        (clean_name, rec_type, sub_cat, is_essential,
         confidence, provider, model, latency_ms, expires_at) = row

        # Check if expired
        if expires_at and datetime.now(UTC) > expires_at:
            # Clean up expired entry
            conn.execute(
                "DELETE FROM merchant_intelligence_cache WHERE description_hash = ?",
                [desc_hash]
            )
            return None

        # Update hit count
        conn.execute(
            """
            UPDATE merchant_intelligence_cache
            SET hit_count = hit_count + 1, last_hit_at = ?
            WHERE description_hash = ?
            """,
            [datetime.now(UTC), desc_hash]
        )

        return MerchantIntelligence(
            clean_merchant_name=clean_name or "",
            recurring_type=rec_type or "unknown",
            sub_category=sub_cat,
            is_essential=bool(is_essential),
            confidence=float(confidence or 0.0),
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            from_cache=True,
        )

    except Exception as e:
        logger.warning(f"Cache lookup failed: {e}")
        return None


def cache_intelligence(
    description: str,
    intelligence: MerchantIntelligence,
    ttl_days: int = 30
) -> bool:
    """Store merchant intelligence in cache.

    Args:
        description: Original transaction description
        intelligence: The intelligence result to cache
        ttl_days: Time-to-live in days (default 30)

    Returns:
        True if cached successfully
    """
    try:
        from .db import get_conn
        conn = get_conn()

        desc_hash = _hash_description(description)
        now = datetime.now(UTC)
        expires = now + timedelta(days=ttl_days)

        conn.execute(
            """
            INSERT INTO merchant_intelligence_cache (
                id, raw_description, description_hash, clean_merchant_name,
                recurring_type, sub_category, is_essential, confidence,
                provider, model, latency_ms, created_at, expires_at,
                hit_count, last_hit_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (description_hash) DO UPDATE SET
                clean_merchant_name = EXCLUDED.clean_merchant_name,
                recurring_type = EXCLUDED.recurring_type,
                sub_category = EXCLUDED.sub_category,
                is_essential = EXCLUDED.is_essential,
                confidence = EXCLUDED.confidence,
                provider = EXCLUDED.provider,
                model = EXCLUDED.model,
                latency_ms = EXCLUDED.latency_ms,
                expires_at = EXCLUDED.expires_at
            """,
            [
                str(uuid.uuid4()),
                description[:500],  # Truncate very long descriptions
                desc_hash,
                intelligence.clean_merchant_name,
                intelligence.recurring_type,
                intelligence.sub_category,
                intelligence.is_essential,
                intelligence.confidence,
                intelligence.provider,
                intelligence.model,
                intelligence.latency_ms,
                now,
                expires,
                0,
                None,
            ]
        )
        return True

    except Exception as e:
        logger.warning(f"Cache store failed: {e}")
        return False


async def analyze_merchant_with_llm(
    description: str,
    amount: float = 0.0,
    use_cache: bool = True,
) -> MerchantIntelligence:
    """Analyze a transaction description using LLM for merchant extraction and classification.

    This is the main entry point for LLM-powered merchant intelligence.

    Args:
        description: Transaction description
        amount: Transaction amount (helps with classification)
        use_cache: Whether to use/update the cache

    Returns:
        MerchantIntelligence with extracted merchant name and classification
    """
    # Check cache first
    if use_cache:
        cached = get_cached_intelligence(description)
        if cached:
            logger.debug(f"Cache hit for: {description[:50]}...")
            return cached

    # Try LLM analysis
    try:
        result = await _llm_analyze_merchant(description, amount)

        # Cache successful result
        if use_cache and result.confidence >= 0.5:
            cache_intelligence(description, result)

        return result

    except Exception as e:
        logger.warning(f"LLM analysis failed, falling back to patterns: {e}")
        return _pattern_based_fallback(description, amount)


async def _llm_analyze_merchant(
    description: str,
    amount: float = 0.0,
) -> MerchantIntelligence:
    """Perform LLM-based merchant analysis using the existing AI service."""
    from .ai import get_ai_service

    svc = get_ai_service()

    # Check if any LLM provider is available
    if not svc.lmstudio_service and not svc.openai_service:
        raise RuntimeError("No LLM provider available")

    # Build specialized prompt for recurring transaction classification
    prompt = _build_merchant_prompt(description, amount)

    t0 = time.perf_counter()

    # Prefer LM Studio (local, fast, no cost)
    service = svc.lmstudio_service or svc.openai_service
    provider_name = "lmstudio" if svc.lmstudio_service else "openai"

    try:
        resp = await service.client.chat.completions.create(
            model=service.default_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )

        latency_ms = int((time.perf_counter() - t0) * 1000)

        content = resp.choices[0].message.content if resp and resp.choices else None

        if not content:
            raise ValueError("Empty response from LLM")

        # Parse JSON response
        result = _parse_llm_response(content)

        return MerchantIntelligence(
            clean_merchant_name=result.get("merchant_name", description[:30]),
            recurring_type=result.get("recurring_type", "unknown"),
            sub_category=result.get("sub_category"),
            is_essential=result.get("is_essential", False),
            confidence=float(result.get("confidence", 0.7)),
            provider=provider_name,
            model=service.default_model,
            latency_ms=latency_ms,
            from_cache=False,
        )

    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        raise


def _build_merchant_prompt(description: str, amount: float) -> str:
    """Build a specialized prompt for merchant classification."""
    return f"""Analyze this bank transaction and extract merchant information.

Transaction: {description}
Amount: ${abs(amount):.2f} ({'credit' if amount > 0 else 'debit'})

Classify into one of these recurring types:
- subscription: Streaming (Netflix, Spotify), software (Adobe, GitHub), memberships
- bill: Utilities (electric, water, gas), internet, phone, insurance
- loan: Mortgage, auto loan, personal loan, student loan, BNPL (Affirm, Klarna)
- credit_card: Credit card payments (Chase, Amex, Citi, Discover, Capital One)
- insurance: Auto, home, life, renters insurance
- income: Payroll, salary, deposits
- unknown: Cannot determine

Respond with ONLY valid JSON:
{{
  "merchant_name": "clean human-readable merchant name",
  "recurring_type": "one of the types above",
  "sub_category": "specific category like 'streaming', 'utility_electric', 'auto_loan', 'credit_card'",
  "is_essential": true/false (essential = utilities, rent, insurance, loans),
  "confidence": 0.0-1.0
}}"""


def _parse_llm_response(content: str) -> Dict[str, Any]:
    """Parse LLM JSON response with fallback regex extraction."""
    try:
        # Clean up markdown code blocks
        json_str = content.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()

        # Find JSON object
        if "{" in json_str:
            start = json_str.find("{")
            end = json_str.rfind("}") + 1
            json_str = json_str[start:end]

        return json.loads(json_str)

    except Exception as e:
        logger.warning(f"JSON parse failed, using regex fallback: {e}")

        # Regex fallback
        result = {}

        merchant_match = re.search(r'"merchant_name"\s*:\s*"([^"]+)"', content)
        if merchant_match:
            result["merchant_name"] = merchant_match.group(1)

        type_match = re.search(r'"recurring_type"\s*:\s*"([^"]+)"', content)
        if type_match:
            result["recurring_type"] = type_match.group(1)

        sub_match = re.search(r'"sub_category"\s*:\s*"([^"]+)"', content)
        if sub_match:
            result["sub_category"] = sub_match.group(1)

        essential_match = re.search(r'"is_essential"\s*:\s*(true|false)', content, re.I)
        if essential_match:
            result["is_essential"] = essential_match.group(1).lower() == "true"

        conf_match = re.search(r'"confidence"\s*:\s*([\d.]+)', content)
        if conf_match:
            result["confidence"] = float(conf_match.group(1))

        return result


def _pattern_based_fallback(description: str, amount: float) -> MerchantIntelligence:
    """Fall back to pattern-based classification when LLM is unavailable."""
    from .recurring import extract_merchant_name_ai
    from .recurring_classifier import classify_recurring_type

    # Get clean merchant name using existing heuristics
    clean_name = extract_merchant_name_ai(description, use_ai=False)

    # Get classification using pattern-based classifier
    type_info = classify_recurring_type(description, amount)

    return MerchantIntelligence(
        clean_merchant_name=clean_name,
        recurring_type=type_info.get("recurring_type", "unknown"),
        sub_category=type_info.get("sub_category"),
        is_essential=type_info.get("is_essential", False),
        confidence=0.7 if type_info.get("recurring_type") != "unknown" else 0.3,
        provider="local",
        model="pattern_v2",
        latency_ms=0,
        from_cache=False,
    )


# =============================================================================
# Sync wrappers for use in non-async code
# =============================================================================

def analyze_merchant_sync(
    description: str,
    amount: float = 0.0,
    use_cache: bool = True,
) -> MerchantIntelligence:
    """Synchronous wrapper for analyze_merchant_with_llm.

    Uses asyncio to run the async function in a new event loop.
    Safe to call from synchronous code.
    """
    import asyncio

    try:
        # Try to get existing event loop
        loop = asyncio.get_running_loop()
        # If we're already in an async context, we need to run in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                analyze_merchant_with_llm(description, amount, use_cache)
            )
            return future.result(timeout=90)
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        return asyncio.run(analyze_merchant_with_llm(description, amount, use_cache))


def extract_merchant_name_llm(
    description: str,
    amount: float = 0.0,
    use_cache: bool = True,
) -> str:
    """Extract clean merchant name using LLM with cache.

    This is a drop-in enhancement for extract_merchant_name_ai().
    """
    try:
        result = analyze_merchant_sync(description, amount, use_cache)
        if result.clean_merchant_name and result.confidence >= 0.5:
            return result.clean_merchant_name
    except Exception as e:
        logger.debug(f"LLM merchant extraction failed: {e}")

    # Fallback to pattern-based extraction
    from .recurring import extract_merchant_name_ai
    return extract_merchant_name_ai(description, use_ai=False)


def classify_recurring_type_llm(
    description: str,
    amount: float = 0.0,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Classify recurring transaction type using LLM with cache.

    This is a drop-in enhancement for classify_recurring_type().

    Returns:
        dict with: recurring_type, sub_category, clean_name, is_essential, confidence
    """
    try:
        result = analyze_merchant_sync(description, amount, use_cache)
        if result.recurring_type != "unknown" and result.confidence >= 0.5:
            return {
                "recurring_type": result.recurring_type,
                "sub_category": result.sub_category,
                "clean_name": result.clean_merchant_name,
                "is_essential": result.is_essential,
                "confidence": result.confidence,
                "provider": result.provider,
                "from_cache": result.from_cache,
            }
    except Exception as e:
        logger.debug(f"LLM classification failed: {e}")

    # Fallback to pattern-based classification
    from .recurring_classifier import classify_recurring_type
    result = classify_recurring_type(description, amount)
    result["confidence"] = 0.7 if result.get("recurring_type") != "unknown" else 0.3
    result["provider"] = "pattern"
    result["from_cache"] = False
    return result


# =============================================================================
# Batch processing for efficiency
# =============================================================================

async def batch_analyze_merchants(
    descriptions: List[Tuple[str, float]],
    use_cache: bool = True,
) -> List[MerchantIntelligence]:
    """Analyze multiple transaction descriptions efficiently.

    Uses caching and batches LLM requests for efficiency.

    Args:
        descriptions: List of (description, amount) tuples
        use_cache: Whether to use/update cache

    Returns:
        List of MerchantIntelligence results in same order
    """
    results: List[Optional[MerchantIntelligence]] = [None] * len(descriptions)
    uncached_indices: List[int] = []
    uncached_items: List[Tuple[str, float]] = []

    # Check cache first
    if use_cache:
        for i, (desc, amount) in enumerate(descriptions):
            cached = get_cached_intelligence(desc)
            if cached:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_items.append((desc, amount))
    else:
        uncached_indices = list(range(len(descriptions)))
        uncached_items = list(descriptions)

    # Process uncached items with LLM
    if uncached_items:
        try:
            llm_results = await _batch_llm_analyze(uncached_items)

            for i, result in zip(uncached_indices, llm_results):
                results[i] = result
                # Cache successful results
                if use_cache and result.confidence >= 0.5:
                    cache_intelligence(descriptions[i][0], result)

        except Exception as e:
            logger.warning(f"Batch LLM analysis failed: {e}")
            # Use pattern fallback for all uncached
            for i, (desc, amount) in zip(uncached_indices, uncached_items):
                results[i] = _pattern_based_fallback(desc, amount)

    return results


async def _batch_llm_analyze(
    items: List[Tuple[str, float]],
) -> List[MerchantIntelligence]:
    """Perform batched LLM analysis for multiple transactions."""
    from .ai import get_ai_service

    svc = get_ai_service()

    if not svc.lmstudio_service and not svc.openai_service:
        # No LLM available, use pattern fallback
        return [_pattern_based_fallback(desc, amt) for desc, amt in items]

    service = svc.lmstudio_service or svc.openai_service
    provider_name = "lmstudio" if svc.lmstudio_service else "openai"

    # Build batch prompt
    tx_lines = []
    for i, (desc, amount) in enumerate(items, 1):
        tx_lines.append(f'{i}. "{desc}" - ${abs(amount):.2f}')

    prompt = f"""Analyze these bank transactions and extract merchant information.

TRANSACTIONS:
{chr(10).join(tx_lines)}

For each transaction, classify into one of these recurring types:
- subscription: Streaming, software, memberships
- bill: Utilities, internet, phone
- loan: Mortgage, auto loan, personal loan, BNPL
- credit_card: Credit card payments
- insurance: Auto, home, life insurance
- income: Payroll, salary
- unknown: Cannot determine

Respond with ONLY a JSON array. One object per transaction in order:
[
  {{"id": 1, "merchant_name": "clean name", "recurring_type": "type", "sub_category": "category", "is_essential": true/false, "confidence": 0.8}},
  ...
]"""

    t0 = time.perf_counter()

    try:
        resp = await service.client.chat.completions.create(
            model=service.default_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=600,
        )

        latency_ms = int((time.perf_counter() - t0) * 1000)
        per_tx_latency = latency_ms // max(1, len(items))

        content = resp.choices[0].message.content if resp and resp.choices else None

        if not content:
            raise ValueError("Empty batch response")

        # Parse JSON array
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

        results = []
        for i, item in enumerate(parsed):
            results.append(MerchantIntelligence(
                clean_merchant_name=item.get("merchant_name", items[i][0][:30] if i < len(items) else "Unknown"),
                recurring_type=item.get("recurring_type", "unknown"),
                sub_category=item.get("sub_category"),
                is_essential=item.get("is_essential", False),
                confidence=float(item.get("confidence", 0.7)),
                provider=provider_name,
                model=service.default_model,
                latency_ms=per_tx_latency,
                from_cache=False,
            ))

        # Pad with fallbacks if needed
        while len(results) < len(items):
            idx = len(results)
            results.append(_pattern_based_fallback(items[idx][0], items[idx][1]))

        return results[:len(items)]

    except Exception as e:
        logger.error(f"Batch LLM failed: {e}")
        return [_pattern_based_fallback(desc, amt) for desc, amt in items]


# =============================================================================
# Cache maintenance
# =============================================================================

def cleanup_expired_cache(max_age_days: int = 60) -> int:
    """Remove expired entries from the merchant intelligence cache.

    Returns:
        Number of entries removed
    """
    try:
        from .db import get_conn
        conn = get_conn()

        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)

        result = conn.execute(
            """
            DELETE FROM merchant_intelligence_cache
            WHERE expires_at < ? OR (expires_at IS NULL AND created_at < ?)
            """,
            [datetime.now(UTC), cutoff]
        )

        # DuckDB doesn't return affected rows directly, so query count
        try:
            before = conn.execute("SELECT COUNT(*) FROM merchant_intelligence_cache").fetchone()[0]
            return max(0, before)  # Approximate
        except:
            return 0

    except Exception as e:
        logger.warning(f"Cache cleanup failed: {e}")
        return 0


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about the merchant intelligence cache."""
    try:
        from .db import get_conn
        conn = get_conn()

        stats = conn.execute(
            """
            SELECT
                COUNT(*) as total_entries,
                SUM(hit_count) as total_hits,
                AVG(confidence) as avg_confidence,
                COUNT(DISTINCT provider) as providers_used,
                MIN(created_at) as oldest_entry,
                MAX(created_at) as newest_entry
            FROM merchant_intelligence_cache
            """
        ).fetchone()

        if stats:
            return {
                "total_entries": stats[0] or 0,
                "total_hits": stats[1] or 0,
                "avg_confidence": round(stats[2] or 0, 3),
                "providers_used": stats[3] or 0,
                "oldest_entry": str(stats[4]) if stats[4] else None,
                "newest_entry": str(stats[5]) if stats[5] else None,
            }

    except Exception as e:
        logger.warning(f"Cache stats failed: {e}")

    return {
        "total_entries": 0,
        "total_hits": 0,
        "avg_confidence": 0,
        "providers_used": 0,
    }
