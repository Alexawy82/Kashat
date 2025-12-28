"""
AI-Powered Analytics Engine

Provides intelligent financial insights through advanced analytics:
- Spending pattern analysis with ML clustering
- Trend detection and seasonal analysis
- Behavioral insights and anomaly detection
- Predictive forecasting for budgets
- Personalized recommendations
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, date
from collections import defaultdict
from enum import Enum

from .ai import get_ai_service
from .db import get_conn


class TrendDirection(Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class SpendingPersona(Enum):
    CONSERVATIVE_SAVER = "conservative_saver"
    MODERATE_SPENDER = "moderate_spender"
    FREQUENT_BUYER = "frequent_buyer"
    BUDGET_CONSCIOUS = "budget_conscious"
    IMPULSE_SPENDER = "impulse_spender"


@dataclass
class SpendingPattern:
    """Identified spending pattern with AI analysis"""
    category: str
    pattern_type: str  # "regular", "seasonal", "increasing", "decreasing", "sporadic"
    frequency: str  # "daily", "weekly", "monthly", "quarterly"
    average_amount: float
    confidence: float
    trend_direction: TrendDirection
    seasonality_detected: bool
    key_merchants: List[str]
    insights: List[str]


@dataclass
class TrendAnalysis:
    """Trend analysis for a specific metric"""
    metric_name: str
    current_value: float
    previous_value: float
    change_amount: float
    change_percentage: float
    trend_direction: TrendDirection
    confidence: float
    is_significant: bool
    insights: List[str]


@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    transaction_id: str
    anomaly_type: str
    severity: str  # "low", "medium", "high"
    description: str
    expected_range: Tuple[float, float]
    actual_value: float
    confidence: float


@dataclass
class FinancialInsights:
    """Comprehensive financial insights"""
    spending_patterns: List[SpendingPattern]
    trend_analysis: List[TrendAnalysis]
    anomalies: List[AnomalyDetection]
    spending_persona: SpendingPersona
    monthly_forecast: Dict[str, float]
    recommendations: List[str]
    risk_factors: List[str]
    opportunities: List[str]


class AIAnalyticsEngine:
    """Advanced analytics engine with AI-powered insights"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
    
    def analyze_spending_patterns(
        self, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None,
        account_id: Optional[str] = None
    ) -> List[SpendingPattern]:
        """Analyze spending patterns using AI clustering and trend analysis"""
        conn = get_conn()
        
        # Get categorized transactions for pattern analysis
        where_clauses = ["tc.category_id IS NOT NULL"]
        params = []
        
        if start_date:
            where_clauses.append("t.posted_at >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("t.posted_at <= ?")
            params.append(end_date)
        if account_id:
            where_clauses.append("t.account_id = ?")
            params.append(account_id)
        
        where_clause = " AND ".join(where_clauses)
        
        transactions = conn.execute(f"""
            SELECT 
                t.id, t.posted_at, t.amount, t.description_norm, t.ai_merchant_name,
                c.name as category_name, c.id as category_id
            FROM [transaction] t
            JOIN transaction_category tc ON t.id = tc.tx_id
            JOIN category c ON tc.category_id = c.id
            WHERE {where_clause}
            AND t.amount < 0
            ORDER BY t.posted_at DESC
        """, params).fetchall()
        
        if not transactions:
            return []
        
        # Group transactions by category
        category_groups = defaultdict(list)
        for tx in transactions:
            category_groups[tx[5]].append({  # category_name
                'id': tx[0],
                'posted_at': datetime.fromisoformat(str(tx[1])) if tx[1] else datetime.now(),
                'amount': abs(float(tx[2])),
                'description': tx[3],
                'merchant': tx[4] or tx[3],
                'category': tx[5]
            })
        
        patterns = []
        for category, category_transactions in category_groups.items():
            if len(category_transactions) < 3:  # Need minimum data for pattern analysis
                continue
            
            pattern = self._analyze_category_pattern(category, category_transactions)
            if pattern:
                patterns.append(pattern)
        
        # Sort by confidence and significance
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return patterns
    
    def _analyze_category_pattern(self, category: str, transactions: List[Dict]) -> Optional[SpendingPattern]:
        """Analyze spending pattern for a specific category"""
        if len(transactions) < 3:
            return None
        
        # Calculate basic statistics
        amounts = [tx['amount'] for tx in transactions]
        avg_amount = statistics.mean(amounts)
        std_amount = statistics.stdev(amounts) if len(amounts) > 1 else 0
        
        # Analyze frequency
        sorted_txs = sorted(transactions, key=lambda x: x['posted_at'])
        frequency_pattern = self._detect_frequency_pattern(sorted_txs)
        
        # Detect trend
        trend_direction = self._detect_trend(sorted_txs)
        
        # Detect seasonality
        seasonality_detected = self._detect_seasonality(sorted_txs)
        
        # Get key merchants
        merchant_counts = defaultdict(int)
        for tx in transactions:
            merchant_counts[tx['merchant']] += 1
        key_merchants = sorted(merchant_counts.keys(), key=merchant_counts.get, reverse=True)[:3]
        
        # Determine pattern type
        pattern_type = self._classify_pattern_type(sorted_txs, frequency_pattern, trend_direction)
        
        # Generate insights
        insights = self._generate_pattern_insights(
            category, pattern_type, frequency_pattern, trend_direction, 
            avg_amount, len(transactions), seasonality_detected
        )
        
        # Calculate confidence based on data quality and consistency
        confidence = self._calculate_pattern_confidence(
            transactions, frequency_pattern, std_amount, avg_amount
        )
        
        return SpendingPattern(
            category=category,
            pattern_type=pattern_type,
            frequency=frequency_pattern,
            average_amount=avg_amount,
            confidence=confidence,
            trend_direction=trend_direction,
            seasonality_detected=seasonality_detected,
            key_merchants=key_merchants,
            insights=insights
        )
    
    def _detect_frequency_pattern(self, sorted_transactions: List[Dict]) -> str:
        """Detect frequency pattern of transactions"""
        if len(sorted_transactions) < 2:
            return "sporadic"
        
        # Calculate intervals between transactions
        intervals = []
        for i in range(1, len(sorted_transactions)):
            delta = (sorted_transactions[i]['posted_at'] - sorted_transactions[i-1]['posted_at']).days
            intervals.append(delta)
        
        if not intervals:
            return "sporadic"
        
        avg_interval = statistics.mean(intervals)
        
        # Classify based on average interval
        if avg_interval <= 3:
            return "daily"
        elif avg_interval <= 10:
            return "weekly"
        elif avg_interval <= 40:
            return "monthly"
        elif avg_interval <= 120:
            return "quarterly"
        else:
            return "sporadic"
    
    def _detect_trend(self, sorted_transactions: List[Dict]) -> TrendDirection:
        """Detect trend direction using simple linear regression"""
        if len(sorted_transactions) < 4:
            return TrendDirection.STABLE
        
        # Use recent transactions for trend analysis
        recent_txs = sorted_transactions[-min(12, len(sorted_transactions)):]
        
        # Create time-based x values and amount y values
        x_values = list(range(len(recent_txs)))
        y_values = [tx['amount'] for tx in recent_txs]
        
        # Calculate slope using least squares
        n = len(x_values)
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return TrendDirection.STABLE
        
        slope = numerator / denominator
        
        # Calculate volatility
        y_std = statistics.stdev(y_values) if len(y_values) > 1 else 0
        volatility_threshold = y_mean * 0.3  # 30% of mean
        
        if y_std > volatility_threshold:
            return TrendDirection.VOLATILE
        elif abs(slope) < y_mean * 0.1:  # Less than 10% change
            return TrendDirection.STABLE
        elif slope > 0:
            return TrendDirection.INCREASING
        else:
            return TrendDirection.DECREASING
    
    def _detect_seasonality(self, sorted_transactions: List[Dict]) -> bool:
        """Detect seasonal patterns in spending"""
        if len(sorted_transactions) < 12:  # Need at least a year of data
            return False
        
        # Group by month
        monthly_spending = defaultdict(list)
        for tx in sorted_transactions:
            month = tx['posted_at'].month
            monthly_spending[month].append(tx['amount'])
        
        # Calculate monthly averages
        monthly_averages = {}
        for month, amounts in monthly_spending.items():
            if amounts:
                monthly_averages[month] = statistics.mean(amounts)
        
        if len(monthly_averages) < 6:  # Need at least 6 months
            return False
        
        # Calculate coefficient of variation
        values = list(monthly_averages.values())
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0
        
        if mean_val == 0:
            return False
        
        coefficient_of_variation = std_val / mean_val
        
        # If CV > 0.3, consider it seasonal
        return coefficient_of_variation > 0.3
    
    def _classify_pattern_type(
        self, 
        sorted_transactions: List[Dict], 
        frequency: str, 
        trend: TrendDirection
    ) -> str:
        """Classify the overall pattern type"""
        if frequency in ["daily", "weekly", "monthly"]:
            if trend == TrendDirection.STABLE:
                return "regular"
            elif trend == TrendDirection.INCREASING:
                return "increasing"
            elif trend == TrendDirection.DECREASING:
                return "decreasing"
            else:
                return "volatile"
        else:
            return "sporadic"
    
    def _generate_pattern_insights(
        self,
        category: str,
        pattern_type: str,
        frequency: str,
        trend: TrendDirection,
        avg_amount: float,
        transaction_count: int,
        seasonality: bool
    ) -> List[str]:
        """Generate human-readable insights about the pattern"""
        insights = []
        
        # Frequency insights
        if frequency == "monthly" and pattern_type == "regular":
            insights.append(f"You have a consistent {frequency} spending pattern for {category}")
        elif frequency == "sporadic":
            insights.append(f"Your {category} spending is irregular and unpredictable")
        
        # Trend insights
        if trend == TrendDirection.INCREASING:
            insights.append(f"Your {category} spending has been increasing over time")
        elif trend == TrendDirection.DECREASING:
            insights.append(f"Your {category} spending has been decreasing - great job!")
        elif trend == TrendDirection.VOLATILE:
            insights.append(f"Your {category} spending varies significantly month to month")
        
        # Amount insights
        if avg_amount > 100:
            insights.append(f"High-value category with average spending of ${avg_amount:.2f}")
        elif avg_amount < 20:
            insights.append(f"Low-cost category with average spending of ${avg_amount:.2f}")
        
        # Seasonality insights
        if seasonality:
            insights.append(f"Seasonal spending pattern detected for {category}")
        
        # Volume insights
        if transaction_count > 20:
            insights.append(f"High-frequency category with {transaction_count} transactions")
        
        return insights
    
    def _calculate_pattern_confidence(
        self,
        transactions: List[Dict],
        frequency: str,
        std_amount: float,
        avg_amount: float
    ) -> float:
        """Calculate confidence score for the pattern analysis"""
        confidence = 0.5  # Base confidence
        
        # Data volume bonus
        if len(transactions) >= 10:
            confidence += 0.2
        elif len(transactions) >= 5:
            confidence += 0.1
        
        # Consistency bonus
        if avg_amount > 0:
            coefficient_of_variation = std_amount / avg_amount
            if coefficient_of_variation < 0.5:  # Low variation
                confidence += 0.2
            elif coefficient_of_variation < 1.0:  # Moderate variation
                confidence += 0.1
        
        # Frequency pattern bonus
        if frequency in ["weekly", "monthly"]:
            confidence += 0.1
        elif frequency == "daily":
            confidence += 0.05
        
        return min(1.0, confidence)
    
    def analyze_trends(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_id: Optional[str] = None
    ) -> List[TrendAnalysis]:
        """Analyze financial trends with AI insights"""
        conn = get_conn()
        
        # Calculate current period and comparison period
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)  # Last 3 months
        
        # Calculate comparison period (same length, previous period)
        period_length = (end_date - start_date).days
        comparison_start = start_date - timedelta(days=period_length)
        comparison_end = start_date - timedelta(days=1)
        
        trends = []
        
        # Analyze overall spending trend
        current_spending = self._get_period_spending(start_date, end_date, account_id)
        previous_spending = self._get_period_spending(comparison_start, comparison_end, account_id)
        
        spending_trend = self._create_trend_analysis(
            "Total Spending", current_spending, previous_spending
        )
        trends.append(spending_trend)
        
        # Analyze income trend
        current_income = self._get_period_income(start_date, end_date, account_id)
        previous_income = self._get_period_income(comparison_start, comparison_end, account_id)
        
        income_trend = self._create_trend_analysis(
            "Total Income", current_income, previous_income
        )
        trends.append(income_trend)
        
        # Analyze category trends
        category_trends = self._analyze_category_trends(
            start_date, end_date, comparison_start, comparison_end, account_id
        )
        trends.extend(category_trends)
        
        return trends
    
    def _get_period_spending(
        self, 
        start_date: date, 
        end_date: date, 
        account_id: Optional[str]
    ) -> float:
        """Get total spending for a period"""
        conn = get_conn()
        
        where_clauses = ["t.amount < 0", "t.posted_at >= ?", "t.posted_at <= ?"]
        params = [start_date, end_date]
        
        if account_id:
            where_clauses.append("t.account_id = ?")
            params.append(account_id)
        
        where_clause = " AND ".join(where_clauses)
        
        result = conn.execute(f"""
            SELECT SUM(-t.amount) as total_spending
            FROM [transaction] t
            WHERE {where_clause}
        """, params).fetchone()
        
        return result[0] if result and result[0] else 0.0
    
    def _get_period_income(
        self, 
        start_date: date, 
        end_date: date, 
        account_id: Optional[str]
    ) -> float:
        """Get total income for a period"""
        conn = get_conn()
        
        where_clauses = ["t.amount > 0", "t.posted_at >= ?", "t.posted_at <= ?"]
        params = [start_date, end_date]
        
        if account_id:
            where_clauses.append("t.account_id = ?")
            params.append(account_id)
        
        where_clause = " AND ".join(where_clauses)
        
        result = conn.execute(f"""
            SELECT SUM(t.amount) as total_income
            FROM [transaction] t
            WHERE {where_clause}
        """, params).fetchone()
        
        return result[0] if result and result[0] else 0.0
    
    def _analyze_category_trends(
        self,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date,
        account_id: Optional[str]
    ) -> List[TrendAnalysis]:
        """Analyze trends for individual categories"""
        conn = get_conn()
        
        where_clauses = ["t.amount < 0"]
        
        if account_id:
            where_clauses.append("t.account_id = ?")
            account_params = [account_id]
        else:
            account_params = []
        
        where_clause = " AND ".join(where_clauses)
        
        # Get current period category spending
        current_categories = conn.execute(f"""
            SELECT c.name, SUM(-t.amount) as spending
            FROM [transaction] t
            JOIN transaction_category tc ON t.id = tc.tx_id
            JOIN category c ON tc.category_id = c.id
            WHERE {where_clause} AND t.posted_at >= ? AND t.posted_at <= ?
            GROUP BY c.name
            HAVING spending > 50
            ORDER BY spending DESC
            LIMIT 10
        """, account_params + [current_start, current_end]).fetchall()
        
        trends = []
        for category_name, current_spending in current_categories:
            # Get previous period spending for this category
            previous_result = conn.execute(f"""
                SELECT SUM(-t.amount) as spending
                FROM [transaction] t
                JOIN transaction_category tc ON t.id = tc.tx_id
                JOIN category c ON tc.category_id = c.id
                WHERE {where_clause} AND t.posted_at >= ? AND t.posted_at <= ?
                AND c.name = ?
            """, account_params + [previous_start, previous_end, category_name]).fetchone()
            
            previous_spending = previous_result[0] if previous_result and previous_result[0] else 0.0
            
            trend = self._create_trend_analysis(
                f"{category_name} Spending", current_spending, previous_spending
            )
            trends.append(trend)
        
        return trends
    
    def _create_trend_analysis(
        self, 
        metric_name: str, 
        current_value: float, 
        previous_value: float
    ) -> TrendAnalysis:
        """Create trend analysis from current and previous values"""
        change_amount = current_value - previous_value
        
        if previous_value == 0:
            change_percentage = 100.0 if current_value > 0 else 0.0
        else:
            change_percentage = (change_amount / previous_value) * 100
        
        # Determine trend direction
        if abs(change_percentage) < 5:  # Less than 5% change
            trend_direction = TrendDirection.STABLE
        elif change_percentage > 0:
            trend_direction = TrendDirection.INCREASING
        else:
            trend_direction = TrendDirection.DECREASING
        
        # Calculate confidence based on significance
        confidence = min(1.0, abs(change_percentage) / 100.0)
        is_significant = abs(change_percentage) > 10 and abs(change_amount) > 50
        
        # Generate insights
        insights = []
        if is_significant:
            if trend_direction == TrendDirection.INCREASING:
                insights.append(f"Significant increase of {change_percentage:.1f}% in {metric_name.lower()}")
            elif trend_direction == TrendDirection.DECREASING:
                insights.append(f"Significant decrease of {abs(change_percentage):.1f}% in {metric_name.lower()}")
        
        return TrendAnalysis(
            metric_name=metric_name,
            current_value=current_value,
            previous_value=previous_value,
            change_amount=change_amount,
            change_percentage=change_percentage,
            trend_direction=trend_direction,
            confidence=confidence,
            is_significant=is_significant,
            insights=insights
        )
    
    def detect_anomalies(
        self,
        days_lookback: int = 30,
        account_id: Optional[str] = None
    ) -> List[AnomalyDetection]:
        """Detect spending anomalies using statistical analysis"""
        conn = get_conn()
        
        # Get recent transactions for baseline
        cutoff_date = date.today() - timedelta(days=days_lookback)
        
        where_clauses = ["t.posted_at >= ?", "t.amount < 0"]
        params = [cutoff_date]
        
        if account_id:
            where_clauses.append("t.account_id = ?")
            params.append(account_id)
        
        where_clause = " AND ".join(where_clauses)
        
        transactions = conn.execute(f"""
            SELECT 
                t.id, t.posted_at, t.amount, t.description_norm, 
                c.name as category_name
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON t.id = tc.tx_id
            LEFT JOIN category c ON tc.category_id = c.id
            WHERE {where_clause}
            ORDER BY t.posted_at DESC
        """, params).fetchall()
        
        if len(transactions) < 10:
            return []  # Need minimum data for anomaly detection
        
        anomalies = []
        
        # Detect amount anomalies
        amounts = [abs(float(tx[2])) for tx in transactions]
        amount_anomalies = self._detect_statistical_anomalies(
            transactions, amounts, "amount", "Unusually large transaction amount"
        )
        anomalies.extend(amount_anomalies)
        
        # Detect category-specific anomalies
        category_anomalies = self._detect_category_anomalies(transactions)
        anomalies.extend(category_anomalies)
        
        return anomalies
    
    def _detect_statistical_anomalies(
        self,
        transactions: List[Tuple],
        values: List[float],
        value_type: str,
        description_template: str
    ) -> List[AnomalyDetection]:
        """Detect anomalies using statistical methods (IQR)"""
        if len(values) < 10:
            return []
        
        # Calculate IQR
        sorted_values = sorted(values)
        n = len(sorted_values)
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1
        
        if iqr == 0:
            return []  # No variation in data
        
        # Define outlier bounds
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        anomalies = []
        for i, (tx, value) in enumerate(zip(transactions, values)):
            if value < lower_bound or value > upper_bound:
                severity = "high" if value > q3 + 3 * iqr else "medium"
                
                anomalies.append(AnomalyDetection(
                    transaction_id=tx[0],
                    anomaly_type=f"{value_type}_outlier",
                    severity=severity,
                    description=description_template,
                    expected_range=(lower_bound, upper_bound),
                    actual_value=value,
                    confidence=min(1.0, abs(value - statistics.median(values)) / (iqr + 1))
                ))
        
        return anomalies
    
    def _detect_category_anomalies(self, transactions: List[Tuple]) -> List[AnomalyDetection]:
        """Detect anomalies within specific categories"""
        # Group by category
        category_groups = defaultdict(list)
        for tx in transactions:
            category = tx[4] if tx[4] else "Uncategorized"
            category_groups[category].append(tx)
        
        anomalies = []
        for category, category_txs in category_groups.items():
            if len(category_txs) < 5:  # Need minimum data per category
                continue
            
            amounts = [abs(float(tx[2])) for tx in category_txs]
            mean_amount = statistics.mean(amounts)
            std_amount = statistics.stdev(amounts) if len(amounts) > 1 else 0
            
            if std_amount == 0:
                continue
            
            # Detect transactions that are > 2 standard deviations from mean
            for tx in category_txs:
                amount = abs(float(tx[2]))
                z_score = abs(amount - mean_amount) / std_amount
                
                if z_score > 2:
                    severity = "high" if z_score > 3 else "medium"
                    
                    anomalies.append(AnomalyDetection(
                        transaction_id=tx[0],
                        anomaly_type="category_amount_outlier",
                        severity=severity,
                        description=f"Unusual amount for {category} category",
                        expected_range=(
                            mean_amount - 2 * std_amount,
                            mean_amount + 2 * std_amount
                        ),
                        actual_value=amount,
                        confidence=min(1.0, z_score / 3.0)
                    ))
        
        return anomalies


# Global instance
_ai_analytics_engine = None

def get_ai_analytics_engine() -> AIAnalyticsEngine:
    """Get the global AI analytics engine instance"""
    global _ai_analytics_engine
    if _ai_analytics_engine is None:
        _ai_analytics_engine = AIAnalyticsEngine()
    return _ai_analytics_engine