"""
AI-Powered Insights Workflow

Provides an AI review layer for financial insights:
- Reviews generated insights with AI for accuracy/relevance
- Learns from user feedback (clicked, dismissed, acted upon)
- Improves insight prioritization over time
- Personalizes insights based on user behavior
"""

from __future__ import annotations

import json
import uuid
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from collections import defaultdict
from enum import Enum

from .db import get_conn

logger = logging.getLogger(__name__)


# ========================================
# DATA CLASSES
# ========================================

class InsightFeedbackType(Enum):
    VIEWED = "viewed"           # User saw the insight
    CLICKED = "clicked"         # User clicked for details
    ACTED = "acted"             # User took action
    DISMISSED = "dismissed"     # User dismissed/hid
    HELPFUL = "helpful"         # User marked as helpful
    NOT_HELPFUL = "not_helpful" # User marked as not helpful


class InsightCategory(Enum):
    SPENDING = "spending"
    SAVINGS = "savings"
    RECURRING = "recurring"
    ANOMALY = "anomaly"
    FORECAST = "forecast"
    OPTIMIZATION = "optimization"
    RISK = "risk"


@dataclass
class InsightFeedback:
    """User feedback on an insight"""
    insight_id: str
    insight_type: str
    insight_category: str
    feedback_type: InsightFeedbackType
    user_action: Optional[str]  # What action was taken
    time_to_action_seconds: Optional[int]
    context: Dict[str, Any]  # Additional context


@dataclass
class InsightPattern:
    """Learned pattern about what insights are useful"""
    pattern_type: str  # e.g., "high_spending_alert", "subscription_cancel"
    category: str
    engagement_rate: float  # Click rate
    action_rate: float      # Action taken rate
    dismiss_rate: float     # Dismissal rate
    helpfulness_score: float
    total_shown: int
    avg_time_to_action: Optional[float]


@dataclass
class AIEnhancedInsight:
    """Insight enhanced by AI review"""
    insight_id: str
    original_priority: int
    ai_priority: int
    original_message: str
    ai_enhanced_message: Optional[str]
    relevance_score: float
    personalization_score: float
    predicted_engagement: float
    reasoning: str


# ========================================
# DATABASE SETUP
# ========================================

def _ensure_insights_ai_tables():
    """Ensure AI workflow tables exist"""
    conn = get_conn()

    # Insights feedback table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS insights_ai_feedback (
                id TEXT PRIMARY KEY,
                insight_id TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                insight_category TEXT,
                feedback_type TEXT NOT NULL,
                user_action TEXT,
                time_to_action_seconds INTEGER,
                context_json TEXT,
                created_at TIMESTAMP NOT NULL
            )
        """)
    except Exception as e:
        logger.debug(f"insights_ai_feedback table may exist: {e}")

    # Insight patterns table (learned behavior)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS insights_pattern_memory (
                id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL UNIQUE,
                category TEXT,
                shown_count INTEGER DEFAULT 0,
                clicked_count INTEGER DEFAULT 0,
                acted_count INTEGER DEFAULT 0,
                dismissed_count INTEGER DEFAULT 0,
                helpful_count INTEGER DEFAULT 0,
                not_helpful_count INTEGER DEFAULT 0,
                total_time_to_action INTEGER DEFAULT 0,
                engagement_rate DOUBLE DEFAULT 0.0,
                action_rate DOUBLE DEFAULT 0.0,
                helpfulness_score DOUBLE DEFAULT 0.5,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)
    except Exception as e:
        logger.debug(f"insights_pattern_memory table may exist: {e}")

    # AI review log
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS insights_ai_review_log (
                id TEXT PRIMARY KEY,
                insight_id TEXT NOT NULL,
                original_priority INTEGER,
                ai_priority INTEGER,
                relevance_score DOUBLE,
                predicted_engagement DOUBLE,
                reasoning TEXT,
                reviewed_at TIMESTAMP NOT NULL
            )
        """)
    except Exception as e:
        logger.debug(f"insights_ai_review_log table may exist: {e}")


# ========================================
# INSIGHTS AI WORKFLOW ENGINE
# ========================================

class InsightsAIWorkflowEngine:
    """AI workflow engine for insights"""

    def __init__(self):
        _ensure_insights_ai_tables()
        self._pattern_cache: Dict[str, InsightPattern] = {}
        self._load_pattern_memory()

    def _load_pattern_memory(self):
        """Load learned insight patterns into cache"""
        conn = get_conn()
        try:
            rows = conn.execute("""
                SELECT pattern_type, category, shown_count, clicked_count,
                       acted_count, dismissed_count, helpful_count, not_helpful_count,
                       total_time_to_action, engagement_rate, action_rate, helpfulness_score
                FROM insights_pattern_memory
            """).fetchall()

            for row in rows:
                pattern_type = row[0]
                shown = int(row[2] or 0)
                clicked = int(row[3] or 0)
                acted = int(row[4] or 0)
                dismissed = int(row[5] or 0)
                helpful = int(row[6] or 0)
                not_helpful = int(row[7] or 0)
                total_time = int(row[8] or 0)

                self._pattern_cache[pattern_type] = InsightPattern(
                    pattern_type=pattern_type,
                    category=row[1] or "",
                    engagement_rate=clicked / shown if shown > 0 else 0.5,
                    action_rate=acted / shown if shown > 0 else 0.0,
                    dismiss_rate=dismissed / shown if shown > 0 else 0.0,
                    helpfulness_score=(helpful - not_helpful) / max(1, helpful + not_helpful) * 0.5 + 0.5,
                    total_shown=shown,
                    avg_time_to_action=total_time / acted if acted > 0 else None
                )

            logger.info(f"Loaded {len(self._pattern_cache)} insight patterns into memory")
        except Exception as e:
            logger.warning(f"Could not load insight patterns: {e}")

    # ========================================
    # AI REVIEW OF INSIGHTS
    # ========================================

    async def review_insights_with_ai(
        self,
        insights: List[Dict[str, Any]],
        use_llm: bool = False
    ) -> List[AIEnhancedInsight]:
        """
        Review and enhance a list of insights with AI.

        Uses learned patterns to:
        - Adjust priority based on engagement history
        - Predict which insights will be acted upon
        - Filter out insights with high dismiss rates
        """
        enhanced = []

        for insight in insights:
            insight_id = insight.get("id", str(uuid.uuid4()))
            insight_type = insight.get("type", "unknown")
            original_priority = insight.get("priority", 5)
            message = insight.get("message", "")

            # Check pattern memory
            pattern = self._get_pattern(insight_type)

            # Calculate AI priority adjustment
            if pattern:
                # Boost priority if high engagement, lower if high dismiss rate
                engagement_factor = pattern.engagement_rate * 2  # 0-2 range
                dismiss_penalty = pattern.dismiss_rate * 1.5
                helpfulness_boost = (pattern.helpfulness_score - 0.5) * 2

                priority_adjustment = engagement_factor - dismiss_penalty + helpfulness_boost
                ai_priority = max(1, min(10, original_priority + int(priority_adjustment * 2)))

                relevance_score = pattern.helpfulness_score
                predicted_engagement = pattern.engagement_rate

                reasoning = f"Based on {pattern.total_shown} showings: {pattern.engagement_rate:.0%} engagement, {pattern.dismiss_rate:.0%} dismiss rate"
            else:
                # New insight type - neutral adjustment
                ai_priority = original_priority
                relevance_score = 0.5
                predicted_engagement = 0.5
                reasoning = "New insight type - no historical data"

            # Optional LLM enhancement
            ai_message = None
            if use_llm and predicted_engagement < 0.3:
                # Try to improve low-engagement insights with LLM
                ai_message = await self._enhance_message_with_llm(message, insight)

            enhanced.append(AIEnhancedInsight(
                insight_id=insight_id,
                original_priority=original_priority,
                ai_priority=ai_priority,
                original_message=message,
                ai_enhanced_message=ai_message,
                relevance_score=relevance_score,
                personalization_score=0.5,  # Could be enhanced with user history
                predicted_engagement=predicted_engagement,
                reasoning=reasoning
            ))

            # Log the review
            self._log_review(insight_id, original_priority, ai_priority, relevance_score, predicted_engagement, reasoning)

        # Sort by AI priority
        enhanced.sort(key=lambda x: x.ai_priority, reverse=True)

        return enhanced

    def _get_pattern(self, insight_type: str) -> Optional[InsightPattern]:
        """Get learned pattern for an insight type"""
        # Try exact match
        if insight_type in self._pattern_cache:
            return self._pattern_cache[insight_type]

        # Try category match
        for pattern_type, pattern in self._pattern_cache.items():
            if pattern_type in insight_type or insight_type in pattern_type:
                return pattern

        return None

    async def _enhance_message_with_llm(
        self,
        message: str,
        insight: Dict[str, Any]
    ) -> Optional[str]:
        """Use LLM to enhance insight message"""
        try:
            from .ai import get_ai_service
            ai_service = get_ai_service()

            prompt = f"""Improve this financial insight to be more actionable and engaging:

Original: {message}

Context: {json.dumps(insight.get('data', {}))}

Provide a clearer, more actionable version in 1-2 sentences."""

            # This would call the LLM - simplified for now
            return None  # LLM integration would go here

        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
            return None

    def _log_review(
        self,
        insight_id: str,
        original_priority: int,
        ai_priority: int,
        relevance_score: float,
        predicted_engagement: float,
        reasoning: str
    ):
        """Log AI review for analysis"""
        conn = get_conn()
        try:
            conn.execute("""
                INSERT INTO insights_ai_review_log
                (id, insight_id, original_priority, ai_priority, relevance_score, predicted_engagement, reasoning, reviewed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                str(uuid.uuid4()),
                insight_id,
                original_priority,
                ai_priority,
                relevance_score,
                predicted_engagement,
                reasoning,
                datetime.now(UTC)
            ])
        except Exception as e:
            logger.warning(f"Could not log insight review: {e}")

    # ========================================
    # LEARNING FROM FEEDBACK
    # ========================================

    async def learn_from_feedback(self, feedback: InsightFeedback):
        """Learn from user feedback on an insight"""

        conn = get_conn()

        # Store feedback record
        try:
            conn.execute("""
                INSERT INTO insights_ai_feedback
                (id, insight_id, insight_type, insight_category, feedback_type, user_action, time_to_action_seconds, context_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                str(uuid.uuid4()),
                feedback.insight_id,
                feedback.insight_type,
                feedback.insight_category,
                feedback.feedback_type.value,
                feedback.user_action,
                feedback.time_to_action_seconds,
                json.dumps(feedback.context) if feedback.context else None,
                datetime.now(UTC)
            ])
        except Exception as e:
            logger.warning(f"Could not store insight feedback: {e}")

        # Update pattern memory
        await self._update_pattern_memory(feedback)

    async def _update_pattern_memory(self, feedback: InsightFeedback):
        """Update pattern memory based on feedback"""

        conn = get_conn()
        pattern_type = feedback.insight_type

        # Get current pattern or create new
        existing = conn.execute(
            "SELECT id, shown_count, clicked_count, acted_count, dismissed_count, helpful_count, not_helpful_count, total_time_to_action FROM insights_pattern_memory WHERE pattern_type = ?",
            [pattern_type]
        ).fetchone()

        if existing:
            pattern_id = existing[0]
            shown = int(existing[1] or 0)
            clicked = int(existing[2] or 0)
            acted = int(existing[3] or 0)
            dismissed = int(existing[4] or 0)
            helpful = int(existing[5] or 0)
            not_helpful = int(existing[6] or 0)
            total_time = int(existing[7] or 0)

            # Update based on feedback type
            if feedback.feedback_type == InsightFeedbackType.VIEWED:
                shown += 1
            elif feedback.feedback_type == InsightFeedbackType.CLICKED:
                clicked += 1
            elif feedback.feedback_type == InsightFeedbackType.ACTED:
                acted += 1
                if feedback.time_to_action_seconds:
                    total_time += feedback.time_to_action_seconds
            elif feedback.feedback_type == InsightFeedbackType.DISMISSED:
                dismissed += 1
            elif feedback.feedback_type == InsightFeedbackType.HELPFUL:
                helpful += 1
            elif feedback.feedback_type == InsightFeedbackType.NOT_HELPFUL:
                not_helpful += 1

            # Calculate rates
            engagement_rate = clicked / shown if shown > 0 else 0.5
            action_rate = acted / shown if shown > 0 else 0.0
            helpfulness_score = (helpful - not_helpful) / max(1, helpful + not_helpful) * 0.5 + 0.5

            conn.execute("""
                UPDATE insights_pattern_memory
                SET shown_count = ?, clicked_count = ?, acted_count = ?, dismissed_count = ?,
                    helpful_count = ?, not_helpful_count = ?, total_time_to_action = ?,
                    engagement_rate = ?, action_rate = ?, helpfulness_score = ?, updated_at = ?
                WHERE id = ?
            """, [shown, clicked, acted, dismissed, helpful, not_helpful, total_time,
                  engagement_rate, action_rate, helpfulness_score, datetime.now(UTC), pattern_id])

            # Update cache
            self._pattern_cache[pattern_type] = InsightPattern(
                pattern_type=pattern_type,
                category=feedback.insight_category or "",
                engagement_rate=engagement_rate,
                action_rate=action_rate,
                dismiss_rate=dismissed / shown if shown > 0 else 0.0,
                helpfulness_score=helpfulness_score,
                total_shown=shown,
                avg_time_to_action=total_time / acted if acted > 0 else None
            )
        else:
            # Create new pattern entry
            shown = 1 if feedback.feedback_type == InsightFeedbackType.VIEWED else 0
            clicked = 1 if feedback.feedback_type == InsightFeedbackType.CLICKED else 0
            acted = 1 if feedback.feedback_type == InsightFeedbackType.ACTED else 0
            dismissed = 1 if feedback.feedback_type == InsightFeedbackType.DISMISSED else 0
            helpful = 1 if feedback.feedback_type == InsightFeedbackType.HELPFUL else 0
            not_helpful = 1 if feedback.feedback_type == InsightFeedbackType.NOT_HELPFUL else 0
            total_time = feedback.time_to_action_seconds or 0

            conn.execute("""
                INSERT INTO insights_pattern_memory
                (id, pattern_type, category, shown_count, clicked_count, acted_count, dismissed_count,
                 helpful_count, not_helpful_count, total_time_to_action, engagement_rate, action_rate,
                 helpfulness_score, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                str(uuid.uuid4()),
                pattern_type,
                feedback.insight_category,
                shown, clicked, acted, dismissed, helpful, not_helpful, total_time,
                0.5, 0.0, 0.5,
                datetime.now(UTC),
                datetime.now(UTC)
            ])

            self._pattern_cache[pattern_type] = InsightPattern(
                pattern_type=pattern_type,
                category=feedback.insight_category or "",
                engagement_rate=0.5,
                action_rate=0.0,
                dismiss_rate=0.0,
                helpfulness_score=0.5,
                total_shown=1,
                avg_time_to_action=None
            )

        logger.info(f"Updated insight pattern for '{pattern_type}': {feedback.feedback_type.value}")

    # ========================================
    # STATISTICS & ANALYSIS
    # ========================================

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about the insights AI learning system"""

        conn = get_conn()

        try:
            # Pattern stats
            pattern_count = conn.execute("SELECT COUNT(*) FROM insights_pattern_memory").fetchone()[0]
            high_engagement = conn.execute(
                "SELECT COUNT(*) FROM insights_pattern_memory WHERE engagement_rate >= 0.5"
            ).fetchone()[0]

            # Feedback stats
            total_feedback = conn.execute("SELECT COUNT(*) FROM insights_ai_feedback").fetchone()[0]

            # Feedback by type
            feedback_by_type = conn.execute("""
                SELECT feedback_type, COUNT(*) as cnt
                FROM insights_ai_feedback
                GROUP BY feedback_type
            """).fetchall()

            # Top performing insight types
            top_patterns = conn.execute("""
                SELECT pattern_type, engagement_rate, action_rate, shown_count
                FROM insights_pattern_memory
                ORDER BY engagement_rate DESC
                LIMIT 5
            """).fetchall()

            # Low performing (candidates for improvement)
            low_patterns = conn.execute("""
                SELECT pattern_type, engagement_rate,
                       CASE WHEN shown_count > 0 THEN CAST(dismissed_count AS DOUBLE) / shown_count ELSE 0.0 END as dismiss_rate,
                       shown_count
                FROM insights_pattern_memory
                WHERE shown_count >= 5 AND engagement_rate < 0.3
                ORDER BY engagement_rate ASC
                LIMIT 5
            """).fetchall()

            return {
                "pattern_memory": {
                    "total_patterns": pattern_count,
                    "high_engagement": high_engagement,
                    "cached_patterns": len(self._pattern_cache)
                },
                "feedback": {
                    "total": total_feedback,
                    "by_type": {row[0]: row[1] for row in feedback_by_type}
                },
                "top_performing": [
                    {
                        "type": row[0],
                        "engagement_rate": round(float(row[1] or 0), 3),
                        "action_rate": round(float(row[2] or 0), 3),
                        "shown": row[3]
                    }
                    for row in top_patterns
                ],
                "needs_improvement": [
                    {
                        "type": row[0],
                        "engagement_rate": round(float(row[1] or 0), 3),
                        "dismiss_rate": round(float(row[2] or 0), 3),
                        "shown": row[3]
                    }
                    for row in low_patterns
                ]
            }
        except Exception as e:
            logger.warning(f"Error getting insight stats: {e}")
            return {"error": str(e)}

    def get_personalized_priority(self, insight_type: str) -> float:
        """Get personalized priority multiplier for an insight type"""
        pattern = self._get_pattern(insight_type)
        if pattern:
            # Higher engagement = higher priority
            return 0.5 + pattern.engagement_rate + (pattern.helpfulness_score - 0.5)
        return 1.0  # Neutral


# ========================================
# GLOBAL INSTANCE & CONVENIENCE FUNCTIONS
# ========================================

_insights_workflow_engine: Optional[InsightsAIWorkflowEngine] = None


def get_insights_ai_workflow() -> InsightsAIWorkflowEngine:
    """Get the global insights AI workflow engine"""
    global _insights_workflow_engine
    if _insights_workflow_engine is None:
        _insights_workflow_engine = InsightsAIWorkflowEngine()
    return _insights_workflow_engine


async def review_insights_with_ai(
    insights: List[Dict[str, Any]],
    use_llm: bool = False
) -> List[Dict[str, Any]]:
    """Convenience function to review insights with AI"""
    engine = get_insights_ai_workflow()
    results = await engine.review_insights_with_ai(insights, use_llm)
    return [asdict(r) for r in results]


async def record_insight_feedback(
    insight_id: str,
    insight_type: str,
    feedback_type: str,
    insight_category: str = "",
    user_action: str = None,
    time_to_action: int = None
) -> Dict[str, str]:
    """Convenience function to record insight feedback"""
    engine = get_insights_ai_workflow()

    feedback = InsightFeedback(
        insight_id=insight_id,
        insight_type=insight_type,
        insight_category=insight_category,
        feedback_type=InsightFeedbackType(feedback_type),
        user_action=user_action,
        time_to_action_seconds=time_to_action,
        context={}
    )

    await engine.learn_from_feedback(feedback)
    return {"status": "learned", "insight_id": insight_id}


def get_insights_learning_stats() -> Dict[str, Any]:
    """Get insights AI learning statistics"""
    engine = get_insights_ai_workflow()
    return engine.get_learning_stats()
