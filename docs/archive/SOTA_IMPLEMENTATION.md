# LedgerLoop SOTA Implementation

## YOUR MISSION

Transform LedgerLoop into a state-of-the-art AI-powered finance platform. Work autonomously - NO asking for approval. Make smart decisions. Test everything. Ship production-ready code.

**Critical Insight**: Most AI features ALREADY EXIST in the codebase but aren't wired up:
- `ai_analytics.py` - spending patterns, trends, anomalies (EXISTS, needs API exposure)
- `ai_insights.py` - personalized insights, health score (EXISTS, needs API exposure)  
- `ai_forecasting.py` - cash flow projection (EXISTS, needs API exposure)

Your job is to CONNECT what exists, FIX what's broken, and ADD minimal new code.

---

## PHASE 0: RECONNAISSANCE (5 min)

```bash
# Verify services running
curl -s http://localhost:8000/api/health | jq .

# Check transaction count
curl -s "http://localhost:8000/api/transactions?limit=1" | jq '.meta.total // .total'

# Check existing AI endpoints
curl -s http://localhost:8000/api/ai/stats | jq .

# List backend files to understand structure
ls apps/backend/src/ledgerloop/*.py | head -20
ls apps/backend/src/ledgerloop/api/routes/*.py
```

Read these key files to understand current state:
- `apps/backend/src/ledgerloop/recurring.py` (find the transfer bug)
- `apps/backend/src/ledgerloop/ai_analytics.py` (understand what's available)
- `apps/backend/src/ledgerloop/ai_insights.py` (understand what's available)
- `apps/backend/src/ledgerloop/api/routes/analytics.py` (see what's already exposed)

---

## PHASE 1: FIX CRITICAL BUG (15 min)

### 1.1 The Recurring Detection Transfer Leak

**THE BUG**: Recurring detection only excludes CONFIRMED transfers. PENDING transfers leak through causing false recurring detection.

**Location**: `apps/backend/src/ledgerloop/recurring.py`

Find the SQL query that filters transfers. It likely has:
```sql
WHERE mt.decided_at IS NOT NULL  -- BUG: Only excludes confirmed!
```

**FIX IT** to exclude ALL transfers (pending AND confirmed):
```sql
WHERE t.id NOT IN (
    SELECT tx1_id FROM matched_transfers
    UNION
    SELECT tx2_id FROM matched_transfers
)
```

**Test the fix**:
```bash
# Before: Note count
curl -s http://localhost:8000/api/recurring | jq 'length'

# Restart backend
docker-compose restart ledgerloop-backend
sleep 10

# After: Should be same or fewer (no transfer leaks)
curl -s http://localhost:8000/api/recurring | jq 'length'
```

### 1.2 Verify AI Provider Works

```bash
# Check current provider setting
curl -s http://localhost:8000/api/settings | jq '.ai_provider'

# If it's "local", update to "auto" for better AI
# Find settings endpoint and update, or edit config directly
```

---

## PHASE 2: EXPOSE EXISTING AI MODULES (45 min)

**These modules EXIST but have NO API endpoints. Create them.**

### 2.1 Create Intelligence Router

**Create file**: `apps/backend/src/ledgerloop/api/routes/intelligence.py`

```python
"""
Intelligence Feed - Aggregates all AI insights
"""
from fastapi import APIRouter
from typing import Optional
from datetime import date, timedelta

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/feed")
async def get_intelligence_feed(limit: int = 10, account_id: Optional[str] = None):
    """
    Aggregated AI intelligence feed combining:
    - Anomalies from ai_analytics
    - Insights from ai_insights  
    - Predictions from ai_forecasting
    - Recurring alerts
    - Transfer suggestions
    """
    from ...ai_analytics import get_ai_analytics_engine
    from ...ai_insights import get_ai_insights_engine
    
    feed_items = []
    
    # Get anomalies
    try:
        analytics = get_ai_analytics_engine()
        anomalies = analytics.detect_anomalies(days_lookback=30, account_id=account_id)
        for a in anomalies[:3]:
            feed_items.append({
                "type": "anomaly",
                "severity": a.severity,
                "title": f"Unusual {a.anomaly_type.replace('_', ' ')}",
                "description": a.description,
                "transaction_id": a.transaction_id,
                "confidence": a.confidence
            })
    except Exception as e:
        pass  # Don't fail if analytics unavailable
    
    # Get personalized insights
    try:
        insights_engine = get_ai_insights_engine()
        insights = insights_engine.generate_personalized_insights(account_id=account_id, insight_limit=5)
        for i in insights:
            feed_items.append({
                "type": "insight",
                "severity": i.priority.value,
                "title": i.title,
                "description": i.description,
                "recommendations": i.recommendations,
                "category": i.category.value,
                "impact_score": i.impact_score
            })
    except Exception as e:
        pass
    
    # Sort by severity/impact
    severity_order = {"urgent": 0, "high": 1, "critical": 1, "medium": 2, "low": 3, "info": 4}
    feed_items.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 5))
    
    return {"items": feed_items[:limit], "total": len(feed_items)}


@router.get("/health-score")
async def get_health_score(account_id: Optional[str] = None):
    """Financial health score with dimension breakdown"""
    from ...ai_insights import get_ai_insights_engine
    
    engine = get_ai_insights_engine()
    report = engine.assess_financial_health(account_id=account_id)
    
    return {
        "overall_score": report.overall_score,
        "health_grade": report.health_grade.value,
        "dimensions": {
            "spending_health": report.spending_health,
            "savings_health": report.savings_health,
            "budgeting_health": report.budgeting_health,
            "trend_health": report.trend_health
        },
        "strengths": report.key_strengths,
        "improvements": report.improvement_areas,
        "recommendations": report.recommendations
    }


@router.get("/spending-behavior")
async def get_spending_behavior(account_id: Optional[str] = None):
    """Spending behavior profile and persona"""
    from ...ai_insights import get_ai_insights_engine
    
    engine = get_ai_insights_engine()
    profile = engine.analyze_spending_behavior(account_id=account_id)
    
    return {
        "persona": profile.persona.value,
        "avg_monthly_spending": profile.avg_monthly_spending,
        "spending_volatility": profile.spending_volatility,
        "top_categories": [{"name": c[0], "amount": c[1]} for c in profile.top_categories],
        "habits": profile.spending_habits,
        "risk_factors": profile.risk_factors,
        "insights": profile.behavioral_insights
    }


@router.get("/predictions")
async def get_predictions(months: int = 3, account_id: Optional[str] = None):
    """Cash flow and spending predictions"""
    from ...ai_forecasting import get_ai_forecasting_engine
    
    engine = get_ai_forecasting_engine()
    projection = engine.project_cashflow(forecast_months=months, account_id=account_id)
    
    return {
        "base_scenario": [
            {
                "month": p.prediction_month.isoformat() if hasattr(p.prediction_month, 'isoformat') else str(p.prediction_month),
                "predicted_value": p.predicted_value,
                "confidence_lower": p.confidence_lower,
                "confidence_upper": p.confidence_upper
            }
            for p in projection.base_scenario
        ],
        "optimistic_scenario": [
            {
                "month": p.prediction_month.isoformat() if hasattr(p.prediction_month, 'isoformat') else str(p.prediction_month),
                "predicted_value": p.predicted_value
            }
            for p in projection.optimistic_scenario
        ],
        "pessimistic_scenario": [
            {
                "month": p.prediction_month.isoformat() if hasattr(p.prediction_month, 'isoformat') else str(p.prediction_month),
                "predicted_value": p.predicted_value
            }
            for p in projection.pessimistic_scenario
        ]
    }
```

### 2.2 Enhance Analytics Router

**Edit file**: `apps/backend/src/ledgerloop/api/routes/analytics.py`

Add these endpoints if they don't exist:

```python
@router.get("/ai/spending-patterns")
async def get_spending_patterns(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    account_id: Optional[str] = None
):
    """AI-analyzed spending patterns"""
    from ...ai_analytics import get_ai_analytics_engine
    
    engine = get_ai_analytics_engine()
    patterns = engine.analyze_spending_patterns(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id
    )
    
    return [
        {
            "category": p.category,
            "pattern_type": p.pattern_type,
            "frequency": p.frequency,
            "average_amount": p.average_amount,
            "confidence": p.confidence,
            "trend": p.trend_direction.value,
            "seasonal": p.seasonality_detected,
            "top_merchants": p.key_merchants,
            "insights": p.insights
        }
        for p in patterns
    ]


@router.get("/ai/trends")
async def get_trends(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    account_id: Optional[str] = None
):
    """AI-analyzed financial trends"""
    from ...ai_analytics import get_ai_analytics_engine
    
    engine = get_ai_analytics_engine()
    trends = engine.analyze_trends(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id
    )
    
    return [
        {
            "metric": t.metric_name,
            "current_value": t.current_value,
            "previous_value": t.previous_value,
            "change_amount": t.change_amount,
            "change_percent": t.change_percentage,
            "direction": t.trend_direction.value,
            "confidence": t.confidence,
            "significant": t.is_significant,
            "insights": t.insights
        }
        for t in trends
    ]


@router.get("/ai/anomalies")
async def get_anomalies(
    days: int = 30,
    account_id: Optional[str] = None
):
    """AI-detected spending anomalies"""
    from ...ai_analytics import get_ai_analytics_engine
    
    engine = get_ai_analytics_engine()
    anomalies = engine.detect_anomalies(
        days_lookback=days,
        account_id=account_id
    )
    
    return [
        {
            "transaction_id": a.transaction_id,
            "type": a.anomaly_type,
            "severity": a.severity,
            "description": a.description,
            "expected_range": list(a.expected_range),
            "actual_value": a.actual_value,
            "confidence": a.confidence
        }
        for a in anomalies
    ]


@router.get("/ai/dashboard")
async def get_ai_dashboard(account_id: Optional[str] = None):
    """Unified AI dashboard data - single endpoint for all AI insights"""
    from ...ai_analytics import get_ai_analytics_engine
    from ...ai_insights import get_ai_insights_engine
    from ...ai_forecasting import get_ai_forecasting_engine
    
    result = {}
    
    # Health score
    try:
        insights_engine = get_ai_insights_engine()
        health = insights_engine.assess_financial_health(account_id=account_id)
        result["health_score"] = {
            "overall": health.overall_score,
            "grade": health.health_grade.value,
            "spending": health.spending_health,
            "savings": health.savings_health,
            "budgeting": health.budgeting_health,
            "trends": health.trend_health
        }
    except Exception:
        result["health_score"] = None
    
    # Top patterns
    try:
        analytics = get_ai_analytics_engine()
        patterns = analytics.analyze_spending_patterns(account_id=account_id)
        result["top_patterns"] = [
            {"category": p.category, "type": p.pattern_type, "amount": p.average_amount}
            for p in patterns[:5]
        ]
    except Exception:
        result["top_patterns"] = []
    
    # Recent anomalies
    try:
        anomalies = analytics.detect_anomalies(days_lookback=14, account_id=account_id)
        result["recent_anomalies"] = len([a for a in anomalies if a.severity in ("high", "critical")])
    except Exception:
        result["recent_anomalies"] = 0
    
    # Cash flow prediction
    try:
        forecast = get_ai_forecasting_engine()
        projection = forecast.project_cashflow(forecast_months=1, account_id=account_id)
        if projection.base_scenario:
            result["next_month_prediction"] = projection.base_scenario[0].predicted_value
        else:
            result["next_month_prediction"] = None
    except Exception:
        result["next_month_prediction"] = None
    
    return result
```

### 2.3 Register Intelligence Router

**Edit file**: `apps/backend/src/ledgerloop/api/main.py`

Add:
```python
from .routes.intelligence import router as intelligence_router
app.include_router(intelligence_router)
```

### 2.4 Test New Endpoints

```bash
docker-compose restart ledgerloop-backend
sleep 10

# Test intelligence feed
curl -s http://localhost:8000/api/intelligence/feed | jq '.items[:2]'

# Test health score
curl -s http://localhost:8000/api/intelligence/health-score | jq .

# Test spending behavior
curl -s http://localhost:8000/api/intelligence/spending-behavior | jq .

# Test predictions
curl -s http://localhost:8000/api/intelligence/predictions | jq '.base_scenario[:2]'

# Test AI dashboard
curl -s http://localhost:8000/api/analytics/ai/dashboard | jq .

# Test patterns
curl -s http://localhost:8000/api/analytics/ai/spending-patterns | jq '.[:2]'

# Test anomalies
curl -s http://localhost:8000/api/analytics/ai/anomalies | jq '.[:2]'
```

---

## PHASE 3: ADD AI-ENHANCED DETECTION (30 min)

### 3.1 AI-Enhanced Recurring Detection

**Edit file**: `apps/backend/src/ledgerloop/api/routes/recurring.py`

Add endpoint:
```python
@router.post("/ai-detect")
async def ai_detect_recurring():
    """
    AI-enhanced recurring detection:
    - Uses LLM to normalize merchant names
    - Detects patterns with fewer occurrences
    - Provides confidence scores
    """
    from ...ai import get_ai_service
    from ...db import get_conn
    
    conn = get_conn()
    ai_service = get_ai_service()
    
    # Get transactions not in any recurring series or transfers
    transactions = conn.execute("""
        SELECT t.id, t.description_norm, t.amount, t.posted_at, t.ai_merchant_name
        FROM transaction t
        LEFT JOIN recurring_member rm ON t.id = rm.tx_id
        WHERE rm.tx_id IS NULL
        AND t.id NOT IN (
            SELECT tx1_id FROM matched_transfers
            UNION
            SELECT tx2_id FROM matched_transfers
        )
        AND t.amount < 0
        ORDER BY t.posted_at DESC
        LIMIT 500
    """).fetchall()
    
    # Group by normalized merchant name
    from collections import defaultdict
    merchant_groups = defaultdict(list)
    
    for tx in transactions:
        # Use AI merchant name if available, otherwise normalize description
        merchant = tx[4] or tx[1][:30]
        merchant_groups[merchant.lower()].append({
            "id": tx[0],
            "description": tx[1],
            "amount": float(tx[2]),
            "date": str(tx[3]),
            "merchant": merchant
        })
    
    # Find potential recurring patterns (2+ occurrences with similar amounts)
    suggestions = []
    for merchant, txs in merchant_groups.items():
        if len(txs) < 2:
            continue
        
        # Check amount consistency
        amounts = [t["amount"] for t in txs]
        avg_amount = sum(amounts) / len(amounts)
        amount_variance = max(amounts) - min(amounts)
        
        # If amounts are within 20% of each other, likely recurring
        if amount_variance / abs(avg_amount) < 0.2:
            suggestions.append({
                "merchant": txs[0]["merchant"],
                "occurrence_count": len(txs),
                "average_amount": round(avg_amount, 2),
                "amount_variance": round(amount_variance, 2),
                "confidence": min(0.95, 0.5 + (len(txs) * 0.1)),
                "transactions": [t["id"] for t in txs[:10]],
                "sample_dates": [t["date"] for t in txs[:5]]
            })
    
    # Sort by confidence
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)
    
    return {
        "suggestions": suggestions[:20],
        "total_analyzed": len(transactions),
        "patterns_found": len(suggestions)
    }


@router.get("/{series_id}/insights")
async def get_series_insights(series_id: str):
    """Get AI insights for a recurring series"""
    from ...db import get_conn
    
    conn = get_conn()
    
    # Get series info
    series = conn.execute("""
        SELECT rs.id, rs.name, rs.merchant, rs.cadence, rs.avg_amount,
               COUNT(rm.tx_id) as occurrence_count,
               MIN(t.posted_at) as first_seen,
               MAX(t.posted_at) as last_seen
        FROM recurring_series rs
        LEFT JOIN recurring_member rm ON rs.id = rm.series_id
        LEFT JOIN transaction t ON rm.tx_id = t.id
        WHERE rs.id = ?
        GROUP BY rs.id
    """, [series_id]).fetchone()
    
    if not series:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Series not found")
    
    # Get price history
    prices = conn.execute("""
        SELECT t.amount, t.posted_at
        FROM recurring_member rm
        JOIN transaction t ON rm.tx_id = t.id
        WHERE rm.series_id = ?
        ORDER BY t.posted_at
    """, [series_id]).fetchall()
    
    price_history = [{"amount": abs(float(p[0])), "date": str(p[1])} for p in prices]
    
    # Calculate annual cost
    avg_amount = abs(float(series[4])) if series[4] else 0
    cadence = series[3]
    annual_multiplier = {"weekly": 52, "biweekly": 26, "monthly": 12, "quarterly": 4, "yearly": 1}.get(cadence, 12)
    annual_cost = avg_amount * annual_multiplier
    
    # Detect price changes
    price_changes = []
    if len(price_history) > 1:
        for i in range(1, len(price_history)):
            if abs(price_history[i]["amount"] - price_history[i-1]["amount"]) > 0.01:
                change_pct = ((price_history[i]["amount"] - price_history[i-1]["amount"]) / price_history[i-1]["amount"]) * 100
                price_changes.append({
                    "date": price_history[i]["date"],
                    "old_amount": price_history[i-1]["amount"],
                    "new_amount": price_history[i]["amount"],
                    "change_percent": round(change_pct, 1)
                })
    
    return {
        "series_id": series_id,
        "name": series[1],
        "merchant": series[2],
        "cadence": cadence,
        "average_amount": avg_amount,
        "annual_cost": round(annual_cost, 2),
        "occurrence_count": series[5],
        "first_seen": str(series[6]),
        "last_seen": str(series[7]),
        "price_history": price_history[-12:],  # Last 12 charges
        "price_changes": price_changes,
        "insights": [
            f"This {cadence} subscription costs ${annual_cost:.2f}/year",
            f"You've been charged {series[5]} times since {str(series[6])[:10]}"
        ] + ([f"Price increased {price_changes[-1]['change_percent']}% on {price_changes[-1]['date'][:10]}"] if price_changes else [])
    }
```

### 3.2 AI-Enhanced Transfer Matching

**Edit file**: `apps/backend/src/ledgerloop/api/routes/transfers.py`

Add endpoint:
```python
@router.post("/ai-match")
async def ai_match_transfers():
    """
    AI-enhanced transfer matching with multi-signal scoring
    """
    from ...db import get_conn
    from datetime import datetime, timedelta
    
    conn = get_conn()
    
    # Get unmatched transactions
    transactions = conn.execute("""
        SELECT t.id, t.description_norm, t.amount, t.posted_at, t.account_id, t.ai_merchant_name
        FROM transaction t
        WHERE t.id NOT IN (
            SELECT tx1_id FROM matched_transfers
            UNION  
            SELECT tx2_id FROM matched_transfers
        )
        AND ABS(t.amount) > 10
        ORDER BY t.posted_at DESC
        LIMIT 1000
    """).fetchall()
    
    # Find potential matches
    suggestions = []
    used_ids = set()
    
    for i, tx1 in enumerate(transactions):
        if tx1[0] in used_ids:
            continue
            
        for tx2 in transactions[i+1:]:
            if tx2[0] in used_ids:
                continue
            
            # Skip if same sign (both credits or both debits)
            if (tx1[2] > 0) == (tx2[2] > 0):
                continue
            
            # Calculate signals
            signals = {}
            confidence = 0
            
            # Amount match (exact = 40 points, within 1% = 30 points)
            amount_diff = abs(abs(tx1[2]) - abs(tx2[2]))
            amount_pct = amount_diff / max(abs(tx1[2]), abs(tx2[2]), 1)
            if amount_diff < 0.01:
                signals["amount_match"] = {"score": 40, "detail": "Exact match"}
                confidence += 40
            elif amount_pct < 0.01:
                signals["amount_match"] = {"score": 30, "detail": f"Within {amount_pct*100:.1f}%"}
                confidence += 30
            else:
                continue  # Skip if amounts don't match
            
            # Date proximity (same day = 30 points, within 3 days = 20, within 7 = 10)
            date1 = datetime.fromisoformat(str(tx1[3]).replace('Z', '+00:00')) if tx1[3] else datetime.now()
            date2 = datetime.fromisoformat(str(tx2[3]).replace('Z', '+00:00')) if tx2[3] else datetime.now()
            day_diff = abs((date1 - date2).days)
            
            if day_diff == 0:
                signals["date_proximity"] = {"score": 30, "detail": "Same day"}
                confidence += 30
            elif day_diff <= 3:
                signals["date_proximity"] = {"score": 20, "detail": f"{day_diff} days apart"}
                confidence += 20
            elif day_diff <= 7:
                signals["date_proximity"] = {"score": 10, "detail": f"{day_diff} days apart"}
                confidence += 10
            else:
                continue  # Skip if too far apart
            
            # Description analysis (transfer keywords = 20 points)
            transfer_keywords = ["transfer", "xfer", "ach", "wire", "zelle", "venmo", "paypal"]
            desc1 = (tx1[1] or "").lower()
            desc2 = (tx2[1] or "").lower()
            if any(kw in desc1 or kw in desc2 for kw in transfer_keywords):
                signals["description"] = {"score": 20, "detail": "Transfer keyword found"}
                confidence += 20
            
            # Round amount detection (10 points for $100, $500, $1000, etc.)
            amount = abs(tx1[2])
            if amount >= 100 and amount % 100 == 0:
                signals["round_amount"] = {"score": 10, "detail": f"Round amount ${amount:.0f}"}
                confidence += 10
            
            if confidence >= 50:
                suggestions.append({
                    "tx1": {
                        "id": tx1[0],
                        "description": tx1[1],
                        "amount": float(tx1[2]),
                        "date": str(tx1[3])
                    },
                    "tx2": {
                        "id": tx2[0],
                        "description": tx2[1],
                        "amount": float(tx2[2]),
                        "date": str(tx2[3])
                    },
                    "confidence": confidence,
                    "signals": signals
                })
                used_ids.add(tx1[0])
                used_ids.add(tx2[0])
                break
    
    # Sort by confidence
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)
    
    return {
        "suggestions": suggestions[:30],
        "analyzed_count": len(transactions),
        "matches_found": len(suggestions)
    }


@router.get("/{pair_id}/signals")
async def get_transfer_signals(pair_id: str):
    """Get detailed matching signals for a transfer pair"""
    from ...db import get_conn
    
    conn = get_conn()
    
    pair = conn.execute("""
        SELECT mt.id, mt.tx1_id, mt.tx2_id, mt.method, mt.decided_at,
               t1.description_norm as desc1, t1.amount as amt1, t1.posted_at as date1,
               t2.description_norm as desc2, t2.amount as amt2, t2.posted_at as date2
        FROM matched_transfers mt
        JOIN transaction t1 ON mt.tx1_id = t1.id
        JOIN transaction t2 ON mt.tx2_id = t2.id
        WHERE mt.id = ?
    """, [pair_id]).fetchone()
    
    if not pair:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transfer pair not found")
    
    # Calculate signals
    signals = []
    
    # Amount match
    amt1, amt2 = abs(float(pair[6])), abs(float(pair[9]))
    if abs(amt1 - amt2) < 0.01:
        signals.append({"signal": "Exact amount match", "strength": "strong"})
    elif abs(amt1 - amt2) / max(amt1, amt2) < 0.01:
        signals.append({"signal": "Amount within 1%", "strength": "medium"})
    
    # Date proximity
    from datetime import datetime
    date1 = datetime.fromisoformat(str(pair[7]).replace('Z', '+00:00'))
    date2 = datetime.fromisoformat(str(pair[10]).replace('Z', '+00:00'))
    days = abs((date1 - date2).days)
    if days == 0:
        signals.append({"signal": "Same day transaction", "strength": "strong"})
    elif days <= 3:
        signals.append({"signal": f"Within {days} days", "strength": "medium"})
    
    # Description keywords
    desc_combined = f"{pair[5]} {pair[8]}".lower()
    if "transfer" in desc_combined:
        signals.append({"signal": "Contains 'transfer'", "strength": "strong"})
    if "zelle" in desc_combined:
        signals.append({"signal": "Zelle payment", "strength": "strong"})
    
    return {
        "pair_id": pair_id,
        "transaction_1": {
            "id": pair[1],
            "description": pair[5],
            "amount": float(pair[6]),
            "date": str(pair[7])
        },
        "transaction_2": {
            "id": pair[2],
            "description": pair[8],
            "amount": float(pair[9]),
            "date": str(pair[10])
        },
        "signals": signals,
        "method": pair[3],
        "confirmed": pair[4] is not None
    }
```

### 3.3 AI Rule Suggestions

**Edit file**: `apps/backend/src/ledgerloop/api/routes/rules.py`

Add endpoint:
```python
@router.post("/ai-suggest")
async def ai_suggest_rules():
    """Generate rule suggestions from uncategorized transaction patterns"""
    from ...db import get_conn
    from collections import defaultdict
    import re
    
    conn = get_conn()
    
    # Get uncategorized transactions
    transactions = conn.execute("""
        SELECT t.id, t.description_norm, t.amount, t.ai_merchant_name
        FROM transaction t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        WHERE tc.tx_id IS NULL
        ORDER BY t.posted_at DESC
        LIMIT 500
    """).fetchall()
    
    # Group by merchant pattern
    merchant_groups = defaultdict(list)
    for tx in transactions:
        # Extract key merchant identifier
        merchant = tx[3] or tx[1]
        # Simplify to first 2-3 words
        key = re.sub(r'[^a-zA-Z\s]', '', merchant).strip().split()[:2]
        key = ' '.join(key).upper()
        if key:
            merchant_groups[key].append({
                "id": tx[0],
                "description": tx[1],
                "amount": float(tx[2])
            })
    
    # Generate rule suggestions
    suggestions = []
    for merchant_key, txs in merchant_groups.items():
        if len(txs) < 3:  # Need at least 3 matches
            continue
        
        # Suggest rule
        suggestions.append({
            "merchant_pattern": merchant_key,
            "suggested_predicate": f"description ILIKE '%{merchant_key}%'",
            "match_count": len(txs),
            "sample_transactions": [t["id"] for t in txs[:5]],
            "sample_descriptions": [t["description"] for t in txs[:3]],
            "total_amount": round(sum(t["amount"] for t in txs), 2),
            "suggested_action": "assign_category",
            "confidence": min(0.95, 0.6 + (len(txs) * 0.05))
        })
    
    # Sort by match count
    suggestions.sort(key=lambda x: x["match_count"], reverse=True)
    
    return {
        "suggestions": suggestions[:15],
        "uncategorized_count": len(transactions),
        "patterns_found": len(suggestions)
    }
```

### 3.4 Test New Detection Endpoints

```bash
docker-compose restart ledgerloop-backend
sleep 10

# Test AI recurring detection
curl -s http://localhost:8000/api/recurring/ai-detect | jq '.suggestions[:2]'

# Test AI transfer matching
curl -s http://localhost:8000/api/transfers/ai-match | jq '.suggestions[:2]'

# Test AI rule suggestions
curl -s http://localhost:8000/api/rules/ai-suggest | jq '.suggestions[:2]'
```

---

## PHASE 4: FRONTEND ENHANCEMENTS (60 min)

### 4.1 Add Intelligence Feed Component

**Create file**: `apps/web/src/components/IntelligenceFeed.tsx`

```tsx
"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertTriangle, Lightbulb, TrendingUp, Bell } from "lucide-react";

interface FeedItem {
  type: string;
  severity: string;
  title: string;
  description: string;
  recommendations?: string[];
  transaction_id?: string;
  confidence?: number;
}

export function IntelligenceFeed() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/intelligence/feed")
      .then((r) => r.json())
      .then((data) => {
        setItems(data.items || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const getIcon = (type: string) => {
    switch (type) {
      case "anomaly": return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case "insight": return <Lightbulb className="h-4 w-4 text-yellow-500" />;
      case "prediction": return <TrendingUp className="h-4 w-4 text-blue-500" />;
      default: return <Bell className="h-4 w-4" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
      case "high":
      case "urgent": return "destructive";
      case "medium":
      case "warning": return "warning";
      default: return "secondary";
    }
  };

  if (loading) {
    return <Card><CardContent className="p-4">Loading insights...</CardContent></Card>;
  }

  if (items.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-sm">Intelligence Feed</CardTitle></CardHeader>
        <CardContent className="text-muted-foreground text-sm">
          No insights available. Import more transactions for AI analysis.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Lightbulb className="h-4 w-4" />
          Intelligence Feed
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.slice(0, 5).map((item, i) => (
          <div key={i} className="border-l-2 border-primary pl-3 py-1">
            <div className="flex items-center gap-2 mb-1">
              {getIcon(item.type)}
              <span className="font-medium text-sm">{item.title}</span>
              <Badge variant={getSeverityColor(item.severity) as any} className="text-xs">
                {item.severity}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">{item.description}</p>
            {item.recommendations && item.recommendations.length > 0 && (
              <p className="text-xs text-blue-600 mt-1">
                💡 {item.recommendations[0]}
              </p>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```

### 4.2 Add Health Score Component

**Create file**: `apps/web/src/components/HealthScore.tsx`

```tsx
"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Heart } from "lucide-react";

interface HealthData {
  overall_score: number;
  health_grade: string;
  dimensions: {
    spending_health: number;
    savings_health: number;
    budgeting_health: number;
    trend_health: number;
  };
  strengths: string[];
  recommendations: string[];
}

export function HealthScore() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/intelligence/health-score")
      .then((r) => r.json())
      .then((data) => {
        setHealth(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case "excellent": return "text-green-600";
      case "good": return "text-blue-600";
      case "fair": return "text-yellow-600";
      case "poor": return "text-orange-600";
      case "critical": return "text-red-600";
      default: return "text-gray-600";
    }
  };

  if (loading) {
    return <Card><CardContent className="p-4">Calculating health score...</CardContent></Card>;
  }

  if (!health) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Heart className="h-4 w-4 text-red-500" />
          Financial Health
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-center mb-4">
          <div className={`text-4xl font-bold ${getGradeColor(health.health_grade)}`}>
            {health.overall_score}
          </div>
          <Badge variant="outline" className="mt-1">
            {health.health_grade.toUpperCase()}
          </Badge>
        </div>
        
        <div className="space-y-2 text-sm">
          <div className="flex justify-between items-center">
            <span>Spending</span>
            <Progress value={health.dimensions.spending_health} className="w-20 h-2" />
          </div>
          <div className="flex justify-between items-center">
            <span>Savings</span>
            <Progress value={health.dimensions.savings_health} className="w-20 h-2" />
          </div>
          <div className="flex justify-between items-center">
            <span>Budgeting</span>
            <Progress value={health.dimensions.budgeting_health} className="w-20 h-2" />
          </div>
          <div className="flex justify-between items-center">
            <span>Trends</span>
            <Progress value={health.dimensions.trend_health} className="w-20 h-2" />
          </div>
        </div>

        {health.recommendations.length > 0 && (
          <div className="mt-3 pt-3 border-t text-xs text-muted-foreground">
            <strong>Top tip:</strong> {health.recommendations[0]}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### 4.3 Update Dashboard to Use New Components

**Edit file**: `apps/web/src/app/page.tsx` or `apps/web/src/components/EnhancedDashboard.tsx`

Find the dashboard layout and add the new components:

```tsx
// Import at top
import { IntelligenceFeed } from "@/components/IntelligenceFeed";
import { HealthScore } from "@/components/HealthScore";

// Add to the dashboard grid layout (find the grid section)
// Add these components alongside existing widgets:

<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Existing widgets */}
  
  {/* Add Intelligence Feed */}
  <IntelligenceFeed />
  
  {/* Add Health Score */}
  <HealthScore />
</div>
```

### 4.4 Add AI Detection Buttons to Recurring Page

**Edit file**: `apps/web/src/app/recurring/page.tsx`

Find the page header/actions area and add:

```tsx
// Add import
import { Sparkles } from "lucide-react";

// Add state
const [aiDetecting, setAiDetecting] = useState(false);
const [aiSuggestions, setAiSuggestions] = useState([]);

// Add function
const runAIDetection = async () => {
  setAiDetecting(true);
  try {
    const res = await fetch("/api/recurring/ai-detect", { method: "POST" });
    const data = await res.json();
    setAiSuggestions(data.suggestions || []);
  } catch (e) {
    console.error("AI detection failed:", e);
  }
  setAiDetecting(false);
};

// Add button in the header area (find where other buttons are)
<Button onClick={runAIDetection} disabled={aiDetecting} variant="outline">
  <Sparkles className="mr-2 h-4 w-4" />
  {aiDetecting ? "Detecting..." : "AI Detect Patterns"}
</Button>

// Add suggestions display (after the button or in a new section)
{aiSuggestions.length > 0 && (
  <Card className="mt-4">
    <CardHeader>
      <CardTitle className="text-sm">AI-Detected Patterns ({aiSuggestions.length})</CardTitle>
    </CardHeader>
    <CardContent>
      {aiSuggestions.slice(0, 5).map((s: any, i: number) => (
        <div key={i} className="flex justify-between items-center py-2 border-b last:border-0">
          <div>
            <div className="font-medium">{s.merchant}</div>
            <div className="text-sm text-muted-foreground">
              {s.occurrence_count} charges, avg ${Math.abs(s.average_amount).toFixed(2)}
            </div>
          </div>
          <Badge>{Math.round(s.confidence * 100)}% confident</Badge>
        </div>
      ))}
    </CardContent>
  </Card>
)}
```

### 4.5 Add AI Match Button to Transfers Page

**Edit file**: `apps/web/src/app/transfers/page.tsx`

Similar pattern - add AI matching button and display results.

### 4.6 Build and Test Frontend

```bash
cd apps/web
npm run build

# Check for errors
# If any TypeScript errors, fix them

# Restart everything
cd ../..
docker-compose up -d --build
```

---

## PHASE 5: FULL VERIFICATION (15 min)

### 5.1 API Smoke Test

```bash
#!/bin/bash
BASE="http://localhost:8000"

echo "=== Core ==="
curl -s "$BASE/api/health" | jq -r '.status // "FAIL"'
curl -s "$BASE/api/transactions?limit=1" | jq -r '.data[0].id // "NO DATA"'

echo "=== AI ==="
curl -s "$BASE/api/ai/stats" | jq -r '.ai_service_status // "FAIL"'

echo "=== Intelligence ==="
curl -s -o /dev/null -w "%{http_code}" "$BASE/api/intelligence/feed"
curl -s -o /dev/null -w "%{http_code}" "$BASE/api/intelligence/health-score"
curl -s -o /dev/null -w "%{http_code}" "$BASE/api/intelligence/predictions"

echo "=== Analytics ==="
curl -s -o /dev/null -w "%{http_code}" "$BASE/api/analytics/ai/dashboard"
curl -s -o /dev/null -w "%{http_code}" "$BASE/api/analytics/ai/spending-patterns"
curl -s -o /dev/null -w "%{http_code}" "$BASE/api/analytics/ai/anomalies"

echo "=== Detection ==="
curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/recurring/ai-detect"
curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/transfers/ai-match"
curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/rules/ai-suggest"

echo "=== Existing ==="
curl -s -o /dev/null -w "%{http_code}" "$BASE/api/recurring"
curl -s -o /dev/null -w "%{http_code}" "$BASE/api/transfers"
curl -s -o /dev/null -w "%{http_code}" "$BASE/api/rules"
```

All should return 200.

### 5.2 Frontend Page Test

```bash
BASE="http://localhost:3000"
for page in "/" "/transactions" "/categories" "/rules" "/recurring" "/transfers" "/ai" "/ingest"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$page")
  echo "$page: $status"
done
```

All should return 200.

### 5.3 Fix Any Failures

If any test fails:
1. Check logs: `docker logs ledgerloop-backend --tail 50`
2. Fix the issue
3. Restart: `docker-compose restart`
4. Re-test

---

## PHASE 6: DOCUMENTATION (10 min)

### 6.1 Create Changelog

**Create file**: `SOTA_CHANGELOG.md`

Document:
- Bug fixes (recurring transfer leak)
- New endpoints added
- Frontend components added
- Configuration changes

### 6.2 Create Test Results

**Create file**: `SOTA_TEST_RESULTS.md`

Document all test results from Phase 5.

---

## OUTPUT FILES REQUIRED

1. `SOTA_CHANGELOG.md` - All changes made
2. `SOTA_TEST_RESULTS.md` - Test results
3. `SOTA_REMAINING.md` - Anything not completed and why

---

## RULES

1. **NO ASKING FOR APPROVAL** - Make decisions and execute
2. **TEST AFTER EVERY PHASE** - Don't proceed if broken
3. **FIX BUGS FIRST** - Phase 1 is mandatory before new features
4. **DON'T OVERCOMPLICATE** - Use existing code, don't rewrite
5. **WORK INCREMENTALLY** - Small changes, frequent tests
6. **DOCUMENT EVERYTHING** - Keep logs of what you changed

---

## SUCCESS CRITERIA

- [ ] Recurring detection excludes ALL transfers (bug fixed)
- [ ] `/api/intelligence/feed` returns insights
- [ ] `/api/intelligence/health-score` returns score
- [ ] `/api/analytics/ai/dashboard` returns unified data
- [ ] `/api/recurring/ai-detect` finds patterns
- [ ] `/api/transfers/ai-match` finds matches
- [ ] `/api/rules/ai-suggest` suggests rules
- [ ] Dashboard shows Intelligence Feed
- [ ] Dashboard shows Health Score
- [ ] All pages load without errors
- [ ] All API endpoints return 200

---

## TIME BUDGET

| Phase | Time | Priority |
|-------|------|----------|
| 0: Recon | 5 min | Required |
| 1: Bug Fix | 15 min | CRITICAL |
| 2: Expose AI | 45 min | HIGH |
| 3: AI Detection | 30 min | HIGH |
| 4: Frontend | 60 min | MEDIUM |
| 5: Verify | 15 min | Required |
| 6: Docs | 10 min | Required |
| **Total** | **~3 hours** | |

---

## BEGIN

Start Phase 0 now. Work methodically through each phase. Test continuously.

**GO.**
