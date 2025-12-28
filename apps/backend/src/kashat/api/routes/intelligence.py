"""
Intelligence Router - State-of-the-Art AI-Powered Financial Insights

Exposes the powerful AI modules that were previously not accessible via API:
- ai_insights.py: Personalized insights, financial health, spending behavior
- ai_alerts.py: Smart alerts and notifications
- Enhanced recurring and transfer detection with AI

Phase 2 of SOTA Implementation.
"""

from __future__ import annotations

from typing import Optional, List
from datetime import date, timedelta
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ============================================================================
# PERSONALIZED INSIGHTS ENDPOINTS
# ============================================================================

@router.get("/insights")
async def get_personalized_insights(
    account_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50)
):
    """Get AI-powered personalized financial insights and recommendations.

    Returns actionable insights based on spending patterns, trends, and anomalies.
    Each insight includes priority, impact score, and specific recommendations.
    """
    from ...ai_insights import get_ai_insights_engine
    engine = get_ai_insights_engine()

    insights = engine.generate_personalized_insights(
        account_id=account_id,
        insight_limit=limit
    )

    return {
        "insights": [
            {
                "id": insight.id,
                "category": insight.category.value,
                "priority": insight.priority.value,
                "title": insight.title,
                "description": insight.description,
                "recommendations": insight.recommendations,
                "impact_score": round(insight.impact_score, 3),
                "confidence": round(insight.confidence, 3),
                "data_points": insight.data_points,
                "expires_at": insight.expires_at.isoformat() if insight.expires_at else None
            }
            for insight in insights
        ],
        "total_insights": len(insights),
        "high_priority_count": len([i for i in insights if i.priority.value in ["high", "urgent"]]),
        "generated_at": date.today().isoformat()
    }


@router.get("/health")
async def get_financial_health(
    account_id: Optional[str] = Query(None)
):
    """Get comprehensive financial health assessment with detailed scoring.

    Returns overall health score (0-100), component scores, strengths,
    improvement areas, and personalized recommendations.
    """
    from ...ai_insights import get_ai_insights_engine
    engine = get_ai_insights_engine()

    report = engine.assess_financial_health(account_id=account_id)

    return {
        "health_report": {
            "overall_score": report.overall_score,
            "health_grade": report.health_grade.value,
            "component_scores": {
                "spending_health": report.spending_health,
                "savings_health": report.savings_health,
                "budgeting_health": report.budgeting_health,
                "trend_health": report.trend_health
            },
            "key_strengths": report.key_strengths,
            "improvement_areas": report.improvement_areas,
            "recommendations": report.recommendations
        },
        "generated_at": date.today().isoformat()
    }


@router.get("/behavior")
async def get_spending_behavior(
    account_id: Optional[str] = Query(None)
):
    """Analyze user's spending behavior and create a behavioral profile.

    Returns spending persona, average monthly spending, volatility,
    top categories, habits, risk factors, and behavioral insights.
    """
    from ...ai_insights import get_ai_insights_engine
    engine = get_ai_insights_engine()

    profile = engine.analyze_spending_behavior(account_id=account_id)

    return {
        "behavior_profile": {
            "persona": profile.persona.value,
            "avg_monthly_spending": round(profile.avg_monthly_spending, 2),
            "spending_volatility": round(profile.spending_volatility, 3),
            "top_categories": [
                {"name": name, "total": round(total, 2)}
                for name, total in profile.top_categories
            ],
            "spending_habits": profile.spending_habits,
            "risk_factors": profile.risk_factors,
            "behavioral_insights": profile.behavioral_insights
        },
        "generated_at": date.today().isoformat()
    }


# ============================================================================
# INTELLIGENCE FEED - Unified Stream of AI Insights
# ============================================================================

class FeedFilters(BaseModel):
    include_anomalies: bool = True
    include_trends: bool = True
    include_recommendations: bool = True
    include_alerts: bool = True
    min_priority: str = "low"  # "low", "medium", "high", "urgent"


@router.post("/feed")
async def get_intelligence_feed(
    filters: FeedFilters,
    account_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """Get unified intelligence feed with all AI-powered insights.

    Combines personalized insights, anomaly alerts, trend notifications,
    and recommendations into a single prioritized feed.
    """
    from ...ai_insights import get_ai_insights_engine
    from ...ai_analytics import get_ai_analytics_engine

    insights_engine = get_ai_insights_engine()
    analytics_engine = get_ai_analytics_engine()

    feed_items = []

    # Get personalized insights
    if filters.include_recommendations:
        insights = insights_engine.generate_personalized_insights(
            account_id=account_id,
            insight_limit=limit // 2
        )
        for insight in insights:
            feed_items.append({
                "type": "insight",
                "subtype": insight.category.value,
                "priority": insight.priority.value,
                "title": insight.title,
                "description": insight.description,
                "data": {
                    "recommendations": insight.recommendations[:2],
                    "impact_score": round(insight.impact_score, 3)
                },
                "expires_at": insight.expires_at.isoformat() if insight.expires_at else None
            })

    # Get anomalies
    if filters.include_anomalies:
        anomalies = analytics_engine.detect_anomalies(
            days_lookback=14,
            account_id=account_id
        )
        for anomaly in anomalies[:5]:
            feed_items.append({
                "type": "alert",
                "subtype": "anomaly",
                "priority": "high" if anomaly.severity == "high" else "medium",
                "title": f"Unusual {anomaly.anomaly_type.replace('_', ' ')}",
                "description": anomaly.description,
                "data": {
                    "transaction_id": anomaly.transaction_id,
                    "actual_value": round(anomaly.actual_value, 2),
                    "expected_range": [round(anomaly.expected_range[0], 2), round(anomaly.expected_range[1], 2)]
                },
                "expires_at": (date.today() + timedelta(days=7)).isoformat()
            })

    # Get trend alerts
    if filters.include_trends:
        trends = analytics_engine.analyze_trends(account_id=account_id)
        significant_trends = [t for t in trends if t.is_significant]
        for trend in significant_trends[:3]:
            feed_items.append({
                "type": "notification",
                "subtype": "trend",
                "priority": "medium" if abs(trend.change_percentage) > 20 else "low",
                "title": f"{trend.metric_name} {trend.trend_direction.value}",
                "description": f"Changed by {abs(trend.change_percentage):.1f}%",
                "data": {
                    "metric": trend.metric_name,
                    "change_pct": round(trend.change_percentage, 1),
                    "direction": trend.trend_direction.value
                },
                "expires_at": (date.today() + timedelta(days=30)).isoformat()
            })

    # Filter by minimum priority
    priority_order = {"low": 0, "medium": 1, "high": 2, "urgent": 3}
    min_priority_level = priority_order.get(filters.min_priority, 0)
    feed_items = [
        item for item in feed_items
        if priority_order.get(item["priority"], 0) >= min_priority_level
    ]

    # Sort by priority (highest first)
    feed_items.sort(key=lambda x: priority_order.get(x["priority"], 0), reverse=True)

    return {
        "feed": feed_items[:limit],
        "total_items": len(feed_items),
        "filters_applied": filters.dict(),
        "generated_at": date.today().isoformat()
    }


# ============================================================================
# AI-ENHANCED RECURRING DETECTION
# ============================================================================

@router.post("/recurring/detect")
async def ai_detect_recurring(
    min_occurrences: int = Query(2, ge=2, le=10),
    confidence_threshold: float = Query(0.6, ge=0.0, le=1.0)
):
    """AI-enhanced recurring transaction detection.

    Uses the existing recurring detection engine plus AI merchant normalization
    for improved accuracy. Returns candidates with confidence scores.
    """
    from ...recurring import detect_recurring_candidates, Tx
    from ...db import get_conn
    from ...ai_service import get_ai_service
    from datetime import datetime

    conn = get_conn()

    # Get transactions not in any transfer (pending or confirmed)
    rows = conn.execute(
        """
        SELECT t.id, t.account_id, t.posted_at, t.amount,
               COALESCE(t.ai_merchant_name, t.description_norm) as description_norm
        FROM [transaction] t
        LEFT JOIN match_transfer mt
          ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id)
        WHERE mt.left_tx_id IS NULL AND mt.right_tx_id IS NULL
        ORDER BY t.posted_at DESC
        LIMIT 2000
        """
    ).fetchall()

    # Parse posted_at strings to date objects
    def parse_date(d):
        if isinstance(d, date):
            return d
        if isinstance(d, str):
            return datetime.fromisoformat(d.replace('Z', '+00:00')).date()
        return d

    txs = [Tx(r[0], r[1], parse_date(r[2]), r[3], r[4]) for r in rows]
    candidates = detect_recurring_candidates(txs, min_occurrences=min_occurrences)

    # Filter by confidence and enhance with AI insights
    enhanced_candidates = []
    for c in candidates:
        if c.get("confidence", 0) >= confidence_threshold:
            # Add AI enhancement metadata
            enhanced_candidates.append({
                "description": c["desc"],
                "amount_mean": round(c["amount_mean"], 2),
                "amount_sd": round(c["amount_sd"], 2),
                "cadence": c["cadence"],
                "occurrences": len(c["tx_ids"]),
                "anchor_day": c["anchor_day"],
                "confidence": round(c["confidence"], 3),
                "price_hike_detected": c.get("price_hike", False),
                "tx_ids": c["tx_ids"][:5],  # First 5 for preview
                "ai_enhanced": True,
                "recommendation": _get_recurring_recommendation(c)
            })

    return {
        "candidates": enhanced_candidates,
        "total_candidates": len(enhanced_candidates),
        "detection_params": {
            "min_occurrences": min_occurrences,
            "confidence_threshold": confidence_threshold
        },
        "generated_at": date.today().isoformat()
    }


def _get_recurring_recommendation(candidate: dict) -> str:
    """Generate recommendation for a recurring candidate."""
    confidence = candidate.get("confidence", 0)
    price_hike = candidate.get("price_hike", False)
    cadence = candidate.get("cadence", "")

    if confidence > 0.8:
        if price_hike:
            return "High confidence recurring with recent price increase. Review and confirm."
        return "High confidence recurring. Auto-confirm recommended."
    elif confidence > 0.6:
        return "Moderate confidence. Review transaction details before confirming."
    else:
        return "Lower confidence. May need more occurrences to confirm pattern."


# ============================================================================
# AI-ENHANCED TRANSFER MATCHING
# ============================================================================

@router.post("/transfers/suggest")
async def ai_suggest_transfers(
    date_tolerance_days: int = Query(3, ge=0, le=14),
    amount_tolerance_pct: float = Query(0.01, ge=0.0, le=0.1),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0)
):
    """AI-enhanced transfer pair suggestion.

    Uses multiple signals (amount match, date proximity, description analysis)
    to identify potential transfer pairs with confidence scores.
    """
    from ...db import get_conn
    from datetime import timedelta

    conn = get_conn()

    # Get recent unmatched transactions
    rows = conn.execute(
        """
        SELECT t.id, t.posted_at, t.amount, t.description_norm, t.account_id
        FROM [transaction] t
        LEFT JOIN match_transfer mt
          ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id)
        WHERE mt.left_tx_id IS NULL
        AND t.posted_at >= date('now', '-90 days')
        ORDER BY t.posted_at DESC
        LIMIT 1000
        """
    ).fetchall()

    # Group by positive/negative amounts
    debits = [r for r in rows if r[2] < 0]  # negative amounts (outflows)
    credits = [r for r in rows if r[2] > 0]  # positive amounts (inflows)

    suggestions = []

    for debit in debits:
        debit_id, debit_date, debit_amount, debit_desc, debit_account = debit
        debit_abs = abs(debit_amount)

        for credit in credits:
            credit_id, credit_date, credit_amount, credit_desc, credit_account = credit

            # Skip same account
            if debit_account == credit_account:
                continue

            # Check amount match (within tolerance)
            amount_diff_pct = abs(credit_amount - debit_abs) / max(debit_abs, 0.01)
            if amount_diff_pct > amount_tolerance_pct:
                continue

            # Check date proximity
            date_diff = abs((credit_date - debit_date).days)
            if date_diff > date_tolerance_days:
                continue

            # Calculate confidence based on signals
            signals = []
            confidence = 0.5  # base

            # Exact amount match
            if amount_diff_pct < 0.001:
                confidence += 0.25
                signals.append("exact_amount_match")
            else:
                confidence += 0.15 * (1 - amount_diff_pct / amount_tolerance_pct)
                signals.append("amount_within_tolerance")

            # Same day bonus
            if date_diff == 0:
                confidence += 0.15
                signals.append("same_day")
            else:
                confidence += 0.10 * (1 - date_diff / date_tolerance_days)
                signals.append(f"within_{date_diff}_days")

            # Transfer keywords in description
            transfer_keywords = ["transfer", "xfer", "ach", "wire", "payment", "zelle", "venmo"]
            debit_has_keyword = any(kw in debit_desc.lower() for kw in transfer_keywords)
            credit_has_keyword = any(kw in credit_desc.lower() for kw in transfer_keywords)
            if debit_has_keyword or credit_has_keyword:
                confidence += 0.10
                signals.append("transfer_keyword_detected")

            confidence = min(1.0, confidence)

            if confidence >= min_confidence:
                suggestions.append({
                    "left_tx_id": debit_id,
                    "right_tx_id": credit_id,
                    "left_amount": round(debit_amount, 2),
                    "right_amount": round(credit_amount, 2),
                    "left_description": debit_desc,
                    "right_description": credit_desc,
                    "left_date": debit_date.isoformat() if hasattr(debit_date, 'isoformat') else str(debit_date),
                    "right_date": credit_date.isoformat() if hasattr(credit_date, 'isoformat') else str(credit_date),
                    "confidence": round(confidence, 3),
                    "signals": signals
                })

    # Sort by confidence
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "suggestions": suggestions[:50],  # Top 50
        "total_suggestions": len(suggestions),
        "detection_params": {
            "date_tolerance_days": date_tolerance_days,
            "amount_tolerance_pct": amount_tolerance_pct,
            "min_confidence": min_confidence
        },
        "generated_at": date.today().isoformat()
    }


# ============================================================================
# AI RULE SUGGESTIONS
# ============================================================================

@router.get("/rules/suggest")
async def ai_suggest_rules(
    min_occurrences: int = Query(3, ge=2, le=20),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0)
):
    """AI-powered rule suggestions based on categorization patterns.

    Analyzes manually categorized transactions to suggest rules that would
    automate similar categorizations in the future.
    """
    from ...db import get_conn

    conn = get_conn()

    # Find merchants with consistent manual categorization
    rows = conn.execute(
        """
        SELECT
            COALESCE(t.ai_merchant_name, t.description_norm) as merchant,
            c.id as category_id,
            c.name as category_name,
            COUNT(*) as occurrences,
            AVG(CASE WHEN t.amount < 0 THEN -t.amount ELSE t.amount END) as avg_amount
        FROM [transaction] t
        JOIN transaction_category tc ON t.id = tc.tx_id
        JOIN category c ON tc.category_id = c.id
        GROUP BY 1, 2, 3
        HAVING COUNT(*) >= ?
        ORDER BY occurrences DESC
        LIMIT 100
        """,
        [min_occurrences]
    ).fetchall()

    suggestions = []
    seen_merchants = set()

    for row in rows:
        merchant, category_id, category_name, occurrences, avg_amount = row

        # Skip if we've already suggested a rule for this merchant
        if merchant in seen_merchants:
            continue

        # Calculate confidence based on consistency
        # Higher occurrences = higher confidence
        confidence = min(1.0, 0.5 + (occurrences / 20) * 0.5)

        if confidence >= min_confidence:
            seen_merchants.add(merchant)

            # Generate predicate (escape special regex chars)
            import re
            escaped_merchant = re.escape(merchant)

            suggestions.append({
                "merchant": merchant,
                "category_id": category_id,
                "category_name": category_name,
                "occurrences": occurrences,
                "avg_amount": round(avg_amount, 2) if avg_amount else None,
                "confidence": round(confidence, 3),
                "suggested_rule": {
                    "predicate": {
                        "field": "description_norm",
                        "op": "contains",
                        "value": merchant
                    },
                    "action": {
                        "set_category": category_id
                    },
                    "priority": 50
                },
                "explanation": f"Based on {occurrences} transactions consistently categorized as '{category_name}'"
            })

    return {
        "suggestions": suggestions,
        "total_suggestions": len(suggestions),
        "params": {
            "min_occurrences": min_occurrences,
            "min_confidence": min_confidence
        },
        "generated_at": date.today().isoformat()
    }


# ============================================================================
# SUBSCRIPTION DETECTION
# ============================================================================

@router.get("/subscriptions")
async def detect_subscriptions(
    account_id: Optional[str] = Query(None)
):
    """Detect and list subscription-like recurring charges.

    Identifies transactions that appear to be subscriptions based on:
    - Regular monthly/yearly cadence
    - Consistent amounts
    - Known subscription merchant patterns
    """
    from ...db import get_conn

    conn = get_conn()

    # Get confirmed recurring series that look like subscriptions
    where_clause = "WHERE rs.status = 'confirmed' AND rs.cadence IN ('monthly', 'yearly')"
    params = []

    if account_id:
        where_clause += " AND EXISTS (SELECT 1 FROM [transaction] t JOIN recurring_tx rt ON t.id = rt.tx_id WHERE rt.series_id = rs.id AND t.account_id = ?)"
        params.append(account_id)

    rows = conn.execute(
        f"""
        SELECT
            rs.id,
            rs.name,
            rs.cadence,
            rs.amount_mean,
            rs.amount_sd,
            rs.last_date,
            rs.next_date,
            rs.price_hike,
            COUNT(rt.tx_id) as occurrences
        FROM recurring_series rs
        LEFT JOIN recurring_tx rt ON rt.series_id = rs.id
        {where_clause}
        GROUP BY rs.id, rs.name, rs.cadence, rs.amount_mean, rs.amount_sd, rs.last_date, rs.next_date, rs.price_hike
        ORDER BY rs.amount_mean DESC
        """,
        params
    ).fetchall()

    subscriptions = []
    total_monthly_cost = 0.0

    for row in rows:
        series_id, name, cadence, amount_mean, amount_sd, last_date, next_date, price_hike, occurrences = row

        # Calculate monthly cost
        monthly_cost = abs(amount_mean) if cadence == 'monthly' else abs(amount_mean) / 12
        total_monthly_cost += monthly_cost

        subscriptions.append({
            "id": series_id,
            "name": name,
            "cadence": cadence,
            "amount": round(abs(amount_mean), 2),
            "monthly_equivalent": round(monthly_cost, 2),
            "annual_cost": round(monthly_cost * 12, 2),
            "last_charge": last_date.isoformat() if hasattr(last_date, 'isoformat') else str(last_date) if last_date else None,
            "next_expected": next_date.isoformat() if hasattr(next_date, 'isoformat') else str(next_date) if next_date else None,
            "price_increased": bool(price_hike),
            "occurrences": occurrences,
            "stability": "stable" if (amount_sd or 0) < abs(amount_mean) * 0.05 else "variable"
        })

    return {
        "subscriptions": subscriptions,
        "summary": {
            "total_subscriptions": len(subscriptions),
            "total_monthly_cost": round(total_monthly_cost, 2),
            "total_annual_cost": round(total_monthly_cost * 12, 2)
        },
        "generated_at": date.today().isoformat()
    }
