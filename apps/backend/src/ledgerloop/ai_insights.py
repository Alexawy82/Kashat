"""
AI-Powered Personalized Financial Insights

Provides intelligent, personalized financial insights and recommendations:
- Spending behavior analysis and persona identification
- Goal-oriented recommendations and alerts
- Personalized budget optimization suggestions
- Risk assessment and financial health scoring
- Actionable insights based on user patterns
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, date
from collections import defaultdict
from enum import Enum

from .ai_analytics import get_ai_analytics_engine, SpendingPersona
from .ai_forecasting import get_ai_forecasting_engine
from .db import get_conn


class InsightCategory(Enum):
    SPENDING_OPTIMIZATION = "spending_optimization"
    SAVINGS_OPPORTUNITY = "savings_opportunity"
    BUDGET_ALERT = "budget_alert"
    TREND_NOTIFICATION = "trend_notification"
    ANOMALY_ALERT = "anomaly_alert"
    FORECAST_WARNING = "forecast_warning"
    GOAL_PROGRESS = "goal_progress"


class InsightPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class FinancialHealthScore(Enum):
    EXCELLENT = "excellent"    # 90-100
    GOOD = "good"             # 75-89
    FAIR = "fair"             # 60-74
    POOR = "poor"             # 40-59
    CRITICAL = "critical"     # 0-39


@dataclass
class PersonalizedInsight:
    """A personalized financial insight with actionable recommendations"""
    id: str
    category: InsightCategory
    priority: InsightPriority
    title: str
    description: str
    recommendations: List[str]
    impact_score: float  # 0-1, higher = more impactful
    confidence: float    # 0-1, higher = more confident
    data_points: Dict[str, Any]
    expires_at: Optional[date]


@dataclass
class FinancialHealthReport:
    """Comprehensive financial health assessment"""
    overall_score: int  # 0-100
    health_grade: FinancialHealthScore
    spending_health: int
    savings_health: int
    budgeting_health: int
    trend_health: int
    key_strengths: List[str]
    improvement_areas: List[str]
    recommendations: List[str]


@dataclass
class SpendingBehaviorProfile:
    """User's spending behavior profile"""
    persona: SpendingPersona
    avg_monthly_spending: float
    spending_volatility: float
    top_categories: List[Tuple[str, float]]
    spending_habits: List[str]
    risk_factors: List[str]
    behavioral_insights: List[str]


class AIInsightsEngine:
    """Advanced insights engine for personalized financial recommendations"""
    
    def __init__(self):
        self.analytics_engine = get_ai_analytics_engine()
        self.forecasting_engine = get_ai_forecasting_engine()
    
    def generate_personalized_insights(
        self, 
        account_id: Optional[str] = None,
        insight_limit: int = 10
    ) -> List[PersonalizedInsight]:
        """Generate personalized financial insights and recommendations"""
        
        insights = []
        
        # Generate different types of insights
        insights.extend(self._generate_spending_optimization_insights(account_id))
        insights.extend(self._generate_savings_opportunity_insights(account_id))
        insights.extend(self._generate_budget_alert_insights(account_id))
        insights.extend(self._generate_trend_notification_insights(account_id))
        insights.extend(self._generate_anomaly_alert_insights(account_id))
        insights.extend(self._generate_forecast_warning_insights(account_id))
        
        # Sort by priority and impact score
        insights.sort(key=lambda x: (
            x.priority == InsightPriority.URGENT,
            x.priority == InsightPriority.HIGH,
            x.impact_score
        ), reverse=True)
        
        return insights[:insight_limit]
    
    def assess_financial_health(
        self, 
        account_id: Optional[str] = None
    ) -> FinancialHealthReport:
        """Assess overall financial health with detailed scoring"""
        
        # Get analytics data
        patterns = self.analytics_engine.analyze_spending_patterns(account_id=account_id)
        trends = self.analytics_engine.analyze_trends(account_id=account_id)
        anomalies = self.analytics_engine.detect_anomalies(account_id=account_id)
        
        # Calculate component scores
        spending_health = self._calculate_spending_health_score(patterns, anomalies)
        savings_health = self._calculate_savings_health_score(account_id)
        budgeting_health = self._calculate_budgeting_health_score(patterns, trends)
        trend_health = self._calculate_trend_health_score(trends)
        
        # Calculate overall score (weighted average)
        overall_score = int(
            spending_health * 0.3 +
            savings_health * 0.25 +
            budgeting_health * 0.25 +
            trend_health * 0.2
        )
        
        # Determine health grade
        if overall_score >= 90:
            health_grade = FinancialHealthScore.EXCELLENT
        elif overall_score >= 75:
            health_grade = FinancialHealthScore.GOOD
        elif overall_score >= 60:
            health_grade = FinancialHealthScore.FAIR
        elif overall_score >= 40:
            health_grade = FinancialHealthScore.POOR
        else:
            health_grade = FinancialHealthScore.CRITICAL
        
        # Generate insights
        key_strengths = self._identify_financial_strengths(
            spending_health, savings_health, budgeting_health, trend_health
        )
        improvement_areas = self._identify_improvement_areas(
            spending_health, savings_health, budgeting_health, trend_health
        )
        recommendations = self._generate_health_recommendations(
            health_grade, improvement_areas
        )
        
        return FinancialHealthReport(
            overall_score=overall_score,
            health_grade=health_grade,
            spending_health=spending_health,
            savings_health=savings_health,
            budgeting_health=budgeting_health,
            trend_health=trend_health,
            key_strengths=key_strengths,
            improvement_areas=improvement_areas,
            recommendations=recommendations
        )
    
    def analyze_spending_behavior(
        self, 
        account_id: Optional[str] = None
    ) -> SpendingBehaviorProfile:
        """Analyze user's spending behavior and create a behavioral profile"""
        
        conn = get_conn()
        
        # Get spending data for analysis
        cutoff_date = date.today() - timedelta(days=180)  # 6 months
        
        where_clauses = ["t.posted_at >= ?", "t.amount < 0"]
        params = [cutoff_date]
        
        if account_id:
            where_clauses.append("t.account_id = ?")
            params.append(account_id)
        
        where_clause = " AND ".join(where_clauses)
        
        spending_data = conn.execute(f"""
            SELECT 
                date_trunc('month', t.posted_at) as month,
                c.name as category,
                SUM(-t.amount) as amount,
                COUNT(*) as transaction_count
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON t.id = tc.tx_id
            LEFT JOIN category c ON tc.category_id = c.id
            WHERE {where_clause}
            GROUP BY date_trunc('month', t.posted_at), c.name
            ORDER BY month
        """, params).fetchall()
        
        if not spending_data:
            return self._create_default_spending_profile()
        
        # Calculate metrics
        monthly_totals = defaultdict(float)
        category_totals = defaultdict(float)
        
        for row in spending_data:
            month, category, amount, count = row
            monthly_totals[month] += amount
            if category:
                category_totals[category] += amount
        
        avg_monthly_spending = statistics.mean(monthly_totals.values()) if monthly_totals else 0
        spending_volatility = (statistics.stdev(monthly_totals.values()) / avg_monthly_spending) if len(monthly_totals) > 1 and avg_monthly_spending > 0 else 0
        
        # Top categories
        top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Determine persona
        persona = self._determine_spending_persona(
            avg_monthly_spending, spending_volatility, top_categories
        )
        
        # Generate behavioral insights
        spending_habits = self._analyze_spending_habits(spending_data, persona)
        risk_factors = self._identify_behavioral_risks(persona, spending_volatility)
        behavioral_insights = self._generate_behavioral_insights(
            persona, avg_monthly_spending, spending_volatility, top_categories
        )
        
        return SpendingBehaviorProfile(
            persona=persona,
            avg_monthly_spending=avg_monthly_spending,
            spending_volatility=spending_volatility,
            top_categories=top_categories,
            spending_habits=spending_habits,
            risk_factors=risk_factors,
            behavioral_insights=behavioral_insights
        )
    
    def _generate_spending_optimization_insights(
        self, 
        account_id: Optional[str]
    ) -> List[PersonalizedInsight]:
        """Generate insights for spending optimization"""
        insights = []
        
        patterns = self.analytics_engine.analyze_spending_patterns(account_id=account_id)
        
        for pattern in patterns[:3]:  # Top 3 patterns
            if pattern.average_amount > 200 and pattern.confidence > 0.7:
                # High spending category with good data
                insight_id = f"spend_opt_{pattern.category.lower().replace(' ', '_')}"
                
                recommendations = [
                    f"Review {pattern.category} spending - averaging ${pattern.average_amount:.2f}",
                    f"Consider setting a monthly budget for {pattern.category}",
                    "Look for alternative options or discounts"
                ]
                
                if pattern.trend_direction.value == "increasing":
                    recommendations.append(f"Address increasing trend in {pattern.category} spending")
                
                insights.append(PersonalizedInsight(
                    id=insight_id,
                    category=InsightCategory.SPENDING_OPTIMIZATION,
                    priority=InsightPriority.MEDIUM,
                    title=f"Optimize {pattern.category} Spending",
                    description=f"Your {pattern.category} spending shows potential for optimization with an average of ${pattern.average_amount:.2f} per transaction.",
                    recommendations=recommendations,
                    impact_score=min(1.0, pattern.average_amount / 500),  # Higher amounts = higher impact
                    confidence=pattern.confidence,
                    data_points={
                        "category": pattern.category,
                        "average_amount": pattern.average_amount,
                        "frequency": pattern.frequency,
                        "trend": pattern.trend_direction.value
                    },
                    expires_at=date.today() + timedelta(days=30)
                ))
        
        return insights
    
    def _generate_savings_opportunity_insights(
        self, 
        account_id: Optional[str]
    ) -> List[PersonalizedInsight]:
        """Generate insights for savings opportunities"""
        insights = []
        
        # Get cash flow projection
        cashflow_projection = self.forecasting_engine.project_cashflow(
            forecast_months=3, account_id=account_id
        )
        
        # Check for positive cash flow opportunities
        positive_months = sum(1 for point in cashflow_projection.base_scenario if point.predicted_value > 500)
        
        if positive_months >= 2:
            avg_surplus = statistics.mean([
                point.predicted_value for point in cashflow_projection.base_scenario 
                if point.predicted_value > 0
            ])
            
            insights.append(PersonalizedInsight(
                id="savings_opportunity_surplus",
                category=InsightCategory.SAVINGS_OPPORTUNITY,
                priority=InsightPriority.MEDIUM,
                title="Savings Opportunity Detected",
                description=f"Your projected cash flow shows potential for saving approximately ${avg_surplus:.2f} per month.",
                recommendations=[
                    "Set up automatic transfers to savings",
                    "Consider opening a high-yield savings account",
                    "Explore investment opportunities for long-term growth",
                    f"Target saving ${avg_surplus * 0.8:.2f} monthly (80% of surplus)"
                ],
                impact_score=min(1.0, avg_surplus / 1000),
                confidence=0.8,
                data_points={
                    "avg_monthly_surplus": avg_surplus,
                    "positive_months": positive_months,
                    "projection_period": 3
                },
                expires_at=date.today() + timedelta(days=14)
            ))
        
        return insights
    
    def _generate_budget_alert_insights(
        self, 
        account_id: Optional[str]
    ) -> List[PersonalizedInsight]:
        """Generate budget-related alerts and insights"""
        insights = []
        
        # Get recent spending trends
        trends = self.analytics_engine.analyze_trends(account_id=account_id)
        
        for trend in trends:
            if (trend.is_significant and 
                trend.change_percentage > 20 and 
                "Spending" in trend.metric_name):
                
                priority = InsightPriority.HIGH if trend.change_percentage > 50 else InsightPriority.MEDIUM
                
                insights.append(PersonalizedInsight(
                    id=f"budget_alert_{trend.metric_name.lower().replace(' ', '_')}",
                    category=InsightCategory.BUDGET_ALERT,
                    priority=priority,
                    title=f"Significant Change in {trend.metric_name}",
                    description=f"Your {trend.metric_name.lower()} has {trend.trend_direction.value} by {abs(trend.change_percentage):.1f}% recently.",
                    recommendations=[
                        f"Review your {trend.metric_name.lower()} patterns",
                        "Consider adjusting your budget accordingly",
                        "Identify the drivers behind this change",
                        "Set alerts for future significant changes"
                    ],
                    impact_score=min(1.0, abs(trend.change_percentage) / 100),
                    confidence=trend.confidence,
                    data_points={
                        "metric": trend.metric_name,
                        "change_percentage": trend.change_percentage,
                        "current_value": trend.current_value,
                        "previous_value": trend.previous_value
                    },
                    expires_at=date.today() + timedelta(days=7)
                ))
        
        return insights
    
    def _generate_trend_notification_insights(
        self, 
        account_id: Optional[str]
    ) -> List[PersonalizedInsight]:
        """Generate insights about important trends"""
        insights = []
        
        patterns = self.analytics_engine.analyze_spending_patterns(account_id=account_id)
        
        for pattern in patterns:
            if pattern.seasonality_detected and pattern.confidence > 0.6:
                insights.append(PersonalizedInsight(
                    id=f"seasonal_trend_{pattern.category.lower().replace(' ', '_')}",
                    category=InsightCategory.TREND_NOTIFICATION,
                    priority=InsightPriority.LOW,
                    title=f"Seasonal Pattern in {pattern.category}",
                    description=f"Your {pattern.category} spending shows seasonal variations that could be planned for.",
                    recommendations=[
                        f"Plan ahead for seasonal {pattern.category} expenses",
                        "Set aside money during low-spending periods",
                        "Consider bulk purchases during off-seasons",
                        "Track seasonal promotions and sales"
                    ],
                    impact_score=0.5,
                    confidence=pattern.confidence,
                    data_points={
                        "category": pattern.category,
                        "pattern_type": pattern.pattern_type,
                        "frequency": pattern.frequency
                    },
                    expires_at=date.today() + timedelta(days=60)
                ))
        
        return insights
    
    def _generate_anomaly_alert_insights(
        self, 
        account_id: Optional[str]
    ) -> List[PersonalizedInsight]:
        """Generate insights about spending anomalies"""
        insights = []
        
        anomalies = self.analytics_engine.detect_anomalies(account_id=account_id)
        high_severity_anomalies = [a for a in anomalies if a.severity == "high"]
        
        if high_severity_anomalies:
            insights.append(PersonalizedInsight(
                id="anomaly_alert_high_severity",
                category=InsightCategory.ANOMALY_ALERT,
                priority=InsightPriority.HIGH,
                title="Unusual Spending Detected",
                description=f"Detected {len(high_severity_anomalies)} high-severity spending anomalies that require attention.",
                recommendations=[
                    "Review flagged transactions for accuracy",
                    "Verify unusual charges with merchants",
                    "Check for potential fraud or unauthorized transactions",
                    "Update spending alerts if patterns have legitimately changed"
                ],
                impact_score=0.8,
                confidence=0.9,
                data_points={
                    "high_severity_count": len(high_severity_anomalies),
                    "total_anomalies": len(anomalies),
                    "max_amount": max([a.actual_value for a in high_severity_anomalies]) if high_severity_anomalies else 0
                },
                expires_at=date.today() + timedelta(days=3)
            ))
        
        return insights
    
    def _generate_forecast_warning_insights(
        self, 
        account_id: Optional[str]
    ) -> List[PersonalizedInsight]:
        """Generate insights about forecast warnings"""
        insights = []
        
        cashflow_projection = self.forecasting_engine.project_cashflow(
            forecast_months=6, account_id=account_id
        )
        
        # Check for negative cash flow in pessimistic scenario
        negative_months = sum(1 for point in cashflow_projection.pessimistic_scenario if point.predicted_value < -500)
        
        if negative_months >= 3:
            insights.append(PersonalizedInsight(
                id="forecast_warning_negative_cashflow",
                category=InsightCategory.FORECAST_WARNING,
                priority=InsightPriority.HIGH,
                title="Cash Flow Risk Detected",
                description=f"Pessimistic projections show {negative_months} months of negative cash flow in the next 6 months.",
                recommendations=[
                    "Build an emergency fund to handle potential shortfalls",
                    "Review and reduce non-essential expenses",
                    "Consider additional income sources",
                    "Monitor actual vs. projected spending closely"
                ],
                impact_score=min(1.0, negative_months / 6),
                confidence=0.7,
                data_points={
                    "negative_months": negative_months,
                    "projection_period": 6,
                    "scenario": "pessimistic"
                },
                expires_at=date.today() + timedelta(days=14)
            ))
        
        return insights
    
    def _calculate_spending_health_score(
        self, 
        patterns: List, 
        anomalies: List
    ) -> int:
        """Calculate spending health score (0-100)"""
        score = 80  # Base score
        
        # Penalize for many anomalies
        if anomalies:
            high_severity_count = len([a for a in anomalies if a.severity == "high"])
            score -= min(30, high_severity_count * 10)
        
        # Reward for consistent patterns
        if patterns:
            consistent_patterns = len([p for p in patterns if p.confidence > 0.7])
            score += min(20, consistent_patterns * 5)
        
        return max(0, min(100, score))
    
    def _calculate_savings_health_score(self, account_id: Optional[str]) -> int:
        """Calculate savings health score based on cash flow"""
        try:
            cashflow_projection = self.forecasting_engine.project_cashflow(
                forecast_months=3, account_id=account_id
            )
            
            positive_months = sum(1 for point in cashflow_projection.base_scenario if point.predicted_value > 0)
            avg_surplus = statistics.mean([
                max(0, point.predicted_value) for point in cashflow_projection.base_scenario
            ])
            
            score = (positive_months / 3) * 70  # 70 points for positive cash flow
            score += min(30, avg_surplus / 50)  # Up to 30 points for surplus amount
            
            return int(score)
        except:
            return 50  # Default score if calculation fails
    
    def _calculate_budgeting_health_score(self, patterns: List, trends: List) -> int:
        """Calculate budgeting health score"""
        score = 60  # Base score
        
        # Reward for regular patterns
        if patterns:
            regular_patterns = len([p for p in patterns if p.pattern_type == "regular"])
            score += min(25, regular_patterns * 5)
        
        # Penalize for negative trends
        if trends:
            negative_trends = len([t for t in trends if t.trend_direction.value == "increasing" and "Spending" in t.metric_name])
            score -= min(20, negative_trends * 10)
        
        return max(0, min(100, score))
    
    def _calculate_trend_health_score(self, trends: List) -> int:
        """Calculate trend health score"""
        if not trends:
            return 50
        
        score = 70  # Base score
        
        # Reward for positive trends (decreasing spending, increasing income)
        positive_trends = 0
        negative_trends = 0
        
        for trend in trends:
            if "Spending" in trend.metric_name and trend.trend_direction.value == "decreasing":
                positive_trends += 1
            elif "Income" in trend.metric_name and trend.trend_direction.value == "increasing":
                positive_trends += 1
            elif "Spending" in trend.metric_name and trend.trend_direction.value == "increasing":
                negative_trends += 1
        
        score += min(20, positive_trends * 10)
        score -= min(30, negative_trends * 15)
        
        return max(0, min(100, score))
    
    def _determine_spending_persona(
        self, 
        avg_monthly_spending: float, 
        volatility: float, 
        top_categories: List[Tuple[str, float]]
    ) -> SpendingPersona:
        """Determine user's spending persona"""
        
        if avg_monthly_spending < 1000:
            if volatility < 0.3:
                return SpendingPersona.CONSERVATIVE_SAVER
            else:
                return SpendingPersona.BUDGET_CONSCIOUS
        elif avg_monthly_spending < 3000:
            if volatility > 0.5:
                return SpendingPersona.IMPULSE_SPENDER
            else:
                return SpendingPersona.MODERATE_SPENDER
        else:
            if volatility > 0.4:
                return SpendingPersona.IMPULSE_SPENDER
            else:
                return SpendingPersona.FREQUENT_BUYER
    
    def _analyze_spending_habits(self, spending_data: List, persona: SpendingPersona) -> List[str]:
        """Analyze spending habits from data"""
        habits = []
        
        # Analyze frequency patterns
        transaction_counts = defaultdict(int)
        for row in spending_data:
            transaction_counts[row[0]] += row[3]  # month, transaction_count
        
        if transaction_counts:
            avg_transactions = statistics.mean(transaction_counts.values())
            if avg_transactions > 50:
                habits.append("High-frequency spender")
            elif avg_transactions < 20:
                habits.append("Infrequent, large purchases")
        
        # Add persona-specific habits
        persona_habits = {
            SpendingPersona.CONSERVATIVE_SAVER: ["Careful with money", "Avoids unnecessary purchases"],
            SpendingPersona.MODERATE_SPENDER: ["Balanced spending approach", "Plans major purchases"],
            SpendingPersona.FREQUENT_BUYER: ["Regular shopping habits", "Multiple small purchases"],
            SpendingPersona.BUDGET_CONSCIOUS: ["Price-sensitive", "Seeks value and deals"],
            SpendingPersona.IMPULSE_SPENDER: ["Spontaneous purchases", "Variable spending patterns"]
        }
        
        habits.extend(persona_habits.get(persona, []))
        return habits
    
    def _identify_behavioral_risks(self, persona: SpendingPersona, volatility: float) -> List[str]:
        """Identify behavioral risk factors"""
        risks = []
        
        if volatility > 0.5:
            risks.append("High spending volatility")
        
        persona_risks = {
            SpendingPersona.IMPULSE_SPENDER: ["Unplanned purchases", "Emotional spending"],
            SpendingPersona.FREQUENT_BUYER: ["Accumulation of small expenses", "Subscription creep"],
        }
        
        risks.extend(persona_risks.get(persona, []))
        return risks
    
    def _generate_behavioral_insights(
        self, 
        persona: SpendingPersona, 
        avg_spending: float, 
        volatility: float, 
        top_categories: List[Tuple[str, float]]
    ) -> List[str]:
        """Generate behavioral insights"""
        insights = []
        
        insights.append(f"Your spending persona: {persona.value.replace('_', ' ').title()}")
        insights.append(f"Average monthly spending: ${avg_spending:.2f}")
        
        if volatility < 0.3:
            insights.append("Consistent spending patterns - good budgeting control")
        elif volatility > 0.5:
            insights.append("Variable spending patterns - consider budgeting tools")
        
        if top_categories:
            top_category = top_categories[0][0]
            insights.append(f"Primary spending category: {top_category}")
        
        return insights
    
    def _create_default_spending_profile(self) -> SpendingBehaviorProfile:
        """Create default profile when no data available"""
        return SpendingBehaviorProfile(
            persona=SpendingPersona.MODERATE_SPENDER,
            avg_monthly_spending=0.0,
            spending_volatility=0.0,
            top_categories=[],
            spending_habits=["Insufficient data for analysis"],
            risk_factors=["Limited transaction history"],
            behavioral_insights=["Import more transactions for detailed analysis"]
        )
    
    def _identify_financial_strengths(
        self, 
        spending_health: int, 
        savings_health: int, 
        budgeting_health: int, 
        trend_health: int
    ) -> List[str]:
        """Identify financial strengths"""
        strengths = []
        
        if spending_health >= 80:
            strengths.append("Excellent spending control")
        if savings_health >= 80:
            strengths.append("Strong savings potential")
        if budgeting_health >= 80:
            strengths.append("Disciplined budgeting habits")
        if trend_health >= 80:
            strengths.append("Positive financial trends")
        
        return strengths
    
    def _identify_improvement_areas(
        self, 
        spending_health: int, 
        savings_health: int, 
        budgeting_health: int, 
        trend_health: int
    ) -> List[str]:
        """Identify areas for improvement"""
        improvements = []
        
        if spending_health < 60:
            improvements.append("Spending optimization needed")
        if savings_health < 60:
            improvements.append("Increase savings rate")
        if budgeting_health < 60:
            improvements.append("Improve budgeting discipline")
        if trend_health < 60:
            improvements.append("Address negative spending trends")
        
        return improvements
    
    def _generate_health_recommendations(
        self, 
        health_grade: FinancialHealthScore, 
        improvement_areas: List[str]
    ) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []
        
        if health_grade == FinancialHealthScore.CRITICAL:
            recommendations.extend([
                "Immediate budget review required",
                "Identify and eliminate unnecessary expenses",
                "Consider financial counseling"
            ])
        elif health_grade == FinancialHealthScore.POOR:
            recommendations.extend([
                "Create and stick to a strict budget",
                "Focus on reducing largest expense categories",
                "Build emergency fund gradually"
            ])
        elif health_grade == FinancialHealthScore.FAIR:
            recommendations.extend([
                "Fine-tune budget allocations",
                "Increase savings rate by 2-3%",
                "Monitor spending trends monthly"
            ])
        else:
            recommendations.extend([
                "Continue current financial habits",
                "Explore investment opportunities",
                "Consider advanced financial planning"
            ])
        
        # Add specific recommendations based on improvement areas
        for area in improvement_areas:
            if "spending" in area.lower():
                recommendations.append("Review and optimize major spending categories")
            elif "savings" in area.lower():
                recommendations.append("Set up automatic savings transfers")
            elif "budgeting" in area.lower():
                recommendations.append("Use budgeting tools and track expenses regularly")
        
        return recommendations


# Global instance
_ai_insights_engine = None

def get_ai_insights_engine() -> AIInsightsEngine:
    """Get the global AI insights engine instance"""
    global _ai_insights_engine
    if _ai_insights_engine is None:
        _ai_insights_engine = AIInsightsEngine()
    return _ai_insights_engine