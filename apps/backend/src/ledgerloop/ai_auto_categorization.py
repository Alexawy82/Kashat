"""
AI Auto-Categorization Service

Automatically categorizes transactions based on confidence thresholds,
learns from user corrections, and provides smart batch processing.
"""

from __future__ import annotations

import uuid
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC

from .db import get_conn
from .ai import get_ai_service
from .ai_enhanced_categorization import categorize_transaction_enhanced
from .ai_smart_categorization import get_smart_categorization_engine, learn_from_transaction_categorization

logger = logging.getLogger(__name__)


@dataclass
class AutoCategorizationConfig:
    """Configuration for auto-categorization behavior"""
    high_confidence_threshold: float = 0.75    # Auto-apply categories (matches ai_auto_categorize_min_conf)
    medium_confidence_threshold: float = 0.60  # Suggest with high priority
    low_confidence_threshold: float = 0.40     # Basic suggestions
    enable_auto_categorization: bool = True
    enable_category_creation: bool = True
    enable_learning: bool = True
    batch_size: int = 50


@dataclass
class AutoCategorizationResult:
    """Result of auto-categorization attempt"""
    transaction_id: str
    success: bool
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""
    action_taken: str = ""  # 'applied', 'suggested', 'skipped', 'created_and_applied'


class AutoCategorizationService:
    """Smart auto-categorization with learning capabilities"""
    
    def __init__(self, config: Optional[AutoCategorizationConfig] = None):
        self.config = config or AutoCategorizationConfig()
        self.smart_engine = get_smart_categorization_engine()
        self.ai_service = get_ai_service()
    
    async def process_transaction(self, transaction_id: str, description: str, amount: float,
                                account_id: str, stored_ai_suggestions: str = None) -> AutoCategorizationResult:
        """Process a single transaction for auto-categorization

        NEW WORKFLOW (patterns first, AI fallback):
        1. Check if already categorized
        2. TRY PATTERNS FIRST (fast, free, predictable)
        3. If pattern confidence < threshold, FALL BACK TO OPENAI/LM Studio
        4. If AI returns high confidence, LEARN THE PATTERN for next time
        """

        try:
            # Step 1: Check if already categorized
            if self._is_already_categorized(transaction_id):
                return AutoCategorizationResult(
                    transaction_id=transaction_id,
                    success=False,
                    action_taken='skipped',
                    reasoning='Transaction already categorized'
                )

            # ============================================
            # Step 2: TRY PATTERNS FIRST (fast, free)
            # ============================================
            best_suggestion = None
            pattern_suggestions = categorize_transaction_enhanced(description, amount)

            if pattern_suggestions and pattern_suggestions[0].confidence >= self.config.high_confidence_threshold:
                # Pattern matched with high confidence - use it directly!
                best_suggestion = pattern_suggestions[0]
                logger.debug(f"Pattern match: {best_suggestion.category_name} ({best_suggestion.confidence:.2f})")

            # ============================================
            # Step 3: FALLBACK TO AI if patterns fail
            # ============================================
            if not best_suggestion or best_suggestion.confidence < self.config.high_confidence_threshold:
                try:
                    # Get fresh AI analysis from OpenAI/LM Studio
                    insights = await self.ai_service.analyze_transaction(description, amount)
                    if insights and insights.category_suggestions:
                        best_ai = insights.category_suggestions[0]

                        # Only use AI if it's better than patterns
                        if not best_suggestion or best_ai.confidence > best_suggestion.confidence:
                            from dataclasses import dataclass
                            @dataclass
                            class AISuggestion:
                                category_name: str
                                confidence: float
                                reasoning: str
                                category_id: str = None
                            best_suggestion = AISuggestion(
                                category_name=best_ai.category_name,
                                confidence=best_ai.confidence,
                                reasoning=best_ai.reasoning,
                                category_id=None
                            )

                            # Store the AI suggestions for future use
                            conn = get_conn()
                            suggestions_json = json.dumps([{
                                "category_name": s.category_name,
                                "confidence": s.confidence,
                                "reasoning": s.reasoning
                            } for s in insights.category_suggestions[:3]])
                            conn.execute("""
                                UPDATE [transaction]
                                SET ai_category_suggestions = ?, ai_confidence_score = ?,
                                    ai_processed_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            """, [suggestions_json, insights.confidence_score, transaction_id])

                            # ============================================
                            # Step 4: LEARN from high-confidence AI results
                            # ============================================
                            if best_ai.confidence >= 0.85:
                                await self._learn_pattern_from_ai(description, best_ai.category_name, best_ai.confidence)

                except Exception as e:
                    logger.warning(f"AI service call failed: {e}")
                    # Keep using pattern suggestion if we have one
                    if pattern_suggestions:
                        best_suggestion = pattern_suggestions[0]

            if not best_suggestion:
                return AutoCategorizationResult(
                    transaction_id=transaction_id,
                    success=False,
                    action_taken='skipped',
                    reasoning='No AI suggestions available'
                )
            
            # Step 3: Apply confidence-based logic
            if best_suggestion.confidence >= self.config.high_confidence_threshold:
                return await self._auto_apply_category(
                    transaction_id, best_suggestion, description, amount
                )
            
            elif best_suggestion.confidence >= self.config.medium_confidence_threshold:
                return await self._store_suggestion(
                    transaction_id, best_suggestion, 'medium_confidence'
                )
            
            elif best_suggestion.confidence >= self.config.low_confidence_threshold:
                return await self._store_suggestion(
                    transaction_id, best_suggestion, 'low_confidence'
                )
            
            else:
                return AutoCategorizationResult(
                    transaction_id=transaction_id,
                    success=False,
                    action_taken='skipped',
                    reasoning=f'Confidence too low: {best_suggestion.confidence:.2f}'
                )
        
        except Exception as e:
            logger.error(f"Error processing transaction {transaction_id}: {e}")
            return AutoCategorizationResult(
                transaction_id=transaction_id,
                success=False,
                action_taken='error',
                reasoning=f'Processing error: {str(e)}'
            )
    
    async def _auto_apply_category(self, transaction_id: str, suggestion, 
                                 description: str, amount: float) -> AutoCategorizationResult:
        """Auto-apply category for high-confidence suggestions"""
        
        conn = get_conn()
        
        # Step 1: Find or create the category
        from .ai_smart_categorization import process_ai_category_suggestion
        category_result = process_ai_category_suggestion(
            suggestion.category_name, 
            confidence=suggestion.confidence,
            auto_create=self.config.enable_category_creation
        )
        
        if not category_result.category_id:
            return AutoCategorizationResult(
                transaction_id=transaction_id,
                success=False,
                action_taken='failed',
                reasoning=f'Could not find/create category: {suggestion.category_name}'
            )
        
        # Step 2: Apply the categorization
        try:
            # Use DELETE + INSERT instead of ON CONFLICT (DuckDB constraint issue)
            conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [transaction_id])
            conn.execute(
                "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
                [transaction_id, category_result.category_id, "ai_auto_enhanced"]
            )

            # Store confidence score and merchant name on the transaction for UI display
            merchant_name = getattr(suggestion, 'merchant_name', None)
            conn.execute(
                "UPDATE [transaction] SET ai_confidence_score = ?, ai_merchant_name = ? WHERE id = ?",
                [suggestion.confidence, merchant_name, transaction_id]
            )

            # Step 3: Log the auto-categorization
            self._log_auto_categorization(
                transaction_id, category_result.category_id, suggestion.confidence,
                suggestion.reasoning, 'auto_applied'
            )

            # Step 4: Learn from this categorization for future merchant matching
            try:
                await learn_from_transaction_categorization(transaction_id, category_result.category_id)
            except Exception as e:
                logger.warning(f"Failed to learn from AI categorization: {e}")

            action = 'created_and_applied' if category_result.created else 'applied'
            
            return AutoCategorizationResult(
                transaction_id=transaction_id,
                success=True,
                category_id=category_result.category_id,
                category_name=category_result.category_name,
                confidence=suggestion.confidence,
                reasoning=suggestion.reasoning,
                action_taken=action
            )
        
        except Exception as e:
            logger.error(f"Error applying category to transaction {transaction_id}: {e}")
            return AutoCategorizationResult(
                transaction_id=transaction_id,
                success=False,
                action_taken='failed',
                reasoning=f'Database error: {str(e)}'
            )
    
    async def _store_suggestion(self, transaction_id: str, suggestion, 
                              priority: str) -> AutoCategorizationResult:
        """Store suggestion for manual review"""
        
        # For now, we'll just return that we have a suggestion
        # In a full implementation, you might store these in a suggestions table
        return AutoCategorizationResult(
            transaction_id=transaction_id,
            success=True,
            category_name=suggestion.category_name,
            confidence=suggestion.confidence,
            reasoning=suggestion.reasoning,
            action_taken=f'suggested_{priority}'
        )
    
    def _is_already_categorized(self, transaction_id: str) -> bool:
        """Check if transaction is already categorized"""
        conn = get_conn()
        result = conn.execute(
            "SELECT 1 FROM transaction_category WHERE tx_id = ? LIMIT 1",
            [transaction_id]
        ).fetchone()
        return result is not None
    
    async def _learn_pattern_from_ai(self, description: str, category_name: str, confidence: float):
        """Learn a new pattern from high-confidence AI categorization

        When OpenAI/LM Studio returns high confidence for a transaction that our
        patterns didn't catch, we extract the merchant name and store it in the
        merchant_category_mapping table so patterns will catch it next time.
        """
        try:
            conn = get_conn()

            # Extract potential merchant name from description
            # Take first 2-3 significant words, uppercase
            import re
            desc_upper = description.upper()

            # Remove common prefixes
            desc_clean = re.sub(r'^(CHECKCARD|PURCHASE|PMNT SENT|PAYMENT|ACH|DEBIT|CREDIT)\s*\d*\s*', '', desc_upper)

            # Extract first meaningful part (likely merchant name)
            match = re.match(r'^([A-Z][A-Z0-9\s\*\-\.\']+?)(?:\s+\d|\s+[A-Z]{2}\s+\d|\s+\d{3})', desc_clean)
            if match:
                merchant_key = match.group(1).strip()
            else:
                # Just take first 25 chars
                merchant_key = desc_clean[:25].strip()

            # Clean up the merchant key
            merchant_key = re.sub(r'[\*\#\-]+$', '', merchant_key).strip()

            if len(merchant_key) < 3:
                return  # Too short to be useful

            # Get category ID
            category_row = conn.execute(
                "SELECT id FROM category WHERE LOWER(name) = LOWER(?)",
                [category_name]
            ).fetchone()

            if not category_row:
                logger.debug(f"Category not found for learning: {category_name}")
                return

            category_id = category_row[0]

            # Check if we already have this mapping
            existing = conn.execute(
                "SELECT id FROM merchant_category_mapping WHERE LOWER(merchant_pattern) = LOWER(?)",
                [merchant_key]
            ).fetchone()

            if existing:
                # Update confidence if higher
                conn.execute("""
                    UPDATE merchant_category_mapping
                    SET confidence = CASE WHEN confidence < ? THEN ? ELSE confidence END,
                        usage_count = usage_count + 1,
                        last_used = ?
                    WHERE LOWER(merchant_pattern) = LOWER(?)
                """, [confidence, confidence, datetime.now(UTC), merchant_key])
                logger.info(f"Updated learned pattern: {merchant_key} -> {category_name}")
            else:
                # Insert new mapping
                import uuid
                conn.execute("""
                    INSERT INTO merchant_category_mapping (id, merchant_name, merchant_pattern, category_id, confidence, usage_count, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                """, [str(uuid.uuid4()), merchant_key, merchant_key, category_id, confidence, datetime.now(UTC)])
                logger.info(f"Learned new pattern: {merchant_key} -> {category_name} ({confidence:.2f})")

        except Exception as e:
            logger.warning(f"Failed to learn pattern from AI: {e}")

    def _log_auto_categorization(self, transaction_id: str, category_id: str,
                               confidence: float, reasoning: str, action: str):
        """Log auto-categorization for tracking and learning"""
        conn = get_conn()
        
        try:
            conn.execute("""
                INSERT INTO auto_categorization_log (
                    id, transaction_id, category_id, confidence, reasoning,
                    match_type, evidence_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                str(uuid.uuid4()), transaction_id, category_id,
                confidence, reasoning, 'enhanced_ai',
                json.dumps({'action': action, 'service': 'enhanced_categorization'}), 
                datetime.now(UTC)
            ])
        except Exception as e:
            logger.warning(f"Could not log auto-categorization: {e}")
    
    async def batch_process_uncategorized(self, account_id: Optional[str] = None,
                                        limit: int = None) -> Dict[str, Any]:
        """Batch process uncategorized transactions"""

        conn = get_conn()
        batch_limit = limit or self.config.batch_size

        # Get uncategorized transactions WITH their stored AI suggestions
        query = """
            SELECT t.id, t.description_norm, t.amount, t.account_id, t.ai_category_suggestions
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON tc.tx_id = t.id
            WHERE tc.tx_id IS NULL
        """
        params = []

        if account_id:
            query += " AND t.account_id = ?"
            params.append(account_id)

        query += " ORDER BY t.posted_at DESC LIMIT ?"
        params.append(batch_limit)

        uncategorized = conn.execute(query, params).fetchall()

        # Process results
        results = {
            'total_processed': 0,
            'auto_applied': 0,
            'categories_created': 0,
            'suggested_high': 0,
            'suggested_medium': 0,
            'suggested_low': 0,
            'skipped': 0,
            'errors': 0,
            'details': []
        }

        for row in uncategorized:
            tx_id, description, amount, acc_id, ai_suggestions = row[0], row[1], row[2], row[3], row[4] if len(row) > 4 else None
            results['total_processed'] += 1

            result = await self.process_transaction(tx_id, description, amount, acc_id, ai_suggestions)
            results['details'].append({
                'transaction_id': tx_id,
                'description': description[:50] + '...' if len(description) > 50 else description,
                'amount': amount,
                'result': result
            })
            
            # Update counters
            if result.action_taken == 'applied':
                results['auto_applied'] += 1
            elif result.action_taken == 'created_and_applied':
                results['auto_applied'] += 1
                results['categories_created'] += 1
            elif result.action_taken == 'suggested_high':
                results['suggested_high'] += 1
            elif result.action_taken == 'suggested_medium':
                results['suggested_medium'] += 1
            elif result.action_taken == 'suggested_low':
                results['suggested_low'] += 1
            elif result.action_taken == 'skipped':
                results['skipped'] += 1
            else:
                results['errors'] += 1
        
        return results
    
    async def learn_from_correction(self, transaction_id: str, correct_category_id: str, 
                                  predicted_category: Optional[str] = None, 
                                  prediction_confidence: float = 0.0):
        """Learn from user corrections to improve future predictions"""
        
        if self.config.enable_learning:
            # Use the smart categorization engine's learning capability
            await self.smart_engine.learn_from_categorization(transaction_id, correct_category_id)
            
            # Store feedback for analysis
            conn = get_conn()
            try:
                conn.execute("""
                    INSERT INTO categorization_feedback (
                        id, transaction_id, predicted_category, actual_category,
                        prediction_confidence, was_correct, feedback_type, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    str(uuid.uuid4()), transaction_id, predicted_category or 'unknown',
                    correct_category_id, prediction_confidence, 
                    predicted_category == correct_category_id, 'user_correction', 
                    datetime.now(UTC)
                ])
            except Exception as e:
                logger.warning(f"Could not store learning feedback: {e}")
    
    def get_auto_categorization_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get auto-categorization performance statistics"""
        conn = get_conn()
        
        try:
            # Get recent auto-categorizations
            recent_auto = conn.execute("""
                SELECT COUNT(*), AVG(confidence), match_type
                FROM auto_categorization_log
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY match_type
            """.format(days)).fetchall()
            
            # Get feedback data
            feedback_stats = conn.execute("""
                SELECT COUNT(*) as total, SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct
                FROM categorization_feedback
                WHERE created_at >= datetime('now', '-{} days')
                AND feedback_type = 'user_correction'
            """.format(days)).fetchone()
            
            accuracy = 0.0
            if feedback_stats and feedback_stats[0] > 0:
                accuracy = feedback_stats[1] / feedback_stats[0]
            
            return {
                'auto_categorizations': [
                    {
                        'match_type': row[2],
                        'count': row[0],
                        'avg_confidence': row[1]
                    }
                    for row in recent_auto
                ],
                'feedback_stats': {
                    'total_feedback': feedback_stats[0] if feedback_stats else 0,
                    'correct_predictions': feedback_stats[1] if feedback_stats else 0,
                    'accuracy': accuracy
                },
                'period_days': days
            }
        
        except Exception as e:
            logger.error(f"Error getting auto-categorization stats: {e}")
            return {'error': str(e)}


# Global instance
_auto_categorization_service = None

def get_auto_categorization_service(config: Optional[AutoCategorizationConfig] = None) -> AutoCategorizationService:
    """Get the global auto-categorization service instance"""
    global _auto_categorization_service
    if _auto_categorization_service is None:
        _auto_categorization_service = AutoCategorizationService(config)
    return _auto_categorization_service


async def auto_categorize_transaction(transaction_id: str, description: str, amount: float, 
                                    account_id: str) -> AutoCategorizationResult:
    """Auto-categorize a single transaction - main function to use"""
    service = get_auto_categorization_service()
    return await service.process_transaction(transaction_id, description, amount, account_id)


async def batch_auto_categorize(account_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """Batch auto-categorize uncategorized transactions"""
    service = get_auto_categorization_service()
    return await service.batch_process_uncategorized(account_id, limit)


async def learn_from_user_correction(transaction_id: str, correct_category_id: str):
    """Learn from user's manual categorization"""
    service = get_auto_categorization_service()
    await service.learn_from_correction(transaction_id, correct_category_id)
