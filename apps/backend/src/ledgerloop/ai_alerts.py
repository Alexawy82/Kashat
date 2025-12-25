"""
AI-Powered Budget Alerts and Notifications System

Intelligent alert system that:
- Monitors spending patterns and budget thresholds
- Provides predictive alerts before budget overruns
- Sends personalized financial notifications
- Learns from user preferences and behaviors
- Provides actionable recommendations with alerts
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta, UTC
from enum import Enum

from .db import get_conn
from .ai_analytics import get_ai_analytics_engine
from .ai_forecasting import get_ai_forecasting_engine
from .ai_insights import get_ai_insights_engine


class AlertType(Enum):
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    SPENDING_SPIKE = "spending_spike"
    UNUSUAL_TRANSACTION = "unusual_transaction"
    RECURRING_MISSED = "recurring_missed"
    INCOME_CHANGE = "income_change"
    SAVINGS_OPPORTUNITY = "savings_opportunity"
    SUBSCRIPTION_REMINDER = "subscription_reminder"
    BILL_DUE = "bill_due"
    FINANCIAL_GOAL = "financial_goal"


class AlertPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH_NOTIFICATION = "push"


@dataclass
class BudgetAlert:
    id: str
    alert_type: AlertType
    priority: AlertPriority
    title: str
    message: str
    category_id: Optional[str]
    category_name: Optional[str]
    current_amount: float
    threshold_amount: float
    percentage_used: float
    time_remaining: str  # "5 days", "2 weeks", etc.
    suggested_actions: List[Dict[str, Any]]
    channels: List[AlertChannel]
    expires_at: datetime
    created_at: datetime
    account_id: str


@dataclass
class AlertRule:
    id: str
    name: str
    alert_type: AlertType
    conditions: Dict[str, Any]
    threshold_config: Dict[str, Any]
    channels: List[AlertChannel]
    is_active: bool
    frequency_limit: str  # "once", "daily", "weekly"
    last_triggered: Optional[datetime]
    user_preferences: Dict[str, Any]
    created_at: datetime


@dataclass
class NotificationPreferences:
    user_id: str
    budget_alerts_enabled: bool
    spending_alerts_enabled: bool
    goal_alerts_enabled: bool
    preferred_channels: List[AlertChannel]
    quiet_hours_start: Optional[str]  # "22:00"
    quiet_hours_end: Optional[str]    # "08:00"
    spending_threshold_percentage: float  # Alert at X% of budget
    large_transaction_threshold: float
    frequency_preference: str  # "immediate", "daily_digest", "weekly_digest"


class AIAlertSystem:
    """Intelligent budget and spending alert system"""
    
    def __init__(self):
        self.analytics_engine = get_ai_analytics_engine()
        self.forecasting_engine = get_ai_forecasting_engine()
        self.insights_engine = get_ai_insights_engine()
    
    async def generate_budget_alerts(
        self,
        account_id: str,
        check_all_categories: bool = True
    ) -> List[BudgetAlert]:
        """Generate intelligent budget alerts"""
        
        alerts = []
        
        # Get user's budget configuration
        budgets = await self._get_active_budgets(account_id)
        
        if not budgets:
            return alerts
        
        current_date = datetime.now(UTC)
        
        for budget in budgets:
            category_id = budget.get('category_id')
            category_name = budget.get('category_name', 'Uncategorized')
            budget_amount = budget.get('amount', 0)
            period_start = budget.get('period_start')
            period_end = budget.get('period_end')
            
            # Get current spending for this category
            current_spending = await self._get_category_spending(
                account_id, category_id, period_start, period_end
            )
            
            percentage_used = (abs(current_spending) / budget_amount) * 100 if budget_amount > 0 else 0
            
            # Calculate time remaining in budget period
            days_remaining = (period_end - current_date.date()).days if period_end else 0
            time_remaining = self._format_time_remaining(days_remaining)
            
            # Generate alerts based on thresholds
            budget_alerts = await self._generate_category_budget_alerts(
                account_id, category_id, category_name, current_spending,
                budget_amount, percentage_used, time_remaining, days_remaining
            )
            
            alerts.extend(budget_alerts)
        
        # Generate predictive budget alerts
        predictive_alerts = await self._generate_predictive_budget_alerts(account_id)
        alerts.extend(predictive_alerts)
        
        return alerts
    
    async def generate_spending_alerts(
        self,
        account_id: str
    ) -> List[BudgetAlert]:
        """Generate spending pattern and anomaly alerts"""
        
        alerts = []
        
        # Unusual spending spikes
        spike_alerts = await self._detect_spending_spikes(account_id)
        alerts.extend(spike_alerts)
        
        # Large transaction alerts
        large_transaction_alerts = await self._detect_large_transactions(account_id)
        alerts.extend(large_transaction_alerts)
        
        # Subscription and recurring transaction alerts
        subscription_alerts = await self._generate_subscription_alerts(account_id)
        alerts.extend(subscription_alerts)
        
        # Income change alerts
        income_alerts = await self._detect_income_changes(account_id)
        alerts.extend(income_alerts)
        
        return alerts
    
    async def generate_opportunity_alerts(
        self,
        account_id: str
    ) -> List[BudgetAlert]:
        """Generate savings and financial opportunity alerts"""
        
        alerts = []
        
        # Savings opportunities
        savings_alerts = await self._identify_savings_opportunities(account_id)
        alerts.extend(savings_alerts)
        
        # Goal progress alerts
        goal_alerts = await self._generate_goal_progress_alerts(account_id)
        alerts.extend(goal_alerts)
        
        # Cash flow optimization alerts
        cashflow_alerts = await self._generate_cashflow_alerts(account_id)
        alerts.extend(cashflow_alerts)
        
        return alerts
    
    async def create_custom_alert_rule(
        self,
        name: str,
        alert_type: AlertType,
        conditions: Dict[str, Any],
        threshold_config: Dict[str, Any],
        channels: List[AlertChannel],
        user_preferences: Dict[str, Any]
    ) -> AlertRule:
        """Create a custom alert rule"""
        
        rule = AlertRule(
            id=str(uuid.uuid4()),
            name=name,
            alert_type=alert_type,
            conditions=conditions,
            threshold_config=threshold_config,
            channels=channels,
            is_active=True,
            frequency_limit=user_preferences.get('frequency', 'daily'),
            last_triggered=None,
            user_preferences=user_preferences,
            created_at=datetime.now(UTC)
        )
        
        await self._store_alert_rule(rule)
        return rule
    
    async def evaluate_custom_alerts(
        self,
        account_id: str
    ) -> List[BudgetAlert]:
        """Evaluate and trigger custom alert rules"""
        
        conn = get_conn()
        
        # Get active alert rules
        rules = conn.execute("""
            SELECT id, name, alert_type, conditions_json, threshold_config_json,
                   channels_json, frequency_limit, last_triggered, user_preferences_json
            FROM alert_rule
            WHERE is_active = true
        """).fetchall()
        
        alerts = []
        
        for rule_data in rules:
            try:
                rule_id, name, alert_type, conditions_json, threshold_json, channels_json, freq_limit, last_triggered, prefs_json = rule_data
                
                conditions = json.loads(conditions_json)
                threshold_config = json.loads(threshold_json)
                channels = [AlertChannel(ch) for ch in json.loads(channels_json)]
                
                # Check if rule should be evaluated (frequency limiting)
                if not await self._should_evaluate_rule(rule_id, freq_limit, last_triggered):
                    continue
                
                # Evaluate rule conditions
                if await self._evaluate_alert_conditions(account_id, conditions, threshold_config):
                    alert = await self._create_alert_from_rule(
                        account_id, rule_id, name, AlertType(alert_type), 
                        conditions, threshold_config, channels
                    )
                    
                    if alert:
                        alerts.append(alert)
                        
                        # Update last triggered time
                        conn.execute(
                            "UPDATE alert_rule SET last_triggered = ? WHERE id = ?",
                            [datetime.now(UTC), rule_id]
                        )
            
            except Exception as e:
                print(f"Error evaluating alert rule {rule_data[0]}: {e}")
        
        return alerts
    
    async def send_alert_notifications(
        self,
        alerts: List[BudgetAlert],
        user_preferences: NotificationPreferences
    ) -> Dict[str, Any]:
        """Send alert notifications through configured channels"""
        
        if not user_preferences.budget_alerts_enabled:
            return {'sent': 0, 'skipped': len(alerts), 'reason': 'alerts_disabled'}
        
        # Filter alerts based on preferences
        filtered_alerts = await self._filter_alerts_by_preferences(alerts, user_preferences)
        
        # Group alerts by priority and channel
        notifications_sent = {
            'in_app': 0,
            'email': 0,
            'sms': 0,
            'push': 0,
            'failed': 0
        }
        
        for alert in filtered_alerts:
            for channel in alert.channels:
                if channel in user_preferences.preferred_channels:
                    success = await self._send_notification(alert, channel, user_preferences)
                    
                    if success:
                        notifications_sent[channel.value] += 1
                    else:
                        notifications_sent['failed'] += 1
        
        return {
            'total_alerts': len(alerts),
            'filtered_alerts': len(filtered_alerts),
            'notifications_sent': notifications_sent
        }
    
    # Helper methods for budget alerts
    
    async def _get_active_budgets(self, account_id: str) -> List[Dict[str, Any]]:
        """Get active budget configurations"""
        
        conn = get_conn()
        
        # This assumes a budget table exists - simplified implementation
        current_date = datetime.now(UTC).date()
        
        budgets = conn.execute("""
            SELECT category_id, amount, period_start, period_end, c.name as category_name
            FROM budget b
            LEFT JOIN category c ON c.id = b.category_id
            WHERE account_id = ? 
            AND period_start <= ? 
            AND period_end >= ?
            AND is_active = true
        """, [account_id, current_date, current_date]).fetchall()
        
        return [
            {
                'category_id': b[0],
                'amount': b[1],
                'period_start': b[2],
                'period_end': b[3],
                'category_name': b[4] or 'Uncategorized'
            }
            for b in budgets
        ]
    
    async def _get_category_spending(
        self,
        account_id: str,
        category_id: Optional[str],
        period_start: date,
        period_end: date
    ) -> float:
        """Get current spending for a category in the given period"""
        
        conn = get_conn()
        
        if category_id:
            spending = conn.execute("""
                SELECT COALESCE(SUM(t.amount), 0)
                FROM [transaction] t
                JOIN transaction_category tc ON tc.tx_id = t.id
                WHERE t.account_id = ? AND tc.category_id = ?
                AND t.posted_at BETWEEN ? AND ?
                AND t.amount < 0
            """, [account_id, category_id, period_start, period_end]).fetchone()[0]
        else:
            # Uncategorized spending
            spending = conn.execute("""
                SELECT COALESCE(SUM(t.amount), 0)
                FROM [transaction] t
                LEFT JOIN transaction_category tc ON tc.tx_id = t.id
                WHERE t.account_id = ? AND tc.tx_id IS NULL
                AND t.posted_at BETWEEN ? AND ?
                AND t.amount < 0
            """, [account_id, period_start, period_end]).fetchone()[0]
        
        return spending
    
    def _format_time_remaining(self, days: int) -> str:
        """Format remaining time in budget period"""
        
        if days <= 0:
            return "period ended"
        elif days == 1:
            return "1 day"
        elif days < 7:
            return f"{days} days"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''}"
        else:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''}"
    
    async def _generate_category_budget_alerts(
        self,
        account_id: str,
        category_id: Optional[str],
        category_name: str,
        current_spending: float,
        budget_amount: float,
        percentage_used: float,
        time_remaining: str,
        days_remaining: int
    ) -> List[BudgetAlert]:
        """Generate alerts for a specific budget category"""
        
        alerts = []
        
        # Critical: Budget exceeded
        if percentage_used >= 100:
            overage = abs(current_spending) - budget_amount
            alerts.append(BudgetAlert(
                id=str(uuid.uuid4()),
                alert_type=AlertType.BUDGET_EXCEEDED,
                priority=AlertPriority.CRITICAL,
                title=f"Budget Exceeded: {category_name}",
                message=f"You've exceeded your {category_name} budget by ${overage:.2f} ({percentage_used:.1f}% used)",
                category_id=category_id,
                category_name=category_name,
                current_amount=abs(current_spending),
                threshold_amount=budget_amount,
                percentage_used=percentage_used,
                time_remaining=time_remaining,
                suggested_actions=[
                    {"action": "review_transactions", "description": f"Review recent {category_name} transactions"},
                    {"action": "adjust_budget", "description": f"Consider increasing {category_name} budget"},
                    {"action": "reduce_spending", "description": f"Limit {category_name} spending for remainder of period"}
                ],
                channels=[AlertChannel.IN_APP, AlertChannel.PUSH_NOTIFICATION],
                expires_at=datetime.now(UTC) + timedelta(days=7),
                created_at=datetime.now(UTC),
                account_id=account_id
            ))
        
        # High: Approaching budget limit
        elif percentage_used >= 85:
            remaining = budget_amount - abs(current_spending)
            alerts.append(BudgetAlert(
                id=str(uuid.uuid4()),
                alert_type=AlertType.BUDGET_WARNING,
                priority=AlertPriority.HIGH,
                title=f"Budget Warning: {category_name}",
                message=f"You've used {percentage_used:.1f}% of your {category_name} budget. ${remaining:.2f} remaining for {time_remaining}.",
                category_id=category_id,
                category_name=category_name,
                current_amount=abs(current_spending),
                threshold_amount=budget_amount,
                percentage_used=percentage_used,
                time_remaining=time_remaining,
                suggested_actions=[
                    {"action": "track_spending", "description": f"Monitor {category_name} spending closely"},
                    {"action": "find_alternatives", "description": f"Look for cheaper alternatives in {category_name}"},
                    {"action": "defer_purchases", "description": f"Delay non-essential {category_name} purchases"}
                ],
                channels=[AlertChannel.IN_APP, AlertChannel.PUSH_NOTIFICATION],
                expires_at=datetime.now(UTC) + timedelta(days=3),
                created_at=datetime.now(UTC),
                account_id=account_id
            ))
        
        # Medium: On track to exceed budget
        elif percentage_used >= 70 and days_remaining > 0:
            # Predict if on track to exceed
            daily_burn_rate = abs(current_spending) / max(1, (30 - days_remaining))
            projected_total = abs(current_spending) + (daily_burn_rate * days_remaining)
            
            if projected_total > budget_amount:
                projected_overage = projected_total - budget_amount
                alerts.append(BudgetAlert(
                    id=str(uuid.uuid4()),
                    alert_type=AlertType.BUDGET_WARNING,
                    priority=AlertPriority.MEDIUM,
                    title=f"Budget Pace Warning: {category_name}",
                    message=f"At current pace, you may exceed your {category_name} budget by ${projected_overage:.2f}",
                    category_id=category_id,
                    category_name=category_name,
                    current_amount=abs(current_spending),
                    threshold_amount=budget_amount,
                    percentage_used=percentage_used,
                    time_remaining=time_remaining,
                    suggested_actions=[
                        {"action": "reduce_pace", "description": f"Slow down {category_name} spending pace"},
                        {"action": "weekly_review", "description": f"Set weekly {category_name} spending limits"},
                        {"action": "budget_adjustment", "description": f"Consider adjusting {category_name} budget"}
                    ],
                    channels=[AlertChannel.IN_APP],
                    expires_at=datetime.now(UTC) + timedelta(days=2),
                    created_at=datetime.now(UTC),
                    account_id=account_id
                ))
        
        return alerts
    
    async def _generate_predictive_budget_alerts(
        self,
        account_id: str
    ) -> List[BudgetAlert]:
        """Generate predictive budget alerts using AI forecasting"""
        
        alerts = []
        
        try:
            # Use AI forecasting to predict upcoming budget issues
            forecast = self.forecasting_engine.forecast_spending(
                account_id=account_id,
                forecast_months=1
            )
            
            # Analyze forecast for potential budget overruns
            for category_forecast in forecast.category_forecasts:
                # This would be expanded with actual forecast analysis
                pass
        
        except Exception as e:
            print(f"Error generating predictive alerts: {e}")
        
        return alerts
    
    async def _detect_spending_spikes(self, account_id: str) -> List[BudgetAlert]:
        """Detect unusual spending spikes"""
        
        alerts = []
        
        try:
            # Get recent spending patterns
            analytics = self.analytics_engine.analyze_spending_patterns(account_id=account_id)
            
            # Look for anomalies
            for pattern in analytics.patterns:
                if hasattr(pattern, 'anomaly_score') and pattern.anomaly_score > 0.8:
                    alerts.append(BudgetAlert(
                        id=str(uuid.uuid4()),
                        alert_type=AlertType.SPENDING_SPIKE,
                        priority=AlertPriority.MEDIUM,
                        title="Unusual Spending Detected",
                        message=f"Unusual spending spike detected in {pattern.category}",
                        category_id=getattr(pattern, 'category_id', None),
                        category_name=pattern.category,
                        current_amount=pattern.average_amount,
                        threshold_amount=pattern.average_amount * 0.5,  # Threshold for normal
                        percentage_used=0,
                        time_remaining="N/A",
                        suggested_actions=[
                            {"action": "review_recent", "description": "Review recent transactions for this category"},
                            {"action": "verify_accuracy", "description": "Verify transaction accuracy and categorization"}
                        ],
                        channels=[AlertChannel.IN_APP],
                        expires_at=datetime.now(UTC) + timedelta(days=1),
                        created_at=datetime.now(UTC),
                        account_id=account_id
                    ))
        
        except Exception as e:
            print(f"Error detecting spending spikes: {e}")
        
        return alerts
    
    async def _detect_large_transactions(self, account_id: str) -> List[BudgetAlert]:
        """Detect unusually large transactions"""
        
        conn = get_conn()
        alerts = []
        
        # Get recent large transactions (last 7 days)
        cutoff_date = datetime.now(UTC) - timedelta(days=7)
        
        # Calculate user's typical transaction size
        avg_transaction = conn.execute("""
            SELECT AVG(ABS(amount)) FROM [transaction] 
            WHERE account_id = ? AND posted_at >= ?
        """, [account_id, cutoff_date - timedelta(days=30)]).fetchone()[0] or 0
        
        large_threshold = max(100, avg_transaction * 3)  # 3x average or $100 minimum
        
        large_transactions = conn.execute("""
            SELECT id, description_norm, amount, posted_at
            FROM [transaction]
            WHERE account_id = ? AND posted_at >= ?
            AND ABS(amount) > ?
            ORDER BY posted_at DESC
            LIMIT 5
        """, [account_id, cutoff_date, large_threshold]).fetchall()
        
        for tx_id, description, amount, posted_at in large_transactions:
            alerts.append(BudgetAlert(
                id=str(uuid.uuid4()),
                alert_type=AlertType.UNUSUAL_TRANSACTION,
                priority=AlertPriority.MEDIUM,
                title="Large Transaction Alert",
                message=f"Large transaction: ${abs(amount):.2f} at {description}",
                category_id=None,
                category_name=None,
                current_amount=abs(amount),
                threshold_amount=large_threshold,
                percentage_used=0,
                time_remaining="N/A",
                suggested_actions=[
                    {"action": "verify_transaction", "description": "Verify this transaction is legitimate"},
                    {"action": "categorize", "description": "Ensure transaction is properly categorized"},
                    {"action": "budget_impact", "description": "Review impact on relevant budget categories"}
                ],
                channels=[AlertChannel.IN_APP, AlertChannel.PUSH_NOTIFICATION],
                expires_at=datetime.now(UTC) + timedelta(days=3),
                created_at=datetime.now(UTC),
                account_id=account_id
            ))
        
        return alerts
    
    # Additional helper methods would be implemented here...
    
    async def _generate_subscription_alerts(self, account_id: str) -> List[BudgetAlert]:
        """Generate subscription-related alerts"""
        return []  # Placeholder
    
    async def _detect_income_changes(self, account_id: str) -> List[BudgetAlert]:
        """Detect changes in income patterns"""
        return []  # Placeholder
    
    async def _identify_savings_opportunities(self, account_id: str) -> List[BudgetAlert]:
        """Identify potential savings opportunities"""
        return []  # Placeholder
    
    async def _generate_goal_progress_alerts(self, account_id: str) -> List[BudgetAlert]:
        """Generate alerts about financial goal progress"""
        return []  # Placeholder
    
    async def _generate_cashflow_alerts(self, account_id: str) -> List[BudgetAlert]:
        """Generate cash flow optimization alerts"""
        return []  # Placeholder
    
    async def _store_alert_rule(self, rule: AlertRule):
        """Store alert rule in database"""
        
        conn = get_conn()
        
        conn.execute("""
            INSERT INTO alert_rule (
                id, name, alert_type, conditions_json, threshold_config_json,
                channels_json, is_active, frequency_limit, last_triggered,
                user_preferences_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            rule.id, rule.name, rule.alert_type.value, json.dumps(rule.conditions),
            json.dumps(rule.threshold_config), json.dumps([ch.value for ch in rule.channels]),
            rule.is_active, rule.frequency_limit, rule.last_triggered,
            json.dumps(rule.user_preferences), rule.created_at
        ])
    
    async def _should_evaluate_rule(
        self, 
        rule_id: str, 
        frequency_limit: str, 
        last_triggered: Optional[datetime]
    ) -> bool:
        """Check if alert rule should be evaluated based on frequency limits"""
        
        if not last_triggered:
            return True
        
        now = datetime.now(UTC)
        
        if frequency_limit == "once":
            return False  # Already triggered
        elif frequency_limit == "daily":
            return (now - last_triggered).days >= 1
        elif frequency_limit == "weekly":
            return (now - last_triggered).days >= 7
        
        return True  # Default to allow evaluation
    
    async def _evaluate_alert_conditions(
        self,
        account_id: str,
        conditions: Dict[str, Any],
        threshold_config: Dict[str, Any]
    ) -> bool:
        """Evaluate if alert conditions are met"""
        # Placeholder implementation
        return False
    
    async def _create_alert_from_rule(
        self,
        account_id: str,
        rule_id: str,
        name: str,
        alert_type: AlertType,
        conditions: Dict[str, Any],
        threshold_config: Dict[str, Any],
        channels: List[AlertChannel]
    ) -> Optional[BudgetAlert]:
        """Create alert from rule evaluation"""
        # Placeholder implementation
        return None
    
    async def _filter_alerts_by_preferences(
        self,
        alerts: List[BudgetAlert],
        preferences: NotificationPreferences
    ) -> List[BudgetAlert]:
        """Filter alerts based on user preferences"""
        
        filtered = []
        
        for alert in alerts:
            # Check if alert type is enabled
            if alert.alert_type == AlertType.BUDGET_WARNING and not preferences.budget_alerts_enabled:
                continue
            
            if alert.alert_type == AlertType.SPENDING_SPIKE and not preferences.spending_alerts_enabled:
                continue
            
            # Check quiet hours
            current_time = datetime.now(UTC).time()
            if preferences.quiet_hours_start and preferences.quiet_hours_end:
                quiet_start = datetime.strptime(preferences.quiet_hours_start, "%H:%M").time()
                quiet_end = datetime.strptime(preferences.quiet_hours_end, "%H:%M").time()
                
                if quiet_start <= current_time <= quiet_end:
                    # Modify channels to exclude real-time notifications
                    alert.channels = [ch for ch in alert.channels if ch == AlertChannel.IN_APP]
            
            filtered.append(alert)
        
        return filtered
    
    async def _send_notification(
        self,
        alert: BudgetAlert,
        channel: AlertChannel,
        preferences: NotificationPreferences
    ) -> bool:
        """Send notification through specified channel"""
        
        try:
            if channel == AlertChannel.IN_APP:
                # Store in-app notification
                return await self._store_in_app_notification(alert)
            
            elif channel == AlertChannel.EMAIL:
                # Send email notification
                return await self._send_email_notification(alert, preferences)
            
            elif channel == AlertChannel.SMS:
                # Send SMS notification
                return await self._send_sms_notification(alert, preferences)
            
            elif channel == AlertChannel.PUSH_NOTIFICATION:
                # Send push notification
                return await self._send_push_notification(alert, preferences)
            
            return False
        
        except Exception as e:
            print(f"Error sending notification via {channel}: {e}")
            return False
    
    async def _store_in_app_notification(self, alert: BudgetAlert) -> bool:
        """Store in-app notification"""
        
        conn = get_conn()
        
        try:
            conn.execute("""
                INSERT INTO notification (
                    id, alert_type, priority, title, message, account_id,
                    data_json, is_read, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                alert.id, alert.alert_type.value, alert.priority.value,
                alert.title, alert.message, alert.account_id,
                json.dumps({
                    'category_id': alert.category_id,
                    'category_name': alert.category_name,
                    'current_amount': alert.current_amount,
                    'threshold_amount': alert.threshold_amount,
                    'suggested_actions': alert.suggested_actions
                }),
                False, alert.created_at, alert.expires_at
            ])
            return True
        
        except Exception as e:
            print(f"Error storing in-app notification: {e}")
            return False
    
    async def _send_email_notification(self, alert: BudgetAlert, preferences: NotificationPreferences) -> bool:
        """Send email notification"""
        # Placeholder - would integrate with email service
        return True
    
    async def _send_sms_notification(self, alert: BudgetAlert, preferences: NotificationPreferences) -> bool:
        """Send SMS notification"""
        # Placeholder - would integrate with SMS service
        return True
    
    async def _send_push_notification(self, alert: BudgetAlert, preferences: NotificationPreferences) -> bool:
        """Send push notification"""
        # Placeholder - would integrate with push notification service
        return True


# Global instance
_ai_alert_system = None

def get_ai_alert_system() -> AIAlertSystem:
    """Get the global AI alert system instance"""
    global _ai_alert_system
    if _ai_alert_system is None:
        _ai_alert_system = AIAlertSystem()
    return _ai_alert_system