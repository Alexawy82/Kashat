"""
AI Integration Module

Combines AI categorization with detection markers to provide unified
transaction processing that includes categories, income detection, 
transfer detection, and Zelle parsing.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple, Any
import logging

from .db import get_conn
from .ai import get_ai_service, TransactionInsights
from .ai_categories import get_category_matcher, auto_create_category
from .ai_smart_categorization import get_smart_categorization_engine, process_ai_category_suggestion
from .ai_enhanced_categorization import categorize_transaction_enhanced
from .detect.income import mark_income
from .detect.zelle import parse_zelle_descriptor
from .transfers import suggest_transfers_v2


logger = logging.getLogger(__name__)


class TransactionProcessor:
    """Unified transaction processor that combines AI and detection"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.category_matcher = get_category_matcher()
    
    async def process_transaction(self, tx_id: str, force_reprocess: bool = False) -> Dict[str, Any]:
        """Process a single transaction with AI categorization and detection"""
        conn = get_conn()
        
        # Get transaction data
        tx_row = conn.execute(
            "SELECT id, description_norm, amount, posted_at, ai_processed_at FROM [transaction] WHERE id = ?",
            [tx_id]
        ).fetchone()
        
        if not tx_row:
            raise ValueError(f"Transaction {tx_id} not found")
        
        tx_id, description, amount, posted_at, ai_processed_at = tx_row
        
        # Skip if already processed (unless forced)
        if ai_processed_at and not force_reprocess:
            return {"status": "skipped", "reason": "already_processed"}
        
        results = {
            "transaction_id": tx_id,
            "description": description,
            "amount": amount,
            "ai_insights": None,
            "category_applied": None,
            "detection_markers": {},
            "status": "processed"
        }
        
        try:
            # Step 1: Enhanced AI Analysis
            enhanced_suggestions = categorize_transaction_enhanced(description, amount)
            
            # Get basic AI insights for merchant info only
            try:
                basic_insights = await self.ai_service.analyze_transaction(description, amount)
                merchant_info = basic_insights.merchant_info
                anomaly_flags = basic_insights.anomaly_flags
            except:
                merchant_info = None
                anomaly_flags = []
            
            results["ai_insights"] = {
                "merchant_name": merchant_info.normalized_name if merchant_info else None,
                "confidence": enhanced_suggestions[0].confidence if enhanced_suggestions else 0.0,
                "provider": "enhanced_ai_v2",
                "suggestions": [
                    {
                        "category": s.category_name,
                        "confidence": s.confidence,
                        "reasoning": s.reasoning
                    }
                    for s in enhanced_suggestions
                ]
            }
            
            # Step 2: Category Assignment using enhanced suggestions
            category_id = await self._apply_best_category_enhanced(tx_id, enhanced_suggestions)
            results["category_applied"] = category_id
            
            # Step 3: Detection Markers
            detection_results = self._apply_detection_markers(tx_id, description, amount)
            results["detection_markers"] = detection_results
            
            # Step 4: Update transaction with enhanced AI data
            self._update_transaction_ai_data_enhanced(tx_id, enhanced_suggestions, merchant_info)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to process transaction {tx_id}: {e}")
            results["status"] = "error"
            results["error"] = str(e)
            return results
    
    async def _apply_best_category_enhanced(self, tx_id: str, enhanced_suggestions) -> Optional[str]:
        """Apply the best category suggestion using enhanced categorization system"""
        if not enhanced_suggestions:
            return None
        
        conn = get_conn()
        best_suggestion = enhanced_suggestions[0]
        
        # Use smart categorization system to find or create category
        category_result = process_ai_category_suggestion(
            best_suggestion.category_name,
            confidence=best_suggestion.confidence,
            auto_create=best_suggestion.confidence >= 0.85  # Higher threshold for auto-creation
        )
        
        category_id = category_result.category_id
        
        if category_id:
            # Apply category to transaction
            conn.execute(
                "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?) ON CONFLICT (tx_id) DO UPDATE SET category_id = EXCLUDED.category_id, applied_by = EXCLUDED.applied_by",
                [tx_id, category_id, f"ai_enhanced_smart"]
            )
            
            # Learn from this categorization for future improvements
            smart_engine = get_smart_categorization_engine()
            await smart_engine.learn_from_categorization(tx_id, category_id)
            
            # Log the smart categorization
            conn.execute(
                "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    str(uuid.uuid4()),
                    "transaction",
                    tx_id,
                    "enhanced_ai_categorize",
                    json.dumps({
                        "category_id": category_id,
                        "category_name": category_result.category_name,
                        "original_ai_suggestion": best_suggestion.category_name,
                        "confidence": best_suggestion.confidence,
                        "provider": "enhanced_ai_v2",
                        "reasoning": best_suggestion.reasoning,
                        "smart_result": {
                            "created": category_result.created,
                            "reason": category_result.reason,
                            "final_confidence": category_result.confidence
                        }
                    }),
                    datetime.now(UTC),
                    f"enhanced_ai_smart"
                ]
            )
        else:
            # Category suggestion was stored for manual review
            logger.info(f"Category suggestion '{best_suggestion.category_name}' stored for manual review (confidence: {best_suggestion.confidence:.2f})")
        
        return category_id

    async def _apply_best_category(self, tx_id: str, ai_insights: TransactionInsights) -> Optional[str]:
        """Apply the best category suggestion using smart categorization system"""
        if not ai_insights.category_suggestions:
            return None
        
        conn = get_conn()
        best_suggestion = ai_insights.category_suggestions[0]
        
        # Use smart categorization system to find or create category
        category_result = process_ai_category_suggestion(
            best_suggestion.category_name,
            confidence=best_suggestion.confidence,
            auto_create=best_suggestion.confidence >= 0.85  # Higher threshold for auto-creation
        )
        
        category_id = category_result.category_id
        
        if category_id:
            # Apply category to transaction
            conn.execute(
                "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?) ON CONFLICT (tx_id) DO UPDATE SET category_id = EXCLUDED.category_id, applied_by = EXCLUDED.applied_by",
                [tx_id, category_id, f"ai_{ai_insights.provider_name}_smart"]
            )
            
            # Learn from this categorization for future improvements
            smart_engine = get_smart_categorization_engine()
            await smart_engine.learn_from_categorization(tx_id, category_id)
            
            # Log the smart categorization
            conn.execute(
                "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    str(uuid.uuid4()),
                    "transaction",
                    tx_id,
                    "smart_ai_categorize",
                    json.dumps({
                        "category_id": category_id,
                        "category_name": category_result.category_name,
                        "original_ai_suggestion": best_suggestion.category_name,
                        "confidence": best_suggestion.confidence,
                        "provider": ai_insights.provider_name,
                        "smart_result": {
                            "created": category_result.created,
                            "reason": category_result.reason,
                            "final_confidence": category_result.confidence
                        }
                    }),
                    datetime.now(UTC),
                    f"smart_ai_{ai_insights.provider_name}"
                ]
            )
        else:
            # Category suggestion was stored for manual review
            logger.info(f"Category suggestion '{best_suggestion.category_name}' stored for manual review (confidence: {best_suggestion.confidence:.2f})")
        
        return category_id
    
    def _apply_detection_markers(self, tx_id: str, description: str, amount: float) -> Dict[str, Any]:
        """Apply detection markers (income, transfer, zelle) to transaction"""
        conn = get_conn()
        detection_results = {}
        
        # Income detection
        is_income = self._detect_income(description, amount)
        if is_income:
            conn.execute(
                "UPDATE [transaction] SET is_income = TRUE WHERE id = ?",
                [tx_id]
            )
            detection_results["income"] = True
        
        # Transfer detection
        is_transfer = self._detect_transfer(description)
        if is_transfer:
            # Add is_transfer field if it doesn't exist
            try:
                conn.execute("ALTER TABLE [transaction] ADD COLUMN is_transfer BOOLEAN DEFAULT FALSE")
            except:
                pass  # Column may already exist
            
            conn.execute(
                "UPDATE [transaction] SET is_transfer = TRUE WHERE id = ?",
                [tx_id]
            )
            detection_results["transfer"] = True
        
        # Zelle detection
        zelle_info = parse_zelle_descriptor(description)
        if zelle_info:
            conn.execute(
                "UPDATE [transaction] SET zelle_direction = ?, zelle_counterparty = ? WHERE id = ?",
                [zelle_info.get("direction"), zelle_info.get("counterparty"), tx_id]
            )
            detection_results["zelle"] = {
                "direction": zelle_info.get("direction"),
                "counterparty": zelle_info.get("counterparty")
            }
        
        # Log detection results
        if detection_results:
            conn.execute(
                "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    str(uuid.uuid4()),
                    "transaction",
                    tx_id,
                    "detection_markers",
                    json.dumps(detection_results),
                    datetime.now(UTC),
                    "detection_system"
                ]
            )
        
        return detection_results
    
    def _detect_income(self, description: str, amount: float) -> bool:
        """Enhanced income detection using multiple indicators"""
        if amount <= 0:
            return False
        
        desc_lower = description.lower()
        
        # Strong income indicators (high confidence)
        strong_income_patterns = [
            'salary', 'payroll', 'wages', 'paycheck', 'direct deposit',
            'employer', 'income', 'pension', 'social security',
            'unemployment', 'benefits', 'refund', 'reimbursement',
            'dividend', 'interest', 'bonus', 'commission', 'royalty',
            'freelance', 'contractor payment', 'consulting fee',
            'tax refund', 'rebate', 'cashback', 'reward'
        ]
        
        # Bank-specific income patterns
        bank_income_patterns = [
            'bank of america, des:bank of am',  # Direct deposits from BoA
            'deposit', 'credit', 'transfer from',
            'automatic deposit', 'ach credit',
            'wire transfer', 'online banking transfer from'
        ]
        
        # Check for strong income indicators
        for pattern in strong_income_patterns:
            if pattern in desc_lower:
                return True
        
        # Check for bank-specific patterns with amount considerations
        for pattern in bank_income_patterns:
            if pattern in desc_lower:
                # Large amounts are more likely to be income
                if amount >= 500:
                    return True
                # Smaller amounts need additional context
                elif amount >= 100 and any(word in desc_lower for word in ['payroll', 'salary', 'wages']):
                    return True
        
        # Use existing income detection as fallback
        try:
            mock_record = [{
                "id": "temp",
                "description_norm": description,
                "amount": amount,
                "posted_at": datetime.now().isoformat()
            }]
            
            income_ids = mark_income(mock_record)
            return "temp" in income_ids
        except Exception:
            # If existing detection fails, use our enhanced logic
            pass
        
        # Additional heuristics for income detection
        # Large round deposits are often income
        if amount >= 1000 and amount % 100 == 0:
            # Check if it's not obviously an expense
            expense_keywords = [
                'payment', 'purchase', 'withdrawal', 'fee', 'charge',
                'bill', 'loan', 'mortgage', 'rent', 'insurance'
            ]
            if not any(keyword in desc_lower for keyword in expense_keywords):
                return True
        
        return False
    
    def _detect_transfer(self, description: str) -> bool:
        """Detect if transaction is a transfer"""
        transfer_patterns = [
            'transfer from',
            'transfer to', 
            'online banking transfer',
            'keep the change',
            'account transfer'
        ]
        
        desc_lower = description.lower()
        return any(pattern in desc_lower for pattern in transfer_patterns)
    
    def _update_transaction_ai_data(self, tx_id: str, ai_insights: TransactionInsights):
        """Update transaction with AI processing data"""
        conn = get_conn()
        
        # Prepare AI data
        merchant_name = ai_insights.merchant_info.normalized_name if ai_insights.merchant_info else None
        suggestions_json = json.dumps([
            {
                "category_name": s.category_name,
                "category_id": s.category_id,
                "confidence": s.confidence,
                "reasoning": s.reasoning
            }
            for s in ai_insights.category_suggestions
        ])
        
        # Update transaction
        conn.execute("""
            UPDATE [transaction] SET
                ai_merchant_name = ?,
                ai_category_suggestions = ?,
                ai_confidence_score = ?,
                ai_processed_at = ?,
                ai_provider = ?,
                ai_model = ?,
                ai_latency_ms = ?
            WHERE id = ?
        """, [
            merchant_name,
            suggestions_json,
            ai_insights.confidence_score,
            datetime.now(UTC),
            ai_insights.provider_name,
            ai_insights.model_name,
            ai_insights.latency_ms,
            tx_id
        ])
    
    def _update_transaction_ai_data_enhanced(self, tx_id: str, enhanced_suggestions, merchant_info):
        """Update transaction with enhanced AI processing data"""
        conn = get_conn()
        
        # Prepare enhanced AI data
        merchant_name = merchant_info.normalized_name if merchant_info else None
        suggestions_json = json.dumps([
            {
                "category_name": s.category_name,
                "confidence": s.confidence,
                "reasoning": s.reasoning
            }
            for s in enhanced_suggestions
        ])
        
        # Get the best confidence score
        confidence_score = enhanced_suggestions[0].confidence if enhanced_suggestions else 0.0
        
        # Update transaction
        conn.execute("""
            UPDATE [transaction] SET
                ai_merchant_name = ?,
                ai_category_suggestions = ?,
                ai_confidence_score = ?,
                ai_processed_at = ?,
                ai_provider = ?,
                ai_model = ?
            WHERE id = ?
        """, [
            merchant_name,
            suggestions_json,
            confidence_score,
            datetime.now(UTC),
            "enhanced_ai_v2",
            "llama3_enhanced",
            tx_id
        ])


async def process_transactions_batch(tx_ids: List[str], force_reprocess: bool = False) -> Dict[str, Any]:
    """Process multiple transactions in batch"""
    processor = TransactionProcessor()
    results = []
    
    for tx_id in tx_ids:
        try:
            result = await processor.process_transaction(tx_id, force_reprocess)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process transaction {tx_id}: {e}")
            results.append({
                "transaction_id": tx_id,
                "status": "error",
                "error": str(e)
            })
    
    # Summary statistics
    processed = sum(1 for r in results if r["status"] == "processed")
    errors = sum(1 for r in results if r["status"] == "error")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    
    return {
        "total": len(tx_ids),
        "processed": processed,
        "errors": errors,
        "skipped": skipped,
        "results": results
    }


async def process_all_uncategorized_transactions() -> Dict[str, Any]:
    """Process all transactions that haven't been categorized or AI processed"""
    conn = get_conn()
    
    # Find uncategorized transactions
    rows = conn.execute("""
        SELECT t.id 
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        WHERE tc.tx_id IS NULL 
           OR t.ai_processed_at IS NULL
        ORDER BY t.posted_at DESC
        LIMIT 1000
    """).fetchall()
    
    tx_ids = [row[0] for row in rows]
    
    if not tx_ids:
        return {"message": "No uncategorized transactions found", "total": 0}
    
    return await process_transactions_batch(tx_ids)


async def run_full_detection_workflow() -> Dict[str, Any]:
    """Run the complete detection workflow: AI + all detections"""
    conn = get_conn()
    
    # Step 1: Process transactions with AI
    ai_results = await process_all_uncategorized_transactions()
    
    # Step 2: Run transfer detection
    transfer_results = suggest_transfers_v2()
    
    # Step 3: Generate summary
    summary = {
        "ai_processing": ai_results,
        "transfer_detection": transfer_results,
        "timestamp": datetime.now(UTC).isoformat()
    }
    
    # Log the workflow execution
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            str(uuid.uuid4()),
            "workflow",
            "ai_detection_full",
            "execute",
            json.dumps(summary),
            datetime.now(UTC),
            "ai_detection_workflow"
        ]
    )
    
    return summary