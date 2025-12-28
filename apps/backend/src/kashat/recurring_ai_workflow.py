"""
AI-Powered Recurring Detection Workflow

Provides an AI review layer on top of pattern-based recurring detection:
- Reviews pattern classification results with LLM
- Learns from user confirmations/corrections
- Improves confidence scoring over time
- Tracks detection accuracy and feedback
"""

from __future__ import annotations

import json
import uuid
import logging
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
class RecurringClassificationResult:
    """Result from pattern-based recurring classification"""
    series_id: str
    merchant_name: str
    description: str
    amount: float
    recurring_type: str  # subscription, bill, loan, etc.
    sub_category: str
    is_essential: bool
    pattern_confidence: float
    cadence: str
    detection_method: str  # pattern, amount_match, merchant_match, etc.
    signals: List[str]  # Evidence that led to classification


@dataclass
class AIReviewResult:
    """Result from AI review of pattern classification"""
    series_id: str
    original_type: str
    ai_suggested_type: str
    original_confidence: float
    ai_confidence: float
    ai_reasoning: str
    corrections: Dict[str, Any]  # Field corrections suggested by AI
    should_override: bool
    review_quality: str  # high, medium, low


@dataclass
class RecurringFeedback:
    """User feedback on recurring classification"""
    series_id: str
    original_type: str
    corrected_type: Optional[str]
    original_is_essential: bool
    corrected_is_essential: Optional[bool]
    was_correct: bool
    feedback_source: str  # user_confirm, user_reject, user_edit, auto_learn
    merchant_pattern: str


@dataclass
class RecurringMerchantMemory:
    """Learned merchant pattern for recurring detection"""
    merchant_pattern: str
    recurring_type: str
    sub_category: str
    is_essential: bool
    confidence: float
    confirmation_count: int
    rejection_count: int
    last_confirmed: Optional[datetime]


# ========================================
# DATABASE SETUP
# ========================================

def _ensure_recurring_ai_tables():
    """Ensure AI workflow tables exist"""
    conn = get_conn()

    # Recurring AI feedback table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recurring_ai_feedback (
                id TEXT PRIMARY KEY,
                series_id TEXT NOT NULL,
                original_type TEXT,
                corrected_type TEXT,
                original_confidence DOUBLE,
                was_correct BOOLEAN NOT NULL,
                feedback_source TEXT NOT NULL,
                merchant_pattern TEXT,
                created_at TIMESTAMP NOT NULL
            )
        """)
    except Exception as e:
        logger.debug(f"recurring_ai_feedback table may exist: {e}")

    # Recurring merchant memory table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recurring_merchant_memory (
                id TEXT PRIMARY KEY,
                merchant_pattern TEXT NOT NULL UNIQUE,
                recurring_type TEXT,
                sub_category TEXT,
                is_essential BOOLEAN DEFAULT FALSE,
                confidence DOUBLE DEFAULT 0.5,
                confirmation_count INTEGER DEFAULT 0,
                rejection_count INTEGER DEFAULT 0,
                last_confirmed TIMESTAMP,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)
    except Exception as e:
        logger.debug(f"recurring_merchant_memory table may exist: {e}")

    # AI review log table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recurring_ai_review_log (
                id TEXT PRIMARY KEY,
                series_id TEXT NOT NULL,
                pattern_type TEXT,
                pattern_confidence DOUBLE,
                ai_type TEXT,
                ai_confidence DOUBLE,
                ai_reasoning TEXT,
                was_applied BOOLEAN DEFAULT FALSE,
                reviewed_at TIMESTAMP NOT NULL
            )
        """)
    except Exception as e:
        logger.debug(f"recurring_ai_review_log table may exist: {e}")


# ========================================
# RECURRING AI WORKFLOW ENGINE
# ========================================

class RecurringAIWorkflowEngine:
    """AI workflow engine for recurring detection"""

    def __init__(self):
        _ensure_recurring_ai_tables()
        self._merchant_memory_cache: Dict[str, RecurringMerchantMemory] = {}
        self._load_merchant_memory()

    def _load_merchant_memory(self):
        """Load merchant memory into cache"""
        conn = get_conn()
        try:
            rows = conn.execute("""
                SELECT merchant_pattern, recurring_type, sub_category, is_essential,
                       confidence, confirmation_count, rejection_count, last_confirmed
                FROM recurring_merchant_memory
                WHERE confidence >= 0.3
            """).fetchall()

            for row in rows:
                pattern = row[0]
                self._merchant_memory_cache[pattern.lower()] = RecurringMerchantMemory(
                    merchant_pattern=pattern,
                    recurring_type=row[1],
                    sub_category=row[2],
                    is_essential=bool(row[3]),
                    confidence=float(row[4] or 0.5),
                    confirmation_count=int(row[5] or 0),
                    rejection_count=int(row[6] or 0),
                    last_confirmed=row[7]
                )

            logger.info(f"Loaded {len(self._merchant_memory_cache)} merchant patterns into memory")
        except Exception as e:
            logger.warning(f"Could not load merchant memory: {e}")

    # ========================================
    # AI REVIEW WORKFLOW
    # ========================================

    async def review_classification_with_ai(
        self,
        classification: RecurringClassificationResult,
        use_llm: bool = True
    ) -> AIReviewResult:
        """
        Review a pattern-based classification with AI.

        This is the core workflow:
        1. Check merchant memory first (learned patterns)
        2. If unknown or low confidence, ask LLM for review
        3. Return enhanced classification with AI reasoning
        """

        # Step 1: Check merchant memory
        memory_result = self._check_merchant_memory(classification)
        if memory_result and memory_result.confidence >= 0.8:
            # High confidence from memory - use it
            return AIReviewResult(
                series_id=classification.series_id,
                original_type=classification.recurring_type,
                ai_suggested_type=memory_result.recurring_type,
                original_confidence=classification.pattern_confidence,
                ai_confidence=memory_result.confidence,
                ai_reasoning=f"Learned from {memory_result.confirmation_count} previous confirmations",
                corrections={
                    "recurring_type": memory_result.recurring_type,
                    "sub_category": memory_result.sub_category,
                    "is_essential": memory_result.is_essential
                } if memory_result.recurring_type != classification.recurring_type else {},
                should_override=memory_result.recurring_type != classification.recurring_type,
                review_quality="high"
            )

        # Step 2: If LLM enabled and low confidence, ask LLM
        if use_llm and classification.pattern_confidence < 0.7:
            llm_result = await self._review_with_llm(classification)
            if llm_result:
                # Log the AI review
                self._log_ai_review(classification, llm_result)
                return llm_result

        # Step 3: Return pattern result as-is with memory boost if available
        confidence_boost = 0.0
        if memory_result:
            confidence_boost = min(0.2, memory_result.confirmation_count * 0.05)

        return AIReviewResult(
            series_id=classification.series_id,
            original_type=classification.recurring_type,
            ai_suggested_type=classification.recurring_type,
            original_confidence=classification.pattern_confidence,
            ai_confidence=min(0.95, classification.pattern_confidence + confidence_boost),
            ai_reasoning="Pattern classification confirmed" + (
                f" (boosted by {memory_result.confirmation_count} confirmations)" if memory_result else ""
            ),
            corrections={},
            should_override=False,
            review_quality="medium" if memory_result else "low"
        )

    def _check_merchant_memory(
        self,
        classification: RecurringClassificationResult
    ) -> Optional[RecurringMerchantMemory]:
        """Check if we have learned this merchant pattern before"""

        # Try exact match
        merchant_lower = classification.merchant_name.lower().strip()
        if merchant_lower in self._merchant_memory_cache:
            return self._merchant_memory_cache[merchant_lower]

        # Try partial match
        for pattern, memory in self._merchant_memory_cache.items():
            if pattern in merchant_lower or merchant_lower in pattern:
                return memory

        return None

    async def _review_with_llm(
        self,
        classification: RecurringClassificationResult
    ) -> Optional[AIReviewResult]:
        """Ask LLM to review and enhance the classification"""

        try:
            from .merchant_intelligence import analyze_merchant_with_llm

            # Build context for LLM
            context = {
                "merchant": classification.merchant_name,
                "description": classification.description,
                "amount": classification.amount,
                "cadence": classification.cadence,
                "pattern_type": classification.recurring_type,
                "pattern_confidence": classification.pattern_confidence,
                "signals": classification.signals
            }

            # Get LLM analysis
            llm_result = await analyze_merchant_with_llm(
                classification.description,
                context=context
            )

            if llm_result and llm_result.get("recurring_type"):
                llm_type = llm_result.get("recurring_type", classification.recurring_type)
                llm_confidence = float(llm_result.get("confidence", 0.7))

                # Determine if LLM suggests different classification
                should_override = (
                    llm_type != classification.recurring_type and
                    llm_confidence > classification.pattern_confidence + 0.1
                )

                corrections = {}
                if should_override:
                    corrections["recurring_type"] = llm_type
                    if llm_result.get("sub_category"):
                        corrections["sub_category"] = llm_result["sub_category"]
                    if llm_result.get("is_essential") is not None:
                        corrections["is_essential"] = llm_result["is_essential"]

                return AIReviewResult(
                    series_id=classification.series_id,
                    original_type=classification.recurring_type,
                    ai_suggested_type=llm_type,
                    original_confidence=classification.pattern_confidence,
                    ai_confidence=llm_confidence,
                    ai_reasoning=llm_result.get("reasoning", "LLM classification"),
                    corrections=corrections,
                    should_override=should_override,
                    review_quality="high" if llm_confidence >= 0.8 else "medium"
                )

        except Exception as e:
            logger.warning(f"LLM review failed: {e}")

        return None

    def _log_ai_review(
        self,
        classification: RecurringClassificationResult,
        review: AIReviewResult
    ):
        """Log AI review for tracking and analysis"""
        conn = get_conn()

        try:
            conn.execute("""
                INSERT INTO recurring_ai_review_log
                (id, series_id, pattern_type, pattern_confidence, ai_type, ai_confidence, ai_reasoning, reviewed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                str(uuid.uuid4()),
                classification.series_id,
                classification.recurring_type,
                classification.pattern_confidence,
                review.ai_suggested_type,
                review.ai_confidence,
                review.ai_reasoning,
                datetime.now(UTC)
            ])
        except Exception as e:
            logger.warning(f"Could not log AI review: {e}")

    # ========================================
    # LEARNING FROM FEEDBACK
    # ========================================

    async def learn_from_feedback(self, feedback: RecurringFeedback):
        """
        Learn from user feedback to improve future classifications.

        This updates:
        1. Merchant memory with confirmation/rejection
        2. Confidence scores based on accuracy
        3. Pattern-to-type mappings
        """

        conn = get_conn()

        # Store feedback record
        try:
            conn.execute("""
                INSERT INTO recurring_ai_feedback
                (id, series_id, original_type, corrected_type, original_confidence, was_correct, feedback_source, merchant_pattern, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
            """, [
                str(uuid.uuid4()),
                feedback.series_id,
                feedback.original_type,
                feedback.corrected_type,
                0.0,  # Will be filled from series
                feedback.was_correct,
                feedback.feedback_source,
                feedback.merchant_pattern,
                datetime.now(UTC)
            ])
        except Exception as e:
            logger.warning(f"Could not store feedback: {e}")

        # Update merchant memory
        await self._update_merchant_memory(feedback)

        # If correction provided, update the series
        if feedback.corrected_type and not feedback.was_correct:
            await self._apply_correction(feedback)

    async def _update_merchant_memory(self, feedback: RecurringFeedback):
        """Update merchant memory based on feedback"""

        if not feedback.merchant_pattern:
            return

        conn = get_conn()
        pattern = feedback.merchant_pattern.strip()
        pattern_lower = pattern.lower()

        # Get current memory or create new
        existing = conn.execute(
            "SELECT id, confirmation_count, rejection_count, confidence FROM recurring_merchant_memory WHERE LOWER(merchant_pattern) = ?",
            [pattern_lower]
        ).fetchone()

        # Track values for cache update
        final_type = feedback.corrected_type or feedback.original_type
        final_essential = feedback.corrected_is_essential if feedback.corrected_is_essential is not None else feedback.original_is_essential
        final_conf = 0.7
        final_confirms = 1 if feedback.was_correct else 0
        final_rejects = 0 if feedback.was_correct else 1

        if existing:
            memory_id, confirms, rejects, conf = existing
            confirms = int(confirms or 0)
            rejects = int(rejects or 0)
            conf = float(conf or 0.5)

            if feedback.was_correct:
                # Confirmation - boost confidence
                final_confirms = confirms + 1
                final_conf = min(0.99, conf + 0.05)
                final_rejects = rejects
                conn.execute("""
                    UPDATE recurring_merchant_memory
                    SET confirmation_count = ?, confidence = ?, last_confirmed = ?, updated_at = ?
                    WHERE id = ?
                """, [final_confirms, final_conf, datetime.now(UTC), datetime.now(UTC), memory_id])
            else:
                # Rejection - decrease confidence or update type
                final_rejects = rejects + 1
                final_confirms = confirms
                final_conf = max(0.1, conf - 0.1)

                # If corrected type provided, update the stored type
                if feedback.corrected_type:
                    final_conf = 0.6  # Reset confidence with new type
                    conn.execute("""
                        UPDATE recurring_merchant_memory
                        SET recurring_type = ?, rejection_count = ?, confidence = ?, updated_at = ?
                        WHERE id = ?
                    """, [feedback.corrected_type, final_rejects, final_conf, datetime.now(UTC), memory_id])
                else:
                    conn.execute("""
                        UPDATE recurring_merchant_memory
                        SET rejection_count = ?, confidence = ?, updated_at = ?
                        WHERE id = ?
                    """, [final_rejects, final_conf, datetime.now(UTC), memory_id])
        else:
            # Create new memory entry
            final_conf = 0.7 if feedback.was_correct else 0.5

            try:
                conn.execute("""
                    INSERT INTO recurring_merchant_memory
                    (id, merchant_pattern, recurring_type, is_essential, confidence, confirmation_count, rejection_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT DO NOTHING
                """, [
                    str(uuid.uuid4()),
                    pattern,
                    final_type,
                    final_essential,
                    final_conf,
                    final_confirms,
                    final_rejects,
                    datetime.now(UTC),
                    datetime.now(UTC)
                ])
            except Exception:
                pass  # Race condition or duplicate - ignore

        # Update cache with actual computed values
        self._merchant_memory_cache[pattern_lower] = RecurringMerchantMemory(
            merchant_pattern=pattern,
            recurring_type=final_type,
            sub_category="",
            is_essential=final_essential,
            confidence=final_conf,
            confirmation_count=final_confirms,
            rejection_count=final_rejects,
            last_confirmed=datetime.now(UTC) if feedback.was_correct else None
        )

        logger.info(f"Updated merchant memory for '{pattern}': {'confirmed' if feedback.was_correct else 'corrected'}")

    async def _apply_correction(self, feedback: RecurringFeedback):
        """Apply user correction to the recurring series"""

        conn = get_conn()

        try:
            updates = []
            params = []

            if feedback.corrected_type:
                updates.append("recurring_type = ?")
                params.append(feedback.corrected_type)

            if feedback.corrected_is_essential is not None:
                updates.append("is_essential = ?")
                params.append(feedback.corrected_is_essential)

            if updates:
                params.append(feedback.series_id)
                conn.execute(f"""
                    UPDATE recurring_series
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, params)

                logger.info(f"Applied correction to series {feedback.series_id}")

        except Exception as e:
            logger.warning(f"Could not apply correction: {e}")

    # ========================================
    # BATCH REVIEW & LEARNING
    # ========================================

    async def batch_review_pending_series(
        self,
        limit: int = 50,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Batch review pending/uncertain recurring series with AI.

        This processes series that:
        - Have low confidence
        - Haven't been reviewed by AI yet
        - Need classification
        """

        conn = get_conn()

        # Get series needing review
        series_list = conn.execute("""
            SELECT rs.id, rs.name, rs.amount_mean, rs.cadence, rs.recurring_type,
                   rs.sub_category, rs.is_essential, rs.llm_confidence
            FROM recurring_series rs
            LEFT JOIN recurring_ai_review_log rl ON rl.series_id = rs.id
            WHERE rs.status = 'active'
              AND (rs.llm_confidence IS NULL OR rs.llm_confidence < 0.7)
              AND rl.id IS NULL
            ORDER BY rs.amount_mean DESC
            LIMIT ?
        """, [limit]).fetchall()

        results = {
            "total_reviewed": 0,
            "enhanced": 0,
            "unchanged": 0,
            "errors": 0,
            "reviews": []
        }

        for series in series_list:
            try:
                series_id, name, amount, cadence, rec_type, sub_cat, essential, llm_conf = series

                # Build classification result from series
                classification = RecurringClassificationResult(
                    series_id=series_id,
                    merchant_name=name or "",
                    description=name or "",
                    amount=float(amount or 0),
                    recurring_type=rec_type or "unknown",
                    sub_category=sub_cat or "",
                    is_essential=bool(essential),
                    pattern_confidence=float(llm_conf or 0.5),
                    cadence=cadence or "monthly",
                    detection_method="existing_series",
                    signals=[]
                )

                # Review with AI
                review = await self.review_classification_with_ai(classification, use_llm)

                results["total_reviewed"] += 1

                if review.should_override and review.corrections:
                    # Apply corrections
                    updates = []
                    params = []

                    for field, value in review.corrections.items():
                        updates.append(f"{field} = ?")
                        params.append(value)

                    updates.append("llm_confidence = ?")
                    params.append(review.ai_confidence)
                    updates.append("llm_classified_at = ?")
                    params.append(datetime.now(UTC))
                    params.append(series_id)

                    conn.execute(f"""
                        UPDATE recurring_series
                        SET {', '.join(updates)}
                        WHERE id = ?
                    """, params)

                    results["enhanced"] += 1
                else:
                    # Just update confidence
                    conn.execute("""
                        UPDATE recurring_series
                        SET llm_confidence = ?, llm_classified_at = ?
                        WHERE id = ?
                    """, [review.ai_confidence, datetime.now(UTC), series_id])

                    results["unchanged"] += 1

                results["reviews"].append({
                    "series_id": series_id,
                    "name": name,
                    "original_type": review.original_type,
                    "ai_type": review.ai_suggested_type,
                    "confidence": review.ai_confidence,
                    "enhanced": review.should_override
                })

            except Exception as e:
                logger.warning(f"Error reviewing series: {e}")
                results["errors"] += 1

        return results

    async def backfill_merchant_memory(self) -> Dict[str, int]:
        """
        Backfill merchant memory from existing confirmed recurring series.

        This bootstraps the learning system from historical data.
        """

        conn = get_conn()

        # Get all active recurring series with classifications
        series_list = conn.execute("""
            SELECT name, recurring_type, sub_category, is_essential,
                   COALESCE(llm_confidence, 0.5) as confidence,
                   COUNT(*) OVER (PARTITION BY name) as occurrence_count
            FROM recurring_series
            WHERE status = 'active'
              AND recurring_type IS NOT NULL
              AND name IS NOT NULL
            ORDER BY confidence DESC, occurrence_count DESC
        """).fetchall()

        stats = {"inserted": 0, "updated": 0, "skipped": 0}

        seen_patterns = set()

        for series in series_list:
            name, rec_type, sub_cat, essential, conf, count = series

            pattern = name.strip().lower()
            if not pattern or pattern in seen_patterns:
                continue
            seen_patterns.add(pattern)

            # Check if exists
            existing = conn.execute(
                "SELECT id, confidence FROM recurring_merchant_memory WHERE LOWER(merchant_pattern) = ?",
                [pattern]
            ).fetchone()

            if existing:
                existing_conf = float(existing[1] or 0)
                if conf > existing_conf:
                    conn.execute("""
                        UPDATE recurring_merchant_memory
                        SET recurring_type = ?, sub_category = ?, is_essential = ?,
                            confidence = ?, updated_at = ?
                        WHERE id = ?
                    """, [rec_type, sub_cat, essential, conf, datetime.now(UTC), existing[0]])
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            else:
                conn.execute("""
                    INSERT INTO recurring_merchant_memory
                    (id, merchant_pattern, recurring_type, sub_category, is_essential, confidence, confirmation_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    str(uuid.uuid4()),
                    name.strip(),
                    rec_type,
                    sub_cat,
                    essential,
                    conf,
                    int(count),
                    datetime.now(UTC),
                    datetime.now(UTC)
                ])
                stats["inserted"] += 1

        # Reload cache
        self._load_merchant_memory()

        logger.info(f"Backfilled merchant memory: {stats}")
        return stats

    # ========================================
    # STATISTICS & ANALYSIS
    # ========================================

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about the AI learning system"""

        conn = get_conn()

        try:
            # Merchant memory stats
            memory_count = conn.execute("SELECT COUNT(*) FROM recurring_merchant_memory").fetchone()[0]
            high_conf_count = conn.execute(
                "SELECT COUNT(*) FROM recurring_merchant_memory WHERE confidence >= 0.8"
            ).fetchone()[0]

            # Feedback stats
            total_feedback = conn.execute("SELECT COUNT(*) FROM recurring_ai_feedback").fetchone()[0]
            correct_feedback = conn.execute(
                "SELECT COUNT(*) FROM recurring_ai_feedback WHERE was_correct = TRUE"
            ).fetchone()[0]

            # AI review stats
            total_reviews = conn.execute("SELECT COUNT(*) FROM recurring_ai_review_log").fetchone()[0]
            applied_reviews = conn.execute(
                "SELECT COUNT(*) FROM recurring_ai_review_log WHERE was_applied = TRUE"
            ).fetchone()[0]

            # Recent activity
            recent_feedback = conn.execute("""
                SELECT series_id, original_type, corrected_type, was_correct, created_at
                FROM recurring_ai_feedback
                ORDER BY created_at DESC
                LIMIT 5
            """).fetchall()

            accuracy = correct_feedback / total_feedback if total_feedback > 0 else 0.0

            return {
                "merchant_memory": {
                    "total_patterns": memory_count,
                    "high_confidence": high_conf_count,
                    "cached_patterns": len(self._merchant_memory_cache)
                },
                "feedback": {
                    "total": total_feedback,
                    "correct": correct_feedback,
                    "accuracy": accuracy
                },
                "ai_reviews": {
                    "total": total_reviews,
                    "applied": applied_reviews
                },
                "recent_feedback": [
                    {
                        "series_id": f[0],
                        "original_type": f[1],
                        "corrected_type": f[2],
                        "was_correct": f[3],
                        "created_at": str(f[4])
                    }
                    for f in recent_feedback
                ]
            }
        except Exception as e:
            logger.warning(f"Error getting learning stats: {e}")
            return {"error": str(e)}

    def get_accuracy_by_type(self) -> Dict[str, float]:
        """Get classification accuracy broken down by recurring type"""

        conn = get_conn()

        try:
            rows = conn.execute("""
                SELECT original_type,
                       COUNT(*) as total,
                       SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct
                FROM recurring_ai_feedback
                GROUP BY original_type
            """).fetchall()

            return {
                row[0]: (row[2] / row[1]) if row[1] > 0 else 0.0
                for row in rows
            }
        except Exception:
            return {}


# ========================================
# GLOBAL INSTANCE & CONVENIENCE FUNCTIONS
# ========================================

_workflow_engine: Optional[RecurringAIWorkflowEngine] = None


def get_recurring_ai_workflow() -> RecurringAIWorkflowEngine:
    """Get the global recurring AI workflow engine"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = RecurringAIWorkflowEngine()
    return _workflow_engine


async def review_recurring_with_ai(
    series_id: str,
    merchant_name: str,
    description: str,
    amount: float,
    recurring_type: str,
    pattern_confidence: float,
    cadence: str = "monthly",
    use_llm: bool = True
) -> Dict[str, Any]:
    """Convenience function to review a single recurring series with AI"""

    engine = get_recurring_ai_workflow()

    classification = RecurringClassificationResult(
        series_id=series_id,
        merchant_name=merchant_name,
        description=description,
        amount=amount,
        recurring_type=recurring_type,
        sub_category="",
        is_essential=False,
        pattern_confidence=pattern_confidence,
        cadence=cadence,
        detection_method="api_call",
        signals=[]
    )

    result = await engine.review_classification_with_ai(classification, use_llm)

    return asdict(result)


async def learn_from_recurring_feedback(
    series_id: str,
    original_type: str,
    corrected_type: Optional[str],
    was_correct: bool,
    merchant_pattern: str,
    is_essential: bool = False,
    corrected_is_essential: Optional[bool] = None
) -> Dict[str, str]:
    """Convenience function to record feedback and learn from it"""

    engine = get_recurring_ai_workflow()

    feedback = RecurringFeedback(
        series_id=series_id,
        original_type=original_type,
        corrected_type=corrected_type,
        original_is_essential=is_essential,
        corrected_is_essential=corrected_is_essential,
        was_correct=was_correct,
        feedback_source="user_feedback",
        merchant_pattern=merchant_pattern
    )

    await engine.learn_from_feedback(feedback)

    return {"status": "learned", "series_id": series_id}


def get_recurring_learning_stats() -> Dict[str, Any]:
    """Get recurring AI learning statistics"""
    engine = get_recurring_ai_workflow()
    return engine.get_learning_stats()
