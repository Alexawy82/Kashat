"""
Budget Intelligence Engine - Smart budget suggestions and pace tracking

FEATURES:
- Generate budget suggestions based on income and spending patterns
- Separate committed (recurring) vs flexible spending
- Track spending pace and warn before overspending
- Integrate with recurring detection and AI analytics
"""

from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

from .db import get_conn
from .income_detector import get_total_monthly_income, detect_income_sources, save_income_sources


class SpendingTrend(Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class PaceStatus(Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    WILL_EXCEED = "will_exceed"
    EXCEEDED = "exceeded"


@dataclass
class CategorySuggestion:
    """A suggested budget for a category."""
    category_id: str
    category_name: str
    suggested_limit: float
    current_avg_spending: float
    trend: SpendingTrend
    trend_percentage: float
    is_committed: bool
    linked_recurring_id: Optional[str]
    reason: str
    confidence: float


@dataclass
class BudgetSuggestion:
    """A complete budget suggestion."""
    id: str
    total_income: float
    savings_target: float
    savings_amount: float
    total_budget: float
    committed_total: float
    flexible_total: float
    subscriptions_total: float
    categories: List[CategorySuggestion]
    confidence: float
    based_on_months: int


@dataclass
class PaceWarning:
    """A pace warning for a budget or category."""
    budget_id: str
    budget_category_id: Optional[str]
    category_name: Optional[str]
    status: PaceStatus
    days_elapsed: int
    days_remaining: int
    amount_spent: float
    amount_limit: float
    daily_rate: float
    projected_total: float
    projected_over_under: float
    exceed_date: Optional[date]
    recommendation: str


def get_budget_settings() -> Dict:
    """Get budget settings from database."""
    conn = get_conn()

    row = conn.execute("""
        SELECT include_irregular_income, income_buffer_percent, default_period,
               auto_rollover, pace_warning_threshold, alert_days_before_exceed,
               suggest_from_spending, seasonal_adjustments, savings_goal_percent,
               show_committed_separate, show_pace_tracking
        FROM budget_settings WHERE id = 'default'
    """).fetchone()

    if not row:
        return {
            'include_irregular_income': False,
            'income_buffer_percent': 0.0,
            'default_period': 'monthly',
            'auto_rollover': False,
            'pace_warning_threshold': 0.8,
            'alert_days_before_exceed': 5,
            'suggest_from_spending': True,
            'seasonal_adjustments': True,
            'savings_goal_percent': 0.20,
            'show_committed_separate': True,
            'show_pace_tracking': True,
        }

    return {
        'include_irregular_income': bool(row[0]),
        'income_buffer_percent': row[1] or 0.0,
        'default_period': row[2] or 'monthly',
        'auto_rollover': bool(row[3]),
        'pace_warning_threshold': row[4] or 0.8,
        'alert_days_before_exceed': row[5] or 5,
        'suggest_from_spending': bool(row[6]) if row[6] is not None else True,
        'seasonal_adjustments': bool(row[7]) if row[7] is not None else True,
        'savings_goal_percent': row[8] or 0.20,
        'show_committed_separate': bool(row[9]) if row[9] is not None else True,
        'show_pace_tracking': bool(row[10]) if row[10] is not None else True,
    }


def update_budget_settings(settings: Dict) -> bool:
    """Update budget settings."""
    conn = get_conn()

    try:
        conn.execute("""
            UPDATE budget_settings SET
                include_irregular_income = ?,
                income_buffer_percent = ?,
                default_period = ?,
                auto_rollover = ?,
                pace_warning_threshold = ?,
                alert_days_before_exceed = ?,
                suggest_from_spending = ?,
                seasonal_adjustments = ?,
                savings_goal_percent = ?,
                show_committed_separate = ?,
                show_pace_tracking = ?,
                updated_at = datetime('now')
            WHERE id = 'default'
        """, [
            settings.get('include_irregular_income', False),
            settings.get('income_buffer_percent', 0.0),
            settings.get('default_period', 'monthly'),
            settings.get('auto_rollover', False),
            settings.get('pace_warning_threshold', 0.8),
            settings.get('alert_days_before_exceed', 5),
            settings.get('suggest_from_spending', True),
            settings.get('seasonal_adjustments', True),
            settings.get('savings_goal_percent', 0.20),
            settings.get('show_committed_separate', True),
            settings.get('show_pace_tracking', True),
        ])
        return True
    except Exception as e:
        print(f"Error updating budget settings: {e}")
        return False


def generate_budget_suggestion(
    savings_target_percent: Optional[float] = None,
    lookback_months: int = 3
) -> BudgetSuggestion:
    """
    Generate a smart budget suggestion based on income and spending patterns.

    Uses:
    - Income from income_detector
    - Committed spending from recurring_series
    - Flexible spending patterns from transaction history
    """
    conn = get_conn()
    settings = get_budget_settings()

    # Get savings target
    savings_percent = savings_target_percent if savings_target_percent is not None else settings['savings_goal_percent']

    # Get income
    income_data = get_total_monthly_income(include_irregular=settings['include_irregular_income'])
    total_income = income_data['total_monthly']

    # Apply income buffer
    if settings['income_buffer_percent'] > 0:
        total_income *= (1 - settings['income_buffer_percent'])

    # Calculate savings
    savings_amount = total_income * savings_percent
    budget_available = total_income - savings_amount

    # Get committed spending from recurring series
    committed = _get_committed_spending(conn)

    # Get flexible spending patterns
    flexible = _get_flexible_spending(conn, lookback_months, committed)

    # Get subscriptions (specific type of recurring)
    subscriptions = _get_subscription_spending(conn)

    # Calculate totals
    committed_total = sum(c['monthly_amount'] for c in committed)
    subscriptions_total = sum(s['monthly_amount'] for s in subscriptions)
    flexible_total = sum(f['avg_monthly'] for f in flexible)

    # Build category suggestions
    categories = []

    # Add committed categories
    for c in committed:
        categories.append(CategorySuggestion(
            category_id=c['category_id'],
            category_name=c['category_name'],
            suggested_limit=c['monthly_amount'],
            current_avg_spending=c['monthly_amount'],
            trend=SpendingTrend.STABLE,
            trend_percentage=0,
            is_committed=True,
            linked_recurring_id=c['recurring_id'],
            reason=f"Recurring {c['type']}: {c['name']}",
            confidence=0.95
        ))

    # Add subscription categories
    for s in subscriptions:
        # Check if already added as committed
        if not any(cat.linked_recurring_id == s['recurring_id'] for cat in categories):
            categories.append(CategorySuggestion(
                category_id=s['category_id'],
                category_name=s['category_name'],
                suggested_limit=s['monthly_amount'],
                current_avg_spending=s['monthly_amount'],
                trend=SpendingTrend.STABLE,
                trend_percentage=0,
                is_committed=True,
                linked_recurring_id=s['recurring_id'],
                reason=f"Subscription: {s['name']}",
                confidence=0.9
            ))

    # Add flexible categories
    for f in flexible:
        # Check if category already added
        if not any(cat.category_id == f['category_id'] for cat in categories):
            trend = _determine_trend(f.get('trend_data', []))
            trend_pct = f.get('trend_percentage', 0)

            # Suggest limit based on average + buffer for trend
            buffer = 1.0
            if trend == SpendingTrend.INCREASING:
                buffer = 1.1  # 10% buffer for increasing
            elif trend == SpendingTrend.VOLATILE:
                buffer = 1.15  # 15% buffer for volatile

            suggested = f['avg_monthly'] * buffer

            categories.append(CategorySuggestion(
                category_id=f['category_id'],
                category_name=f['category_name'],
                suggested_limit=round(suggested, 2),
                current_avg_spending=f['avg_monthly'],
                trend=trend,
                trend_percentage=trend_pct,
                is_committed=False,
                linked_recurring_id=None,
                reason=_generate_reason(f['category_name'], trend, f['avg_monthly']),
                confidence=0.7
            ))

    # Calculate overall confidence
    if categories:
        avg_confidence = sum(c.confidence for c in categories) / len(categories)
    else:
        avg_confidence = 0.5

    return BudgetSuggestion(
        id=str(uuid.uuid4()),
        total_income=round(total_income, 2),
        savings_target=savings_percent,
        savings_amount=round(savings_amount, 2),
        total_budget=round(budget_available, 2),
        committed_total=round(committed_total + subscriptions_total, 2),
        flexible_total=round(flexible_total, 2),
        subscriptions_total=round(subscriptions_total, 2),
        categories=categories,
        confidence=round(avg_confidence, 2),
        based_on_months=lookback_months
    )


def _get_committed_spending(conn) -> List[Dict]:
    """Get committed spending from recurring series (bills, loans, etc.)."""
    # Query recurring series for committed types
    rows = conn.execute("""
        SELECT
            rs.id,
            rs.name,
            rs.display_name,
            rs.recurring_type,
            rs.sub_category,
            rs.amount_mean,
            rs.cadence,
            rs.is_essential,
            tc.category_id,
            c.name as category_name
        FROM recurring_series rs
        LEFT JOIN recurring_tx rt ON rt.series_id = rs.id
        LEFT JOIN transaction_category tc ON tc.tx_id = rt.tx_id
        LEFT JOIN category c ON c.id = tc.category_id
        WHERE rs.status = 'active'
          AND rs.recurring_type IN ('bill', 'utility', 'insurance', 'loan', 'rent', 'mortgage')
          AND rs.amount_mean IS NOT NULL
          AND rs.amount_mean < 0
        GROUP BY rs.id
        ORDER BY ABS(rs.amount_mean) DESC
    """).fetchall()

    committed = []
    for r in rows:
        monthly = _to_monthly_from_cadence(abs(r[5] or 0), r[6])
        committed.append({
            'recurring_id': r[0],
            'name': r[2] or r[1],
            'type': r[3],
            'sub_category': r[4],
            'monthly_amount': round(monthly, 2),
            'cadence': r[6],
            'is_essential': bool(r[7]),
            'category_id': r[8] or 'uncategorized',
            'category_name': r[9] or 'Uncategorized'
        })

    return committed


def _get_subscription_spending(conn) -> List[Dict]:
    """Get subscription spending from recurring series."""
    rows = conn.execute("""
        SELECT
            rs.id,
            rs.name,
            rs.display_name,
            rs.recurring_type,
            rs.sub_category,
            rs.amount_mean,
            rs.cadence,
            tc.category_id,
            c.name as category_name
        FROM recurring_series rs
        LEFT JOIN recurring_tx rt ON rt.series_id = rs.id
        LEFT JOIN transaction_category tc ON tc.tx_id = rt.tx_id
        LEFT JOIN category c ON c.id = tc.category_id
        WHERE rs.status = 'active'
          AND rs.recurring_type = 'subscription'
          AND rs.amount_mean IS NOT NULL
          AND rs.amount_mean < 0
        GROUP BY rs.id
        ORDER BY ABS(rs.amount_mean) DESC
    """).fetchall()

    subscriptions = []
    for r in rows:
        monthly = _to_monthly_from_cadence(abs(r[5] or 0), r[6])
        subscriptions.append({
            'recurring_id': r[0],
            'name': r[2] or r[1],
            'type': r[3],
            'sub_category': r[4],
            'monthly_amount': round(monthly, 2),
            'cadence': r[6],
            'category_id': r[7] or 'uncategorized',
            'category_name': r[8] or 'Subscriptions'
        })

    return subscriptions


def _get_flexible_spending(conn, lookback_months: int, committed: List[Dict]) -> List[Dict]:
    """Get flexible spending patterns by category."""
    cutoff_date = (date.today() - timedelta(days=lookback_months * 30)).isoformat()

    # Get committed recurring IDs to exclude
    committed_recurring_ids = [c['recurring_id'] for c in committed]

    # Query spending by category, excluding committed recurring
    rows = conn.execute("""
        SELECT
            c.id as category_id,
            c.name as category_name,
            SUM(ABS(t.amount)) as total_spent,
            COUNT(t.id) as tx_count,
            AVG(ABS(t.amount)) as avg_tx_amount
        FROM [transaction] t
        JOIN transaction_category tc ON tc.tx_id = t.id
        JOIN category c ON c.id = tc.category_id
        LEFT JOIN recurring_tx rt ON rt.tx_id = t.id
        WHERE t.amount < 0
          AND t.posted_at >= ?
          AND (t.is_adjustment IS NULL OR t.is_adjustment = 0)
          AND (rt.series_id IS NULL OR rt.series_id NOT IN (SELECT value FROM json_each(?)))
        GROUP BY c.id
        HAVING total_spent > 10
        ORDER BY total_spent DESC
    """, [cutoff_date, str(committed_recurring_ids)]).fetchall()

    flexible = []
    for r in rows:
        monthly_avg = (r[2] or 0) / lookback_months
        flexible.append({
            'category_id': r[0],
            'category_name': r[1],
            'total_spent': round(r[2] or 0, 2),
            'tx_count': r[3],
            'avg_tx_amount': round(r[4] or 0, 2),
            'avg_monthly': round(monthly_avg, 2)
        })

    return flexible


def _to_monthly_from_cadence(amount: float, cadence: str) -> float:
    """Convert amount to monthly based on cadence."""
    if not cadence:
        return amount

    cadence_lower = cadence.lower()
    if 'week' in cadence_lower:
        return amount * 4.33
    elif 'biweek' in cadence_lower or 'bi-week' in cadence_lower:
        return amount * 2.17
    elif 'quarter' in cadence_lower:
        return amount / 3
    elif 'year' in cadence_lower or 'annual' in cadence_lower:
        return amount / 12
    else:  # monthly or unknown
        return amount


def _determine_trend(trend_data: List[float]) -> SpendingTrend:
    """Determine spending trend from monthly data."""
    if len(trend_data) < 2:
        return SpendingTrend.STABLE

    # Calculate simple trend
    first_half = sum(trend_data[:len(trend_data)//2]) / (len(trend_data)//2)
    second_half = sum(trend_data[len(trend_data)//2:]) / (len(trend_data) - len(trend_data)//2)

    if first_half == 0:
        return SpendingTrend.STABLE

    change = (second_half - first_half) / first_half

    if change > 0.1:
        return SpendingTrend.INCREASING
    elif change < -0.1:
        return SpendingTrend.DECREASING
    else:
        return SpendingTrend.STABLE


def _generate_reason(category_name: str, trend: SpendingTrend, avg_amount: float) -> str:
    """Generate a human-readable reason for the suggestion."""
    trend_text = {
        SpendingTrend.INCREASING: "trending up",
        SpendingTrend.DECREASING: "trending down",
        SpendingTrend.STABLE: "stable",
        SpendingTrend.VOLATILE: "variable"
    }.get(trend, "")

    return f"Based on ${avg_amount:.0f}/mo average, {trend_text}"


def calculate_budget_pace(budget_id: str, category_id: Optional[str] = None) -> PaceWarning:
    """
    Calculate spending pace for a budget or category.

    Returns warning if on track to exceed budget.
    """
    conn = get_conn()

    # Get budget details
    budget = conn.execute("""
        SELECT id, name, period, start_date FROM budget WHERE id = ?
    """, [budget_id]).fetchone()

    if not budget:
        raise ValueError(f"Budget not found: {budget_id}")

    # Get period bounds
    period_start, period_end = _get_current_period(budget[2], budget[3])

    # Get limit and spent
    if category_id:
        row = conn.execute("""
            SELECT bc.amount_limit, c.name
            FROM budget_category bc
            JOIN category c ON c.id = bc.category_id
            WHERE bc.id = ? AND bc.budget_id = ?
        """, [category_id, budget_id]).fetchone()

        if not row:
            raise ValueError(f"Category not found in budget: {category_id}")

        limit = row[0]
        category_name = row[1]

        # Get spent for this category
        spent = abs(conn.execute("""
            SELECT COALESCE(SUM(ABS(t.amount)), 0)
            FROM [transaction] t
            JOIN transaction_category tc ON tc.tx_id = t.id
            JOIN budget_category bc ON bc.category_id = tc.category_id
            WHERE bc.id = ?
              AND t.posted_at >= ?
              AND t.posted_at < ?
              AND t.amount < 0
        """, [category_id, period_start, period_end]).fetchone()[0])

    else:
        # Overall budget
        limit = conn.execute("""
            SELECT COALESCE(SUM(amount_limit), 0) FROM budget_category WHERE budget_id = ?
        """, [budget_id]).fetchone()[0]

        category_name = None

        # Get total spent across all categories in budget
        spent = abs(conn.execute("""
            SELECT COALESCE(SUM(ABS(t.amount)), 0)
            FROM [transaction] t
            JOIN transaction_category tc ON tc.tx_id = t.id
            JOIN budget_category bc ON bc.category_id = tc.category_id
            WHERE bc.budget_id = ?
              AND t.posted_at >= ?
              AND t.posted_at < ?
              AND t.amount < 0
        """, [budget_id, period_start, period_end]).fetchone()[0])

    # Calculate pace
    today = date.today()
    period_start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
    period_end_date = datetime.strptime(period_end, '%Y-%m-%d').date()

    days_elapsed = max(1, (today - period_start_date).days)
    days_remaining = max(0, (period_end_date - today).days)
    total_days = (period_end_date - period_start_date).days

    daily_rate = spent / days_elapsed if days_elapsed > 0 else 0
    projected_total = daily_rate * total_days

    # Determine status
    if spent >= limit:
        status = PaceStatus.EXCEEDED
    elif projected_total > limit:
        status = PaceStatus.WILL_EXCEED
    elif projected_total > limit * 0.9:
        status = PaceStatus.AT_RISK
    else:
        status = PaceStatus.ON_TRACK

    # Calculate exceed date if applicable
    exceed_date = None
    if daily_rate > 0 and limit > spent:
        days_to_exceed = (limit - spent) / daily_rate
        exceed_date = today + timedelta(days=int(days_to_exceed))
        if exceed_date > period_end_date:
            exceed_date = None

    # Generate recommendation
    recommendation = _generate_pace_recommendation(
        status, spent, limit, days_remaining, daily_rate
    )

    return PaceWarning(
        budget_id=budget_id,
        budget_category_id=category_id,
        category_name=category_name,
        status=status,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        amount_spent=round(spent, 2),
        amount_limit=round(limit, 2),
        daily_rate=round(daily_rate, 2),
        projected_total=round(projected_total, 2),
        projected_over_under=round(projected_total - limit, 2),
        exceed_date=exceed_date,
        recommendation=recommendation
    )


def _get_current_period(period: str, start_date: Optional[str]) -> Tuple[str, str]:
    """Get current period start and end dates."""
    today = date.today()

    if period == 'monthly':
        period_start = today.replace(day=1)
        if today.month == 12:
            period_end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            period_end = today.replace(month=today.month + 1, day=1)
    elif period == 'weekly':
        period_start = today - timedelta(days=today.weekday())
        period_end = period_start + timedelta(days=7)
    else:  # yearly
        period_start = today.replace(month=1, day=1)
        period_end = today.replace(year=today.year + 1, month=1, day=1)

    return period_start.isoformat(), period_end.isoformat()


def _generate_pace_recommendation(
    status: PaceStatus,
    spent: float,
    limit: float,
    days_remaining: int,
    daily_rate: float
) -> str:
    """Generate a recommendation based on pace status."""

    if status == PaceStatus.EXCEEDED:
        return f"You've exceeded your budget by ${spent - limit:.2f}. Consider adjusting your budget or reducing spending."

    if status == PaceStatus.WILL_EXCEED:
        remaining = limit - spent
        safe_daily = remaining / max(1, days_remaining)
        return f"At current pace, you'll exceed by end of period. Try to spend ≤${safe_daily:.2f}/day for remaining {days_remaining} days."

    if status == PaceStatus.AT_RISK:
        remaining = limit - spent
        return f"You're close to your limit. ${remaining:.2f} left for {days_remaining} days."

    remaining = limit - spent
    return f"On track! ${remaining:.2f} remaining for {days_remaining} days."


def get_committed_flexible_breakdown(budget_id: str) -> Dict:
    """Get breakdown of committed vs flexible spending for a budget."""
    conn = get_conn()

    # Get period bounds
    budget = conn.execute("""
        SELECT period, start_date FROM budget WHERE id = ?
    """, [budget_id]).fetchone()

    if not budget:
        return {'committed': [], 'flexible': [], 'totals': {}}

    period_start, period_end = _get_current_period(budget[0], budget[1])

    # Get committed categories (linked to recurring)
    committed = conn.execute("""
        SELECT
            bc.id,
            c.name as category_name,
            bc.amount_limit,
            bc.linked_recurring_id,
            COALESCE(SUM(ABS(t.amount)), 0) as spent
        FROM budget_category bc
        JOIN category c ON c.id = bc.category_id
        LEFT JOIN [transaction] t ON t.id IN (
            SELECT tc.tx_id FROM transaction_category tc
            WHERE tc.category_id = bc.category_id
        ) AND t.posted_at >= ? AND t.posted_at < ? AND t.amount < 0
        WHERE bc.budget_id = ?
          AND bc.is_committed = 1
        GROUP BY bc.id
    """, [period_start, period_end, budget_id]).fetchall()

    # Get flexible categories
    flexible = conn.execute("""
        SELECT
            bc.id,
            c.name as category_name,
            bc.amount_limit,
            COALESCE(SUM(ABS(t.amount)), 0) as spent
        FROM budget_category bc
        JOIN category c ON c.id = bc.category_id
        LEFT JOIN [transaction] t ON t.id IN (
            SELECT tc.tx_id FROM transaction_category tc
            WHERE tc.category_id = bc.category_id
        ) AND t.posted_at >= ? AND t.posted_at < ? AND t.amount < 0
        WHERE bc.budget_id = ?
          AND (bc.is_committed = 0 OR bc.is_committed IS NULL)
        GROUP BY bc.id
    """, [period_start, period_end, budget_id]).fetchall()

    committed_list = [
        {
            'id': r[0],
            'category_name': r[1],
            'limit': r[2],
            'linked_recurring_id': r[3],
            'spent': round(r[4], 2),
            'remaining': round(r[2] - r[4], 2)
        }
        for r in committed
    ]

    flexible_list = [
        {
            'id': r[0],
            'category_name': r[1],
            'limit': r[2],
            'spent': round(r[3], 2),
            'remaining': round(r[2] - r[3], 2)
        }
        for r in flexible
    ]

    return {
        'committed': committed_list,
        'flexible': flexible_list,
        'totals': {
            'committed_limit': sum(c['limit'] for c in committed_list),
            'committed_spent': sum(c['spent'] for c in committed_list),
            'flexible_limit': sum(f['limit'] for f in flexible_list),
            'flexible_spent': sum(f['spent'] for f in flexible_list),
        }
    }


def apply_budget_suggestion(
    suggestion: BudgetSuggestion,
    budget_name: str,
    selected_categories: Optional[List[str]] = None
) -> str:
    """
    Create a budget from a suggestion.

    Args:
        suggestion: The budget suggestion to apply
        budget_name: Name for the new budget
        selected_categories: Optional list of category IDs to include (all if None)

    Returns:
        The new budget ID
    """
    conn = get_conn()

    budget_id = str(uuid.uuid4())

    # Create budget
    conn.execute("""
        INSERT INTO budget (id, name, period, start_date, is_active, income_target,
                           savings_target, auto_suggested, created_at, updated_at)
        VALUES (?, ?, 'monthly', date('now', 'start of month'), 1, ?, ?, 1,
                datetime('now'), datetime('now'))
    """, [budget_id, budget_name, suggestion.total_income, suggestion.savings_target])

    # Add categories
    for cat in suggestion.categories:
        if selected_categories and cat.category_id not in selected_categories:
            continue

        cat_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO budget_category (id, budget_id, category_id, amount_limit,
                                        is_committed, source, trend, avg_actual,
                                        linked_recurring_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, [
            cat_id,
            budget_id,
            cat.category_id,
            cat.suggested_limit,
            cat.is_committed,
            'suggested' if not cat.is_committed else 'recurring',
            cat.trend.value,
            cat.current_avg_spending,
            cat.linked_recurring_id
        ])

        # Link to recurring if applicable
        if cat.linked_recurring_id:
            conn.execute("""
                INSERT INTO budget_recurring_link (id, budget_id, budget_category_id,
                                                  recurring_series_id, is_committed, created_at)
                VALUES (?, ?, ?, ?, 1, datetime('now'))
            """, [str(uuid.uuid4()), budget_id, cat_id, cat.linked_recurring_id])

    return budget_id


def generate_category_suggestions(lookback_months: int = 3) -> List[Dict]:
    """Generate per-category budget suggestions."""
    suggestion = generate_budget_suggestion(lookback_months=lookback_months)

    return [
        {
            'category_id': cat.category_id,
            'category_name': cat.category_name,
            'suggested_limit': cat.suggested_limit,
            'current_avg': cat.current_avg_spending,
            'trend': cat.trend.value,
            'trend_percentage': cat.trend_percentage,
            'is_committed': cat.is_committed,
            'reason': cat.reason,
            'confidence': cat.confidence
        }
        for cat in suggestion.categories
    ]


def save_pace_snapshot(budget_id: str, category_id: Optional[str] = None) -> str:
    """Save a pace snapshot for historical tracking."""
    conn = get_conn()

    try:
        pace = calculate_budget_pace(budget_id, category_id)
    except ValueError:
        return None

    snapshot_id = str(uuid.uuid4())

    # Get period info
    budget = conn.execute("SELECT period, start_date FROM budget WHERE id = ?", [budget_id]).fetchone()
    period_start, period_end = _get_current_period(budget[0], budget[1])

    conn.execute("""
        INSERT INTO budget_pace_snapshot (
            id, budget_id, budget_category_id, snapshot_date, period_start, period_end,
            days_elapsed, days_remaining, amount_spent, amount_limit,
            daily_rate, projected_total, projected_over_under, exceed_date, status
        ) VALUES (?, ?, ?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        snapshot_id,
        budget_id,
        category_id,
        period_start,
        period_end,
        pace.days_elapsed,
        pace.days_remaining,
        pace.amount_spent,
        pace.amount_limit,
        pace.daily_rate,
        pace.projected_total,
        pace.projected_over_under,
        pace.exceed_date.isoformat() if pace.exceed_date else None,
        pace.status.value
    ])

    return snapshot_id
