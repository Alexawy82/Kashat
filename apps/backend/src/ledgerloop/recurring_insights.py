"""
Phase 3: Recurring Insights Engine

Provides intelligent insights for recurring charges:
- Cash flow forecasting with recurring expense modeling
- Cancellation risk scoring
- Optimization suggestions
- Natural language insight generation
"""

from __future__ import annotations

import statistics
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, UTC
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from enum import Enum

from .db import get_conn

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InsightType(Enum):
    CASH_FLOW = "cash_flow"
    CANCELLATION_RISK = "cancellation_risk"
    OPTIMIZATION = "optimization"
    PRICE_ALERT = "price_alert"
    UPCOMING_PAYMENT = "upcoming_payment"
    SAVINGS_OPPORTUNITY = "savings_opportunity"


@dataclass
class CashFlowForecast:
    """Cash flow forecast with recurring charges included."""
    forecast_date: date
    expected_income: float
    expected_recurring: float
    expected_discretionary: float
    net_cash_flow: float
    recurring_breakdown: List[Dict[str, Any]]
    confidence: float


@dataclass
class CancellationRisk:
    """Risk assessment for a recurring charge being cancelled."""
    series_id: str
    merchant: str
    risk_level: RiskLevel
    risk_score: float  # 0-1, higher = more likely to cancel
    risk_factors: List[str]
    recommendation: str
    potential_savings: float


@dataclass
class OptimizationSuggestion:
    """Suggestion for optimizing recurring charges."""
    suggestion_id: str
    title: str
    description: str
    category: str  # 'downgrade', 'cancel', 'consolidate', 'negotiate', 'switch'
    affected_series: List[str]
    potential_monthly_savings: float
    potential_annual_savings: float
    confidence: float
    action_steps: List[str]
    priority: int  # 1 = highest


@dataclass
class RecurringInsight:
    """Natural language insight about recurring charges."""
    insight_id: str
    insight_type: InsightType
    title: str
    message: str
    data: Dict[str, Any]
    priority: int
    expires_at: Optional[date]
    actionable: bool
    action_label: Optional[str]
    action_series_id: Optional[str]


# =============================================================================
# RECURRING INSIGHTS ENGINE
# =============================================================================

class RecurringInsightsEngine:
    """Engine for generating insights about recurring charges."""

    def __init__(self):
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = get_conn()
        return self._conn

    # =========================================================================
    # CASH FLOW FORECASTING
    # =========================================================================

    def forecast_cash_flow(
        self,
        months: int = 3,
        include_pending: bool = False,
    ) -> List[CashFlowForecast]:
        """Generate cash flow forecast including recurring charges.

        Args:
            months: Number of months to forecast (1-12)
            include_pending: Include pending (unconfirmed) recurring series

        Returns:
            List of CashFlowForecast for each month
        """
        months = max(1, min(12, months))
        today = date.today()

        # Get confirmed recurring series
        status_filter = "('confirmed', 'pending')" if include_pending else "('confirmed')"
        series = self.conn.execute(f"""
            SELECT
                rs.id, rs.name, rs.display_name, rs.cadence, rs.anchor_day,
                rs.amount_mean, rs.recurring_type, rs.is_essential,
                rs.next_date, rs.last_date
            FROM recurring_series rs
            WHERE rs.status IN {status_filter}
        """).fetchall()

        # Get historical income (last 6 months average)
        income_data = self.conn.execute("""
            SELECT AVG(monthly_income) as avg_income FROM (
                SELECT date_trunc('month', posted_at) as month, SUM(amount) as monthly_income
                FROM [transaction]
                WHERE amount > 0
                  AND posted_at >= CURRENT_DATE - INTERVAL '6 months'
                  AND is_income = TRUE
                GROUP BY date_trunc('month', posted_at)
            )
        """).fetchone()
        avg_monthly_income = float(income_data[0] or 0) if income_data else 0

        # Get historical discretionary spending (last 6 months average)
        discretionary_data = self.conn.execute("""
            SELECT AVG(monthly_disc) as avg_disc FROM (
                SELECT date_trunc('month', posted_at) as month, SUM(-amount) as monthly_disc
                FROM [transaction] t
                LEFT JOIN recurring_tx rt ON rt.tx_id = t.id
                WHERE amount < 0
                  AND posted_at >= CURRENT_DATE - INTERVAL '6 months'
                  AND rt.tx_id IS NULL
                GROUP BY date_trunc('month', posted_at)
            )
        """).fetchone()
        avg_discretionary = float(discretionary_data[0] or 0) if discretionary_data else 0

        forecasts = []

        for month_offset in range(months):
            forecast_month = today.replace(day=1) + timedelta(days=32 * month_offset)
            forecast_month = forecast_month.replace(day=1)
            month_end = (forecast_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            # Calculate recurring charges for this month
            recurring_charges = []
            total_recurring = 0.0

            for row in series:
                (sid, name, display_name, cadence, anchor_day,
                 amount_mean, rec_type, is_essential, next_date, last_date) = row

                # Check if payment falls in this month
                if self._payment_in_month(cadence, anchor_day, next_date, forecast_month):
                    amount = abs(float(amount_mean or 0))
                    total_recurring += amount
                    recurring_charges.append({
                        "series_id": sid,
                        "merchant": display_name or name,
                        "amount": amount,
                        "type": rec_type,
                        "is_essential": bool(is_essential),
                        "expected_date": self._get_expected_date(
                            cadence, anchor_day, forecast_month
                        ),
                    })

            # Calculate net cash flow
            net = avg_monthly_income - total_recurring - avg_discretionary

            forecasts.append(CashFlowForecast(
                forecast_date=forecast_month,
                expected_income=avg_monthly_income,
                expected_recurring=total_recurring,
                expected_discretionary=avg_discretionary,
                net_cash_flow=net,
                recurring_breakdown=recurring_charges,
                confidence=0.7 if month_offset < 2 else 0.5,
            ))

        return forecasts

    def _payment_in_month(
        self,
        cadence: str,
        anchor_day: int,
        next_date: Any,
        target_month: date,
    ) -> bool:
        """Check if a recurring payment falls in the target month."""
        if cadence == "monthly":
            return True  # Monthly payments occur every month

        if cadence == "weekly":
            return True  # Weekly payments occur multiple times per month

        if cadence == "biweekly":
            return True  # Biweekly likely hits each month

        if cadence == "quarterly":
            # Check if this is a quarter boundary month
            if next_date:
                try:
                    next_d = date.fromisoformat(str(next_date))
                    # Check if next_date is in target month
                    if next_d.year == target_month.year and next_d.month == target_month.month:
                        return True
                    # Check future quarters
                    for q in range(4):
                        check_date = next_d + timedelta(days=91 * q)
                        if check_date.year == target_month.year and check_date.month == target_month.month:
                            return True
                except (ValueError, TypeError):
                    pass
            return target_month.month in [1, 4, 7, 10]  # Fallback to standard quarters

        if cadence == "semi_annual":
            if next_date:
                try:
                    next_d = date.fromisoformat(str(next_date))
                    for h in range(2):
                        check_date = next_d + timedelta(days=182 * h)
                        if check_date.year == target_month.year and check_date.month == target_month.month:
                            return True
                except (ValueError, TypeError):
                    pass
            return target_month.month in [1, 7]

        if cadence == "annual":
            if next_date:
                try:
                    next_d = date.fromisoformat(str(next_date))
                    return next_d.month == target_month.month
                except (ValueError, TypeError):
                    pass
            return False

        return True  # Default: assume it occurs

    def _get_expected_date(
        self,
        cadence: str,
        anchor_day: int,
        target_month: date,
    ) -> str:
        """Get expected payment date for a month."""
        import calendar
        day = anchor_day or 15
        max_day = calendar.monthrange(target_month.year, target_month.month)[1]
        day = min(day, max_day)
        return date(target_month.year, target_month.month, day).isoformat()

    # =========================================================================
    # CANCELLATION RISK SCORING
    # =========================================================================

    def calculate_cancellation_risks(
        self,
        limit: int = 20,
    ) -> List[CancellationRisk]:
        """Calculate cancellation risk scores for recurring charges.

        Factors considered:
        - Price increases (price_hike flag)
        - Amount relative to income
        - Category (discretionary vs essential)
        - Usage patterns (for subscriptions)
        - How long since confirmation
        - Missed payment patterns

        Args:
            limit: Maximum number of results

        Returns:
            List of CancellationRisk sorted by risk score (highest first)
        """
        # Get confirmed recurring series with details
        series = self.conn.execute("""
            SELECT
                rs.id, rs.name, rs.display_name, rs.cadence,
                rs.amount_mean, rs.recurring_type, rs.sub_category,
                rs.is_essential, rs.price_hike, rs.annual_cost,
                rs.decided_at, rs.last_date, rs.next_date,
                rs.status
            FROM recurring_series rs
            WHERE rs.status = 'confirmed'
            ORDER BY rs.amount_mean DESC
        """).fetchall()

        # Get total monthly income for context
        income_result = self.conn.execute("""
            SELECT AVG(monthly) FROM (
                SELECT date_trunc('month', posted_at) as m, SUM(amount) as monthly
                FROM [transaction]
                WHERE amount > 0 AND is_income = TRUE
                  AND posted_at >= CURRENT_DATE - INTERVAL '3 months'
                GROUP BY date_trunc('month', posted_at)
            )
        """).fetchone()
        monthly_income = float(income_result[0] or 5000) if income_result else 5000

        risks = []
        today = date.today()

        for row in series:
            (sid, name, display_name, cadence, amount_mean, rec_type,
             sub_category, is_essential, price_hike, annual_cost,
             decided_at, last_date, next_date, status) = row

            risk_score = 0.0
            risk_factors = []
            amount = abs(float(amount_mean or 0))

            # Factor 1: Essential vs Discretionary (base risk)
            if not is_essential:
                risk_score += 0.2
                risk_factors.append("Discretionary expense")
            else:
                risk_score -= 0.1  # Essential items less likely to cancel

            # Factor 2: Price hike detected
            if price_hike:
                risk_score += 0.25
                risk_factors.append("Recent price increase detected")

            # Factor 3: Cost relative to income
            income_ratio = amount / max(1, monthly_income)
            if income_ratio > 0.05:  # More than 5% of income
                risk_score += 0.15
                risk_factors.append(f"High cost relative to income ({income_ratio*100:.1f}%)")
            elif income_ratio > 0.02:  # 2-5% of income
                risk_score += 0.05

            # Factor 4: Subscription type risk (streaming, gaming higher risk)
            high_risk_categories = ["streaming", "streaming_video", "streaming_music", "gaming", "news", "creator"]
            if sub_category in high_risk_categories:
                risk_score += 0.15
                risk_factors.append(f"High-churn category: {sub_category}")

            # Factor 5: Multiple similar subscriptions
            similar_count = self._count_similar_subscriptions(rec_type, sub_category)
            if similar_count > 1:
                risk_score += 0.1 * min(similar_count - 1, 3)
                risk_factors.append(f"{similar_count} similar subscriptions active")

            # Factor 6: Overdue or missed payments
            if last_date:
                try:
                    last_d = date.fromisoformat(str(last_date))
                    days_since = (today - last_d).days
                    expected_interval = {"monthly": 35, "quarterly": 100, "annual": 380}.get(cadence, 35)
                    if days_since > expected_interval:
                        risk_score += 0.3
                        risk_factors.append(f"Possibly already cancelled ({days_since} days since last charge)")
                except (ValueError, TypeError):
                    pass

            # Normalize score to 0-1
            risk_score = max(0.0, min(1.0, risk_score))

            # Determine risk level
            if risk_score >= 0.7:
                risk_level = RiskLevel.HIGH
            elif risk_score >= 0.4:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW

            # Generate recommendation
            recommendation = self._generate_risk_recommendation(
                risk_level, risk_factors, display_name or name, amount
            )

            risks.append(CancellationRisk(
                series_id=sid,
                merchant=display_name or name,
                risk_level=risk_level,
                risk_score=round(risk_score, 3),
                risk_factors=risk_factors,
                recommendation=recommendation,
                potential_savings=float(annual_cost or amount * 12),
            ))

        # Sort by risk score (highest first)
        risks.sort(key=lambda x: x.risk_score, reverse=True)
        return risks[:limit]

    def _count_similar_subscriptions(self, rec_type: str, sub_category: str) -> int:
        """Count similar active subscriptions."""
        result = self.conn.execute("""
            SELECT COUNT(*) FROM recurring_series
            WHERE status = 'confirmed'
              AND recurring_type = ?
              AND sub_category = ?
        """, [rec_type, sub_category]).fetchone()
        return int(result[0]) if result else 0

    def _generate_risk_recommendation(
        self,
        risk_level: RiskLevel,
        factors: List[str],
        merchant: str,
        amount: float,
    ) -> str:
        """Generate recommendation based on risk factors."""
        if risk_level == RiskLevel.HIGH:
            if "price increase" in " ".join(factors).lower():
                return f"Consider cancelling {merchant} after recent price hike. Could save ${amount*12:.0f}/year."
            if "similar subscriptions" in " ".join(factors).lower():
                return f"Review if you need multiple similar services. Consider consolidating."
            return f"Review necessity of {merchant}. High cancellation likelihood detected."
        elif risk_level == RiskLevel.MEDIUM:
            return f"Monitor {merchant} usage. Consider downgrading if underutilized."
        else:
            return f"{merchant} appears to be providing good value. Keep monitoring."

    # =========================================================================
    # OPTIMIZATION SUGGESTIONS
    # =========================================================================

    def generate_optimization_suggestions(
        self,
        limit: int = 10,
    ) -> List[OptimizationSuggestion]:
        """Generate optimization suggestions for recurring charges.

        Suggestion types:
        - Cancel unused subscriptions
        - Downgrade plans
        - Consolidate similar services
        - Switch to annual billing
        - Negotiate better rates

        Args:
            limit: Maximum number of suggestions

        Returns:
            List of OptimizationSuggestion sorted by potential savings
        """
        suggestions = []

        # Get all confirmed recurring with details
        series = self.conn.execute("""
            SELECT
                rs.id, rs.name, rs.display_name, rs.cadence,
                rs.amount_mean, rs.recurring_type, rs.sub_category,
                rs.is_essential, rs.annual_cost
            FROM recurring_series rs
            WHERE rs.status = 'confirmed'
        """).fetchall()

        # Group by type and subcategory for consolidation analysis
        by_category: Dict[str, List] = defaultdict(list)
        for row in series:
            key = f"{row[5]}_{row[6]}"  # recurring_type_sub_category
            by_category[key].append(row)

        suggestion_id = 0

        # 1. Find consolidation opportunities (multiple streaming, etc.)
        for key, items in by_category.items():
            if len(items) > 1:
                rec_type, sub_cat = key.split("_", 1) if "_" in key else (key, "")
                if rec_type == "subscription" and sub_cat in ["streaming", "streaming_video", "streaming_music"]:
                    total_cost = sum(abs(float(i[4] or 0)) for i in items)
                    merchants = [i[2] or i[1] for i in items]

                    if len(items) >= 3:
                        # Suggest keeping 1-2 and cancelling rest
                        savings = total_cost * 0.5  # Assume cancel half
                        suggestion_id += 1
                        suggestions.append(OptimizationSuggestion(
                            suggestion_id=f"consolidate_{suggestion_id}",
                            title=f"Consolidate {len(items)} streaming services",
                            description=f"You have {len(items)} streaming subscriptions: {', '.join(merchants)}. Consider keeping 1-2 favorites.",
                            category="consolidate",
                            affected_series=[i[0] for i in items],
                            potential_monthly_savings=savings,
                            potential_annual_savings=savings * 12,
                            confidence=0.7,
                            action_steps=[
                                "Review which streaming services you use most",
                                "Check for overlap in content libraries",
                                "Consider rotating subscriptions monthly",
                                "Cancel least-used services",
                            ],
                            priority=1,
                        ))

        # 2. Find annual billing opportunities
        for row in series:
            sid, name, display_name, cadence, amount, rec_type, sub_cat, is_essential, annual_cost = row
            if cadence == "monthly" and rec_type == "subscription":
                amount = abs(float(amount or 0))
                # Typical annual discount is 15-20%
                potential_savings = amount * 12 * 0.17
                if potential_savings > 10:  # Only suggest if savings > $10/year
                    suggestion_id += 1
                    suggestions.append(OptimizationSuggestion(
                        suggestion_id=f"annual_{suggestion_id}",
                        title=f"Switch {display_name or name} to annual billing",
                        description=f"Annual subscriptions typically save 15-20%. Could save ~${potential_savings:.0f}/year.",
                        category="switch",
                        affected_series=[sid],
                        potential_monthly_savings=potential_savings / 12,
                        potential_annual_savings=potential_savings,
                        confidence=0.6,
                        action_steps=[
                            f"Check if {display_name or name} offers annual billing",
                            "Calculate if you'll use the service for a full year",
                            "Switch at next renewal if discount is available",
                        ],
                        priority=2,
                    ))

        # 3. Find high-cost discretionary items
        for row in series:
            sid, name, display_name, cadence, amount, rec_type, sub_cat, is_essential, annual_cost = row
            amount = abs(float(amount or 0))
            if not is_essential and amount > 50:  # High cost discretionary
                suggestion_id += 1
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=f"review_{suggestion_id}",
                    title=f"Review ${amount:.0f}/mo {display_name or name} subscription",
                    description=f"High-cost discretionary subscription. Annual cost: ${amount*12:.0f}.",
                    category="downgrade",
                    affected_series=[sid],
                    potential_monthly_savings=amount * 0.5,  # Assume downgrade saves 50%
                    potential_annual_savings=amount * 6,
                    confidence=0.5,
                    action_steps=[
                        "Review your usage of this service",
                        "Check for cheaper tier options",
                        "Consider if free alternatives exist",
                        "Set reminder to review at next renewal",
                    ],
                    priority=3,
                ))

        # 4. Find negotiation opportunities (bills, insurance)
        for row in series:
            sid, name, display_name, cadence, amount, rec_type, sub_cat, is_essential, annual_cost = row
            amount = abs(float(amount or 0))
            if rec_type in ("bill", "insurance") and amount > 100:
                suggestion_id += 1
                potential_savings = amount * 0.15  # Assume 15% negotiation success
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=f"negotiate_{suggestion_id}",
                    title=f"Negotiate {display_name or name} rate",
                    description=f"Bills and insurance are often negotiable. Could potentially save ${potential_savings:.0f}/mo.",
                    category="negotiate",
                    affected_series=[sid],
                    potential_monthly_savings=potential_savings,
                    potential_annual_savings=potential_savings * 12,
                    confidence=0.4,
                    action_steps=[
                        "Research competitor rates",
                        "Call and ask for loyalty discount",
                        "Threaten to switch providers if needed",
                        "Ask about bundle discounts",
                    ],
                    priority=4,
                ))

        # Sort by annual savings (highest first)
        suggestions.sort(key=lambda x: x.potential_annual_savings, reverse=True)
        return suggestions[:limit]

    # =========================================================================
    # NATURAL LANGUAGE INSIGHT GENERATION
    # =========================================================================

    def generate_insights(
        self,
        limit: int = 10,
    ) -> List[RecurringInsight]:
        """Generate natural language insights about recurring charges.

        Args:
            limit: Maximum number of insights

        Returns:
            List of RecurringInsight sorted by priority
        """
        insights = []
        today = date.today()

        # Get summary stats
        summary = self._get_recurring_summary()

        # 1. Total recurring spend insight
        if summary["total_monthly"] > 0:
            insights.append(RecurringInsight(
                insight_id="total_recurring",
                insight_type=InsightType.CASH_FLOW,
                title="Monthly Recurring Total",
                message=f"You have ${summary['total_monthly']:.0f} in recurring charges across {summary['total_count']} subscriptions and bills. That's ${summary['total_monthly']*12:.0f} annually.",
                data=summary,
                priority=1,
                expires_at=today + timedelta(days=7),
                actionable=True,
                action_label="View All",
                action_series_id=None,
            ))

        # 2. Essential vs discretionary breakdown
        if summary["discretionary_monthly"] > 0:
            pct = (summary["discretionary_monthly"] / max(1, summary["total_monthly"])) * 100
            insights.append(RecurringInsight(
                insight_id="discretionary_breakdown",
                insight_type=InsightType.OPTIMIZATION,
                title="Discretionary Spending",
                message=f"${summary['discretionary_monthly']:.0f}/mo ({pct:.0f}%) goes to discretionary subscriptions. Consider reviewing for savings opportunities.",
                data={"discretionary": summary["discretionary_monthly"], "percentage": pct},
                priority=2,
                expires_at=today + timedelta(days=14),
                actionable=True,
                action_label="Review Subscriptions",
                action_series_id=None,
            ))

        # 3. Upcoming payments (next 7 days)
        upcoming = self._get_upcoming_payments(days=7)
        if upcoming:
            total_upcoming = sum(p["amount"] for p in upcoming)
            insights.append(RecurringInsight(
                insight_id="upcoming_7days",
                insight_type=InsightType.UPCOMING_PAYMENT,
                title="Upcoming Payments",
                message=f"{len(upcoming)} payments totaling ${total_upcoming:.0f} expected in the next 7 days.",
                data={"payments": upcoming, "total": total_upcoming},
                priority=1,
                expires_at=today + timedelta(days=7),
                actionable=False,
                action_label=None,
                action_series_id=None,
            ))

        # 4. Price increase alerts
        price_hikes = self._get_recent_price_hikes()
        for hike in price_hikes[:3]:
            insights.append(RecurringInsight(
                insight_id=f"price_hike_{hike['series_id']}",
                insight_type=InsightType.PRICE_ALERT,
                title=f"Price Increase: {hike['merchant']}",
                message=f"{hike['merchant']} recently increased their price. Review if still worth it.",
                data=hike,
                priority=1,
                expires_at=today + timedelta(days=30),
                actionable=True,
                action_label="Review",
                action_series_id=hike["series_id"],
            ))

        # 5. High cancellation risk items
        risks = self.calculate_cancellation_risks(limit=3)
        for risk in risks:
            if risk.risk_level in (RiskLevel.HIGH, RiskLevel.MEDIUM):
                insights.append(RecurringInsight(
                    insight_id=f"risk_{risk.series_id}",
                    insight_type=InsightType.CANCELLATION_RISK,
                    title=f"Consider: {risk.merchant}",
                    message=risk.recommendation,
                    data={
                        "series_id": risk.series_id,
                        "risk_score": risk.risk_score,
                        "savings": risk.potential_savings,
                    },
                    priority=2 if risk.risk_level == RiskLevel.HIGH else 3,
                    expires_at=today + timedelta(days=14),
                    actionable=True,
                    action_label="Review",
                    action_series_id=risk.series_id,
                ))

        # 6. Savings opportunities
        optimizations = self.generate_optimization_suggestions(limit=3)
        for opt in optimizations:
            if opt.potential_annual_savings > 50:
                insights.append(RecurringInsight(
                    insight_id=f"savings_{opt.suggestion_id}",
                    insight_type=InsightType.SAVINGS_OPPORTUNITY,
                    title=opt.title,
                    message=f"{opt.description} Save up to ${opt.potential_annual_savings:.0f}/year.",
                    data={
                        "suggestion_id": opt.suggestion_id,
                        "savings": opt.potential_annual_savings,
                        "category": opt.category,
                    },
                    priority=2,
                    expires_at=today + timedelta(days=30),
                    actionable=True,
                    action_label="View Details",
                    action_series_id=opt.affected_series[0] if opt.affected_series else None,
                ))

        # Sort by priority
        insights.sort(key=lambda x: x.priority)
        return insights[:limit]

    def _get_recurring_summary(self) -> Dict[str, Any]:
        """Get summary statistics for recurring charges."""
        result = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN cadence = 'monthly' THEN ABS(amount_mean)
                         WHEN cadence = 'weekly' THEN ABS(amount_mean) * 4.33
                         WHEN cadence = 'biweekly' THEN ABS(amount_mean) * 2.17
                         WHEN cadence = 'quarterly' THEN ABS(amount_mean) / 3
                         WHEN cadence = 'semi_annual' THEN ABS(amount_mean) / 6
                         WHEN cadence = 'annual' THEN ABS(amount_mean) / 12
                         ELSE ABS(amount_mean) END) as monthly_total,
                SUM(CASE WHEN is_essential THEN
                    CASE WHEN cadence = 'monthly' THEN ABS(amount_mean)
                         WHEN cadence = 'weekly' THEN ABS(amount_mean) * 4.33
                         ELSE ABS(amount_mean) END
                    ELSE 0 END) as essential_monthly,
                SUM(CASE WHEN NOT is_essential OR is_essential IS NULL THEN
                    CASE WHEN cadence = 'monthly' THEN ABS(amount_mean)
                         WHEN cadence = 'weekly' THEN ABS(amount_mean) * 4.33
                         ELSE ABS(amount_mean) END
                    ELSE 0 END) as discretionary_monthly
            FROM recurring_series
            WHERE status = 'confirmed'
        """).fetchone()

        return {
            "total_count": int(result[0] or 0),
            "total_monthly": float(result[1] or 0),
            "essential_monthly": float(result[2] or 0),
            "discretionary_monthly": float(result[3] or 0),
        }

    def _get_upcoming_payments(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get payments expected in the next N days."""
        today = date.today()
        end_date = today + timedelta(days=days)

        result = self.conn.execute("""
            SELECT id, display_name, name, amount_mean, next_date
            FROM recurring_series
            WHERE status = 'confirmed'
              AND next_date >= CAST(? AS DATE)
              AND next_date <= CAST(? AS DATE)
            ORDER BY next_date
        """, [today.isoformat(), end_date.isoformat()]).fetchall()

        return [
            {
                "series_id": r[0],
                "merchant": r[1] or r[2],
                "amount": abs(float(r[3] or 0)),
                "date": str(r[4]),
            }
            for r in result
        ]

    def _get_recent_price_hikes(self) -> List[Dict[str, Any]]:
        """Get series with recent price increases."""
        result = self.conn.execute("""
            SELECT id, display_name, name, amount_mean
            FROM recurring_series
            WHERE status = 'confirmed'
              AND price_hike = TRUE
        """).fetchall()

        return [
            {
                "series_id": r[0],
                "merchant": r[1] or r[2],
                "amount": abs(float(r[3] or 0)),
            }
            for r in result
        ]


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_insights_engine: Optional[RecurringInsightsEngine] = None


def get_recurring_insights_engine() -> RecurringInsightsEngine:
    """Get the global recurring insights engine instance."""
    global _insights_engine
    if _insights_engine is None:
        _insights_engine = RecurringInsightsEngine()
    return _insights_engine
