"""
AI-Powered Data Quality Management System

Automated data quality system that:
- Continuously monitors transaction data for quality issues
- Detects and corrects common data problems automatically
- Provides data integrity validation and cleansing
- Learns from patterns to prevent future quality issues
- Generates quality reports and improvement recommendations
"""

from __future__ import annotations

import re
import json
import uuid
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime, date, timedelta, UTC
from collections import defaultdict, Counter
from enum import Enum

from .db import get_conn


class QualityIssueType(Enum):
    MISSING_DATA = "missing_data"
    INVALID_FORMAT = "invalid_format"
    INCONSISTENT_DATA = "inconsistent_data"
    DUPLICATE_ENTRY = "duplicate_entry"
    OUTLIER_VALUE = "outlier_value"
    ENCODING_ERROR = "encoding_error"
    CATEGORIZATION_ERROR = "categorization_error"
    DATE_INCONSISTENCY = "date_inconsistency"
    AMOUNT_ANOMALY = "amount_anomaly"
    MERCHANT_INCONSISTENCY = "merchant_inconsistency"


class QualitySeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CorrectionStatus(Enum):
    DETECTED = "detected"
    AUTO_CORRECTED = "auto_corrected"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    USER_CORRECTED = "user_corrected"
    IGNORED = "ignored"


@dataclass
class QualityIssue:
    id: str
    issue_type: QualityIssueType
    severity: QualitySeverity
    entity_type: str  # "transaction", "category", "account"
    entity_id: str
    description: str
    current_value: Optional[str]
    suggested_correction: Optional[str]
    confidence: float
    auto_correctable: bool
    impact_assessment: str
    detection_method: str
    created_at: datetime
    corrected_at: Optional[datetime]
    status: CorrectionStatus


@dataclass
class QualityRule:
    id: str
    name: str
    issue_type: QualityIssueType
    entity_type: str
    validation_logic: Dict[str, Any]
    correction_logic: Optional[Dict[str, Any]]
    is_active: bool
    auto_correct: bool
    severity: QualitySeverity
    created_at: datetime


@dataclass
class QualityReport:
    account_id: str
    report_date: datetime
    total_transactions: int
    issues_found: int
    issues_corrected: int
    quality_score: float
    issue_breakdown: Dict[str, int]
    trends: Dict[str, Any]
    recommendations: List[str]


class AIDataQualityEngine:
    """Intelligent data quality monitoring and correction system"""
    
    def __init__(self):
        self._quality_rules = []
        self._correction_patterns = {}
        self._quality_cache = {}
    
    async def run_quality_assessment(
        self,
        account_id: str,
        entity_types: Optional[List[str]] = None,
        days_lookback: int = 30
    ) -> QualityReport:
        """Run comprehensive data quality assessment"""
        
        if entity_types is None:
            entity_types = ["transaction", "category", "account"]
        
        conn = get_conn()
        cutoff_date = datetime.now(UTC) - timedelta(days=days_lookback)
        
        # Get transaction count for the period
        total_transactions = conn.execute("""
            SELECT COUNT(*) FROM [transaction] 
            WHERE account_id = ? AND created_at >= ?
        """, [account_id, cutoff_date]).fetchone()[0]
        
        all_issues = []
        
        # Run quality checks for each entity type
        for entity_type in entity_types:
            issues = await self._detect_quality_issues(account_id, entity_type, cutoff_date)
            all_issues.extend(issues)
        
        # Auto-correct issues where possible
        corrected_count = await self._auto_correct_issues(all_issues)
        
        # Calculate quality score
        quality_score = await self._calculate_quality_score(account_id, all_issues, total_transactions)
        
        # Generate issue breakdown
        issue_breakdown = self._create_issue_breakdown(all_issues)
        
        # Analyze trends
        trends = await self._analyze_quality_trends(account_id)
        
        # Generate recommendations
        recommendations = await self._generate_quality_recommendations(all_issues, trends)
        
        report = QualityReport(
            account_id=account_id,
            report_date=datetime.now(UTC),
            total_transactions=total_transactions,
            issues_found=len(all_issues),
            issues_corrected=corrected_count,
            quality_score=quality_score,
            issue_breakdown=issue_breakdown,
            trends=trends,
            recommendations=recommendations
        )
        
        # Store quality report
        await self._store_quality_report(report)
        
        return report
    
    async def detect_and_fix_real_time(
        self,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any]
    ) -> List[QualityIssue]:
        """Detect and fix quality issues in real-time during data processing"""
        
        issues = []
        
        # Run applicable quality rules
        applicable_rules = await self._get_applicable_rules(entity_type)
        
        for rule in applicable_rules:
            issue = await self._apply_quality_rule(rule, entity_type, entity_id, data)
            
            if issue:
                issues.append(issue)
                
                # Auto-correct if possible and enabled
                if rule.auto_correct and issue.auto_correctable:
                    await self._apply_correction(issue, data)
                    issue.status = CorrectionStatus.AUTO_CORRECTED
                    issue.corrected_at = datetime.now(UTC)
        
        return issues
    
    async def learn_from_corrections(
        self,
        issue: QualityIssue,
        user_correction: str,
        feedback: Optional[str] = None
    ):
        """Learn from user corrections to improve quality detection"""
        
        conn = get_conn()
        
        # Store user correction
        conn.execute("""
            INSERT INTO quality_correction_feedback (
                id, issue_id, original_value, user_correction, 
                ai_suggestion, feedback, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4()), issue.id, issue.current_value,
            user_correction, issue.suggested_correction, feedback, datetime.now(UTC)
        ])
        
        # Update correction patterns
        await self._update_correction_patterns(issue, user_correction)
        
        # Mark issue as user corrected
        issue.status = CorrectionStatus.USER_CORRECTED
        issue.corrected_at = datetime.now(UTC)
        await self._update_quality_issue(issue)
    
    async def create_custom_quality_rule(
        self,
        name: str,
        issue_type: QualityIssueType,
        entity_type: str,
        validation_logic: Dict[str, Any],
        correction_logic: Optional[Dict[str, Any]] = None,
        severity: QualitySeverity = QualitySeverity.MEDIUM,
        auto_correct: bool = False
    ) -> QualityRule:
        """Create custom quality rule"""
        
        rule = QualityRule(
            id=str(uuid.uuid4()),
            name=name,
            issue_type=issue_type,
            entity_type=entity_type,
            validation_logic=validation_logic,
            correction_logic=correction_logic,
            is_active=True,
            auto_correct=auto_correct,
            severity=severity,
            created_at=datetime.now(UTC)
        )
        
        await self._store_quality_rule(rule)
        return rule
    
    async def get_quality_dashboard_data(
        self,
        account_id: str
    ) -> Dict[str, Any]:
        """Get data for quality dashboard"""
        
        conn = get_conn()
        
        # Recent quality issues
        recent_issues = conn.execute("""
            SELECT issue_type, severity, COUNT(*) as count
            FROM quality_issue 
            WHERE entity_id IN (
                SELECT id FROM [transaction] WHERE account_id = ?
            )
            AND created_at >= ?
            GROUP BY issue_type, severity
            ORDER BY count DESC
        """, [account_id, datetime.now(UTC) - timedelta(days=7)]).fetchall()
        
        # Quality trends
        quality_trends = conn.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as issues_count
            FROM quality_issue
            WHERE entity_id IN (
                SELECT id FROM [transaction] WHERE account_id = ?
            )
            AND created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, [account_id, datetime.now(UTC) - timedelta(days=30)]).fetchall()
        
        # Auto-correction success rate
        correction_stats = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'auto_corrected' THEN 1 ELSE 0 END) as auto_corrected,
                SUM(CASE WHEN status = 'user_corrected' THEN 1 ELSE 0 END) as user_corrected
            FROM quality_issue
            WHERE entity_id IN (
                SELECT id FROM [transaction] WHERE account_id = ?
            )
            AND created_at >= ?
        """, [account_id, datetime.now(UTC) - timedelta(days=30)]).fetchone()
        
        return {
            'recent_issues': [
                {'type': r[0], 'severity': r[1], 'count': r[2]} 
                for r in recent_issues
            ],
            'quality_trends': [
                {'date': r[0], 'issues_count': r[1]} 
                for r in quality_trends
            ],
            'correction_stats': {
                'total': correction_stats[0] if correction_stats else 0,
                'auto_corrected': correction_stats[1] if correction_stats else 0,
                'user_corrected': correction_stats[2] if correction_stats else 0,
                'auto_success_rate': (correction_stats[1] / correction_stats[0] * 100) if correction_stats and correction_stats[0] > 0 else 0
            }
        }
    
    # Core quality detection methods
    
    async def _detect_quality_issues(
        self,
        account_id: str,
        entity_type: str,
        cutoff_date: datetime
    ) -> List[QualityIssue]:
        """Detect quality issues for specific entity type"""
        
        issues = []
        
        if entity_type == "transaction":
            issues.extend(await self._detect_transaction_quality_issues(account_id, cutoff_date))
        elif entity_type == "category":
            issues.extend(await self._detect_category_quality_issues(account_id, cutoff_date))
        elif entity_type == "account":
            issues.extend(await self._detect_account_quality_issues(account_id, cutoff_date))
        
        return issues
    
    async def _detect_transaction_quality_issues(
        self,
        account_id: str,
        cutoff_date: datetime
    ) -> List[QualityIssue]:
        """Detect transaction-specific quality issues"""
        
        conn = get_conn()
        issues = []
        
        # Get transactions for analysis
        transactions = conn.execute("""
            SELECT id, description_norm, amount, posted_at, created_at, 
                   ai_merchant_name, ai_confidence_score
            FROM [transaction] 
            WHERE account_id = ? AND created_at >= ?
        """, [account_id, cutoff_date]).fetchall()
        
        for tx in transactions:
            tx_id, description, amount, posted_at, created_at, ai_merchant, ai_confidence = tx
            
            # Check for missing or poor descriptions
            if not description or len(description.strip()) < 3:
                issues.append(QualityIssue(
                    id=str(uuid.uuid4()),
                    issue_type=QualityIssueType.MISSING_DATA,
                    severity=QualitySeverity.HIGH,
                    entity_type="transaction",
                    entity_id=tx_id,
                    description="Transaction has missing or inadequate description",
                    current_value=description,
                    suggested_correction=await self._suggest_description_correction(tx_id),
                    confidence=0.8,
                    auto_correctable=True,
                    impact_assessment="Poor description affects categorization and analysis",
                    detection_method="missing_data_rule",
                    created_at=datetime.now(UTC),
                    corrected_at=None,
                    status=CorrectionStatus.DETECTED
                ))
            
            # Check for encoding issues
            if self._has_encoding_issues(description):
                issues.append(QualityIssue(
                    id=str(uuid.uuid4()),
                    issue_type=QualityIssueType.ENCODING_ERROR,
                    severity=QualitySeverity.MEDIUM,
                    entity_type="transaction",
                    entity_id=tx_id,
                    description="Transaction description contains encoding errors",
                    current_value=description,
                    suggested_correction=self._fix_encoding_issues(description),
                    confidence=0.9,
                    auto_correctable=True,
                    impact_assessment="Encoding errors affect readability and matching",
                    detection_method="encoding_validation",
                    created_at=datetime.now(UTC),
                    corrected_at=None,
                    status=CorrectionStatus.DETECTED
                ))
            
            # Check for amount anomalies
            if amount == 0:
                issues.append(QualityIssue(
                    id=str(uuid.uuid4()),
                    issue_type=QualityIssueType.AMOUNT_ANOMALY,
                    severity=QualitySeverity.HIGH,
                    entity_type="transaction",
                    entity_id=tx_id,
                    description="Transaction has zero amount",
                    current_value=str(amount),
                    suggested_correction="Manual review required",
                    confidence=1.0,
                    auto_correctable=False,
                    impact_assessment="Zero amount transactions may be errors or placeholders",
                    detection_method="amount_validation",
                    created_at=datetime.now(UTC),
                    corrected_at=None,
                    status=CorrectionStatus.DETECTED
                ))
            
            # Check for extreme amounts
            if abs(amount) > 10000:  # Configurable threshold
                issues.append(QualityIssue(
                    id=str(uuid.uuid4()),
                    issue_type=QualityIssueType.OUTLIER_VALUE,
                    severity=QualitySeverity.MEDIUM,
                    entity_type="transaction",
                    entity_id=tx_id,
                    description=f"Transaction amount ${amount:,.2f} is unusually large",
                    current_value=str(amount),
                    suggested_correction="Verify amount accuracy",
                    confidence=0.7,
                    auto_correctable=False,
                    impact_assessment="Large amounts may be errors or require special attention",
                    detection_method="outlier_detection",
                    created_at=datetime.now(UTC),
                    corrected_at=None,
                    status=CorrectionStatus.DETECTED
                ))
            
            # Check for date inconsistencies
            if posted_at and created_at:
                try:
                    posted_date = datetime.fromisoformat(str(posted_at)) if isinstance(posted_at, str) else posted_at
                    created_date = datetime.fromisoformat(str(created_at)) if isinstance(created_at, str) else created_at
                    
                    if isinstance(posted_date, datetime) and isinstance(created_date, datetime):
                        days_diff = abs((posted_date.date() - created_date.date()).days)
                        
                        if days_diff > 365:  # More than a year difference
                            issues.append(QualityIssue(
                                id=str(uuid.uuid4()),
                                issue_type=QualityIssueType.DATE_INCONSISTENCY,
                                severity=QualitySeverity.MEDIUM,
                                entity_type="transaction",
                                entity_id=tx_id,
                                description=f"Large gap between posted date and import date ({days_diff} days)",
                                current_value=f"Posted: {posted_date}, Created: {created_date}",
                                suggested_correction="Verify date accuracy",
                                confidence=0.8,
                                auto_correctable=False,
                                impact_assessment="Date inconsistencies affect timeline analysis",
                                detection_method="date_validation",
                                created_at=datetime.now(UTC),
                                corrected_at=None,
                                status=CorrectionStatus.DETECTED
                            ))
                except:
                    pass
            
            # Check for inconsistent merchant names
            if ai_merchant and description:
                merchant_consistency = await self._check_merchant_consistency(description, ai_merchant)
                if merchant_consistency < 0.6:
                    issues.append(QualityIssue(
                        id=str(uuid.uuid4()),
                        issue_type=QualityIssueType.MERCHANT_INCONSISTENCY,
                        severity=QualitySeverity.LOW,
                        entity_type="transaction",
                        entity_id=tx_id,
                        description="AI merchant name doesn't match transaction description well",
                        current_value=f"Description: {description}, AI Merchant: {ai_merchant}",
                        suggested_correction=await self._suggest_merchant_correction(description, ai_merchant),
                        confidence=merchant_consistency,
                        auto_correctable=True,
                        impact_assessment="Inconsistent merchant data affects categorization",
                        detection_method="merchant_consistency_check",
                        created_at=datetime.now(UTC),
                        corrected_at=None,
                        status=CorrectionStatus.DETECTED
                    ))
        
        return issues
    
    async def _detect_category_quality_issues(
        self,
        account_id: str,
        cutoff_date: datetime
    ) -> List[QualityIssue]:
        """Detect category-related quality issues"""
        
        conn = get_conn()
        issues = []
        
        # Check for over-categorization (same transaction with multiple categories)
        over_categorized = conn.execute("""
            SELECT tc.tx_id, COUNT(*) as category_count
            FROM transaction_category tc
            JOIN [transaction] t ON t.id = tc.tx_id
            WHERE t.account_id = ? AND t.created_at >= ?
            GROUP BY tc.tx_id
            HAVING category_count > 1
        """, [account_id, cutoff_date]).fetchall()
        
        for tx_id, category_count in over_categorized:
            issues.append(QualityIssue(
                id=str(uuid.uuid4()),
                issue_type=QualityIssueType.CATEGORIZATION_ERROR,
                severity=QualitySeverity.MEDIUM,
                entity_type="transaction",
                entity_id=tx_id,
                description=f"Transaction has {category_count} categories (should typically have 1)",
                current_value=str(category_count),
                suggested_correction="Review and consolidate categories",
                confidence=0.9,
                auto_correctable=False,
                impact_assessment="Over-categorization can skew financial analysis",
                detection_method="categorization_validation",
                created_at=datetime.now(UTC),
                corrected_at=None,
                status=CorrectionStatus.DETECTED
            ))
        
        # Check for uncategorized transactions
        uncategorized = conn.execute("""
            SELECT t.id, t.description_norm, t.amount
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON tc.tx_id = t.id
            WHERE t.account_id = ? AND t.created_at >= ?
            AND tc.tx_id IS NULL
            AND ABS(t.amount) > 5  -- Only flag significant amounts
        """, [account_id, cutoff_date]).fetchall()
        
        for tx_id, description, amount in uncategorized:
            issues.append(QualityIssue(
                id=str(uuid.uuid4()),
                issue_type=QualityIssueType.MISSING_DATA,
                severity=QualitySeverity.MEDIUM,
                entity_type="transaction",
                entity_id=tx_id,
                description=f"Significant transaction (${abs(amount):.2f}) is uncategorized",
                current_value="No category",
                suggested_correction=await self._suggest_category_for_transaction(tx_id, description, amount),
                confidence=0.7,
                auto_correctable=True,
                impact_assessment="Uncategorized transactions reduce budget tracking accuracy",
                detection_method="missing_categorization",
                created_at=datetime.now(UTC),
                corrected_at=None,
                status=CorrectionStatus.DETECTED
            ))
        
        return issues
    
    async def _detect_account_quality_issues(
        self,
        account_id: str,
        cutoff_date: datetime
    ) -> List[QualityIssue]:
        """Detect account-level quality issues"""
        
        issues = []
        # Account-level quality checks would go here
        # For now, returning empty list
        return issues
    
    # Correction methods
    
    async def _auto_correct_issues(self, issues: List[QualityIssue]) -> int:
        """Auto-correct issues where possible"""
        
        corrected_count = 0
        
        for issue in issues:
            if issue.auto_correctable and issue.confidence >= 0.8:
                success = await self._apply_auto_correction(issue)
                if success:
                    issue.status = CorrectionStatus.AUTO_CORRECTED
                    issue.corrected_at = datetime.now(UTC)
                    corrected_count += 1
                    await self._update_quality_issue(issue)
        
        return corrected_count
    
    async def _apply_auto_correction(self, issue: QualityIssue) -> bool:
        """Apply automatic correction for an issue"""
        
        conn = get_conn()
        
        try:
            if issue.issue_type == QualityIssueType.ENCODING_ERROR:
                # Fix encoding in transaction description
                if issue.suggested_correction:
                    conn.execute(
                        "UPDATE [transaction] SET description_norm = ? WHERE id = ?",
                        [issue.suggested_correction, issue.entity_id]
                    )
                    return True
            
            elif issue.issue_type == QualityIssueType.MISSING_DATA and issue.entity_type == "transaction":
                # Apply suggested description correction
                if issue.suggested_correction:
                    conn.execute(
                        "UPDATE [transaction] SET description_norm = ? WHERE id = ?",
                        [issue.suggested_correction, issue.entity_id]
                    )
                    return True
            
            elif issue.issue_type == QualityIssueType.MERCHANT_INCONSISTENCY:
                # Apply suggested merchant correction
                if issue.suggested_correction:
                    conn.execute(
                        "UPDATE [transaction] SET ai_merchant_name = ? WHERE id = ?",
                        [issue.suggested_correction, issue.entity_id]
                    )
                    return True
            
            # Add more correction types as needed
            
        except Exception as e:
            print(f"Error applying auto-correction: {e}")
        
        return False
    
    # Helper methods
    
    def _has_encoding_issues(self, text: str) -> bool:
        """Check if text has encoding issues"""
        if not text:
            return False
        
        # Common encoding issue patterns
        encoding_patterns = [
            r'Ã¢', r'â€', r'Ã©', r'Ã¨', r'Ã ', r'Ã¡',  # UTF-8 mojibake
            r'\\x[0-9a-fA-F]{2}',  # Hex escape sequences
            r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]'  # Control characters
        ]
        
        for pattern in encoding_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _fix_encoding_issues(self, text: str) -> str:
        """Fix common encoding issues"""
        if not text:
            return text
        
        # Common fixes
        fixes = {
            'Ã¢â‚¬â„¢': "'",
            'Ã¢â‚¬â€œ': "—",
            'Ã¢â‚¬Å"': '"',
            'Ã¢â‚¬': '"',
            'â€™': "'",
            'â€œ': '"',
            'â€': '"',
            'â€"': "—",
            'â€¦': "...",
        }
        
        fixed_text = text
        for bad, good in fixes.items():
            fixed_text = fixed_text.replace(bad, good)
        
        # Remove control characters
        fixed_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', fixed_text)
        
        return fixed_text.strip()
    
    async def _suggest_description_correction(self, tx_id: str) -> Optional[str]:
        """Suggest description correction for transaction"""
        
        conn = get_conn()
        
        # Get transaction details
        tx = conn.execute(
            "SELECT ai_merchant_name, amount FROM [transaction] WHERE id = ?",
            [tx_id]
        ).fetchone()
        
        if tx and tx[0]:  # Has AI merchant name
            ai_merchant, amount = tx
            # Use AI merchant name as description
            return f"{ai_merchant} - ${abs(amount):.2f}"
        
        return None
    
    async def _check_merchant_consistency(self, description: str, ai_merchant: str) -> float:
        """Check consistency between description and AI merchant name"""
        
        if not description or not ai_merchant:
            return 0.0
        
        # Normalize both strings
        desc_norm = re.sub(r'[^a-zA-Z0-9\s]', '', description.lower())
        merchant_norm = re.sub(r'[^a-zA-Z0-9\s]', '', ai_merchant.lower())
        
        # Check for common words
        desc_words = set(desc_norm.split())
        merchant_words = set(merchant_norm.split())
        
        if not desc_words or not merchant_words:
            return 0.0
        
        # Calculate overlap
        intersection = len(desc_words & merchant_words)
        union = len(desc_words | merchant_words)
        
        return intersection / union if union > 0 else 0.0
    
    async def _suggest_merchant_correction(self, description: str, ai_merchant: str) -> Optional[str]:
        """Suggest merchant name correction"""
        
        # Simple approach: extract likely merchant name from description
        desc_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', description)
        desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
        
        # Take first few meaningful words
        words = [w for w in desc_clean.split() if len(w) > 2 and not w.isdigit()]
        
        if words:
            return ' '.join(words[:3])  # Take first 3 meaningful words
        
        return ai_merchant  # Fallback to current AI merchant
    
    async def _suggest_category_for_transaction(
        self,
        tx_id: str,
        description: str,
        amount: float
    ) -> Optional[str]:
        """Suggest category for uncategorized transaction"""
        
        # Use smart categorization engine if available
        try:
            from .ai_smart_categorization import get_smart_categorization_engine
            categorization_engine = get_smart_categorization_engine()
            
            predictions = await categorization_engine.predict_category(
                tx_id, description, amount, ""  # account_id not needed for suggestion
            )
            
            if predictions:
                return predictions[0].category_name
        
        except ImportError:
            pass
        
        # Fallback to simple keyword matching
        desc_lower = description.lower()
        
        category_keywords = {
            'Groceries': ['grocery', 'food', 'market', 'whole foods', 'kroger'],
            'Restaurants': ['restaurant', 'cafe', 'pizza', 'burger', 'food'],
            'Gas': ['gas', 'fuel', 'shell', 'exxon', 'bp', 'chevron'],
            'Shopping': ['amazon', 'target', 'walmart', 'store', 'shop'],
            'Utilities': ['electric', 'water', 'gas', 'internet', 'phone']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in desc_lower for keyword in keywords):
                return category
        
        return "Miscellaneous"
    
    async def _calculate_quality_score(
        self,
        account_id: str,
        issues: List[QualityIssue],
        total_transactions: int
    ) -> float:
        """Calculate overall data quality score"""
        
        if total_transactions == 0:
            return 100.0
        
        # Weight issues by severity
        severity_weights = {
            QualitySeverity.LOW: 1,
            QualitySeverity.MEDIUM: 3,
            QualitySeverity.HIGH: 5,
            QualitySeverity.CRITICAL: 10
        }
        
        total_impact = sum(severity_weights[issue.severity] for issue in issues)
        
        # Calculate score (0-100, where 100 is perfect quality)
        max_possible_impact = total_transactions * 10  # Assuming worst case
        quality_score = max(0, 100 - (total_impact / max_possible_impact * 100))
        
        return min(100, quality_score)
    
    def _create_issue_breakdown(self, issues: List[QualityIssue]) -> Dict[str, int]:
        """Create breakdown of issues by type"""
        
        breakdown = defaultdict(int)
        for issue in issues:
            breakdown[issue.issue_type.value] += 1
        
        return dict(breakdown)
    
    async def _analyze_quality_trends(self, account_id: str) -> Dict[str, Any]:
        """Analyze quality trends over time"""
        
        conn = get_conn()
        
        # Get quality issues over time
        trends = conn.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as issue_count
            FROM quality_issue
            WHERE entity_id IN (SELECT id FROM [transaction] WHERE account_id = ?)
            AND created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """, [account_id, datetime.now(UTC) - timedelta(days=30)]).fetchall()
        
        return {
            'daily_issues': [{'date': t[0], 'count': t[1]} for t in trends],
            'trend_direction': self._calculate_trend_direction(trends)
        }
    
    def _calculate_trend_direction(self, trends: List[Tuple]) -> str:
        """Calculate if quality is improving or deteriorating"""
        
        if len(trends) < 7:
            return "insufficient_data"
        
        recent_avg = sum(t[1] for t in trends[:7]) / 7
        older_avg = sum(t[1] for t in trends[-7:]) / 7
        
        if recent_avg < older_avg * 0.8:
            return "improving"
        elif recent_avg > older_avg * 1.2:
            return "deteriorating"
        else:
            return "stable"
    
    async def _generate_quality_recommendations(
        self,
        issues: List[QualityIssue],
        trends: Dict[str, Any]
    ) -> List[str]:
        """Generate quality improvement recommendations"""
        
        recommendations = []
        
        # Analyze issue patterns
        issue_counts = Counter(issue.issue_type for issue in issues)
        
        if issue_counts[QualityIssueType.MISSING_DATA] > 5:
            recommendations.append("Consider reviewing import processes to ensure complete data capture")
        
        if issue_counts[QualityIssueType.ENCODING_ERROR] > 3:
            recommendations.append("Review data source encoding to prevent character corruption")
        
        if issue_counts[QualityIssueType.CATEGORIZATION_ERROR] > 10:
            recommendations.append("Review categorization rules and consider AI-assisted categorization")
        
        if trends.get('trend_direction') == 'deteriorating':
            recommendations.append("Data quality is declining - consider implementing stricter validation rules")
        
        if not recommendations:
            recommendations.append("Overall data quality is good - continue current practices")
        
        return recommendations
    
    # Storage methods
    
    async def _store_quality_issue(self, issue: QualityIssue):
        """Store quality issue in database"""
        
        conn = get_conn()
        
        conn.execute("""
            INSERT INTO quality_issue (
                id, issue_type, severity, entity_type, entity_id, description,
                current_value, suggested_correction, confidence, auto_correctable,
                impact_assessment, detection_method, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            issue.id, issue.issue_type.value, issue.severity.value,
            issue.entity_type, issue.entity_id, issue.description,
            issue.current_value, issue.suggested_correction, issue.confidence,
            issue.auto_correctable, issue.impact_assessment, issue.detection_method,
            issue.created_at, issue.status.value
        ])
    
    async def _update_quality_issue(self, issue: QualityIssue):
        """Update quality issue in database"""
        
        conn = get_conn()
        
        conn.execute("""
            UPDATE quality_issue 
            SET status = ?, corrected_at = ?
            WHERE id = ?
        """, [issue.status.value, issue.corrected_at, issue.id])
    
    async def _store_quality_rule(self, rule: QualityRule):
        """Store quality rule in database"""
        
        conn = get_conn()
        
        conn.execute("""
            INSERT INTO quality_rule (
                id, name, issue_type, entity_type, validation_logic_json,
                correction_logic_json, is_active, auto_correct, severity, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            rule.id, rule.name, rule.issue_type.value, rule.entity_type,
            json.dumps(rule.validation_logic), 
            json.dumps(rule.correction_logic) if rule.correction_logic else None,
            rule.is_active, rule.auto_correct, rule.severity.value, rule.created_at
        ])
    
    async def _store_quality_report(self, report: QualityReport):
        """Store quality report in database"""
        
        conn = get_conn()
        
        conn.execute("""
            INSERT INTO quality_report (
                id, account_id, report_date, total_transactions, issues_found,
                issues_corrected, quality_score, issue_breakdown_json,
                trends_json, recommendations_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4()), report.account_id, report.report_date,
            report.total_transactions, report.issues_found, report.issues_corrected,
            report.quality_score, json.dumps(report.issue_breakdown),
            json.dumps(report.trends), json.dumps(report.recommendations)
        ])
    
    async def _get_applicable_rules(self, entity_type: str) -> List[QualityRule]:
        """Get quality rules applicable to entity type"""
        
        # Return built-in rules for now
        # In practice, this would load from database
        return []
    
    async def _apply_quality_rule(
        self,
        rule: QualityRule,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any]
    ) -> Optional[QualityIssue]:
        """Apply quality rule to data"""
        
        # Placeholder implementation
        return None
    
    async def _apply_correction(self, issue: QualityIssue, data: Dict[str, Any]) -> bool:
        """Apply correction to data"""
        
        # Placeholder implementation
        return True
    
    async def _update_correction_patterns(
        self,
        issue: QualityIssue,
        user_correction: str
    ):
        """Update correction patterns based on user feedback"""
        
        # Store pattern for future use
        pattern_key = f"{issue.issue_type.value}_{issue.current_value}"
        self._correction_patterns[pattern_key] = user_correction


# Global instance
_ai_data_quality_engine = None

def get_ai_data_quality_engine() -> AIDataQualityEngine:
    """Get the global AI data quality engine instance"""
    global _ai_data_quality_engine
    if _ai_data_quality_engine is None:
        _ai_data_quality_engine = AIDataQualityEngine()
    return _ai_data_quality_engine