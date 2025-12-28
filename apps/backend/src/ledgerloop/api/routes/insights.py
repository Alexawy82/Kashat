"""
Smart Insights API - AI-powered financial insights and alerts

Provides:
- Spending spike detection
- Price increase alerts
- Top spending analysis
- Smart recommendation cards
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ...db import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["insights"])


# =============================================================================
# Models
# =============================================================================

class InsightSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"


class InsightType(str, Enum):
    SPENDING_SPIKE = "spending_spike"
    PRICE_INCREASE = "price_increase"
    TOP_SPENDING = "top_spending"
    SAVINGS_OPPORTUNITY = "savings_opportunity"


class InsightCard(BaseModel):
    """A smart insight card for the dashboard."""
    type: InsightType
    title: str
    message: str
    severity: InsightSeverity
    amount: Optional[float] = None
    percent_change: Optional[float] = None
    action_url: Optional[str] = None
    category_id: Optional[str] = None
    series_id: Optional[str] = None


class SpendingSpike(BaseModel):
    """Detected spending spike in a category."""
    category_id: str
    category_name: str
    current: float
    average: float
    percent_change: float


class PriceIncrease(BaseModel):
    """Detected price increase in recurring payment."""
    series_id: str
    merchant: str
    old_price: float
    new_price: float
    percent_change: float


# =============================================================================
# Detection Functions
# =============================================================================

def detect_spending_spikes(conn, threshold: float = 0.3) -> List[SpendingSpike]:
    """Find categories where current month > 3-month average by threshold."""
    today = date.today()
    current_month_start = today.replace(day=1)
    three_months_ago = (current_month_start - timedelta(days=90)).replace(day=1)

    # Get current month spending by category
    current_spending = conn.execute(
        """
        SELECT c.id, c.name, SUM(ABS(t.amount)) as total
        FROM [transaction] t
        JOIN transaction_category tc ON t.id = tc.tx_id
        JOIN category c ON tc.category_id = c.id
        WHERE t.amount < 0
          AND t.posted_at >= ?
        GROUP BY c.id, c.name
        HAVING total > 50
        """,
        [current_month_start.isoformat()]
    ).fetchall()

    # Get 3-month average by category
    avg_spending = conn.execute(
        """
        SELECT c.id, AVG(monthly_total) as avg_total
        FROM (
            SELECT c.id, strftime('%Y-%m', t.posted_at) as month, SUM(ABS(t.amount)) as monthly_total
            FROM [transaction] t
            JOIN transaction_category tc ON t.id = tc.tx_id
            JOIN category c ON tc.category_id = c.id
            WHERE t.amount < 0
              AND t.posted_at >= ?
              AND t.posted_at < ?
            GROUP BY c.id, month
        ) sub
        JOIN category c ON sub.id = c.id
        GROUP BY c.id
        """,
        [three_months_ago.isoformat(), current_month_start.isoformat()]
    ).fetchall()

    avg_map = {row[0]: row[1] for row in avg_spending}

    spikes = []
    for cat_id, cat_name, current in current_spending:
        avg = avg_map.get(cat_id, 0)
        if avg > 0:
            pct_change = (current - avg) / avg
            if pct_change >= threshold:
                spikes.append(SpendingSpike(
                    category_id=cat_id,
                    category_name=cat_name,
                    current=round(current, 2),
                    average=round(avg, 2),
                    percent_change=round(pct_change * 100, 1)
                ))

    return sorted(spikes, key=lambda x: -x.percent_change)


def detect_price_increases(conn, threshold: float = 0.05) -> List[PriceIncrease]:
    """Find recurring series where price has increased.

    Note: ledgerloop schema doesn't have price_hike tracking,
    so this returns empty for now.
    """
    # Without price_hike tracking, we can't detect increases
    return []


def get_top_categories_this_month(conn, limit: int = 5) -> List[dict]:
    """Get top spending categories for current month."""
    current_month_start = date.today().replace(day=1)

    rows = conn.execute(
        """
        SELECT c.id, c.name, SUM(ABS(t.amount)) as total
        FROM [transaction] t
        JOIN transaction_category tc ON t.id = tc.tx_id
        JOIN category c ON tc.category_id = c.id
        WHERE t.amount < 0
          AND t.posted_at >= ?
        GROUP BY c.id, c.name
        ORDER BY total DESC
        LIMIT ?
        """,
        [current_month_start.isoformat(), limit]
    ).fetchall()

    return [
        {"id": row[0], "name": row[1], "total": round(row[2], 2)}
        for row in rows
    ]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/cards")
def get_insight_cards(
    limit: int = Query(10, ge=1, le=20)
) -> List[InsightCard]:
    """Generate smart insight cards for dashboard."""
    conn = get_conn()
    cards = []

    # Spending spikes
    spikes = detect_spending_spikes(conn)
    for spike in spikes[:3]:
        severity = InsightSeverity.ALERT if spike.percent_change > 100 else (
            InsightSeverity.WARNING if spike.percent_change > 50 else InsightSeverity.INFO
        )
        cards.append(InsightCard(
            type=InsightType.SPENDING_SPIKE,
            title=f"Spending up on {spike.category_name}",
            message=f"You spent ${spike.current:.0f} this month vs ${spike.average:.0f} average (+{spike.percent_change:.0f}%)",
            severity=severity,
            amount=spike.current,
            percent_change=spike.percent_change,
            action_url=f"/transactions?category={spike.category_id}",
            category_id=spike.category_id
        ))

    # Price increases
    increases = detect_price_increases(conn)
    for inc in increases[:2]:
        cards.append(InsightCard(
            type=InsightType.PRICE_INCREASE,
            title=f"{inc.merchant} price increased",
            message=f"Went from ${inc.old_price:.2f} to ${inc.new_price:.2f} (+{inc.percent_change:.0f}%)",
            severity=InsightSeverity.WARNING,
            amount=inc.new_price,
            percent_change=inc.percent_change,
            action_url=f"/recurring/{inc.series_id}",
            series_id=inc.series_id
        ))

    # Top spending categories
    top = get_top_categories_this_month(conn)
    if top:
        top_summary = ", ".join(f"{c['name']}: ${c['total']:.0f}" for c in top[:3])
        cards.append(InsightCard(
            type=InsightType.TOP_SPENDING,
            title="Top spending this month",
            message=top_summary,
            severity=InsightSeverity.INFO,
            action_url="/analytics"
        ))

    return cards[:limit]


@router.get("/spending-spikes")
def get_spending_spikes(
    threshold: float = Query(0.3, ge=0.1, le=2.0, description="Percentage threshold (0.3 = 30%)")
) -> List[SpendingSpike]:
    """Get detailed spending spike analysis."""
    conn = get_conn()
    return detect_spending_spikes(conn, threshold)


@router.get("/price-increases")
def get_price_increases_endpoint() -> List[PriceIncrease]:
    """Get detected price increases in recurring payments."""
    conn = get_conn()
    return detect_price_increases(conn)


@router.get("/top-categories")
def get_top_categories(
    limit: int = Query(10, ge=1, le=20)
) -> List[dict]:
    """Get top spending categories for current month."""
    conn = get_conn()
    return get_top_categories_this_month(conn, limit)
