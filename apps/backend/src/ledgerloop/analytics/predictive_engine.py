"""
Phase 1 Predictive Analytics Engine

Enhances the existing AI analytics with predictive capabilities:
- Spending pattern analysis with caching
- Cash flow forecasting with seasonal adjustments
- Smart insights generation
- Prediction accuracy tracking
"""

from __future__ import annotations

import math
import statistics
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, date
from collections import defaultdict
from enum import Enum

from ..db import get_conn
from ..ai_analytics import TrendDirection, SpendingPattern
from ..ai_forecasting import ForecastConfidence, ForecastPoint


@dataclass
class PredictivePattern:
    """Enhanced spending pattern with prediction capabilities"""
    category_id: Optional[str]
    category_name: str
    monthly_avg: float
    trend_factor: float
    seasonal_factors: Dict[int, float]  # month -> multiplier
    volatility: float
    confidence: float
    pattern_type: str
    last_updated: datetime


@dataclass
class CashFlowPrediction:
    """Cash flow prediction for a specific month"""
    target_month: str
    predicted_income: float
    predicted_spending: float
    net_cash_flow: float
    spending_breakdown: Dict[str, float]
    confidence: float
    methodology: str
    assumptions: List[str]


@dataclass
class SmartInsight:
    """Actionable financial insight"""
    insight_type: str
    priority: int
    title: str
    message: str
    amount: Optional[float]
    category_id: Optional[str]
    transaction_id: Optional[str]
    action_text: str
    valid_until: Optional[date]


class PredictiveAnalyticsEngine:
    """Phase 1 predictive analytics engine"""
    
    def __init__(self):
        self.conn = get_conn()
    
    def analyze_spending_patterns(self, account_id: str = "default", force_refresh: bool = False) -> List[PredictivePattern]:
        """Analyze spending patterns with caching for performance"""
        
        # Check cache first unless forced refresh
        if not force_refresh:
            cached_patterns = self._get_cached_patterns(account_id)
            if cached_patterns:
                return cached_patterns
        
        # Analyze patterns from scratch
        patterns = self._compute_spending_patterns(account_id)
        
        # Cache results
        self._cache_spending_patterns(account_id, patterns)
        
        return patterns
    
    def _compute_spending_patterns(self, account_id: str) -> List[PredictivePattern]:
        """Compute spending patterns from transaction data"""
        
        # Get historical transaction data (12 months)
        query = """
            SELECT 
                COALESCE(c.id, 'uncategorized') as category_id,
                COALESCE(c.name, 'Uncategorized') as category_name,
                strftime('%Y-%m', t.posted_at) as month_year,
                strftime('%m', t.posted_at) as month_num,
                SUM(ABS(t.amount)) as total_spent,
                COUNT(*) as transaction_count
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON t.id = tc.tx_id
            LEFT JOIN category c ON tc.category_id = c.id
            WHERE t.account_id = ? 
                AND t.amount < 0  -- Only expenses
                AND t.posted_at >= current_date - INTERVAL 12 MONTH
                AND NOT EXISTS (
                    SELECT 1 FROM match_transfer mt 
                    WHERE (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) 
                    AND mt.decided_at IS NOT NULL
                )
            GROUP BY category_id, category_name, month_year, month_num
            ORDER BY category_name, month_year
        """
        
        rows = self.conn.execute(query, [account_id]).fetchall()
        
        # Group by category
        category_data = defaultdict(list)
        for row in rows:
            category_id, category_name, month_year, month_num, total_spent, tx_count = row
            category_data[category_id].append({
                'category_name': category_name,
                'month_year': month_year,
                'month_num': int(month_num),
                'amount': float(total_spent),
                'count': tx_count
            })
        
        patterns = []
        for category_id, monthly_data in category_data.items():
            if len(monthly_data) < 2:  # Need at least 2 months of data
                continue
                
            pattern = self._analyze_category_pattern(category_id, monthly_data)
            if pattern:
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_category_pattern(self, category_id: str, monthly_data: List[Dict]) -> Optional[PredictivePattern]:
        """Analyze pattern for a specific category"""
        
        if not monthly_data:
            return None
        
        category_name = monthly_data[0]['category_name']
        amounts = [d['amount'] for d in monthly_data]
        
        # Calculate basic statistics
        monthly_avg = statistics.mean(amounts)
        volatility = statistics.stdev(amounts) / monthly_avg if monthly_avg > 0 else 0
        
        # Calculate trend
        trend_factor = self._calculate_trend(amounts)
        
        # Calculate seasonal patterns
        seasonal_factors = self._calculate_seasonal_factors(monthly_data)
        
        # Determine pattern type
        pattern_type = self._determine_pattern_type(amounts, trend_factor, volatility)
        
        # Calculate confidence based on data quality
        confidence = min(1.0, len(monthly_data) / 6) * (1 - min(volatility, 1.0))
        
        return PredictivePattern(
            category_id=category_id if category_id != 'uncategorized' else None,
            category_name=category_name,
            monthly_avg=monthly_avg,
            trend_factor=trend_factor,
            seasonal_factors=seasonal_factors,
            volatility=volatility,
            confidence=confidence,
            pattern_type=pattern_type,
            last_updated=datetime.now()
        )
    
    def _calculate_trend(self, amounts: List[float]) -> float:
        """Calculate linear trend in spending amounts"""
        if len(amounts) < 2:
            return 0.0
        
        n = len(amounts)
        x = list(range(n))
        
        # Simple linear regression
        sum_x = sum(x)
        sum_y = sum(amounts)
        sum_xy = sum(x[i] * amounts[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope
    
    def _calculate_seasonal_factors(self, monthly_data: List[Dict]) -> Dict[int, float]:
        """Calculate seasonal multipliers for each month"""
        
        # Group by month number
        month_amounts = defaultdict(list)
        for data in monthly_data:
            month_amounts[data['month_num']].append(data['amount'])
        
        # Calculate average for each month
        monthly_avgs = {}
        for month, amounts in month_amounts.items():
            monthly_avgs[month] = statistics.mean(amounts)
        
        # Calculate overall average
        overall_avg = statistics.mean(monthly_avgs.values()) if monthly_avgs else 1.0
        
        # Calculate seasonal factors
        seasonal_factors = {}
        for month, avg in monthly_avgs.items():
            seasonal_factors[month] = avg / overall_avg if overall_avg > 0 else 1.0
        
        return seasonal_factors
    
    def _determine_pattern_type(self, amounts: List[float], trend_factor: float, volatility: float) -> str:
        """Determine the type of spending pattern"""
        
        if volatility > 0.5:
            return "sporadic"
        elif abs(trend_factor) > statistics.mean(amounts) * 0.1:
            return "increasing" if trend_factor > 0 else "decreasing"
        elif len(amounts) >= 6:  # Need enough data for seasonal analysis
            return "seasonal"
        else:
            return "regular"
    
    def _cache_spending_patterns(self, account_id: str, patterns: List[PredictivePattern]) -> None:
        """Cache spending patterns for performance"""
        
        try:
            # Check if table exists first
            tables = self.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            if 'spending_patterns' not in table_names:
                return  # Skip caching if table doesn't exist
                
            # Clear existing cache for this account
            self.conn.execute("DELETE FROM spending_patterns WHERE account_id = ?", [account_id])
            
            # Insert new patterns
            for pattern in patterns:
                pattern_id = str(uuid.uuid4())
                self.conn.execute("""
                    INSERT INTO spending_patterns (
                        id, account_id, category_id, category_name, month_year, 
                        amount_avg, amount_trend, volatility, confidence_score, pattern_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    pattern_id, account_id, pattern.category_id, pattern.category_name,
                    datetime.now().strftime('%Y-%m'), pattern.monthly_avg, pattern.trend_factor,
                    pattern.volatility, pattern.confidence, pattern.pattern_type
                ])
        except Exception:
            # Fail silently if caching doesn't work
            pass
    
    def _get_cached_patterns(self, account_id: str) -> Optional[List[PredictivePattern]]:
        """Get cached spending patterns if recent enough"""
        
        # Check if we have recent cached data (last 24 hours)
        query = """
            SELECT category_id, category_name, amount_avg, amount_trend, 
                   volatility, confidence_score, pattern_type, updated_at
            FROM spending_patterns 
            WHERE account_id = ? 
                AND updated_at > current_timestamp - INTERVAL 1 DAY
        """
        
        try:
            # Check if table exists first
            tables = self.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            if 'spending_patterns' not in table_names:
                return None
            rows = self.conn.execute(query, [account_id]).fetchall()
        except Exception:
            return None
        
        if not rows:
            return None
        
        patterns = []
        for row in rows:
            category_id, category_name, amount_avg, amount_trend, volatility, confidence, pattern_type, updated_at = row
            
            # Get seasonal factors from separate table
            seasonal_query = """
                SELECT month_number, seasonal_multiplier 
                FROM seasonal_patterns 
                WHERE category_id = ? OR (category_id IS NULL AND ? IS NULL)
            """
            try:
                if 'seasonal_patterns' in table_names:
                    seasonal_rows = self.conn.execute(seasonal_query, [category_id, category_id]).fetchall()
                    seasonal_factors = {int(row[0]): float(row[1]) for row in seasonal_rows}
                else:
                    seasonal_factors = {}
            except Exception:
                seasonal_factors = {}
            
            patterns.append(PredictivePattern(
                category_id=category_id,
                category_name=category_name,
                monthly_avg=amount_avg,
                trend_factor=amount_trend,
                seasonal_factors=seasonal_factors,
                volatility=volatility,
                confidence=confidence,
                pattern_type=pattern_type,
                last_updated=datetime.fromisoformat(updated_at)
            ))
        
        return patterns
    
    def forecast_cash_flow(self, account_id: str = "default", months_ahead: int = 6) -> List[CashFlowPrediction]:
        """Forecast cash flow for the specified number of months"""
        
        # Get spending patterns
        patterns = self.analyze_spending_patterns(account_id)
        
        # Get income patterns
        income_pattern = self._analyze_income_pattern(account_id)
        
        # Generate predictions for each month
        predictions = []
        current_date = datetime.now()
        
        for month_offset in range(1, months_ahead + 1):
            target_date = current_date + timedelta(days=30 * month_offset)
            target_month = target_date.strftime('%Y-%m')
            target_month_num = target_date.month
            
            # Predict spending by category
            spending_breakdown = {}
            total_predicted_spending = 0.0
            
            for pattern in patterns:
                # Base prediction from trend
                base_amount = pattern.monthly_avg + (pattern.trend_factor * month_offset)
                
                # Apply seasonal adjustment
                seasonal_multiplier = pattern.seasonal_factors.get(target_month_num, 1.0)
                predicted_amount = base_amount * seasonal_multiplier
                
                # Ensure non-negative
                predicted_amount = max(0, predicted_amount)
                
                spending_breakdown[pattern.category_name] = predicted_amount
                total_predicted_spending += predicted_amount
            
            # Predict income
            predicted_income = self._predict_monthly_income(income_pattern, month_offset)
            
            # Calculate net cash flow
            net_cash_flow = predicted_income - total_predicted_spending
            
            # Calculate confidence based on pattern confidence
            avg_confidence = statistics.mean([p.confidence for p in patterns]) if patterns else 0.5
            confidence = avg_confidence * (1 - (month_offset - 1) * 0.1)  # Decay confidence over time
            
            predictions.append(CashFlowPrediction(
                target_month=target_month,
                predicted_income=predicted_income,
                predicted_spending=total_predicted_spending,
                net_cash_flow=net_cash_flow,
                spending_breakdown=spending_breakdown,
                confidence=max(0.1, confidence),
                methodology="pattern_analysis_with_seasonality",
                assumptions=[
                    "Based on historical spending patterns",
                    "Seasonal adjustments applied",
                    "Linear trend extrapolation"
                ]
            ))
        
        # Cache predictions
        self._cache_predictions(account_id, predictions)
        
        return predictions
    
    def _analyze_income_pattern(self, account_id: str) -> Dict[str, float]:
        """Analyze income patterns for prediction"""
        
        query = """
            SELECT 
                strftime('%Y-%m', posted_at) as month_year,
                SUM(amount) as monthly_income
            FROM [transaction] 
            WHERE account_id = ? 
                AND amount > 0 
                AND (is_income = TRUE OR amount > 1000)
                AND posted_at >= current_date - INTERVAL 12 MONTH
                AND NOT EXISTS (
                    SELECT 1 FROM match_transfer mt 
                    WHERE (id = mt.left_tx_id OR id = mt.right_tx_id) 
                    AND mt.decided_at IS NOT NULL
                )
            GROUP BY month_year
            ORDER BY month_year
        """
        
        rows = self.conn.execute(query, [account_id]).fetchall()
        
        if not rows:
            return {'avg_income': 0, 'trend': 0, 'confidence': 0}
        
        incomes = [float(row[1]) for row in rows]
        
        return {
            'avg_income': statistics.mean(incomes),
            'trend': self._calculate_trend(incomes),
            'confidence': min(1.0, len(incomes) / 6)
        }
    
    def _predict_monthly_income(self, income_pattern: Dict[str, float], month_offset: int) -> float:
        """Predict income for a specific month offset"""
        
        base_income = income_pattern.get('avg_income', 0)
        trend = income_pattern.get('trend', 0)
        
        # Apply trend
        predicted_income = base_income + (trend * month_offset)
        
        return max(0, predicted_income)
    
    def _cache_predictions(self, account_id: str, predictions: List[CashFlowPrediction]) -> None:
        """Cache predictions for future reference and accuracy tracking"""
        
        for prediction in predictions:
            prediction_id = str(uuid.uuid4())
            
            # Cache cash flow prediction
            self.conn.execute("""
                INSERT INTO predictions (
                    id, account_id, prediction_type, target_month,
                    predicted_amount, confidence, methodology
                ) VALUES (?, ?, 'cashflow', ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    predicted_amount = EXCLUDED.predicted_amount,
                    confidence = EXCLUDED.confidence,
                    methodology = EXCLUDED.methodology
            """, [
                prediction_id, account_id, prediction.target_month,
                prediction.net_cash_flow, prediction.confidence, prediction.methodology
            ])

            # Cache spending prediction
            spending_prediction_id = str(uuid.uuid4())
            self.conn.execute("""
                INSERT INTO predictions (
                    id, account_id, prediction_type, target_month,
                    predicted_amount, confidence, methodology
                ) VALUES (?, ?, 'spending', ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    predicted_amount = EXCLUDED.predicted_amount,
                    confidence = EXCLUDED.confidence,
                    methodology = EXCLUDED.methodology
            """, [
                spending_prediction_id, account_id, prediction.target_month,
                prediction.predicted_spending, prediction.confidence, prediction.methodology
            ])

            # Cache income prediction
            income_prediction_id = str(uuid.uuid4())
            self.conn.execute("""
                INSERT INTO predictions (
                    id, account_id, prediction_type, target_month,
                    predicted_amount, confidence, methodology
                ) VALUES (?, ?, 'income', ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    predicted_amount = EXCLUDED.predicted_amount,
                    confidence = EXCLUDED.confidence,
                    methodology = EXCLUDED.methodology
            """, [
                income_prediction_id, account_id, prediction.target_month,
                prediction.predicted_income, prediction.confidence, prediction.methodology
            ])
    
    def generate_smart_insights(self, account_id: str = "default") -> List[SmartInsight]:
        """Generate actionable financial insights"""
        
        insights = []
        current_month = datetime.now().strftime('%Y-%m')
        
        # Get current month spending so far
        current_spending = self._get_month_to_date_spending(account_id, current_month)
        
        # Get predictions for this month
        predictions = self.forecast_cash_flow(account_id, 1)
        if predictions:
            current_prediction = predictions[0]
            
            # Spending trend insights
            days_into_month = datetime.now().day
            projected_month_end = current_spending * (30 / days_into_month)
            
            if projected_month_end > current_prediction.predicted_spending * 1.15:
                variance_pct = ((projected_month_end - current_prediction.predicted_spending) / 
                              current_prediction.predicted_spending * 100)
                
                insights.append(SmartInsight(
                    insight_type="spending_alert",
                    priority=9,
                    title="Overspending Alert",
                    message=f"You're on track to spend {variance_pct:.0f}% more than predicted this month",
                    amount=projected_month_end - current_prediction.predicted_spending,
                    category_id=None,
                    transaction_id=None,
                    action_text="Review your discretionary spending categories",
                    valid_until=date.today() + timedelta(days=7)
                ))
        
        # Unusual transaction insights
        unusual_insights = self._detect_unusual_transactions(account_id)
        insights.extend(unusual_insights)
        
        # Budget variance insights
        budget_insights = self._analyze_budget_variance(account_id)
        insights.extend(budget_insights)
        
        # Savings opportunity insights
        savings_insights = self._identify_savings_opportunities(account_id)
        insights.extend(savings_insights)
        
        # Cache insights
        self._cache_insights(account_id, insights)
        
        return sorted(insights, key=lambda x: x.priority, reverse=True)
    
    def _get_month_to_date_spending(self, account_id: str, month: str) -> float:
        """Get spending for current month up to today"""
        
        query = """
            SELECT SUM(ABS(amount))
            FROM [transaction] 
            WHERE account_id = ? 
                AND amount < 0
                AND strftime('%Y-%m', posted_at) = ?
                AND NOT EXISTS (
                    SELECT 1 FROM match_transfer mt 
                    WHERE (id = mt.left_tx_id OR id = mt.right_tx_id) 
                    AND mt.decided_at IS NOT NULL
                )
        """
        
        result = self.conn.execute(query, [account_id, month]).fetchone()
        return float(result[0]) if result[0] else 0.0
    
    def _detect_unusual_transactions(self, account_id: str) -> List[SmartInsight]:
        """Detect unusual transactions in the last 7 days"""
        
        query = """
            SELECT t.id, t.amount, t.description_norm, t.posted_at, c.name as category_name
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON t.id = tc.tx_id
            LEFT JOIN category c ON tc.category_id = c.id
            WHERE t.account_id = ?
                AND t.amount < 0
                AND t.posted_at >= current_date - INTERVAL 7 DAY
                AND ABS(t.amount) > (
                    SELECT COALESCE(AVG(ABS(amount)) * 2.5, 50)
                    FROM [transaction] 
                    WHERE account_id = ? AND amount < 0
                )
            ORDER BY ABS(t.amount) DESC
            LIMIT 5
        """
        
        rows = self.conn.execute(query, [account_id, account_id]).fetchall()
        
        insights = []
        for row in rows:
            tx_id, amount, description, posted_at, category = row
            
            insights.append(SmartInsight(
                insight_type="unusual_transaction",
                priority=7,
                title="Unusual Transaction Detected",
                message=f"Large ${abs(amount):.2f} transaction in {category or 'Unknown'} category",
                amount=abs(amount),
                category_id=None,
                transaction_id=tx_id,
                action_text="Review if this was expected",
                valid_until=date.today() + timedelta(days=14)
            ))
        
        return insights
    
    def _analyze_budget_variance(self, account_id: str) -> List[SmartInsight]:
        """Analyze budget variance by comparing to historical patterns"""
        
        patterns = self.analyze_spending_patterns(account_id)
        current_month = datetime.now().strftime('%Y-%m')
        
        insights = []
        
        for pattern in patterns:
            if pattern.confidence < 0.3:  # Skip low-confidence patterns
                continue
            
            current_spending = self._get_category_month_spending(account_id, pattern.category_id, current_month)
            expected_spending = pattern.monthly_avg
            
            if current_spending > expected_spending * 1.3:  # 30% over average
                variance_pct = ((current_spending - expected_spending) / expected_spending * 100)
                
                insights.append(SmartInsight(
                    insight_type="budget_variance",
                    priority=6,
                    title="Category Over Budget",
                    message=f"{pattern.category_name} spending is {variance_pct:.0f}% above normal",
                    amount=current_spending - expected_spending,
                    category_id=pattern.category_id,
                    transaction_id=None,
                    action_text="Consider reducing spending in this category",
                    valid_until=date.today() + timedelta(days=5)
                ))
        
        return insights
    
    def _get_category_month_spending(self, account_id: str, category_id: Optional[str], month: str) -> float:
        """Get spending for a specific category in a specific month"""
        
        if category_id:
            query = """
                SELECT SUM(ABS(t.amount))
                FROM [transaction] t
                JOIN transaction_category tc ON t.id = tc.tx_id
                WHERE t.account_id = ? 
                    AND tc.category_id = ?
                    AND t.amount < 0
                    AND strftime('%Y-%m', t.posted_at) = ?
            """
            result = self.conn.execute(query, [account_id, category_id, month]).fetchone()
        else:
            query = """
                SELECT SUM(ABS(amount))
                FROM [transaction] 
                WHERE account_id = ? 
                    AND amount < 0
                    AND strftime('%Y-%m', posted_at) = ?
                    AND id NOT IN (SELECT tx_id FROM transaction_category)
            """
            result = self.conn.execute(query, [account_id, month]).fetchone()
        
        return float(result[0]) if result[0] else 0.0
    
    def _identify_savings_opportunities(self, account_id: str) -> List[SmartInsight]:
        """Identify potential savings opportunities"""
        
        # Find top merchants in discretionary categories
        query = """
            SELECT t.description_norm as merchant,
                   c.name as category_name,
                   SUM(ABS(t.amount)) as total_spent,
                   COUNT(*) as frequency
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON t.id = tc.tx_id
            LEFT JOIN category c ON tc.category_id = c.id
            WHERE t.account_id = ?
                AND t.amount < 0
                AND t.posted_at >= current_date - INTERVAL 3 MONTH
                AND c.name IN ('Dining', 'Entertainment', 'Shopping', 'Subscriptions')
            GROUP BY merchant, category_name
            HAVING total_spent > 100 AND frequency >= 3
            ORDER BY total_spent DESC
            LIMIT 5
        """
        
        rows = self.conn.execute(query, [account_id]).fetchall()
        
        insights = []
        for row in rows:
            merchant, category, total_spent, frequency = row
            potential_savings = total_spent * 0.15  # Assume 15% reduction potential
            
            insights.append(SmartInsight(
                insight_type="savings_opportunity",
                priority=5,
                title="Savings Opportunity",
                message=f"You could save ~${potential_savings:.0f}/month by reducing {merchant} visits",
                amount=potential_savings,
                category_id=None,
                transaction_id=None,
                action_text="Consider alternatives or set a budget limit",
                valid_until=date.today() + timedelta(days=30)
            ))
        
        return insights
    
    def _cache_insights(self, account_id: str, insights: List[SmartInsight]) -> None:
        """Cache insights to avoid regenerating frequently"""
        
        # Clear old insights for this account
        self.conn.execute("""
            DELETE FROM smart_insights 
            WHERE account_id = ? 
                AND (is_dismissed = TRUE OR valid_until < current_date)
        """, [account_id])
        
        # Insert new insights
        for insight in insights:
            insight_id = str(uuid.uuid4())
            self.conn.execute("""
                INSERT INTO smart_insights (
                    id, account_id, insight_type, priority, title, message,
                    amount, category_id, transaction_id, action_text, valid_until
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
            """, [
                insight_id, account_id, insight.insight_type, insight.priority,
                insight.title, insight.message, insight.amount, insight.category_id,
                insight.transaction_id, insight.action_text, insight.valid_until
            ])


# Global instance
_predictive_engine = None

def get_predictive_engine() -> PredictiveAnalyticsEngine:
    """Get the global predictive analytics engine instance"""
    global _predictive_engine
    if _predictive_engine is None:
        _predictive_engine = PredictiveAnalyticsEngine()
    return _predictive_engine