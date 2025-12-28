"""
AI Workflow API Routes

Unified endpoints for AI-powered workflows:
- Insights AI workflow
- Ingestion AI workflow
- Learning statistics
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/ai-workflow", tags=["ai-workflow"])


# =============================================================================
# INSIGHTS AI WORKFLOW
# =============================================================================

class InsightFeedbackRequest(BaseModel):
    insight_id: str
    insight_type: str
    feedback_type: str  # viewed, clicked, acted, dismissed, helpful, not_helpful
    insight_category: str = ""
    user_action: Optional[str] = None
    time_to_action: Optional[int] = None


class InsightReviewRequest(BaseModel):
    insights: List[Dict[str, Any]]
    use_llm: bool = False


@router.post("/insights/feedback")
async def submit_insight_feedback(body: InsightFeedbackRequest):
    """Submit feedback on an insight to train the AI.

    Feedback types:
    - viewed: User saw the insight
    - clicked: User clicked for details
    - acted: User took action on the insight
    - dismissed: User dismissed/hid the insight
    - helpful: User marked as helpful
    - not_helpful: User marked as not helpful
    """
    try:
        from ...insights_ai_workflow import record_insight_feedback

        result = await record_insight_feedback(
            insight_id=body.insight_id,
            insight_type=body.insight_type,
            feedback_type=body.feedback_type,
            insight_category=body.insight_category,
            user_action=body.user_action,
            time_to_action=body.time_to_action
        )

        return result

    except Exception as e:
        return {"error": str(e), "status": "failed"}


@router.post("/insights/review")
async def review_insights(body: InsightReviewRequest):
    """Review insights with AI to enhance priority and relevance.

    Takes a list of insights and returns AI-enhanced versions with:
    - Adjusted priorities based on learned engagement patterns
    - Predicted engagement rates
    - Relevance scores
    """
    try:
        from ...insights_ai_workflow import review_insights_with_ai

        result = await review_insights_with_ai(
            insights=body.insights,
            use_llm=body.use_llm
        )

        return {"enhanced_insights": result}

    except Exception as e:
        return {"error": str(e)}


@router.get("/insights/stats")
def get_insights_learning_stats():
    """Get statistics about the insights AI learning system.

    Returns:
    - Pattern memory statistics
    - Feedback counts by type
    - Top performing insight types
    - Insight types needing improvement
    """
    try:
        from ...insights_ai_workflow import get_insights_learning_stats
        return get_insights_learning_stats()
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# INGESTION AI WORKFLOW
# =============================================================================

class IngestFeedbackRequest(BaseModel):
    transaction_id: str
    field: str  # description, merchant, category, amount, date
    original_value: str
    corrected_value: str
    import_run_id: Optional[str] = None
    institution: Optional[str] = None


class IngestReviewRequest(BaseModel):
    transactions: List[Dict[str, Any]]
    institution: Optional[str] = None
    use_llm: bool = False


class LearnInstitutionRequest(BaseModel):
    institution: str
    transactions: List[Dict[str, Any]]


@router.post("/ingest/feedback")
async def submit_ingest_correction(body: IngestFeedbackRequest):
    """Submit a correction to an imported transaction.

    This teaches the AI to handle similar transactions better in the future.

    Fields that can be corrected:
    - description: The cleaned description
    - merchant: The extracted merchant name
    - category: The assigned category
    - amount: The parsed amount (sign correction)
    - date: The parsed date
    """
    try:
        from ...ingest_ai_workflow import record_ingest_correction

        result = await record_ingest_correction(
            transaction_id=body.transaction_id,
            field=body.field,
            original_value=body.original_value,
            corrected_value=body.corrected_value,
            import_run_id=body.import_run_id,
            institution=body.institution
        )

        return result

    except Exception as e:
        return {"error": str(e), "status": "failed"}


@router.post("/ingest/review")
async def review_imported_transactions(body: IngestReviewRequest):
    """Review imported transactions with AI.

    Applies learned patterns to:
    - Clean up descriptions
    - Extract merchant names
    - Suggest categories
    - Fix amount signs
    """
    try:
        from ...ingest_ai_workflow import review_imported_transactions as review_func

        result = await review_func(
            transactions=body.transactions,
            institution=body.institution,
            use_llm=body.use_llm
        )

        return {"enhanced_transactions": result}

    except Exception as e:
        return {"error": str(e)}


@router.post("/ingest/learn-institution")
async def learn_institution_patterns(body: LearnInstitutionRequest):
    """Learn parsing patterns specific to an institution.

    Analyzes transactions to discover:
    - Common prefixes/suffixes to remove
    - Date formats used
    - Amount format patterns
    """
    try:
        from ...ingest_ai_workflow import get_ingest_ai_workflow

        engine = get_ingest_ai_workflow()
        result = await engine.learn_institution_patterns(
            institution=body.institution,
            transactions=body.transactions
        )

        return result

    except Exception as e:
        return {"error": str(e)}


@router.get("/ingest/stats")
def get_ingest_learning_stats():
    """Get statistics about the ingestion AI learning system.

    Returns:
    - Pattern memory statistics
    - Correction counts by field
    - Institution patterns learned
    - Top corrections applied
    """
    try:
        from ...ingest_ai_workflow import get_ingest_learning_stats
        return get_ingest_learning_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/ingest/quality/{import_run_id}")
def analyze_import_quality(import_run_id: str):
    """Analyze the quality of an import run.

    Returns:
    - Total transactions
    - Confidence distribution
    - Field issues found
    - Recommendations
    """
    try:
        from ...ingest_ai_workflow import get_ingest_ai_workflow
        from dataclasses import asdict

        engine = get_ingest_ai_workflow()
        report = engine.analyze_import_quality(import_run_id)

        return asdict(report)

    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# UNIFIED STATS
# =============================================================================

@router.get("/stats")
def get_all_ai_workflow_stats():
    """Get unified statistics across all AI workflows.

    Combines stats from:
    - Recurring AI workflow
    - Insights AI workflow
    - Ingestion AI workflow
    """
    stats = {}

    try:
        from ...recurring_ai_workflow import get_recurring_learning_stats
        stats["recurring"] = get_recurring_learning_stats()
    except Exception as e:
        stats["recurring"] = {"error": str(e)}

    try:
        from ...insights_ai_workflow import get_insights_learning_stats
        stats["insights"] = get_insights_learning_stats()
    except Exception as e:
        stats["insights"] = {"error": str(e)}

    try:
        from ...ingest_ai_workflow import get_ingest_learning_stats
        stats["ingest"] = get_ingest_learning_stats()
    except Exception as e:
        stats["ingest"] = {"error": str(e)}

    # Calculate totals
    total_patterns = 0
    total_feedback = 0

    for key in ["recurring", "insights", "ingest"]:
        if "error" not in stats.get(key, {}):
            memory = stats[key].get("pattern_memory", stats[key].get("merchant_memory", {}))
            total_patterns += memory.get("total_patterns", 0)
            feedback = stats[key].get("feedback", {})
            total_feedback += feedback.get("total", 0)

    stats["totals"] = {
        "total_patterns": total_patterns,
        "total_feedback": total_feedback
    }

    return stats
