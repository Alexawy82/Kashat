"""
AI-Powered Ingestion Workflow

Provides an AI review layer for transaction ingestion/import:
- Reviews parsed transactions for accuracy
- Learns from user corrections to imports
- Improves field mapping and parsing over time
- Learns institution-specific patterns
"""

from __future__ import annotations

import json
import uuid
import logging
import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, UTC
from collections import defaultdict

from .db import get_conn

logger = logging.getLogger(__name__)


# ========================================
# DATA CLASSES
# ========================================

@dataclass
class IngestFeedback:
    """User feedback on imported transaction"""
    transaction_id: str
    import_run_id: str
    field_corrected: str  # amount, date, description, category, etc.
    original_value: str
    corrected_value: str
    institution_pattern: Optional[str]  # e.g., "Bank of America", "Chase"
    description_pattern: Optional[str]  # Pattern from description


@dataclass
class IngestPattern:
    """Learned pattern for ingestion"""
    pattern_type: str  # field_mapping, date_format, amount_format, etc.
    institution: Optional[str]
    pattern_key: str  # The pattern to match
    correction_value: str  # The corrected value/format
    confidence: float
    usage_count: int
    last_used: datetime


@dataclass
class AIEnhancedTransaction:
    """Transaction enhanced by AI review"""
    transaction_id: str
    original_description: str
    ai_clean_description: str
    original_amount: float
    ai_adjusted_amount: Optional[float]
    ai_merchant_name: str
    ai_category_suggestion: Optional[str]
    confidence: float
    corrections_applied: List[str]
    reasoning: str


@dataclass
class ParseQualityReport:
    """Quality report for an import run"""
    import_run_id: str
    total_transactions: int
    auto_corrected: int
    needs_review: int
    high_confidence: int
    field_issues: Dict[str, int]
    recommendations: List[str]


# ========================================
# DATABASE SETUP
# ========================================

def _ensure_ingest_ai_tables():
    """Ensure AI workflow tables exist"""
    conn = get_conn()

    # Ingest feedback table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingest_ai_feedback (
                id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                import_run_id TEXT,
                field_corrected TEXT NOT NULL,
                original_value TEXT,
                corrected_value TEXT,
                institution_pattern TEXT,
                description_pattern TEXT,
                created_at TIMESTAMP NOT NULL
            )
        """)
    except Exception as e:
        logger.debug(f"ingest_ai_feedback table may exist: {e}")

    # Ingest pattern memory table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingest_pattern_memory (
                id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                institution TEXT,
                pattern_key TEXT NOT NULL,
                correction_value TEXT NOT NULL,
                confidence DOUBLE DEFAULT 0.7,
                usage_count INTEGER DEFAULT 1,
                last_used TIMESTAMP,
                created_at TIMESTAMP NOT NULL,
                UNIQUE(pattern_type, institution, pattern_key)
            )
        """)
    except Exception as e:
        logger.debug(f"ingest_pattern_memory table may exist: {e}")

    # Institution patterns table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS institution_parse_patterns (
                id TEXT PRIMARY KEY,
                institution_name TEXT NOT NULL,
                date_format TEXT,
                amount_format TEXT,
                description_cleanup_regex TEXT,
                common_prefixes TEXT,
                common_suffixes TEXT,
                confidence DOUBLE DEFAULT 0.5,
                sample_count INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                UNIQUE(institution_name)
            )
        """)
    except Exception as e:
        logger.debug(f"institution_parse_patterns table may exist: {e}")


# ========================================
# INGEST AI WORKFLOW ENGINE
# ========================================

class IngestAIWorkflowEngine:
    """AI workflow engine for transaction ingestion"""

    def __init__(self):
        _ensure_ingest_ai_tables()
        self._pattern_cache: Dict[str, IngestPattern] = {}
        self._institution_cache: Dict[str, Dict[str, Any]] = {}
        self._load_patterns()

    def _load_patterns(self):
        """Load learned patterns into cache"""
        conn = get_conn()

        try:
            # Load ingest patterns
            rows = conn.execute("""
                SELECT pattern_type, institution, pattern_key, correction_value,
                       confidence, usage_count, last_used
                FROM ingest_pattern_memory
                WHERE confidence >= 0.5
            """).fetchall()

            for row in rows:
                key = f"{row[0]}:{row[1] or 'global'}:{row[2]}"
                self._pattern_cache[key] = IngestPattern(
                    pattern_type=row[0],
                    institution=row[1],
                    pattern_key=row[2],
                    correction_value=row[3],
                    confidence=float(row[4] or 0.7),
                    usage_count=int(row[5] or 1),
                    last_used=row[6]
                )

            logger.info(f"Loaded {len(self._pattern_cache)} ingest patterns")

            # Load institution patterns
            inst_rows = conn.execute("""
                SELECT institution_name, date_format, amount_format,
                       description_cleanup_regex, common_prefixes, common_suffixes,
                       confidence, sample_count
                FROM institution_parse_patterns
            """).fetchall()

            for row in inst_rows:
                self._institution_cache[row[0].lower()] = {
                    "institution": row[0],
                    "date_format": row[1],
                    "amount_format": row[2],
                    "cleanup_regex": row[3],
                    "prefixes": row[4].split(",") if row[4] else [],
                    "suffixes": row[5].split(",") if row[5] else [],
                    "confidence": float(row[6] or 0.5),
                    "sample_count": int(row[7] or 0)
                }

            logger.info(f"Loaded {len(self._institution_cache)} institution patterns")

        except Exception as e:
            logger.warning(f"Could not load ingest patterns: {e}")

    # ========================================
    # AI REVIEW OF TRANSACTIONS
    # ========================================

    async def review_transactions_with_ai(
        self,
        transactions: List[Dict[str, Any]],
        institution: Optional[str] = None,
        use_llm: bool = False
    ) -> List[AIEnhancedTransaction]:
        """
        Review imported transactions with AI.

        Uses learned patterns to:
        - Clean up descriptions
        - Fix common parsing errors
        - Extract merchant names
        - Suggest categories
        """
        enhanced = []
        inst_patterns = self._get_institution_patterns(institution)

        for tx in transactions:
            tx_id = tx.get("id", str(uuid.uuid4()))
            description = tx.get("description", tx.get("description_norm", ""))
            amount = float(tx.get("amount", 0))

            corrections = []
            confidence = 0.7

            # Step 1: Clean description using learned patterns
            clean_desc, desc_corrections = self._clean_description(description, institution)
            corrections.extend(desc_corrections)

            # Step 2: Extract merchant name
            merchant_name = self._extract_merchant(clean_desc, institution)

            # Step 3: Check for amount corrections
            adjusted_amount = self._check_amount_patterns(amount, description, institution)

            # Step 4: Suggest category based on patterns
            category_suggestion = self._suggest_category(merchant_name, description, amount)

            # Step 5: Calculate confidence
            if corrections:
                confidence = min(0.95, 0.7 + len(corrections) * 0.05)

            # Optional LLM enhancement
            if use_llm and confidence < 0.6:
                llm_result = await self._enhance_with_llm(tx)
                if llm_result:
                    if llm_result.get("merchant"):
                        merchant_name = llm_result["merchant"]
                    if llm_result.get("category"):
                        category_suggestion = llm_result["category"]
                    confidence = max(confidence, float(llm_result.get("confidence", 0.7)))

            enhanced.append(AIEnhancedTransaction(
                transaction_id=tx_id,
                original_description=description,
                ai_clean_description=clean_desc,
                original_amount=amount,
                ai_adjusted_amount=adjusted_amount if adjusted_amount != amount else None,
                ai_merchant_name=merchant_name,
                ai_category_suggestion=category_suggestion,
                confidence=confidence,
                corrections_applied=corrections,
                reasoning=f"Applied {len(corrections)} learned corrections" if corrections else "No corrections needed"
            ))

        return enhanced

    def _get_institution_patterns(self, institution: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get learned patterns for an institution"""
        if not institution:
            return None
        return self._institution_cache.get(institution.lower())

    def _clean_description(
        self,
        description: str,
        institution: Optional[str]
    ) -> Tuple[str, List[str]]:
        """Clean description using learned patterns"""
        corrections = []
        clean = description

        # Apply institution-specific cleanup
        inst_patterns = self._get_institution_patterns(institution)
        if inst_patterns and inst_patterns.get("cleanup_regex"):
            try:
                original = clean
                clean = re.sub(inst_patterns["cleanup_regex"], "", clean)
                if clean != original:
                    corrections.append(f"institution_cleanup:{institution}")
            except Exception:
                pass

        # Apply learned description patterns
        for key, pattern in self._pattern_cache.items():
            if pattern.pattern_type == "description_cleanup":
                if pattern.pattern_key.lower() in clean.lower():
                    clean = clean.replace(pattern.pattern_key, pattern.correction_value)
                    corrections.append(f"pattern:{pattern.pattern_key}")

        # Standard cleanup
        # Remove common noise patterns
        noise_patterns = [
            r'\s*CHECKCARD\s*\d{4}\s*',
            r'\s*PURCHASE\s*\d{4}\s*',
            r'\s*\d{24,}\s*',  # Long transaction IDs
            r'\s*\d{2}/\d{2}\s*$',  # Date suffixes
            r'\s*#\d+\s*',  # Reference numbers
        ]

        for noise in noise_patterns:
            original = clean
            clean = re.sub(noise, ' ', clean, flags=re.IGNORECASE)
            if clean != original:
                corrections.append("noise_removal")

        # Clean whitespace
        clean = ' '.join(clean.split())

        return clean, corrections

    def _extract_merchant(
        self,
        description: str,
        institution: Optional[str]
    ) -> str:
        """Extract merchant name from description"""

        # Check learned merchant patterns
        desc_lower = description.lower()

        for key, pattern in self._pattern_cache.items():
            if pattern.pattern_type == "merchant_name":
                if pattern.pattern_key.lower() in desc_lower:
                    return pattern.correction_value

        # Use existing merchant extraction
        try:
            from .recurring import extract_merchant_name_ai
            return extract_merchant_name_ai(description)
        except ImportError:
            pass

        # Fallback: Take first meaningful words
        words = description.split()
        if len(words) >= 2:
            return ' '.join(words[:2]).title()
        return description.title()

    def _check_amount_patterns(
        self,
        amount: float,
        description: str,
        institution: Optional[str]
    ) -> float:
        """Check for amount correction patterns"""

        # Check for sign correction patterns
        for key, pattern in self._pattern_cache.items():
            if pattern.pattern_type == "amount_sign":
                if pattern.pattern_key.lower() in description.lower():
                    if pattern.correction_value == "negative" and amount > 0:
                        return -amount
                    elif pattern.correction_value == "positive" and amount < 0:
                        return -amount

        return amount

    def _suggest_category(
        self,
        merchant: str,
        description: str,
        amount: float
    ) -> Optional[str]:
        """Suggest category based on patterns"""

        # Check learned category patterns
        for key, pattern in self._pattern_cache.items():
            if pattern.pattern_type == "category":
                if pattern.pattern_key.lower() in merchant.lower():
                    return pattern.correction_value

        return None

    async def _enhance_with_llm(
        self,
        transaction: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to enhance transaction parsing"""
        try:
            from .ai import get_ai_service
            ai_service = get_ai_service()

            # LLM call would go here
            return None

        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
            return None

    # ========================================
    # LEARNING FROM FEEDBACK
    # ========================================

    async def learn_from_feedback(self, feedback: IngestFeedback):
        """Learn from user correction to imported transaction"""

        conn = get_conn()

        # Store feedback record
        try:
            conn.execute("""
                INSERT INTO ingest_ai_feedback
                (id, transaction_id, import_run_id, field_corrected, original_value, corrected_value, institution_pattern, description_pattern, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                str(uuid.uuid4()),
                feedback.transaction_id,
                feedback.import_run_id,
                feedback.field_corrected,
                feedback.original_value,
                feedback.corrected_value,
                feedback.institution_pattern,
                feedback.description_pattern,
                datetime.now(UTC)
            ])
        except Exception as e:
            logger.warning(f"Could not store ingest feedback: {e}")

        # Update pattern memory based on field corrected
        await self._update_pattern_memory(feedback)

    async def _update_pattern_memory(self, feedback: IngestFeedback):
        """Update pattern memory based on feedback"""

        conn = get_conn()

        # Determine pattern type and key
        pattern_type = self._map_field_to_pattern_type(feedback.field_corrected)
        pattern_key = feedback.original_value[:100] if feedback.original_value else ""
        correction_value = feedback.corrected_value[:200] if feedback.corrected_value else ""

        if not pattern_key or not correction_value:
            return

        institution = feedback.institution_pattern

        # Check if pattern exists (NULL-safe comparison for institution)
        if institution:
            existing = conn.execute("""
                SELECT id, confidence, usage_count
                FROM ingest_pattern_memory
                WHERE pattern_type = ? AND institution = ? AND pattern_key = ?
            """, [pattern_type, institution, pattern_key]).fetchone()
        else:
            existing = conn.execute("""
                SELECT id, confidence, usage_count
                FROM ingest_pattern_memory
                WHERE pattern_type = ? AND institution IS NULL AND pattern_key = ?
            """, [pattern_type, pattern_key]).fetchone()

        if existing:
            pattern_id = existing[0]
            conf = float(existing[1] or 0.7)
            usage = int(existing[2] or 1)

            new_conf = min(0.99, conf + 0.05)
            new_usage = usage + 1

            conn.execute("""
                UPDATE ingest_pattern_memory
                SET correction_value = ?, confidence = ?, usage_count = ?, last_used = ?
                WHERE id = ?
            """, [correction_value, new_conf, new_usage, datetime.now(UTC), pattern_id])

            # Update cache
            cache_key = f"{pattern_type}:{institution or 'global'}:{pattern_key}"
            self._pattern_cache[cache_key] = IngestPattern(
                pattern_type=pattern_type,
                institution=institution,
                pattern_key=pattern_key,
                correction_value=correction_value,
                confidence=new_conf,
                usage_count=new_usage,
                last_used=datetime.now(UTC)
            )
        else:
            # Create new pattern
            conn.execute("""
                INSERT INTO ingest_pattern_memory
                (id, pattern_type, institution, pattern_key, correction_value, confidence, usage_count, last_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                str(uuid.uuid4()),
                pattern_type,
                institution,
                pattern_key,
                correction_value,
                0.7,
                1,
                datetime.now(UTC),
                datetime.now(UTC)
            ])

            cache_key = f"{pattern_type}:{institution or 'global'}:{pattern_key}"
            self._pattern_cache[cache_key] = IngestPattern(
                pattern_type=pattern_type,
                institution=institution,
                pattern_key=pattern_key,
                correction_value=correction_value,
                confidence=0.7,
                usage_count=1,
                last_used=datetime.now(UTC)
            )

        logger.info(f"Learned ingest pattern: {pattern_type} '{pattern_key}' -> '{correction_value}'")

    def _map_field_to_pattern_type(self, field: str) -> str:
        """Map field name to pattern type"""
        mapping = {
            "description": "description_cleanup",
            "merchant": "merchant_name",
            "category": "category",
            "amount": "amount_sign",
            "date": "date_format",
            "account": "account_mapping",
        }
        return mapping.get(field.lower(), field.lower())

    # ========================================
    # INSTITUTION LEARNING
    # ========================================

    async def learn_institution_patterns(
        self,
        institution: str,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Learn parsing patterns specific to an institution"""

        conn = get_conn()

        # Analyze transactions to find patterns
        descriptions = [tx.get("description", "") for tx in transactions]
        amounts = [float(tx.get("amount", 0)) for tx in transactions]

        # Find common prefixes
        prefixes = self._find_common_prefixes(descriptions)

        # Find common suffixes
        suffixes = self._find_common_suffixes(descriptions)

        # Build cleanup regex
        cleanup_parts = []
        for prefix in prefixes[:3]:
            if len(prefix) >= 3:
                cleanup_parts.append(re.escape(prefix))
        for suffix in suffixes[:3]:
            if len(suffix) >= 3:
                cleanup_parts.append(re.escape(suffix) + "$")

        cleanup_regex = "|".join(cleanup_parts) if cleanup_parts else None

        # Store or update institution patterns
        existing = conn.execute(
            "SELECT id, sample_count FROM institution_parse_patterns WHERE LOWER(institution_name) = ?",
            [institution.lower()]
        ).fetchone()

        if existing:
            inst_id = existing[0]
            sample_count = int(existing[1] or 0) + len(transactions)

            conn.execute("""
                UPDATE institution_parse_patterns
                SET description_cleanup_regex = ?, common_prefixes = ?, common_suffixes = ?,
                    sample_count = ?, updated_at = ?
                WHERE id = ?
            """, [
                cleanup_regex,
                ",".join(prefixes[:5]),
                ",".join(suffixes[:5]),
                sample_count,
                datetime.now(UTC),
                inst_id
            ])
        else:
            conn.execute("""
                INSERT INTO institution_parse_patterns
                (id, institution_name, description_cleanup_regex, common_prefixes, common_suffixes,
                 confidence, sample_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                str(uuid.uuid4()),
                institution,
                cleanup_regex,
                ",".join(prefixes[:5]),
                ",".join(suffixes[:5]),
                0.7,
                len(transactions),
                datetime.now(UTC),
                datetime.now(UTC)
            ])

        # Update cache
        self._institution_cache[institution.lower()] = {
            "institution": institution,
            "cleanup_regex": cleanup_regex,
            "prefixes": prefixes[:5],
            "suffixes": suffixes[:5],
            "sample_count": len(transactions)
        }

        return {
            "institution": institution,
            "patterns_learned": {
                "prefixes": prefixes[:5],
                "suffixes": suffixes[:5],
                "cleanup_regex": cleanup_regex
            },
            "sample_count": len(transactions)
        }

    def _find_common_prefixes(self, strings: List[str], min_len: int = 5, min_freq: float = 0.2) -> List[str]:
        """Find common prefixes in a list of strings"""
        if not strings:
            return []

        prefix_counts = defaultdict(int)

        for s in strings:
            for length in range(min_len, min(30, len(s))):
                prefix = s[:length]
                prefix_counts[prefix] += 1

        threshold = len(strings) * min_freq
        common = [p for p, count in prefix_counts.items() if count >= threshold]

        # Sort by length (prefer longer prefixes)
        common.sort(key=len, reverse=True)

        # Remove prefixes that are substrings of longer ones
        result = []
        for p in common:
            if not any(p in existing and p != existing for existing in result):
                result.append(p)

        return result[:10]

    def _find_common_suffixes(self, strings: List[str], min_len: int = 5, min_freq: float = 0.2) -> List[str]:
        """Find common suffixes in a list of strings"""
        if not strings:
            return []

        suffix_counts = defaultdict(int)

        for s in strings:
            for length in range(min_len, min(30, len(s))):
                suffix = s[-length:]
                suffix_counts[suffix] += 1

        threshold = len(strings) * min_freq
        common = [s for s, count in suffix_counts.items() if count >= threshold]

        common.sort(key=len, reverse=True)

        result = []
        for s in common:
            if not any(s in existing and s != existing for existing in result):
                result.append(s)

        return result[:10]

    # ========================================
    # STATISTICS & ANALYSIS
    # ========================================

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about the ingest AI learning system"""

        conn = get_conn()

        try:
            # Pattern stats
            pattern_count = conn.execute("SELECT COUNT(*) FROM ingest_pattern_memory").fetchone()[0]
            high_conf = conn.execute(
                "SELECT COUNT(*) FROM ingest_pattern_memory WHERE confidence >= 0.8"
            ).fetchone()[0]

            # Feedback stats
            total_feedback = conn.execute("SELECT COUNT(*) FROM ingest_ai_feedback").fetchone()[0]

            # Feedback by field
            feedback_by_field = conn.execute("""
                SELECT field_corrected, COUNT(*) as cnt
                FROM ingest_ai_feedback
                GROUP BY field_corrected
                ORDER BY cnt DESC
            """).fetchall()

            # Institution stats
            institution_count = conn.execute("SELECT COUNT(*) FROM institution_parse_patterns").fetchone()[0]

            # Most corrected patterns
            top_corrections = conn.execute("""
                SELECT pattern_type, pattern_key, correction_value, usage_count
                FROM ingest_pattern_memory
                ORDER BY usage_count DESC
                LIMIT 10
            """).fetchall()

            return {
                "pattern_memory": {
                    "total_patterns": pattern_count,
                    "high_confidence": high_conf,
                    "cached_patterns": len(self._pattern_cache)
                },
                "feedback": {
                    "total": total_feedback,
                    "by_field": {row[0]: row[1] for row in feedback_by_field}
                },
                "institutions": {
                    "total": institution_count,
                    "cached": len(self._institution_cache)
                },
                "top_corrections": [
                    {
                        "type": row[0],
                        "original": row[1][:30] if row[1] else "",
                        "corrected": row[2][:30] if row[2] else "",
                        "usage": row[3]
                    }
                    for row in top_corrections
                ]
            }
        except Exception as e:
            logger.warning(f"Error getting ingest stats: {e}")
            return {"error": str(e)}

    def analyze_import_quality(self, import_run_id: str) -> ParseQualityReport:
        """Analyze quality of an import run"""

        conn = get_conn()

        try:
            # Get transactions from this import
            transactions = conn.execute("""
                SELECT t.id, t.description_norm, t.amount, t.posted_at,
                       t.ai_merchant_name, t.ai_confidence_score
                FROM [transaction] t
                JOIN import_file f ON f.id = t.source_raw_id
                WHERE f.run_id = ?
            """, [import_run_id]).fetchall()

            total = len(transactions)
            high_conf = 0
            needs_review = 0
            auto_corrected = 0
            field_issues = defaultdict(int)

            for tx in transactions:
                confidence = float(tx[5] or 0)

                if confidence >= 0.8:
                    high_conf += 1
                elif confidence < 0.5:
                    needs_review += 1
                    field_issues["low_confidence"] += 1

                # Check for common issues
                desc = tx[1] or ""
                if len(desc) < 5:
                    field_issues["short_description"] += 1
                if re.search(r'\d{20,}', desc):
                    field_issues["long_numbers"] += 1

            recommendations = []
            if needs_review / max(1, total) > 0.2:
                recommendations.append("Consider reviewing low-confidence transactions")
            if field_issues.get("short_description", 0) > 10:
                recommendations.append("Many transactions have very short descriptions")

            return ParseQualityReport(
                import_run_id=import_run_id,
                total_transactions=total,
                auto_corrected=auto_corrected,
                needs_review=needs_review,
                high_confidence=high_conf,
                field_issues=dict(field_issues),
                recommendations=recommendations
            )

        except Exception as e:
            logger.warning(f"Error analyzing import: {e}")
            return ParseQualityReport(
                import_run_id=import_run_id,
                total_transactions=0,
                auto_corrected=0,
                needs_review=0,
                high_confidence=0,
                field_issues={},
                recommendations=[f"Error: {str(e)}"]
            )


# ========================================
# GLOBAL INSTANCE & CONVENIENCE FUNCTIONS
# ========================================

_ingest_workflow_engine: Optional[IngestAIWorkflowEngine] = None


def get_ingest_ai_workflow() -> IngestAIWorkflowEngine:
    """Get the global ingest AI workflow engine"""
    global _ingest_workflow_engine
    if _ingest_workflow_engine is None:
        _ingest_workflow_engine = IngestAIWorkflowEngine()
    return _ingest_workflow_engine


async def review_imported_transactions(
    transactions: List[Dict[str, Any]],
    institution: Optional[str] = None,
    use_llm: bool = False
) -> List[Dict[str, Any]]:
    """Convenience function to review imported transactions"""
    engine = get_ingest_ai_workflow()
    results = await engine.review_transactions_with_ai(transactions, institution, use_llm)
    return [asdict(r) for r in results]


async def record_ingest_correction(
    transaction_id: str,
    field: str,
    original_value: str,
    corrected_value: str,
    import_run_id: str = None,
    institution: str = None
) -> Dict[str, str]:
    """Convenience function to record an import correction"""
    engine = get_ingest_ai_workflow()

    feedback = IngestFeedback(
        transaction_id=transaction_id,
        import_run_id=import_run_id,
        field_corrected=field,
        original_value=original_value,
        corrected_value=corrected_value,
        institution_pattern=institution,
        description_pattern=None
    )

    await engine.learn_from_feedback(feedback)
    return {"status": "learned", "transaction_id": transaction_id, "field": field}


def get_ingest_learning_stats() -> Dict[str, Any]:
    """Get ingest AI learning statistics"""
    engine = get_ingest_ai_workflow()
    return engine.get_learning_stats()
