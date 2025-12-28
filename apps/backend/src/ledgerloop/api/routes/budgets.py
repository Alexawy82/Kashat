"""
Budget System API - Create and track spending budgets

Provides:
- Budget CRUD operations
- Category budget limits
- Budget progress tracking
"""

import logging
from datetime import date, datetime, UTC, timedelta
from typing import Optional, List
from enum import Enum
import uuid

from fastapi import APIRouter, Query, Path, HTTPException
from pydantic import BaseModel, Field

from ...db import get_conn

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
    """Budget progress for a period."""
    budget_id: str
    budget_name: str
    period_start: str
    period_end: str
    days_remaining: int
    total_limit: float
    total_spent: float
    total_remaining: float
    percent_used: float
    categories: List[BudgetCategory] = []
    on_track: bool


# =============================================================================
# Helper Functions
# =============================================================================

def _ensure_budget_tables(conn):
    """Ensure budget tables exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            period TEXT DEFAULT 'monthly',
            start_date TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS budget_category (
            id TEXT PRIMARY KEY,
            budget_id TEXT NOT NULL,
            category_id TEXT NOT NULL,
            amount_limit REAL NOT NULL,
            rollover INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (budget_id) REFERENCES budget(id),
            FOREIGN KEY (category_id) REFERENCES category(id)
        )
    """)


def _get_current_period(period: str, start_date: Optional[str] = None) -> tuple:
    """Get the current budget period start and end dates."""
    today = date.today()

    if period == "weekly":
        period_start = today - timedelta(days=today.weekday())
        period_end = period_start + timedelta(days=6)
    elif period == "yearly":
        period_start = today.replace(month=1, day=1)
        period_end = today.replace(month=12, day=31)
    else:  # monthly (default)
        period_start = today.replace(day=1)
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
    _ensure_budget_tables(conn)

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
            created_at=row[5] or "",
            total_limit=round(total_limit, 2),
            total_spent=round(total_spent, 2),
            categories=categories
        ))

    return budgets


@router.post("")
def create_budget(body: BudgetCreate) -> Budget:
    """Create a new budget."""
    conn = get_conn()
    _ensure_budget_tables(conn)

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

    budgets = list_budgets(active_only=False)
    return next(b for b in budgets if b.id == budget_id)


@router.get("/{budget_id}")
def get_budget(budget_id: str = Path(...)) -> Budget:
    """Get a specific budget."""
    conn = get_conn()
    _ensure_budget_tables(conn)

    row = conn.execute(
        "SELECT id FROM budget WHERE id = ?",
        [budget_id]
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Budget not found")

    budgets = list_budgets(active_only=False)
    budget = next((b for b in budgets if b.id == budget_id), None)

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    return budget


@router.get("/{budget_id}/progress")
def get_budget_progress(budget_id: str = Path(...)) -> BudgetProgress:
    """Get budget progress for the current period."""
    conn = get_conn()
    _ensure_budget_tables(conn)

    row = conn.execute(
        "SELECT id, name, period, start_date FROM budget WHERE id = ?",
        [budget_id]
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Budget not found")

    budget_name = row[1]
    period = row[2]

    # Get period dates
    period_start, period_end = _get_current_period(period, row[3])
    today = date.today()
    days_remaining = max(0, (period_end - today).days)

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

    total_remaining = max(0, total_limit - total_spent)
    percent_used = (total_spent / total_limit * 100) if total_limit > 0 else 0

    # Calculate if on track: if we've spent less than proportional time elapsed
    total_days = (period_end - period_start).days + 1
    days_elapsed = (today - period_start).days + 1
    expected_percent = (days_elapsed / total_days * 100) if total_days > 0 else 100
    on_track = percent_used <= expected_percent

    return BudgetProgress(
        budget_id=budget_id,
        budget_name=budget_name,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        days_remaining=days_remaining,
        total_limit=round(total_limit, 2),
        total_spent=round(total_spent, 2),
        total_remaining=round(total_remaining, 2),
        percent_used=round(percent_used, 1),
        categories=categories,
        on_track=on_track
    )


@router.delete("/{budget_id}")
def delete_budget(budget_id: str) -> dict:
    """Delete a budget."""
    conn = get_conn()
    _ensure_budget_tables(conn)

    existing = conn.execute("SELECT id FROM budget WHERE id = ?", [budget_id]).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Budget not found")

    conn.execute("DELETE FROM budget_category WHERE budget_id = ?", [budget_id])
    conn.execute("DELETE FROM budget WHERE id = ?", [budget_id])

    return {"deleted": True, "id": budget_id}
