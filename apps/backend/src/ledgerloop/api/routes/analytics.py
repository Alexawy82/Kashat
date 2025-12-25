from __future__ import annotations

from typing import Optional, List
from datetime import date, timedelta, datetime
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ...db import get_conn
# Heavy AI modules are imported lazily inside endpoint handlers to reduce import overhead


router = APIRouter(prefix="/analytics", tags=["analytics"])

# Simple in-process cache for summary/predictions
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 120.0

def _cache_get(key: str) -> dict | None:
    import time
    v = _CACHE.get(key)
    if not v:
        return None
    ts, data = v
    if (time.time() - ts) > _CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return data

def _cache_set(key: str, value: dict) -> None:
    import time
    _CACHE[key] = (time.time(), value)


@router.get("/monthly")
def monthly_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    account_id: Optional[str] = Query(None),
):
    conn = get_conn()
    where = [
        "NOT (mt.decided_at IS NOT NULL AND COALESCE(mt.include_in_analytics, FALSE) = FALSE)",
        "(t.is_adjustment IS FALSE OR t.is_adjustment IS NULL)",
    ]
    params = []
    if start_date:
        where.append("t.posted_at >= ?")
        params.append(start_date)
    if end_date:
        where.append("t.posted_at <= ?")
        params.append(end_date)
    if account_id:
        where.append("t.account_id = ?")
        params.append(account_id)
    wh = " WHERE " + " AND ".join(where)
    rows = conn.execute(
        f"""
        SELECT date_trunc('month', t.posted_at) AS month,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS income,
               SUM(t.amount) AS net
        FROM [transaction] t
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        {wh}
        GROUP BY 1
        ORDER BY 1
        """,
        params,
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/category-monthly")
def category_monthly(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    account_id: Optional[str] = Query(None),
):
    conn = get_conn()
    where = [
        "NOT (mt.decided_at IS NOT NULL AND COALESCE(mt.include_in_analytics, FALSE) = FALSE)",
        "(t.is_adjustment IS FALSE OR t.is_adjustment IS NULL)",
    ]
    params = []
    if start_date:
        where.append("t.posted_at >= ?")
        params.append(start_date)
    if end_date:
        where.append("t.posted_at <= ?")
        params.append(end_date)
    if account_id:
        where.append("t.account_id = ?")
        params.append(account_id)
    wh = " WHERE " + " AND ".join(where)
    rows = conn.execute(
        f"""
        SELECT date_trunc('month', t.posted_at) AS month,
               c.id as category_id,
               c.name as category_name,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        {wh}
        GROUP BY 1,2,3
        ORDER BY 1,3
        """,
        params,
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/merchants")
def merchant_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    account_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    conn = get_conn()
    where = [
        "NOT (mt.decided_at IS NOT NULL AND COALESCE(mt.include_in_analytics, FALSE) = FALSE)",
        "(t.is_adjustment IS FALSE OR t.is_adjustment IS NULL)",
    ]
    params = []
    if start_date:
        where.append("t.posted_at >= ?")
        params.append(start_date)
    if end_date:
        where.append("t.posted_at <= ?")
        params.append(end_date)
    if account_id:
        where.append("t.account_id = ?")
        params.append(account_id)
    wh = " WHERE " + " AND ".join(where)
    rows = conn.execute(
        f"""
        SELECT t.description_norm as merchant,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               COUNT(*) as count
        FROM [transaction] t
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        {wh}
        GROUP BY 1
        ORDER BY spend DESC
        LIMIT ?
        """,
        params + [limit],
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/cashflow")
def cashflow(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    account_id: Optional[str] = Query(None),
):
    conn = get_conn()
    where = [
        "NOT (mt.decided_at IS NOT NULL AND COALESCE(mt.include_in_analytics, FALSE) = FALSE)",
        "(t.is_adjustment IS FALSE OR t.is_adjustment IS NULL)",
    ]
    params: list = []
    if start_date:
        where.append("t.posted_at >= ?")
        params.append(start_date)
    if end_date:
        where.append("t.posted_at <= ?")
        params.append(end_date)
    if account_id:
        where.append("t.account_id = ?")
        params.append(account_id)
    wh = " WHERE " + " AND ".join(where)
    row = conn.execute(
        f"""
        SELECT 
            SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS income,
            SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS debits,
            SUM(t.amount) AS net
        FROM [transaction] t
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        {wh}
        """,
        params,
    ).fetchone()
    
    if row is None:
        return {"income": 0.0, "debits": 0.0, "net": 0.0}
    
    return {"income": row[0] or 0.0, "debits": row[1] or 0.0, "net": row[2] or 0.0}


@router.get("/summary")
def summary(
    start_date: Optional[date] = Query(None, alias="from"),
    end_date: Optional[date] = Query(None, alias="to"),
    include_transfers: bool = Query(False, alias="includeTransfers"),
):
    """Unified analytics summary with totals, byMonth, byCategory, topMerchants.

    Adds a 120s in-process cache keyed by params.
    """
    key = f"summary:{start_date}:{end_date}:{include_transfers}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    conn = get_conn()
    where = ["(t.is_adjustment IS FALSE OR t.is_adjustment IS NULL)"]
    params: list = []
    if start_date:
        where.append("t.posted_at >= ?")
        params.append(start_date)
    if end_date:
        where.append("t.posted_at <= ?")
        params.append(end_date)
    join_mt = "LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL"
    if not include_transfers:
        # Exclude confirmed transfers unless explicitly included in analytics
        where.append("NOT (mt.decided_at IS NOT NULL AND COALESCE(mt.include_in_analytics, FALSE) = FALSE)")

    wh = (" WHERE " + " AND ".join(where)) if where else ""

    # totals
    row = conn.execute(
        f"""
        SELECT 
            SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS income,
            SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
            SUM(t.amount) AS net
        FROM [transaction] t
        {join_mt}
        {wh}
        """,
        params,
    ).fetchone() or (0.0, 0.0, 0.0)

    totals = {"income": row[0] or 0.0, "spend": row[1] or 0.0, "net": row[2] or 0.0}

    # byMonth
    rows_month = conn.execute(
        f"""
        SELECT date_trunc('month', t.posted_at) AS month,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS income,
               SUM(t.amount) AS net
        FROM [transaction] t
        {join_mt}
        {wh}
        GROUP BY 1
        ORDER BY 1
        """,
        params,
    ).fetchall()
    cols_month = [c[0] for c in conn.description]
    by_month = [dict(zip(cols_month, r)) for r in rows_month]

    # byCategory
    rows_cat = conn.execute(
        f"""
        SELECT c.id as category_id,
               c.name as category_name,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               COUNT(*) as count
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        {join_mt}
        {wh}
        GROUP BY 1,2
        ORDER BY spend DESC NULLS LAST, count DESC
        """,
        params,
    ).fetchall()
    cols_cat = [c[0] for c in conn.description]
    by_category = [dict(zip(cols_cat, r)) for r in rows_cat]

    # topMerchants
    rows_merch = conn.execute(
        f"""
        SELECT t.description_norm as merchant,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               COUNT(*) as count
        FROM [transaction] t
        {join_mt}
        {wh}
        GROUP BY 1
        ORDER BY spend DESC
        LIMIT 25
        """,
        params,
    ).fetchall()
    cols_merch = [c[0] for c in conn.description]
    top_merchants = [dict(zip(cols_merch, r)) for r in rows_merch]

    result = {
        "totals": totals,
        "byMonth": by_month,
        "byCategory": by_category,
        "topMerchants": top_merchants,
    }
    _cache_set(key, result)
    return result


 


@router.get("/recurring")
def recurring_series():
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, COALESCE(display_name, name) as payee, cadence, amount_mean as avg_amount, amount_sd as variance, last_date, next_date, price_hike FROM recurring_series WHERE status IN ('pending','confirmed') AND NOT regexp_matches(lower(COALESCE(display_name, name)), '(online banking transfer|automatic transfer)') ORDER BY payee"
        ).fetchall()
    except Exception:
        rows = conn.execute(
            "SELECT id, name as payee, cadence, amount_mean as avg_amount, amount_sd as variance, last_date, next_date, price_hike FROM recurring_series WHERE status IN ('pending','confirmed') AND NOT regexp_matches(lower(name), '(online banking transfer|automatic transfer)') ORDER BY name"
        ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


# AI-Enhanced Analytics Endpoints

@router.get("/ai/spending-patterns")
async def get_spending_patterns(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    account_id: Optional[str] = Query(None)
):
    """Get AI-powered spending pattern analysis"""
    from ...ai_analytics import get_ai_analytics_engine
    analytics_engine = get_ai_analytics_engine()
    
    patterns = analytics_engine.analyze_spending_patterns(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id
    )
    
    return {
        "patterns": [
            {
                "category": pattern.category,
                "pattern_type": pattern.pattern_type,
                "frequency": pattern.frequency,
                "average_amount": round(pattern.average_amount, 2),
                "confidence": round(pattern.confidence, 3),
                "trend_direction": pattern.trend_direction.value,
                "seasonality_detected": pattern.seasonality_detected,
                "key_merchants": pattern.key_merchants,
                "insights": pattern.insights
            }
            for pattern in patterns
        ],
        "analysis_period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "total_patterns": len(patterns)
    }


@router.get("/predictions")
def predictions(
    start_date: Optional[date] = Query(None, alias="from"),
    end_date: Optional[date] = Query(None, alias="to"),
):
    """Heuristic predictions for budget risk, savings opportunities and recurring forecast.

    Deterministic rules-first outputs; cached for 120s.
    """
    key = f"predictions:{start_date}:{end_date}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    conn = get_conn()
    where = ["(t.is_adjustment IS FALSE OR t.is_adjustment IS NULL)"]
    params: list = []
    if start_date:
        where.append("t.posted_at >= ?")
        params.append(start_date)
    if end_date:
        where.append("t.posted_at <= ?")
        params.append(end_date)
    join_mt = "LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL"
    # exclude confirmed transfers unless explicitly included in analytics
    where.append("NOT (mt.decided_at IS NOT NULL AND COALESCE(mt.include_in_analytics, FALSE) = FALSE)")
    wh = " WHERE " + " AND ".join(where)

    # Aggregate spend per category and merchant for heuristics
    rows_cat = conn.execute(
        f"""
        SELECT COALESCE(c.name,'Uncategorized') AS category,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               COUNT(*) as count
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        {join_mt}
        {wh}
        GROUP BY 1
        ORDER BY spend DESC
        """,
        params,
    ).fetchall()
    cols_cat = [c[0] for c in conn.description]
    cats = [dict(zip(cols_cat, r)) for r in rows_cat]

    # Compute monthly averages for top categories to gauge budget risk
    rows_month = conn.execute(
        f"""
        SELECT date_trunc('month', t.posted_at) AS month,
               COALESCE(c.name,'Uncategorized') AS category,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        {join_mt}
        {wh}
        GROUP BY 1,2
        ORDER BY 1,3 DESC
        """,
        params,
    ).fetchall()
    cols_m = [c[0] for c in conn.description]
    series = [dict(zip(cols_m, r)) for r in rows_month]

    # Simple rule: categories with rising last month vs avg -> budgetRisk
    import collections
    by_cat: dict[str, list[float]] = collections.defaultdict(list)
    for row in series:
        by_cat[str(row["category"])].append(float(row["spend"]))
    budget_risk = []
    for cat_name, vals in by_cat.items():
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        last = vals[-1]
        if avg > 0:
            delta_pct = (last - avg) / avg * 100.0
        else:
            delta_pct = 0.0
        if last > avg * 1.15 and last > 50:  # threshold
            budget_risk.append({
                "category": cat_name,
                "projected": round(last, 2),
                "budget": round(avg, 2),
                "deltaPct": round(delta_pct, 2),
                "explanation": f"Last month {cat_name} spend {last:.2f} is {delta_pct:.1f}% over average {avg:.2f}"
            })
    budget_risk.sort(key=lambda x: -x["deltaPct"])  # highest risk first

    # Savings opportunities: top merchants within top categories, assume 10% potential
    rows_merch = conn.execute(
        f"""
        SELECT t.description_norm AS merchant,
               COALESCE(c.name,'Uncategorized') AS category,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               LIST(t.id) AS tx_ids
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        {join_mt}
        {wh}
        GROUP BY 1,2
        ORDER BY spend DESC
        LIMIT 50
        """,
        params,
    ).fetchall()
    cols_merch = [c[0] for c in conn.description]
    merch_rows = [dict(zip(cols_merch, r)) for r in rows_merch]
    savings_ops = []
    for m in merch_rows[:10]:
        est = float(m["spend"]) * 0.1
        tx_ids = m.get("tx_ids") or []
        # DuckDB LIST returns Python list already
        savings_ops.append({
            "pattern": f"{m['merchant']} in {m['category']}",
            "estMonthlySave": round(est, 2),
            "evidence": tx_ids[:10],
            "explanation": "10% reduction scenario on discretionary merchants"
        })

    # Recurring forecast: use recurring_series if present
    rows_rec = conn.execute(
        """
        SELECT name AS merchant, next_date AS nextDate, amount_mean AS expectedAmount,
               CASE WHEN price_hike THEN 0.85 ELSE 0.7 END AS confidence
        FROM recurring_series
        WHERE next_date IS NOT NULL
        ORDER BY next_date
        LIMIT 50
        """,
    ).fetchall()
    cols_rec = [c[0] for c in conn.description]
    recurring_forecast = [dict(zip(cols_rec, r)) for r in rows_rec]

    result = {
        "budgetRisk": budget_risk,
        "savingsOps": savings_ops,
        "recurringForecast": recurring_forecast,
    }
    _cache_set(key, result)
    return result


@router.get("/ai/trends")
async def get_trend_analysis(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    account_id: Optional[str] = Query(None)
):
    """Get AI-powered trend analysis"""
    from ...ai_analytics import get_ai_analytics_engine
    analytics_engine = get_ai_analytics_engine()
    
    trends = analytics_engine.analyze_trends(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id
    )
    
    return {
        "trends": [
            {
                "metric_name": trend.metric_name,
                "current_value": round(trend.current_value, 2),
                "previous_value": round(trend.previous_value, 2),
                "change_amount": round(trend.change_amount, 2),
                "change_percentage": round(trend.change_percentage, 2),
                "trend_direction": trend.trend_direction.value,
                "confidence": round(trend.confidence, 3),
                "is_significant": trend.is_significant,
                "insights": trend.insights
            }
            for trend in trends
        ],
        "analysis_summary": {
            "significant_trends": len([t for t in trends if t.is_significant]),
            "total_metrics": len(trends)
        }
    }


@router.get("/ai/anomalies")
async def get_anomaly_detection(
    days_lookback: int = Query(30, ge=7, le=90),
    account_id: Optional[str] = Query(None)
):
    """Get AI-powered anomaly detection"""
    from ...ai_analytics import get_ai_analytics_engine
    analytics_engine = get_ai_analytics_engine()
    
    anomalies = analytics_engine.detect_anomalies(
        days_lookback=days_lookback,
        account_id=account_id
    )
    
    return {
        "anomalies": [
            {
                "transaction_id": anomaly.transaction_id,
                "anomaly_type": anomaly.anomaly_type,
                "severity": anomaly.severity,
                "description": anomaly.description,
                "expected_range": {
                    "lower": round(anomaly.expected_range[0], 2),
                    "upper": round(anomaly.expected_range[1], 2)
                },
                "actual_value": round(anomaly.actual_value, 2),
                "confidence": round(anomaly.confidence, 3)
            }
            for anomaly in anomalies
        ],
        "summary": {
            "total_anomalies": len(anomalies),
            "high_severity": len([a for a in anomalies if a.severity == "high"]),
            "medium_severity": len([a for a in anomalies if a.severity == "medium"]),
            "lookback_days": days_lookback
        }
    }


@router.get("/ai/forecasts/spending")
async def get_spending_forecast(
    category: Optional[str] = Query(None),
    forecast_months: int = Query(6, ge=1, le=24),
    account_id: Optional[str] = Query(None)
):
    """Get AI-powered spending forecast"""
    from ...ai_forecasting import get_ai_forecasting_engine
    forecasting_engine = get_ai_forecasting_engine()
    
    forecast = forecasting_engine.forecast_spending(
        category=category,
        forecast_months=forecast_months,
        account_id=account_id
    )
    
    return {
        "forecast": {
            "forecast_type": forecast.forecast_type.value,
            "period_start": forecast.period_start,
            "period_end": forecast.period_end,
            "total_predicted": round(forecast.total_predicted, 2),
            "accuracy_score": round(forecast.accuracy_score, 3),
            "methodology": forecast.methodology,
            "key_assumptions": forecast.key_assumptions,
            "risk_factors": forecast.risk_factors,
            "forecast_points": [
                {
                    "date": point.date,
                    "predicted_value": round(point.predicted_value, 2),
                    "confidence_interval_lower": round(point.confidence_interval_lower, 2),
                    "confidence_interval_upper": round(point.confidence_interval_upper, 2),
                    "confidence": point.confidence.value,
                    "factors": point.factors
                }
                for point in forecast.forecast_points
            ]
        },
        "parameters": {
            "category": category,
            "forecast_months": forecast_months
        }
    }


@router.get("/ai/forecasts/income")
async def get_income_forecast(
    forecast_months: int = Query(6, ge=1, le=24),
    account_id: Optional[str] = Query(None)
):
    """Get AI-powered income forecast"""
    from ...ai_forecasting import get_ai_forecasting_engine
    forecasting_engine = get_ai_forecasting_engine()
    
    forecast = forecasting_engine.forecast_income(
        forecast_months=forecast_months,
        account_id=account_id
    )
    
    return {
        "forecast": {
            "forecast_type": forecast.forecast_type.value,
            "period_start": forecast.period_start,
            "period_end": forecast.period_end,
            "total_predicted": round(forecast.total_predicted, 2),
            "accuracy_score": round(forecast.accuracy_score, 3),
            "methodology": forecast.methodology,
            "key_assumptions": forecast.key_assumptions,
            "risk_factors": forecast.risk_factors,
            "forecast_points": [
                {
                    "date": point.date,
                    "predicted_value": round(point.predicted_value, 2),
                    "confidence_interval_lower": round(point.confidence_interval_lower, 2),
                    "confidence_interval_upper": round(point.confidence_interval_upper, 2),
                    "confidence": point.confidence.value,
                    "factors": point.factors
                }
                for point in forecast.forecast_points
            ]
        },
        "parameters": {
            "forecast_months": forecast_months
        }
    }


@router.get("/ai/forecasts/cashflow")
async def get_cashflow_projection(
    forecast_months: int = Query(12, ge=3, le=24),
    account_id: Optional[str] = Query(None)
):
    """Get AI-powered cash flow projection with scenarios"""
    from ...ai_forecasting import get_ai_forecasting_engine
    forecasting_engine = get_ai_forecasting_engine()
    
    projection = forecasting_engine.project_cashflow(
        forecast_months=forecast_months,
        account_id=account_id
    )
    
    def format_scenario(scenario):
        return [
            {
                "date": point.date,
                "predicted_value": round(point.predicted_value, 2),
                "confidence_interval_lower": round(point.confidence_interval_lower, 2),
                "confidence_interval_upper": round(point.confidence_interval_upper, 2),
                "confidence": point.confidence.value,
                "factors": point.factors
            }
            for point in scenario
        ]
    
    return {
        "projection": {
            "base_scenario": format_scenario(projection.base_scenario),
            "optimistic_scenario": format_scenario(projection.optimistic_scenario),
            "pessimistic_scenario": format_scenario(projection.pessimistic_scenario),
            "break_even_analysis": projection.break_even_analysis,
            "runway_months": projection.runway_months,
            "recommendations": projection.recommendations
        },
        "parameters": {
            "forecast_months": forecast_months
        }
    }


@router.get("/ai/predictions/category/{category_name}")
async def get_category_spending_prediction(
    category_name: str,
    account_id: Optional[str] = Query(None)
):
    """Get AI-powered spending prediction for a specific category"""
    from ...ai_forecasting import get_ai_forecasting_engine
    forecasting_engine = get_ai_forecasting_engine()
    
    prediction = forecasting_engine.predict_category_spending(
        category=category_name,
        account_id=account_id
    )
    
    return {
        "prediction": {
            "category": prediction.category,
            "next_month_prediction": round(prediction.next_month_prediction, 2),
            "next_quarter_prediction": round(prediction.next_quarter_prediction, 2),
            "confidence": prediction.confidence.value,
            "trend_factor": round(prediction.trend_factor, 4),
            "seasonality_factor": round(prediction.seasonality_factor, 3),
            "volatility_score": round(prediction.volatility_score, 3),
            "key_drivers": prediction.key_drivers
        }
    }


class InsightRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    account_id: Optional[str] = None
    include_forecasts: bool = True
    include_anomalies: bool = True


@router.post("/ai/comprehensive-insights")
async def get_comprehensive_insights(request: InsightRequest):
    """Get comprehensive AI-powered financial insights"""
    from ...ai_analytics import get_ai_analytics_engine
    from ...ai_forecasting import get_ai_forecasting_engine
    analytics_engine = get_ai_analytics_engine()
    forecasting_engine = get_ai_forecasting_engine()
    
    # Gather all insights
    insights = {}
    
    # Spending patterns
    patterns = analytics_engine.analyze_spending_patterns(
        start_date=request.start_date,
        end_date=request.end_date,
        account_id=request.account_id
    )
    insights["spending_patterns"] = {
        "total_patterns": len(patterns),
        "top_patterns": [
            {
                "category": p.category,
                "pattern_type": p.pattern_type,
                "confidence": round(p.confidence, 3),
                "insights": p.insights[:2]  # Top 2 insights
            }
            for p in patterns[:5]  # Top 5 patterns
        ]
    }
    
    # Trend analysis
    trends = analytics_engine.analyze_trends(
        start_date=request.start_date,
        end_date=request.end_date,
        account_id=request.account_id
    )
    significant_trends = [t for t in trends if t.is_significant]
    insights["trends"] = {
        "significant_trends_count": len(significant_trends),
        "key_trends": [
            {
                "metric": t.metric_name,
                "change_percentage": round(t.change_percentage, 1),
                "direction": t.trend_direction.value,
                "insights": t.insights
            }
            for t in significant_trends[:3]  # Top 3 significant trends
        ]
    }
    
    # Anomalies
    if request.include_anomalies:
        anomalies = analytics_engine.detect_anomalies(account_id=request.account_id)
        high_severity_anomalies = [a for a in anomalies if a.severity == "high"]
        insights["anomalies"] = {
            "total_anomalies": len(anomalies),
            "high_severity_count": len(high_severity_anomalies),
            "recent_anomalies": [
                {
                    "transaction_id": a.transaction_id,
                    "description": a.description,
                    "severity": a.severity,
                    "actual_value": round(a.actual_value, 2)
                }
                for a in high_severity_anomalies[:3]  # Top 3 high severity
            ]
        }
    
    # Forecasts
    if request.include_forecasts:
        spending_forecast = forecasting_engine.forecast_spending(
            forecast_months=3, account_id=request.account_id
        )
        income_forecast = forecasting_engine.forecast_income(
            forecast_months=3, account_id=request.account_id
        )
        
        next_month_spending = spending_forecast.forecast_points[0].predicted_value if spending_forecast.forecast_points else 0
        next_month_income = income_forecast.forecast_points[0].predicted_value if income_forecast.forecast_points else 0
        
        insights["forecasts"] = {
            "next_month_spending": round(next_month_spending, 2),
            "next_month_income": round(next_month_income, 2),
            "next_month_net": round(next_month_income - next_month_spending, 2),
            "spending_accuracy": round(spending_forecast.accuracy_score, 3),
            "income_accuracy": round(income_forecast.accuracy_score, 3)
        }
    
    # Generate summary recommendations
    recommendations = []
    
    if insights.get("trends", {}).get("significant_trends_count", 0) > 0:
        recommendations.append("Review significant spending trend changes")
    
    if insights.get("anomalies", {}).get("high_severity_count", 0) > 0:
        recommendations.append("Investigate high-severity spending anomalies")
    
    if request.include_forecasts:
        net_forecast = insights.get("forecasts", {}).get("next_month_net", 0)
        if net_forecast < 0:
            recommendations.append("Consider reducing expenses for positive cash flow")
        elif net_forecast > 1000:
            recommendations.append("Opportunity to increase savings or investments")
    
    insights["recommendations"] = recommendations
    insights["generated_at"] = date.today()
    
    return insights


@router.get("/ai/dashboard-summary")
async def get_ai_dashboard_summary(
    account_id: Optional[str] = Query(None)
):
    """Get AI-enhanced dashboard summary for quick overview"""
    from ...ai_analytics import get_ai_analytics_engine
    from ...ai_forecasting import get_ai_forecasting_engine
    analytics_engine = get_ai_analytics_engine()
    forecasting_engine = get_ai_forecasting_engine()
    
    # Quick analytics for dashboard
    patterns = analytics_engine.analyze_spending_patterns(account_id=account_id)
    trends = analytics_engine.analyze_trends(account_id=account_id)
    anomalies = analytics_engine.detect_anomalies(days_lookback=7, account_id=account_id)
    
    # Next month prediction
    spending_forecast = forecasting_engine.forecast_spending(
        forecast_months=1, account_id=account_id
    )
    
    return {
        "ai_insights": {
            "patterns_detected": len(patterns),
            "significant_trends": len([t for t in trends if t.is_significant]),
            "recent_anomalies": len(anomalies),
            "next_month_spending_prediction": round(
                spending_forecast.forecast_points[0].predicted_value, 2
            ) if spending_forecast.forecast_points else 0,
            "prediction_confidence": spending_forecast.accuracy_score
        },
        "top_insights": [
            f"Found {len(patterns)} spending patterns across categories",
            f"Detected {len([t for t in trends if t.is_significant])} significant trends",
            f"Identified {len(anomalies)} potential anomalies in recent transactions"
        ],
        "action_items": [
            "Review spending patterns for optimization opportunities",
            "Monitor significant trend changes",
            "Investigate any detected anomalies"
        ]
    }
@router.get("/dashboard")
async def dashboard(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    account_id: Optional[str] = Query(None),
    merchants_limit: int = Query(10, ge=1, le=1000),
    include_ai: bool = Query(False),
):
    """Aggregated dashboard payload with comparisons and KPIs.

    - Computes cashflow, monthly, top merchants/categories for the period.
    - Provides previous-period comparisons for cashflow.
    - Optionally includes AI insights/trends summary.
    """
    conn = get_conn()

    # Resolve period; default to last 90 days if not provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=89)

    # Previous period of equal length
    period_days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)

    def _cashflow(sd: date, ed: date):
        where = [
            "NOT (mt.decided_at IS NOT NULL AND COALESCE(mt.include_in_analytics, FALSE) = FALSE)",
            "(t.is_adjustment IS FALSE OR t.is_adjustment IS NULL)",
        ]
        params: list = []
        where.append("t.posted_at >= ?"); params.append(sd)
        where.append("t.posted_at <= ?"); params.append(ed)
        if account_id:
            where.append("t.account_id = ?"); params.append(account_id)
        wh = " WHERE " + " AND ".join(where)
        row = conn.execute(
            f"""
            SELECT 
                SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS income,
                SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS debits,
                SUM(t.amount) AS net
            FROM [transaction] t
            LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
            {wh}
            """,
            params,
        ).fetchone()
        return {
            "income": float(row[0] or 0.0),
            "debits": float(row[1] or 0.0),
            "net": float(row[2] or 0.0),
        }

    cur_cf = _cashflow(start_date, end_date)
    prev_cf = _cashflow(prev_start, prev_end)

    def _delta(a: float, b: float) -> dict:
        d = a - b
        pct = (d / b * 100.0) if b else None
        return {"current": a, "previous": b, "delta": d, "delta_pct": pct}

    savings_rate = (cur_cf["net"] / cur_cf["income"] * 100.0) if cur_cf["income"] else 0.0

    # Monthly series for the window
    _params = [start_date, end_date]
    _where_acc = ""
    if account_id:
        _where_acc = " AND t.account_id = ?"
        _params.append(account_id)
    rows = conn.execute(
        """
        SELECT date_trunc('month', t.posted_at) AS month,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS income,
               SUM(t.amount) AS net
        FROM [transaction] t
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        WHERE t.posted_at >= ? AND t.posted_at <= ?
        """ + _where_acc + """
        GROUP BY 1
        ORDER BY 1
        """,
        _params,
    ).fetchall()
    cols = [c[0] for c in conn.description]
    monthly = [dict(zip(cols, r)) for r in rows]

    # Top merchants during period
    _params = [start_date, end_date, merchants_limit]
    _where_acc = ""
    if account_id:
        _where_acc = " AND t.account_id = ?"
        _params.insert(2, account_id)  # before limit
    rows = conn.execute(
        """
        SELECT t.description_norm as merchant,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               COUNT(*) as count
        FROM [transaction] t
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        WHERE t.posted_at >= ? AND t.posted_at <= ?
        """ + _where_acc + """
        GROUP BY 1
        ORDER BY spend DESC
        LIMIT ?
        """,
        _params,
    ).fetchall()
    cols = [c[0] for c in conn.description]
    merchants = [dict(zip(cols, r)) for r in rows]

    # Top categories during period
    _params = [start_date, end_date]
    _where_acc = ""
    if account_id:
        _where_acc = " AND t.account_id = ?"
        _params.append(account_id)
    rows = conn.execute(
        """
        SELECT c.id as category_id,
               c.name as category_name,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               COUNT(*) as count
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        WHERE t.posted_at >= ? AND t.posted_at <= ?
        """ + _where_acc + """
        GROUP BY 1,2
        ORDER BY spend DESC NULLS LAST
        LIMIT 12
        """,
        _params,
    ).fetchall()
    cols = [c[0] for c in conn.description]
    top_categories = [dict(zip(cols, r)) for r in rows]

    result = {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "previous_start": prev_start,
            "previous_end": prev_end,
        },
        # Simple summary block for tests/UI expecting a top-level summary
        "summary": {
            "income": cur_cf["income"],
            "spending": cur_cf["debits"],
            "net": cur_cf["net"],
            "savings_rate_pct": round(savings_rate, 2),
        },
        "cashflow": {
            "income": _delta(cur_cf["income"], prev_cf["income"]),
            "spending": _delta(cur_cf["debits"], prev_cf["debits"]),
            "net": _delta(cur_cf["net"], prev_cf["net"]),
            "savings_rate_pct": round(savings_rate, 2),
        },
        "monthly": monthly,
        "merchants": merchants,
        "top_categories": top_categories,
    }

    if include_ai:
        from ...ai_analytics import get_ai_analytics_engine
        analytics_engine = get_ai_analytics_engine()
        try:
            patterns = analytics_engine.analyze_spending_patterns(start_date=start_date, end_date=end_date, account_id=account_id)
            trends = analytics_engine.analyze_trends(start_date=start_date, end_date=end_date, account_id=account_id)
            insights = {
                "patterns": [
                    {
                        "category": p.category,
                        "pattern_type": p.pattern_type,
                        "confidence": round(p.confidence, 3),
                        "key_merchants": p.key_merchants,
                    }
                    for p in patterns[:5]
                ],
                "trends": [
                    {
                        "metric_name": t.metric_name,
                        "change_percentage": round(t.change_percentage, 2),
                        "trend_direction": t.trend_direction.value,
                        "confidence": round(t.confidence, 3),
                    }
                    for t in trends[:5]
                ],
            }
            result["ai"] = insights
        except Exception:
            result["ai"] = {"error": "ai_unavailable"}

    return result


# Phase 1 Predictive Analytics Endpoints

@router.get("/predictive/patterns")
async def get_predictive_patterns(
    account_id: str = Query("default"),
    force_refresh: bool = Query(False)
):
    """Get enhanced spending patterns with prediction capabilities"""
    try:
        from ...analytics.predictive_engine import get_predictive_engine
        engine = get_predictive_engine()
        patterns = engine.analyze_spending_patterns(account_id, force_refresh)
        return {
            "patterns": [
                {
                    "category_id": p.category_id,
                    "category_name": p.category_name,
                    "monthly_average": round(p.monthly_avg, 2),
                    "trend_factor": round(p.trend_factor, 4),
                    "seasonal_factors": {k: round(v, 3) for k, v in p.seasonal_factors.items()},
                    "volatility": round(p.volatility, 3),
                    "confidence": round(p.confidence, 3),
                    "pattern_type": p.pattern_type,
                    "predictability": "High" if p.confidence > 0.7 else "Medium" if p.confidence > 0.4 else "Low"
                }
                for p in patterns
            ],
            "total_patterns": len(patterns),
            "analysis_date": date.today().isoformat()
        }
    except Exception:
        return {
            "patterns": [],
            "total_patterns": 0,
            "analysis_date": date.today().isoformat(),
            "error": "Predictive patterns unavailable"
        }


@router.get("/predictive/cashflow-forecast")
async def get_cashflow_forecast(
    account_id: str = Query("default"),
    months: int = Query(6, ge=1, le=12)
):
    """Get predictive cash flow forecast"""
    try:
        from ...analytics.predictive_engine import get_predictive_engine
        engine = get_predictive_engine()
        predictions = engine.forecast_cash_flow(account_id, months)
        return {
            "forecast": [
                {
                    "month": p.target_month,
                    "predicted_income": round(p.predicted_income, 2),
                    "predicted_spending": round(p.predicted_spending, 2),
                    "net_cash_flow": round(p.net_cash_flow, 2),
                    "spending_by_category": {k: round(v, 2) for k, v in p.spending_breakdown.items()},
                    "confidence": round(p.confidence, 3),
                    "methodology": p.methodology,
                    "assumptions": p.assumptions
                }
                for p in predictions
            ],
            "forecast_horizon_months": months,
            "generated_at": datetime.now().isoformat()
        }
    except Exception:
        return {
            "forecast": [],
            "forecast_horizon_months": months,
            "generated_at": datetime.now().isoformat(),
            "error": "Cashflow forecast unavailable"
        }


@router.get("/predictive/insights")
async def get_smart_insights(
    account_id: str = Query("default"),
    include_read: bool = Query(False)
):
    """Get smart financial insights and alerts"""
    try:
        engine = get_predictive_engine()
        insights = engine.generate_smart_insights(account_id)
        
        return {
            "insights": [
                {
                    "type": i.insight_type,
                    "priority": i.priority,
                    "title": i.title,
                    "message": i.message,
                    "amount": round(i.amount, 2) if i.amount else None,
                    "category_id": i.category_id,
                    "transaction_id": i.transaction_id,
                    "action_text": i.action_text,
                    "valid_until": i.valid_until.isoformat() if i.valid_until else None,
                    "severity": "high" if i.priority >= 8 else "medium" if i.priority >= 6 else "low"
                }
                for i in insights
            ],
            "total_insights": len(insights),
            "high_priority_count": len([i for i in insights if i.priority >= 8]),
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        # Return empty insights if tables don't exist or other errors
        return {
            "insights": [],
            "total_insights": 0,
            "high_priority_count": 0,
            "generated_at": datetime.now().isoformat(),
            "error": "Predictive analytics not available yet - need more transaction data"
        }
