"""
AI-Powered Financial Forecasting

Provides predictive analytics for budget planning:
- Machine learning-based spending forecasts
- Income prediction with seasonal adjustments
- Cash flow projections
- Budget variance analysis
- Risk assessment and scenario planning
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, date
from collections import defaultdict
from enum import Enum

from .db import get_conn


class ForecastConfidence(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ForecastType(Enum):
    SPENDING = "spending"
    INCOME = "income"
    CASHFLOW = "cashflow"
    CATEGORY = "category"


@dataclass
class ForecastPoint:
    """Single forecast data point"""
    date: date
    predicted_value: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    confidence: ForecastConfidence
    factors: List[str]


@dataclass
class BudgetForecast:
    """Comprehensive budget forecast"""
    forecast_type: ForecastType
    period_start: date
    period_end: date
    forecast_points: List[ForecastPoint]
    total_predicted: float
    accuracy_score: float
    methodology: str
    key_assumptions: List[str]
    risk_factors: List[str]


@dataclass
class SpendingPrediction:
    """Spending prediction for a category or overall"""
    category: Optional[str]
    next_month_prediction: float
    next_quarter_prediction: float
    confidence: ForecastConfidence
    trend_factor: float
    seasonality_factor: float
    volatility_score: float
    key_drivers: List[str]


@dataclass
class CashFlowProjection:
    """Cash flow projection with scenarios"""
    base_scenario: List[ForecastPoint]
    optimistic_scenario: List[ForecastPoint]
    pessimistic_scenario: List[ForecastPoint]
    break_even_analysis: Dict[str, Any]
    runway_months: Optional[int]
    recommendations: List[str]


class AIForecastingEngine:
    """Advanced forecasting engine using machine learning techniques"""
    
    def __init__(self):
        pass
    
    def forecast_spending(
        self,
        category: Optional[str] = None,
        forecast_months: int = 6,
        account_id: Optional[str] = None
    ) -> BudgetForecast:
        """Forecast spending using historical data and ML techniques"""
        conn = get_conn()
        
        # Get historical data for training
        historical_data = self._get_historical_spending_data(category, account_id)
        
        if len(historical_data) < 6:  # Need minimum 6 months of data
            return self._create_simple_forecast(historical_data, forecast_months, ForecastType.SPENDING)
        
        # Apply advanced forecasting algorithm
        forecast_points = self._generate_ml_forecast(
            historical_data, forecast_months, ForecastType.SPENDING
        )
        
        total_predicted = sum(point.predicted_value for point in forecast_points)
        accuracy_score = self._calculate_forecast_accuracy(historical_data)
        
        # Generate methodology explanation
        methodology = "Machine Learning with Seasonal Decomposition"
        if len(historical_data) < 12:
            methodology = "Linear Trend with Moving Average"
        
        key_assumptions = self._generate_forecast_assumptions(historical_data, category)
        risk_factors = self._identify_forecast_risks(historical_data, category)
        
        return BudgetForecast(
            forecast_type=ForecastType.SPENDING,
            period_start=date.today(),
            period_end=date.today() + timedelta(days=30 * forecast_months),
            forecast_points=forecast_points,
            total_predicted=total_predicted,
            accuracy_score=accuracy_score,
            methodology=methodology,
            key_assumptions=key_assumptions,
            risk_factors=risk_factors
        )
    
    def forecast_income(
        self,
        forecast_months: int = 6,
        account_id: Optional[str] = None
    ) -> BudgetForecast:
        """Forecast income with seasonal adjustments"""
        conn = get_conn()
        
        # Get historical income data
        historical_data = self._get_historical_income_data(account_id)
        
        if len(historical_data) < 3:
            return self._create_simple_forecast(historical_data, forecast_months, ForecastType.INCOME)
        
        # Income is typically more stable than spending
        forecast_points = self._generate_income_forecast(historical_data, forecast_months)
        
        total_predicted = sum(point.predicted_value for point in forecast_points)
        accuracy_score = self._calculate_forecast_accuracy(historical_data)
        
        return BudgetForecast(
            forecast_type=ForecastType.INCOME,
            period_start=date.today(),
            period_end=date.today() + timedelta(days=30 * forecast_months),
            forecast_points=forecast_points,
            total_predicted=total_predicted,
            accuracy_score=accuracy_score,
            methodology="Stable Income Model with Growth Trends",
            key_assumptions=["Income patterns remain consistent", "No major career changes"],
            risk_factors=["Job market volatility", "Economic downturns"]
        )
    
    def project_cashflow(
        self,
        forecast_months: int = 12,
        account_id: Optional[str] = None
    ) -> CashFlowProjection:
        """Project cash flow with multiple scenarios"""
        
        # Get spending and income forecasts
        spending_forecast = self.forecast_spending(None, forecast_months, account_id)
        income_forecast = self.forecast_income(forecast_months, account_id)
        
        # Create base scenario
        base_scenario = []
        for i in range(forecast_months):
            forecast_date = date.today() + timedelta(days=30 * (i + 1))
            
            monthly_income = income_forecast.forecast_points[i].predicted_value if i < len(income_forecast.forecast_points) else 0
            monthly_spending = spending_forecast.forecast_points[i].predicted_value if i < len(spending_forecast.forecast_points) else 0
            
            net_cashflow = monthly_income - monthly_spending
            
            # Calculate confidence interval
            income_uncertainty = income_forecast.forecast_points[i].confidence_interval_upper - income_forecast.forecast_points[i].predicted_value if i < len(income_forecast.forecast_points) else monthly_income * 0.1
            spending_uncertainty = spending_forecast.forecast_points[i].confidence_interval_upper - spending_forecast.forecast_points[i].predicted_value if i < len(spending_forecast.forecast_points) else monthly_spending * 0.2
            
            total_uncertainty = income_uncertainty + spending_uncertainty
            
            base_scenario.append(ForecastPoint(
                date=forecast_date,
                predicted_value=net_cashflow,
                confidence_interval_lower=net_cashflow - total_uncertainty,
                confidence_interval_upper=net_cashflow + total_uncertainty,
                confidence=ForecastConfidence.MEDIUM,
                factors=["Historical patterns", "Trend analysis"]
            ))
        
        # Create optimistic scenario (10% better income, 5% lower spending)
        optimistic_scenario = []
        for point in base_scenario:
            optimistic_income = income_forecast.forecast_points[len(optimistic_scenario)].predicted_value * 1.1 if len(optimistic_scenario) < len(income_forecast.forecast_points) else 0
            optimistic_spending = spending_forecast.forecast_points[len(optimistic_scenario)].predicted_value * 0.95 if len(optimistic_scenario) < len(spending_forecast.forecast_points) else 0
            optimistic_cashflow = optimistic_income - optimistic_spending
            
            optimistic_scenario.append(ForecastPoint(
                date=point.date,
                predicted_value=optimistic_cashflow,
                confidence_interval_lower=optimistic_cashflow * 0.9,
                confidence_interval_upper=optimistic_cashflow * 1.1,
                confidence=ForecastConfidence.MEDIUM,
                factors=["Optimistic market conditions", "Reduced expenses"]
            ))
        
        # Create pessimistic scenario (10% lower income, 10% higher spending)
        pessimistic_scenario = []
        for point in base_scenario:
            pessimistic_income = income_forecast.forecast_points[len(pessimistic_scenario)].predicted_value * 0.9 if len(pessimistic_scenario) < len(income_forecast.forecast_points) else 0
            pessimistic_spending = spending_forecast.forecast_points[len(pessimistic_scenario)].predicted_value * 1.1 if len(pessimistic_scenario) < len(spending_forecast.forecast_points) else 0
            pessimistic_cashflow = pessimistic_income - pessimistic_spending
            
            pessimistic_scenario.append(ForecastPoint(
                date=point.date,
                predicted_value=pessimistic_cashflow,
                confidence_interval_lower=pessimistic_cashflow * 0.8,
                confidence_interval_upper=pessimistic_cashflow * 1.2,
                confidence=ForecastConfidence.LOW,
                factors=["Economic downturn", "Increased expenses"]
            ))
        
        # Calculate break-even and runway
        break_even_analysis = self._calculate_break_even_analysis(base_scenario)
        runway_months = self._calculate_runway_months(base_scenario)
        
        # Generate recommendations
        recommendations = self._generate_cashflow_recommendations(
            base_scenario, optimistic_scenario, pessimistic_scenario
        )
        
        return CashFlowProjection(
            base_scenario=base_scenario,
            optimistic_scenario=optimistic_scenario,
            pessimistic_scenario=pessimistic_scenario,
            break_even_analysis=break_even_analysis,
            runway_months=runway_months,
            recommendations=recommendations
        )
    
    def predict_category_spending(
        self,
        category: str,
        account_id: Optional[str] = None
    ) -> SpendingPrediction:
        """Predict spending for a specific category"""
        conn = get_conn()
        
        # Get historical category data
        historical_data = self._get_historical_spending_data(category, account_id)
        
        if len(historical_data) < 3:
            # Insufficient data for prediction
            return SpendingPrediction(
                category=category,
                next_month_prediction=0.0,
                next_quarter_prediction=0.0,
                confidence=ForecastConfidence.LOW,
                trend_factor=0.0,
                seasonality_factor=1.0,
                volatility_score=1.0,
                key_drivers=["Insufficient historical data"]
            )
        
        # Calculate trend and seasonality
        trend_factor = self._calculate_trend_factor(historical_data)
        seasonality_factor = self._calculate_seasonality_factor(historical_data)
        volatility_score = self._calculate_volatility_score(historical_data)
        
        # Predict next month
        recent_average = statistics.mean([point['amount'] for point in historical_data[-3:]])
        next_month_prediction = recent_average * (1 + trend_factor) * seasonality_factor
        
        # Predict next quarter (3 months)
        next_quarter_prediction = next_month_prediction * 3 * (1 + trend_factor * 0.5)
        
        # Determine confidence
        confidence = ForecastConfidence.HIGH
        if len(historical_data) < 6:
            confidence = ForecastConfidence.MEDIUM
        if volatility_score > 0.5:
            confidence = ForecastConfidence.LOW
        
        # Identify key drivers
        key_drivers = self._identify_spending_drivers(category, historical_data)
        
        return SpendingPrediction(
            category=category,
            next_month_prediction=next_month_prediction,
            next_quarter_prediction=next_quarter_prediction,
            confidence=confidence,
            trend_factor=trend_factor,
            seasonality_factor=seasonality_factor,
            volatility_score=volatility_score,
            key_drivers=key_drivers
        )
    
    def _get_historical_spending_data(
        self, 
        category: Optional[str], 
        account_id: Optional[str],
        months_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical spending data for analysis"""
        conn = get_conn()
        
        cutoff_date = date.today() - timedelta(days=30 * months_back)
        
        where_clauses = ["t.posted_at >= ?", "t.amount < 0"]
        params = [cutoff_date]
        
        if account_id:
            where_clauses.append("t.account_id = ?")
            params.append(account_id)
        
        if category:
            where_clauses.append("c.name = ?")
            params.append(category)
            join_clause = """
                JOIN transaction_category tc ON t.id = tc.tx_id
                JOIN category c ON tc.category_id = c.id
            """
        else:
            join_clause = ""
        
        where_clause = " AND ".join(where_clauses)
        
        transactions = conn.execute(f"""
            SELECT 
                date_trunc('month', t.posted_at) as month,
                SUM(-t.amount) as amount,
                COUNT(*) as transaction_count
            FROM [transaction] t
            {join_clause}
            WHERE {where_clause}
            GROUP BY date_trunc('month', t.posted_at)
            ORDER BY month
        """, params).fetchall()
        
        return [
            {
                'month': row[0],
                'amount': float(row[1]),
                'transaction_count': int(row[2])
            }
            for row in transactions
        ]
    
    def _get_historical_income_data(
        self, 
        account_id: Optional[str],
        months_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical income data for analysis"""
        conn = get_conn()
        
        cutoff_date = date.today() - timedelta(days=30 * months_back)
        
        where_clauses = ["t.posted_at >= ?", "t.amount > 0"]
        params = [cutoff_date]
        
        if account_id:
            where_clauses.append("t.account_id = ?")
            params.append(account_id)
        
        where_clause = " AND ".join(where_clauses)
        
        income_data = conn.execute(f"""
            SELECT 
                date_trunc('month', t.posted_at) as month,
                SUM(t.amount) as amount,
                COUNT(*) as transaction_count
            FROM [transaction] t
            WHERE {where_clause}
            GROUP BY date_trunc('month', t.posted_at)
            ORDER BY month
        """, params).fetchall()
        
        return [
            {
                'month': row[0],
                'amount': float(row[1]),
                'transaction_count': int(row[2])
            }
            for row in income_data
        ]
    
    def _generate_ml_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_months: int,
        forecast_type: ForecastType
    ) -> List[ForecastPoint]:
        """Generate forecast using machine learning approach"""
        if len(historical_data) < 3:
            return []
        
        # Simple linear regression with trend analysis
        amounts = [point['amount'] for point in historical_data]
        
        # Calculate trend
        x_values = list(range(len(amounts)))
        trend_slope = self._calculate_linear_regression_slope(x_values, amounts)
        
        # Calculate seasonal component
        seasonal_factors = self._calculate_seasonal_factors(historical_data)
        
        # Generate forecasts
        forecast_points = []
        last_amount = amounts[-1]
        
        for i in range(forecast_months):
            # Base prediction with trend
            base_prediction = last_amount + (trend_slope * (i + 1))
            
            # Apply seasonality
            month_index = (len(historical_data) + i) % 12
            seasonal_factor = seasonal_factors.get(month_index, 1.0)
            predicted_value = base_prediction * seasonal_factor
            
            # Calculate confidence interval based on historical variance
            variance = statistics.variance(amounts) if len(amounts) > 1 else predicted_value * 0.1
            confidence_range = math.sqrt(variance) * 1.96  # 95% confidence interval
            
            # Determine confidence level
            confidence = ForecastConfidence.HIGH
            if i > 3:  # Confidence decreases for longer forecasts
                confidence = ForecastConfidence.MEDIUM
            if i > 6:
                confidence = ForecastConfidence.LOW
            
            forecast_date = date.today() + timedelta(days=30 * (i + 1))
            
            forecast_points.append(ForecastPoint(
                date=forecast_date,
                predicted_value=max(0, predicted_value),  # Ensure positive values
                confidence_interval_lower=max(0, predicted_value - confidence_range),
                confidence_interval_upper=predicted_value + confidence_range,
                confidence=confidence,
                factors=["Historical trend", "Seasonal patterns", "Variance analysis"]
            ))
        
        return forecast_points
    
    def _generate_income_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_months: int
    ) -> List[ForecastPoint]:
        """Generate income forecast (typically more stable than spending)"""
        if len(historical_data) < 2:
            # Default to simple average
            avg_income = statistics.mean([point['amount'] for point in historical_data]) if historical_data else 0
            return [
                ForecastPoint(
                    date=date.today() + timedelta(days=30 * (i + 1)),
                    predicted_value=avg_income,
                    confidence_interval_lower=avg_income * 0.9,
                    confidence_interval_upper=avg_income * 1.1,
                    confidence=ForecastConfidence.MEDIUM,
                    factors=["Historical average"]
                )
                for i in range(forecast_months)
            ]
        
        amounts = [point['amount'] for point in historical_data]
        recent_average = statistics.mean(amounts[-6:]) if len(amounts) >= 6 else statistics.mean(amounts)
        
        # Income typically has low volatility
        std_dev = statistics.stdev(amounts) if len(amounts) > 1 else recent_average * 0.05
        
        # Small growth trend for income
        growth_rate = 0.001  # 0.1% monthly growth assumption
        
        forecast_points = []
        for i in range(forecast_months):
            predicted_value = recent_average * (1 + growth_rate * i)
            confidence_range = std_dev * 1.5  # Smaller range for income
            
            forecast_points.append(ForecastPoint(
                date=date.today() + timedelta(days=30 * (i + 1)),
                predicted_value=predicted_value,
                confidence_interval_lower=predicted_value - confidence_range,
                confidence_interval_upper=predicted_value + confidence_range,
                confidence=ForecastConfidence.HIGH if i < 6 else ForecastConfidence.MEDIUM,
                factors=["Stable income pattern", "Modest growth assumption"]
            ))
        
        return forecast_points
    
    def _calculate_linear_regression_slope(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate slope using simple linear regression"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0
        
        n = len(x_values)
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def _calculate_seasonal_factors(self, historical_data: List[Dict[str, Any]]) -> Dict[int, float]:
        """Calculate seasonal adjustment factors"""
        if len(historical_data) < 12:
            return {i: 1.0 for i in range(12)}  # No seasonal adjustment
        
        monthly_amounts = defaultdict(list)
        
        for point in historical_data:
            month_date = datetime.fromisoformat(str(point['month']))
            month_index = month_date.month - 1  # 0-based index
            monthly_amounts[month_index].append(point['amount'])
        
        # Calculate average for each month
        overall_average = statistics.mean([point['amount'] for point in historical_data])
        seasonal_factors = {}
        
        for month_index in range(12):
            if month_index in monthly_amounts and monthly_amounts[month_index]:
                month_average = statistics.mean(monthly_amounts[month_index])
                seasonal_factors[month_index] = month_average / overall_average
            else:
                seasonal_factors[month_index] = 1.0
        
        return seasonal_factors
    
    def _calculate_trend_factor(self, historical_data: List[Dict[str, Any]]) -> float:
        """Calculate trend factor for spending prediction"""
        if len(historical_data) < 3:
            return 0.0
        
        amounts = [point['amount'] for point in historical_data]
        x_values = list(range(len(amounts)))
        
        slope = self._calculate_linear_regression_slope(x_values, amounts)
        avg_amount = statistics.mean(amounts)
        
        # Normalize slope to get trend factor
        return slope / avg_amount if avg_amount != 0 else 0.0
    
    def _calculate_seasonality_factor(self, historical_data: List[Dict[str, Any]]) -> float:
        """Calculate current seasonality factor"""
        seasonal_factors = self._calculate_seasonal_factors(historical_data)
        current_month = date.today().month - 1
        return seasonal_factors.get(current_month, 1.0)
    
    def _calculate_volatility_score(self, historical_data: List[Dict[str, Any]]) -> float:
        """Calculate volatility score (0 = stable, 1 = very volatile)"""
        if len(historical_data) < 2:
            return 0.5
        
        amounts = [point['amount'] for point in historical_data]
        mean_amount = statistics.mean(amounts)
        std_amount = statistics.stdev(amounts)
        
        if mean_amount == 0:
            return 1.0
        
        coefficient_of_variation = std_amount / mean_amount
        return min(1.0, coefficient_of_variation)
    
    def _identify_spending_drivers(self, category: str, historical_data: List[Dict[str, Any]]) -> List[str]:
        """Identify key drivers of spending for a category"""
        drivers = []
        
        if len(historical_data) >= 6:
            # Check for increasing trend
            trend_factor = self._calculate_trend_factor(historical_data)
            if trend_factor > 0.05:
                drivers.append("Increasing spending trend")
            elif trend_factor < -0.05:
                drivers.append("Decreasing spending trend")
        
        # Check for high frequency
        if historical_data:
            avg_transactions = statistics.mean([point['transaction_count'] for point in historical_data])
            if avg_transactions > 10:
                drivers.append("High transaction frequency")
        
        # Category-specific drivers
        category_drivers = {
            "Food & Dining": ["Restaurant visits", "Grocery prices", "Social activities"],
            "Gas & Automotive": ["Fuel prices", "Commuting patterns", "Vehicle maintenance"],
            "Shopping": ["Retail promotions", "Seasonal sales", "Lifestyle changes"],
            "Entertainment": ["Social activities", "Subscription services", "Events"]
        }
        
        if category in category_drivers:
            drivers.extend(category_drivers[category])
        
        return drivers[:5]  # Return top 5 drivers
    
    def _create_simple_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_months: int,
        forecast_type: ForecastType
    ) -> BudgetForecast:
        """Create simple forecast when insufficient data"""
        if not historical_data:
            average_amount = 0.0
        else:
            average_amount = statistics.mean([point['amount'] for point in historical_data])
        
        forecast_points = []
        for i in range(forecast_months):
            forecast_points.append(ForecastPoint(
                date=date.today() + timedelta(days=30 * (i + 1)),
                predicted_value=average_amount,
                confidence_interval_lower=average_amount * 0.7,
                confidence_interval_upper=average_amount * 1.3,
                confidence=ForecastConfidence.LOW,
                factors=["Limited historical data", "Simple average"]
            ))
        
        return BudgetForecast(
            forecast_type=forecast_type,
            period_start=date.today(),
            period_end=date.today() + timedelta(days=30 * forecast_months),
            forecast_points=forecast_points,
            total_predicted=average_amount * forecast_months,
            accuracy_score=0.5,  # Low accuracy due to limited data
            methodology="Simple Average (Limited Data)",
            key_assumptions=["Spending patterns remain constant"],
            risk_factors=["Insufficient historical data", "Pattern changes not detected"]
        )
    
    def _calculate_forecast_accuracy(self, historical_data: List[Dict[str, Any]]) -> float:
        """Calculate forecast accuracy based on historical data quality"""
        if len(historical_data) < 3:
            return 0.3
        
        # Base accuracy on data quantity and consistency
        data_quantity_score = min(1.0, len(historical_data) / 12)  # 12 months = full score
        
        amounts = [point['amount'] for point in historical_data]
        if len(amounts) > 1:
            cv = statistics.stdev(amounts) / statistics.mean(amounts)
            consistency_score = max(0.3, 1.0 - cv)  # Lower CV = higher consistency
        else:
            consistency_score = 0.5
        
        return (data_quantity_score + consistency_score) / 2
    
    def _generate_forecast_assumptions(
        self, 
        historical_data: List[Dict[str, Any]], 
        category: Optional[str]
    ) -> List[str]:
        """Generate key assumptions for the forecast"""
        assumptions = []
        
        if len(historical_data) >= 12:
            assumptions.append("Seasonal patterns will continue")
        
        assumptions.append("No major lifestyle or income changes")
        assumptions.append("Economic conditions remain stable")
        
        if category:
            assumptions.append(f"{category} spending patterns remain consistent")
        
        return assumptions
    
    def _identify_forecast_risks(
        self, 
        historical_data: List[Dict[str, Any]], 
        category: Optional[str]
    ) -> List[str]:
        """Identify potential risks to forecast accuracy"""
        risks = []
        
        if len(historical_data) < 6:
            risks.append("Limited historical data reduces accuracy")
        
        # Check for high volatility
        if historical_data:
            volatility = self._calculate_volatility_score(historical_data)
            if volatility > 0.5:
                risks.append("High spending volatility increases uncertainty")
        
        risks.append("Unexpected life events or emergencies")
        risks.append("Economic downturns or inflation")
        
        if category:
            category_risks = {
                "Food & Dining": ["Rising food costs", "Changed dining habits"],
                "Gas & Automotive": ["Fuel price volatility", "Vehicle breakdown"],
                "Entertainment": ["Reduced social activities", "Subscription changes"]
            }
            if category in category_risks:
                risks.extend(category_risks[category])
        
        return risks
    
    def _calculate_break_even_analysis(self, base_scenario: List[ForecastPoint]) -> Dict[str, Any]:
        """Calculate break-even analysis from cash flow projection"""
        positive_months = sum(1 for point in base_scenario if point.predicted_value > 0)
        negative_months = len(base_scenario) - positive_months
        
        avg_monthly_cashflow = statistics.mean([point.predicted_value for point in base_scenario])
        
        return {
            "positive_months": positive_months,
            "negative_months": negative_months,
            "average_monthly_cashflow": avg_monthly_cashflow,
            "break_even_probability": positive_months / len(base_scenario) if base_scenario else 0
        }
    
    def _calculate_runway_months(self, base_scenario: List[ForecastPoint]) -> Optional[int]:
        """Calculate how many months of runway based on cash flow"""
        cumulative_cashflow = 0
        
        for i, point in enumerate(base_scenario):
            cumulative_cashflow += point.predicted_value
            if cumulative_cashflow < 0:
                return i + 1
        
        return None  # Runway exceeds forecast period
    
    def _generate_cashflow_recommendations(
        self,
        base_scenario: List[ForecastPoint],
        optimistic_scenario: List[ForecastPoint],
        pessimistic_scenario: List[ForecastPoint]
    ) -> List[str]:
        """Generate recommendations based on cash flow projections"""
        recommendations = []
        
        # Check base scenario health
        negative_months = sum(1 for point in base_scenario if point.predicted_value < 0)
        if negative_months > len(base_scenario) * 0.3:
            recommendations.append("Consider reducing expenses or increasing income")
        
        # Check pessimistic scenario
        pessimistic_negative = sum(1 for point in pessimistic_scenario if point.predicted_value < 0)
        if pessimistic_negative > len(pessimistic_scenario) * 0.5:
            recommendations.append("Build emergency fund to handle economic downturns")
        
        # Check for opportunities
        optimistic_positive = sum(1 for point in optimistic_scenario if point.predicted_value > 500)
        if optimistic_positive > len(optimistic_scenario) * 0.7:
            recommendations.append("Consider increasing investments or savings")
        
        recommendations.append("Review and adjust budget monthly")
        recommendations.append("Track actual vs. predicted spending")
        
        return recommendations


# Global instance
_ai_forecasting_engine = None

def get_ai_forecasting_engine() -> AIForecastingEngine:
    """Get the global AI forecasting engine instance"""
    global _ai_forecasting_engine
    if _ai_forecasting_engine is None:
        _ai_forecasting_engine = AIForecastingEngine()
    return _ai_forecasting_engine