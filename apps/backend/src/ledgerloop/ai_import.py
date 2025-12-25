"""
AI-Enhanced Import Processing

Provides intelligent enhancements during CSV/PDF import:
- Real-time merchant normalization
- Smart category suggestions
- Quality scoring for import data
- Anomaly detection during import
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .ai import get_ai_service, TransactionInsights
from .ai_categories import get_category_matcher
from .ai_enhanced_categorization import categorize_transaction_enhanced
from .ai_smart_categorization import process_ai_category_suggestion
from .db import get_conn


@dataclass
class ImportEnhancement:
    """AI enhancement results for a single transaction during import"""
    original_description: str
    ai_merchant_name: Optional[str]
    ai_confidence: float
    suggested_category_id: Optional[str]
    suggested_category_name: Optional[str]
    category_confidence: float
    anomaly_flags: List[str]
    quality_score: float  # 0-1 rating of import data quality


@dataclass
class ImportAnalysis:
    """Analysis results for an entire import batch"""
    total_transactions: int
    ai_enhanced_count: int
    avg_quality_score: float
    anomalies_detected: int
    auto_categorized_count: int
    suggested_rules: List[Dict[str, Any]]
    processing_time_ms: int


class AIImportProcessor:
    """Processes transactions during import with AI enhancements"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.category_matcher = get_category_matcher()
    
    async def process_import_batch(
        self, 
        transactions: List[Dict[str, Any]], 
        account_id: str,
        run_id: str
    ) -> ImportAnalysis:
        """Process a batch of transactions with AI enhancements"""
        start_time = datetime.now()
        
        enhancements = []
        suggested_rules = []
        
        # Process in smaller batches to prevent overwhelming
        batch_size = 20
        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i + batch_size]
            batch_enhancements = await self._process_transaction_batch(batch)
            enhancements.extend(batch_enhancements)
            
            # Small delay to prevent system overload
            await asyncio.sleep(0.05)
        
        # Analyze patterns for rule suggestions
        suggested_rules = self._analyze_patterns_for_rules(enhancements)
        
        # Calculate statistics
        ai_enhanced_count = sum(1 for e in enhancements if e.ai_merchant_name)
        auto_categorized_count = sum(1 for e in enhancements if e.suggested_category_id)
        avg_quality_score = sum(e.quality_score for e in enhancements) / len(enhancements) if enhancements else 0
        anomalies_detected = sum(len(e.anomaly_flags) for e in enhancements)
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Store AI results in database
        await self._store_batch_enhancements(enhancements, transactions, run_id)
        
        return ImportAnalysis(
            total_transactions=len(transactions),
            ai_enhanced_count=ai_enhanced_count,
            avg_quality_score=round(avg_quality_score, 3),
            anomalies_detected=anomalies_detected,
            auto_categorized_count=auto_categorized_count,
            suggested_rules=suggested_rules,
            processing_time_ms=processing_time
        )
    
    async def _process_transaction_batch(self, transactions: List[Dict[str, Any]]) -> List[ImportEnhancement]:
        """Process a small batch of transactions with ENHANCED AI"""
        enhancements = []
        
        for tx in transactions:
            description = tx.get('description', '')
            amount = float(tx.get('amount', 0))
            
            # Use ENHANCED categorization instead of basic AI
            enhanced_suggestions = categorize_transaction_enhanced(description, amount)
            
            # Get basic AI insights for merchant info only
            try:
                basic_insights = await self.ai_service.analyze_transaction(description, amount)
                merchant_info = basic_insights.merchant_info
                anomaly_flags = basic_insights.anomaly_flags
            except:
                merchant_info = None
                anomaly_flags = []
            
            # Find or create category for best enhanced suggestion
            suggested_category_id = None
            suggested_category_name = None
            category_confidence = 0.0
            
            if enhanced_suggestions:
                best_suggestion = enhanced_suggestions[0]
                suggested_category_name = best_suggestion.category_name
                category_confidence = best_suggestion.confidence
                
                # Try to find or create the category
                try:
                    category_result = process_ai_category_suggestion(
                        best_suggestion.category_name,
                        confidence=best_suggestion.confidence,
                        auto_create=best_suggestion.confidence >= 0.8  # Auto-create high confidence categories
                    )
                    suggested_category_id = category_result.category_id
                    if category_result.category_name:
                        suggested_category_name = category_result.category_name
                except Exception as e:
                    # If category processing fails, just use the suggestion without ID
                    print(f"Category processing failed for {best_suggestion.category_name}: {e}")
            
            # Calculate quality score
            quality_score = self._calculate_quality_score_enhanced(tx, enhanced_suggestions, merchant_info)
            
            enhancement = ImportEnhancement(
                original_description=description,
                ai_merchant_name=merchant_info.normalized_name if merchant_info else None,
                ai_confidence=merchant_info.confidence if merchant_info else category_confidence,
                suggested_category_id=suggested_category_id,
                suggested_category_name=suggested_category_name,
                category_confidence=category_confidence,
                anomaly_flags=anomaly_flags,
                quality_score=quality_score
            )
            
            enhancements.append(enhancement)
        
        return enhancements
    
    def _calculate_quality_score(self, transaction: Dict[str, Any], insights: TransactionInsights) -> float:
        """Calculate quality score for import data (0-1 scale)"""
        score = 0.5  # Base score
        
        # Description quality
        description = transaction.get('description', '')
        if len(description) > 10:
            score += 0.1
        if len(description) > 25:
            score += 0.1
        
        # Date completeness
        if transaction.get('posted_at'):
            score += 0.1
        
        # Amount validity
        amount = transaction.get('amount', 0)
        if amount != 0:
            score += 0.1
        
        # AI confidence bonus
        if insights.merchant_info and insights.merchant_info.confidence > 0.8:
            score += 0.1
        
        # Anomaly penalty
        if insights.anomaly_flags:
            score -= 0.1 * len(insights.anomaly_flags)
        
        return max(0.0, min(1.0, score))
    
    def _calculate_quality_score_enhanced(self, transaction: Dict[str, Any], enhanced_suggestions, merchant_info) -> float:
        """Calculate quality score for import data using enhanced AI (0-1 scale)"""
        score = 0.5  # Base score
        
        # Description quality
        description = transaction.get('description', '')
        if len(description) > 10:
            score += 0.1
        if len(description) > 25:
            score += 0.1
        
        # Date completeness
        if transaction.get('posted_at'):
            score += 0.1
        
        # Amount validity
        amount = transaction.get('amount', 0)
        if amount != 0:
            score += 0.1
        
        # Enhanced AI confidence bonus
        if enhanced_suggestions and enhanced_suggestions[0].confidence > 0.8:
            score += 0.15  # Higher bonus for enhanced AI
        
        # Merchant info bonus
        if merchant_info and merchant_info.confidence > 0.8:
            score += 0.1
        
        # Non-generic category bonus
        if enhanced_suggestions and enhanced_suggestions[0].category_name.lower() not in ['purchase', 'uncategorized', 'other']:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _analyze_patterns_for_rules(self, enhancements: List[ImportEnhancement]) -> List[Dict[str, Any]]:
        """Analyze transaction patterns to suggest new rules"""
        suggested_rules = []
        
        # Group by normalized merchant names
        merchant_groups = {}
        for enhancement in enhancements:
            if enhancement.ai_merchant_name and enhancement.suggested_category_id:
                merchant = enhancement.ai_merchant_name
                category_id = enhancement.suggested_category_id
                category_name = enhancement.suggested_category_name
                
                if merchant not in merchant_groups:
                    merchant_groups[merchant] = {}
                
                if category_id not in merchant_groups[merchant]:
                    merchant_groups[merchant][category_id] = {
                        'category_name': category_name,
                        'count': 0,
                        'total_confidence': 0.0
                    }
                
                merchant_groups[merchant][category_id]['count'] += 1
                merchant_groups[merchant][category_id]['total_confidence'] += enhancement.category_confidence
        
        # Generate rule suggestions for consistent patterns
        for merchant, categories in merchant_groups.items():
            # Find dominant category for this merchant
            best_category = max(categories.items(), key=lambda x: x[1]['count'])
            category_id, category_info = best_category
            
            if category_info['count'] >= 3:  # At least 3 transactions
                avg_confidence = category_info['total_confidence'] / category_info['count']
                
                if avg_confidence > 0.7:  # High confidence
                    suggested_rules.append({
                        'priority': 100,
                        'predicate': {
                            'op': 'contains',
                            'field': 'description',
                            'value': merchant.lower()
                        },
                        'action': {
                            'type': 'set_category',
                            'category_id': category_id
                        },
                        'reasoning': f"Auto-suggested: {category_info['count']} transactions from '{merchant}' categorized as '{category_info['category_name']}' with {avg_confidence:.1%} confidence",
                        'confidence': avg_confidence,
                        'transaction_count': category_info['count']
                    })
        
        # Sort by confidence and transaction count
        suggested_rules.sort(key=lambda r: (r['confidence'], r['transaction_count']), reverse=True)
        
        return suggested_rules[:10]  # Return top 10 suggestions
    
    async def _store_batch_enhancements(
        self, 
        enhancements: List[ImportEnhancement], 
        transactions: List[Dict[str, Any]], 
        run_id: str
    ):
        """Store AI enhancement results in database"""
        conn = get_conn()
        
        # Update import_run with AI statistics
        ai_enhanced_count = sum(1 for e in enhancements if e.ai_merchant_name)
        avg_quality_score = sum(e.quality_score for e in enhancements) / len(enhancements) if enhancements else 0
        anomalies_detected = sum(len(e.anomaly_flags) for e in enhancements)
        
        conn.execute("""
            UPDATE import_run 
            SET ai_enhanced_count = ?, ai_avg_quality_score = ?, ai_anomalies_detected = ?
            WHERE id = ?
        """, [ai_enhanced_count, round(avg_quality_score, 3), anomalies_detected, run_id])
        
        # Get auto-categorization settings
        from .settings import load_settings
        settings = load_settings()
        auto_apply = settings.get("ai_auto_categorize_on_import", True)
        min_confidence = float(settings.get("ai_auto_categorize_min_conf", 0.7))

        # Store individual AI results (if transactions have IDs)
        for enhancement, transaction in zip(enhancements, transactions):
            tx_id = transaction.get('id')
            if tx_id and enhancement.ai_merchant_name:
                # Best effort to also include provider/model/latency if present
                # These may not be available here without changing method signatures; set provider from global config
                from .ai import get_ai_service
                svc = get_ai_service()
                provider = getattr(svc, 'provider', 'local')
                model = None
                if provider == 'openai' and svc.openai_service:
                    model = getattr(svc.openai_service, 'default_model', None)
                if provider == 'lmstudio' and svc.lmstudio_service:
                    model = getattr(svc.lmstudio_service, 'default_model', None)
                conn.execute("""
                    UPDATE [transaction]
                    SET ai_merchant_name = ?, ai_confidence_score = ?, ai_processed_at = CURRENT_TIMESTAMP,
                        ai_provider = COALESCE(ai_provider, ?), ai_model = COALESCE(ai_model, ?)
                    WHERE id = ?
                """, [enhancement.ai_merchant_name, enhancement.ai_confidence, provider, model, tx_id])

                # AUTO-APPLY CATEGORY if confidence is high enough
                if (auto_apply and
                    enhancement.suggested_category_id and
                    enhancement.category_confidence >= min_confidence):
                    try:
                        # Check if already categorized
                        existing = conn.execute(
                            "SELECT 1 FROM transaction_category WHERE tx_id = ?", [tx_id]
                        ).fetchone()
                        if not existing:
                            conn.execute("""
                                INSERT INTO transaction_category (tx_id, category_id, applied_by)
                                VALUES (?, ?, 'ai_import')
                            """, [tx_id, enhancement.suggested_category_id])

                            # Learn from this categorization for merchant memory
                            try:
                                from .ai_smart_categorization import learn_from_transaction_categorization
                                import asyncio
                                asyncio.create_task(
                                    learn_from_transaction_categorization(tx_id, enhancement.suggested_category_id)
                                )
                            except Exception:
                                pass  # Don't fail import if learning fails
                    except Exception as e:
                        print(f"Auto-categorization failed for {tx_id}: {e}")


# Global instance
_ai_import_processor = None

def get_ai_import_processor() -> AIImportProcessor:
    """Get the global AI import processor instance"""
    global _ai_import_processor
    if _ai_import_processor is None:
        _ai_import_processor = AIImportProcessor()
    return _ai_import_processor
