"""
Budget System API - Create and track spending budgets

Provides:
- Budget CRUD operations
- Category budget limits
- Budget progress tracking
- Period management
"""

import logging
from datetime import date, datetime, UTC, timedelta
from typing import Optional, List
from enum import Enum
import uuid

from fastapi import APIRouter, Query, Path, HTTPException
from pydantic import BaseModel, Field

from ...db import get_conn
from ...income_detector import (
    detect_income_sources, get_total_monthly_income, save_income_sources,
    update_income_source, get_saved_income_sources, backfill_income_transactions,
    detect_and_save_income, mark_transaction_income
)
from ...budget_intelligence import (
    generate_budget_suggestion, calculate_budget_pace, get_committed_flexible_breakdown,
    apply_budget_suggestion, generate_category_suggestions, get_budget_settings,
    update_budget_settings, save_pace_snapshot
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/budgets", tags=["budgets"])


# =============================================================================
# Models
# =============================================================================

class BudgetPeriod(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class BudgetCategoryCreate(BaseModel):
    """Create a category budget limit."""
    category_id: str
    amount_limit: float = Field(gt=0)
    rollover: bool = False


class BudgetCreate(BaseModel):
    """Create a new budget."""
    name: str = Field(min_length=1, max_length=100)
    period: BudgetPeriod = BudgetPeriod.MONTHLY
    start_date: Optional[str] = None
    categories: List[BudgetCategoryCreate] = []


class BudgetUpdate(BaseModel):
    """Update budget details."""
    name: Optional[str] = None
    is_active: Optional[bool] = None


class BudgetCategory(BaseModel):
    """A category within a budget with its limit."""
    id: str
    category_id: str
    category_name: str
    amount_limit: float
    rollover: bool
    spent: float = 0.0
    remaining: float = 0.0
    percent_used: float = 0.0


class Budget(BaseModel):
    """A budget with its categories."""
    id: str
    name: str
    period: str
    start_date: Optional[str]
    is_active: bool
    created_at: str
    total_limit: float
    total_spent: float
    categories: List[BudgetCategory] = []


class BudgetProgress(BaseModel):
    """Current period progress for a budget."""
    budget_id: str
    budget_name: str
    period_start: str
    period_end: str
    days_remaining: int
    total_limit: float
    total_spent: float
    total_remaining: float
    percent_used: float
    categories: List[BudgetCategory]
    on_track: bool


# =============================================================================
# Helper Functions
# =============================================================================

def _get_current_period(period: str, start_date: Optional[str] = None) -> tuple[date, date]:
    """Get the current budget period start and end dates."""
    today = date.today()

    if period == "weekly":
        # Week starts on Monday
        period_start = today - timedelta(days=today.weekday())
        period_end = period_start + timedelta(days=6)
    elif period == "yearly":
        period_start = today.replace(month=1, day=1)
        period_end = today.replace(month=12, day=31)
    else:  # monthly (default)
        period_start = today.replace(day=1)
        # Last day of month
        next_month = today.replace(day=28) + timedelta(days=4)
        period_end = next_month - timedelta(days=next_month.day)

    return period_start, period_end


def _calculate_category_spent(conn, category_id: str, period_start: date, period_end: date) -> float:
    """Calculate total spent in a category for a period."""
    result = conn.execute(
        """
        SELECT COALESCE(SUM(ABS(t.amount)), 0)
        FROM [transaction] t
        JOIN transaction_category tc ON t.id = tc.tx_id
        WHERE tc.category_id = ?
          AND t.amount < 0
          AND t.posted_at >= ?
          AND t.posted_at <= ?
        """,
        [category_id, period_start.isoformat(), period_end.isoformat()]
    ).fetchone()
    return float(result[0]) if result else 0.0


# =============================================================================
# Endpoints
# =============================================================================

@router.get("")
def list_budgets(
    active_only: bool = Query(True, description="Only return active budgets")
) -> List[Budget]:
    """List all budgets."""
    conn = get_conn()

    where = "WHERE is_active = 1" if active_only else ""
    rows = conn.execute(
        f"""
        SELECT id, name, period, start_date, is_active, created_at
        FROM budget
        {where}
        ORDER BY created_at DESC
        """
    ).fetchall()

    budgets = []
    for row in rows:
        budget_id = row[0]
        period = row[2]

        # Get categories
        cat_rows = conn.execute(
            """
            SELECT bc.id, bc.category_id, c.name, bc.amount_limit, bc.rollover
            FROM budget_category bc
            JOIN category c ON bc.category_id = c.id
            WHERE bc.budget_id = ?
            """,
            [budget_id]
        ).fetchall()

        period_start, period_end = _get_current_period(period, row[3])
        total_limit = 0.0
        total_spent = 0.0
        categories = []

        for cat in cat_rows:
            limit = float(cat[3])
            spent = _calculate_category_spent(conn, cat[1], period_start, period_end)
            remaining = max(0, limit - spent)
            pct = (spent / limit * 100) if limit > 0 else 0

            categories.append(BudgetCategory(
                id=cat[0],
                category_id=cat[1],
                category_name=cat[2],
                amount_limit=limit,
                rollover=bool(cat[4]),
                spent=round(spent, 2),
                remaining=round(remaining, 2),
                percent_used=round(pct, 1)
            ))
            total_limit += limit
            total_spent += spent

        budgets.append(Budget(
            id=budget_id,
            name=row[1],
            period=period,
            start_date=row[3],
            is_active=bool(row[4]),
            created_at=row[5],
            total_limit=round(total_limit, 2),
            total_spent=round(total_spent, 2),
            categories=categories
        ))

    return budgets


@router.post("")
def create_budget(body: BudgetCreate) -> Budget:
    """Create a new budget."""
    conn = get_conn()

    budget_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    start = body.start_date or date.today().replace(day=1).isoformat()

    conn.execute(
        """
        INSERT INTO budget (id, name, period, start_date, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, 1, ?, ?)
        """,
        [budget_id, body.name, body.period.value, start, now, now]
    )

    # Add categories
    for cat in body.categories:
        cat_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO budget_category (id, budget_id, category_id, amount_limit, rollover, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [cat_id, budget_id, cat.category_id, cat.amount_limit, int(cat.rollover), now]
        )

    # Return the created budget
    budgets = list_budgets(active_only=False)
    return next(b for b in budgets if b.id == budget_id)


# =============================================================================
# BUDGET INTELLIGENCE ENDPOINTS (must come before /{budget_id} routes)
# =============================================================================

@router.get("/income")
def get_income_sources_endpoint() -> dict:
    """Get detected income sources."""
    saved = get_saved_income_sources()
    if saved:
        income = get_total_monthly_income()
        return {
            "sources": saved,
            "total_monthly": income['total_monthly'],
            "by_type": income.get('by_type', {}),
            "confidence": income.get('confidence', 0)
        }

    detected = detect_income_sources()
    income = get_total_monthly_income()

    return {
        "sources": [d.to_dict() for d in detected],
        "total_monthly": income['total_monthly'],
        "by_type": income.get('by_type', {}),
        "confidence": income.get('confidence', 0),
        "needs_confirmation": True
    }


@router.post("/income/detect")
def detect_and_save_income_endpoint() -> dict:
    """Detect income sources and save to database.

    Uses adaptive lookback to find income even if default period has no data.
    """
    # Use the improved function with adaptive detection
    result = detect_and_save_income()

    return result


@router.post("/income/backfill")
def backfill_income_endpoint() -> dict:
    """Scan all positive transactions and mark likely income.

    This identifies:
    - Salary/paycheck deposits
    - Zelle/Venmo received
    - Investment dividends
    - ATM deposits

    And excludes:
    - Internal transfers (savings to checking)
    - Refunds and rebates
    - Account corrections
    """
    result = backfill_income_transactions()
    return result


@router.get("/suggest")
def get_budget_suggestion_endpoint(
    savings_percent: Optional[float] = Query(None, ge=0, le=0.5),
    lookback_months: int = Query(3, ge=1, le=12)
) -> dict:
    """Generate a smart budget suggestion."""
    suggestion = generate_budget_suggestion(
        savings_target_percent=savings_percent,
        lookback_months=lookback_months
    )

    return {
        "id": suggestion.id,
        "name": f"Smart Budget {date.today().strftime('%B %Y')}",
        "period": "monthly",
        "total_income": suggestion.total_income,
        "suggested_total": suggestion.total_budget,
        "savings_target": suggestion.savings_amount,
        "savings_percent": suggestion.savings_target,
        "categories": [
            {
                "category_id": cat.category_id,
                "category_name": cat.category_name,
                "suggested_limit": cat.suggested_limit,
                "avg_spending": cat.current_avg_spending,
                "max_spending": cat.current_avg_spending * 1.2,
                "trend": cat.trend.value,
                "is_committed": cat.is_committed,
                "recurring_amount": cat.suggested_limit if cat.is_committed else 0,
                "confidence": cat.confidence,
                "rationale": cat.reason
            }
            for cat in suggestion.categories
        ],
        "created_at": datetime.now(UTC).isoformat()
    }


class ApplySuggestionRequest(BaseModel):
    """Request to apply a budget suggestion."""
    suggestion_id: Optional[str] = None
    custom_name: Optional[str] = None


@router.post("/suggest/apply")
def apply_suggestion_endpoint(request: ApplySuggestionRequest) -> dict:
    """Create a budget from a suggestion."""
    suggestion = generate_budget_suggestion()
    name = request.custom_name or f"Smart Budget {date.today().strftime('%B %Y')}"

    budget_id = apply_budget_suggestion(suggestion, name, None)

    return {
        "budget_id": budget_id,
        "name": name,
        "categories_count": len(suggestion.categories)
    }


@router.get("/suggest/categories")
def get_category_suggestions_endpoint(
    lookback_months: int = Query(3, ge=1, le=12)
) -> dict:
    """Get per-category budget suggestions."""
    suggestions = generate_category_suggestions(lookback_months)
    return {"categories": suggestions}


@router.get("/insights")
def get_budget_insights_endpoint() -> dict:
    """Get budget-related insights."""
    from ...ai_insights import get_ai_insights_engine, InsightCategory

    engine = get_ai_insights_engine()
    all_insights = engine.generate_personalized_insights(insight_limit=20)

    budget_categories = {
        InsightCategory.BUDGET_SUGGESTION,
        InsightCategory.BUDGET_PACE_WARNING,
        InsightCategory.INCOME_DETECTED,
        InsightCategory.CATEGORY_TREND,
        InsightCategory.COMMITTED_SPENDING,
        InsightCategory.BUDGET_ALERT
    }

    budget_insights = [
        {
            "id": i.id,
            "category": i.category.value,
            "priority": i.priority.value,
            "title": i.title,
            "text": i.description,
            "action": i.recommendations[0] if i.recommendations else None,
            "impact_score": i.impact_score,
            "confidence": i.confidence
        }
        for i in all_insights
        if i.category in budget_categories
    ]

    return {"insights": budget_insights}


@router.get("/settings")
def get_budget_settings_endpoint() -> dict:
    """Get budget settings."""
    settings = get_budget_settings()
    return settings


@router.put("/settings")
def update_budget_settings_endpoint(settings: dict) -> dict:
    """Update budget settings."""
    success = update_budget_settings(settings)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update settings")
    return {"updated": True, "settings": get_budget_settings()}


# =============================================================================
# BUDGET CRUD ENDPOINTS (with path parameters)
# =============================================================================

@router.get("/{budget_id}")
def get_budget(budget_id: str = Path(...)) -> Budget:
    """Get a specific budget."""
    conn = get_conn()

    row = conn.execute(
        "SELECT id, name, period, start_date, is_active, created_at FROM budget WHERE id = ?",
        [budget_id]
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Use list_budgets logic but filter
    budgets = list_budgets(active_only=False)
    budget = next((b for b in budgets if b.id == budget_id), None)

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    return budget


@router.put("/{budget_id}")
def update_budget(budget_id: str, body: BudgetUpdate) -> Budget:
    """Update a budget."""
    conn = get_conn()

    # Check exists
    existing = conn.execute("SELECT id FROM budget WHERE id = ?", [budget_id]).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Budget not found")

    updates = []
    params = []

    if body.name is not None:
        updates.append("name = ?")
        params.append(body.name)
    if body.is_active is not None:
        updates.append("is_active = ?")
        params.append(int(body.is_active))

    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.now(UTC).isoformat())
        params.append(budget_id)

        conn.execute(
            f"UPDATE budget SET {', '.join(updates)} WHERE id = ?",
            params
        )

    return get_budget(budget_id)


@router.delete("/{budget_id}")
def delete_budget(budget_id: str) -> dict:
    """Delete a budget."""
    conn = get_conn()

    # Check exists
    existing = conn.execute("SELECT id FROM budget WHERE id = ?", [budget_id]).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Delete categories first (cascade should handle this, but be explicit)
    conn.execute("DELETE FROM budget_category WHERE budget_id = ?", [budget_id])
    conn.execute("DELETE FROM budget_period WHERE budget_id = ?", [budget_id])
    conn.execute("DELETE FROM budget WHERE id = ?", [budget_id])

    return {"deleted": True, "id": budget_id}


@router.get("/{budget_id}/progress")
def get_budget_progress(budget_id: str = Path(...)) -> BudgetProgress:
    """Get current period spending vs budget limits."""
    conn = get_conn()

    row = conn.execute(
        "SELECT id, name, period, start_date FROM budget WHERE id = ?",
        [budget_id]
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Budget not found")

    period = row[2]
    period_start, period_end = _get_current_period(period, row[3])

    # Get categories with spending
    cat_rows = conn.execute(
        """
        SELECT bc.id, bc.category_id, c.name, bc.amount_limit, bc.rollover
        FROM budget_category bc
        JOIN category c ON bc.category_id = c.id
        WHERE bc.budget_id = ?
        """,
        [budget_id]
    ).fetchall()

    total_limit = 0.0
    total_spent = 0.0
    categories = []

    for cat in cat_rows:
        limit = float(cat[3])
        spent = _calculate_category_spent(conn, cat[1], period_start, period_end)
        remaining = max(0, limit - spent)
        pct = (spent / limit * 100) if limit > 0 else 0

        categories.append(BudgetCategory(
            id=cat[0],
            category_id=cat[1],
            category_name=cat[2],
            amount_limit=limit,
            rollover=bool(cat[4]),
            spent=round(spent, 2),
            remaining=round(remaining, 2),
            percent_used=round(pct, 1)
        ))
        total_limit += limit
        total_spent += spent

    days_remaining = (period_end - date.today()).days
    total_remaining = max(0, total_limit - total_spent)
    percent_used = (total_spent / total_limit * 100) if total_limit > 0 else 0

    # Determine if on track (spending rate vs days elapsed)
    days_elapsed = (date.today() - period_start).days + 1
    total_days = (period_end - period_start).days + 1
    expected_percent = (days_elapsed / total_days * 100) if total_days > 0 else 0
    on_track = percent_used <= expected_percent * 1.1  # Allow 10% buffer

    return BudgetProgress(
        budget_id=budget_id,
        budget_name=row[1],
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        days_remaining=max(0, days_remaining),
        total_limit=round(total_limit, 2),
        total_spent=round(total_spent, 2),
        total_remaining=round(total_remaining, 2),
        percent_used=round(percent_used, 1),
        categories=categories,
        on_track=on_track
    )


@router.put("/{budget_id}/categories/{category_id}")
def set_category_limit(
    budget_id: str = Path(...),
    category_id: str = Path(...),
    amount_limit: float = Query(..., gt=0),
    rollover: bool = Query(False)
) -> BudgetCategory:
    """Set or update a category limit in a budget."""
    conn = get_conn()

    # Check budget exists
    budget = conn.execute("SELECT id, period FROM budget WHERE id = ?", [budget_id]).fetchone()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Check category exists
    cat = conn.execute("SELECT id, name FROM category WHERE id = ?", [category_id]).fetchone()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if budget_category exists
    existing = conn.execute(
        "SELECT id FROM budget_category WHERE budget_id = ? AND category_id = ?",
        [budget_id, category_id]
    ).fetchone()

    now = datetime.now(UTC).isoformat()

    if existing:
        # Update
        conn.execute(
            "UPDATE budget_category SET amount_limit = ?, rollover = ? WHERE id = ?",
            [amount_limit, int(rollover), existing[0]]
        )
        bc_id = existing[0]
    else:
        # Insert
        bc_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO budget_category (id, budget_id, category_id, amount_limit, rollover, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [bc_id, budget_id, category_id, amount_limit, int(rollover), now]
        )

    # Calculate current spending
    period_start, period_end = _get_current_period(budget[1])
    spent = _calculate_category_spent(conn, category_id, period_start, period_end)
    remaining = max(0, amount_limit - spent)
    pct = (spent / amount_limit * 100) if amount_limit > 0 else 0

    return BudgetCategory(
        id=bc_id,
        category_id=category_id,
        category_name=cat[1],
        amount_limit=amount_limit,
        rollover=rollover,
        spent=round(spent, 2),
        remaining=round(remaining, 2),
        percent_used=round(pct, 1)
    )


@router.delete("/{budget_id}/categories/{category_id}")
def remove_category_limit(
    budget_id: str = Path(...),
    category_id: str = Path(...)
) -> dict:
    """Remove a category from a budget."""
    conn = get_conn()

    result = conn.execute(
        "DELETE FROM budget_category WHERE budget_id = ? AND category_id = ?",
        [budget_id, category_id]
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Budget category not found")

    return {"deleted": True, "budget_id": budget_id, "category_id": category_id}


# =============================================================================
# PACE & BREAKDOWN ENDPOINTS (require budget_id path parameter)
# =============================================================================

@router.get("/{budget_id}/pace")
def get_budget_pace_endpoint(
    budget_id: str = Path(...),
    category_id: Optional[str] = Query(None)
) -> dict:
    """Get pace warnings for a budget."""
    try:
        pace = calculate_budget_pace(budget_id, category_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "budget_id": pace.budget_id,
        "overall_status": pace.status.value,
        "overall_pace_percent": (pace.amount_spent / pace.amount_limit * 100) if pace.amount_limit > 0 else 0,
        "total_spent": pace.amount_spent,
        "total_limit": pace.amount_limit,
        "days_elapsed": pace.days_elapsed,
        "days_remaining": pace.days_remaining,
        "warnings": [{
            "category_id": pace.budget_category_id or "overall",
            "category_name": pace.category_name or "Overall Budget",
            "status": pace.status.value,
            "spent": pace.amount_spent,
            "limit": pace.amount_limit,
            "pace_percent": (pace.amount_spent / pace.amount_limit * 100) if pace.amount_limit > 0 else 0,
            "expected_by_end": pace.projected_total,
            "days_in_period": pace.days_elapsed + pace.days_remaining,
            "days_elapsed": pace.days_elapsed,
            "days_remaining": pace.days_remaining,
            "message": pace.recommendation
        }] if pace.status.value != "on_track" else [],
        "period_start": date.today().replace(day=1).isoformat(),
        "period_end": (date.today().replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()
    }


@router.post("/{budget_id}/pace/snapshot")
def save_pace_endpoint(
    budget_id: str = Path(...),
    category_id: Optional[str] = Query(None)
) -> dict:
    """Save a pace snapshot for tracking."""
    snapshot_id = save_pace_snapshot(budget_id, category_id)
    if not snapshot_id:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"snapshot_id": snapshot_id}


@router.get("/{budget_id}/breakdown")
def get_breakdown_endpoint(budget_id: str = Path(...)) -> dict:
    """Get committed vs flexible breakdown for a budget."""
    breakdown = get_committed_flexible_breakdown(budget_id)
    return breakdown


@router.put("/income/{source_id}")
def update_income_endpoint(
    source_id: str = Path(...),
    user_confirmed: Optional[bool] = None,
    amount_override: Optional[float] = None,
    name_override: Optional[str] = None,
    is_active: Optional[bool] = None
) -> dict:
    """Confirm or adjust an income source."""
    success = update_income_source(
        source_id,
        user_confirmed=user_confirmed,
        user_amount_override=amount_override,
        user_name_override=name_override,
        is_active=is_active
    )

    if not success:
        raise HTTPException(status_code=404, detail="Income source not found")

    return {"updated": True, "id": source_id}
