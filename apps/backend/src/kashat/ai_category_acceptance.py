"""
AI Category Acceptance Service

Handles smart category acceptance with automatic creation and duplicate prevention.
Provides "Accept All" functionality that creates missing categories intelligently.
"""

from __future__ import annotations

import uuid
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, UTC
from difflib import SequenceMatcher

from .db import get_conn
from .ai_smart_categorization import get_smart_categorization_engine, CategoryCreationResult
from .ai_category_schemas import SingleAcceptanceRequest, BatchAcceptanceRequest

logger = logging.getLogger(__name__)


def _normalize_batch_request(request: BatchAcceptanceRequest) -> BatchAcceptanceRequest:
    """Normalize per-item flags using batch-level controls."""
    normalized_acceptances = [
        acc.model_copy(update={
            "create_if_missing": request.create_missing_categories,
            "auto_merge_similar": request.auto_merge_threshold > 0,
        })
        for acc in request.acceptances
    ]
    return BatchAcceptanceRequest(
        acceptances=normalized_acceptances,
        create_missing_categories=request.create_missing_categories,
        auto_merge_threshold=request.auto_merge_threshold,
        create_parent_hierarchy=request.create_parent_hierarchy,
    )


@dataclass
class CategoryAcceptanceResult:
    """Result of category acceptance"""
    success: bool
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    action_taken: str = ""  # 'applied_existing', 'created_and_applied', 'merged_and_applied', 'failed'
    similar_category_found: Optional[str] = None
    reasoning: str = ""
    warnings: List[str] = None


@dataclass
class BatchAcceptanceResult:
    """Result of batch category acceptance"""
    total_requested: int
    successful_applications: int
    categories_created: int
    categories_merged: int
    failed_applications: int
    details: List[CategoryAcceptanceResult]
    new_categories: List[Dict[str, str]]
    warnings: List[str]


class SmartCategoryAcceptanceService:
    """Service for smart category acceptance with duplicate prevention"""
    
    def __init__(self):
        self.smart_engine = get_smart_categorization_engine()
        self.similarity_threshold = 0.85
        
    def accept_single_category(self, request: SingleAcceptanceRequest) -> CategoryAcceptanceResult:
        """Accept a single AI category suggestion"""
        
        try:
            # Step 1: Find existing exact match
            existing_id = self._find_exact_category(request.suggested_category_name)
            if existing_id:
                return self._apply_existing_category(request, existing_id)
            
            # Step 2: Find similar category to prevent duplicates
            if request.auto_merge_similar:
                similar_result = self._find_and_handle_similar_category(request)
                if similar_result:
                    return similar_result
            
            # Step 3: Create new category if allowed
            if request.create_if_missing:
                return self._create_and_apply_category(request)
            
            # Step 4: Fallback - cannot proceed
            return CategoryAcceptanceResult(
                success=False,
                action_taken='failed',
                reasoning=f'Category "{request.suggested_category_name}" not found and creation disabled',
                warnings=['Category creation was disabled']
            )
            
        except Exception as e:
            logger.error(f"Error accepting category for transaction {request.transaction_id}: {e}")
            return CategoryAcceptanceResult(
                success=False,
                action_taken='failed',
                reasoning=f'Error during acceptance: {str(e)}',
                warnings=[f'System error: {str(e)}']
            )
    
    def accept_batch_categories(self, request: BatchAcceptanceRequest) -> BatchAcceptanceResult:
        """Accept multiple AI category suggestions in batch"""
        request = _normalize_batch_request(request)
        original_threshold = self.similarity_threshold
        if request.auto_merge_threshold > 0:
            self.similarity_threshold = request.auto_merge_threshold

        result = BatchAcceptanceResult(
            total_requested=len(request.acceptances),
            successful_applications=0,
            categories_created=0,
            categories_merged=0,
            failed_applications=0,
            details=[],
            new_categories=[],
            warnings=[]
        )
        
        # Track categories we create to avoid duplicates within batch
        created_in_batch = {}
        try:
            for acceptance_request in request.acceptances:
                # Check if we already created this category in this batch
                category_lower = acceptance_request.suggested_category_name.lower()
                if category_lower in created_in_batch:
                    # Use the category we already created
                    batch_result = self._apply_existing_category(
                        acceptance_request, 
                        created_in_batch[category_lower]
                    )
                    batch_result.action_taken = 'applied_batch_created'
                    batch_result.reasoning += ' (created earlier in this batch)'
                else:
                    # Process normally
                    batch_result = self.accept_single_category(acceptance_request)
                    
                    # Track if we created a new category
                    if batch_result.action_taken == 'created_and_applied' and batch_result.category_id:
                        created_in_batch[category_lower] = batch_result.category_id
                        result.new_categories.append({
                            'id': batch_result.category_id,
                            'name': batch_result.category_name,
                            'created_for_transaction': acceptance_request.transaction_id
                        })
                
                # Update counters
                if batch_result.success:
                    result.successful_applications += 1
                    if batch_result.action_taken == 'created_and_applied':
                        result.categories_created += 1
                    elif batch_result.action_taken == 'merged_and_applied':
                        result.categories_merged += 1
                else:
                    result.failed_applications += 1
                
                # Collect warnings
                if batch_result.warnings:
                    result.warnings.extend(batch_result.warnings)
                
                result.details.append(batch_result)
        finally:
            self.similarity_threshold = original_threshold
        
        return result
    
    def _find_exact_category(self, category_name: str) -> Optional[str]:
        """Find exact category match using normalized form if available"""
        conn = get_conn()
        try:
            result = conn.execute(
                "SELECT id FROM category WHERE normalized_name = lower(trim(?))",
                [category_name]
            ).fetchone()
        except Exception:
            result = conn.execute(
                "SELECT id FROM category WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))",
                [category_name]
            ).fetchone()
        return result[0] if result else None
    
    def _find_similar_categories(self, category_name: str, threshold: float = 0.85) -> List[Tuple[str, str, float]]:
        """Find similar categories to prevent duplicates"""
        conn = get_conn()
        categories = conn.execute("SELECT id, name FROM category").fetchall()
        
        similar_categories = []
        category_name_clean = category_name.lower().strip()
        
        for cat_id, cat_name in categories:
            cat_name_clean = cat_name.lower().strip()
            
            # Calculate similarity
            similarity = SequenceMatcher(None, category_name_clean, cat_name_clean).ratio()
            
            if similarity >= threshold:
                similar_categories.append((cat_id, cat_name, similarity))
        
        # Sort by similarity (highest first)
        return sorted(similar_categories, key=lambda x: x[2], reverse=True)
    
    def _find_and_handle_similar_category(self, request: SingleAcceptanceRequest) -> Optional[CategoryAcceptanceResult]:
        """Find and handle similar categories"""
        similar_categories = self._find_similar_categories(
            request.suggested_category_name, 
            self.similarity_threshold
        )
        
        if similar_categories:
            # Use the most similar category
            best_match_id, best_match_name, similarity = similar_categories[0]
            
            logger.info(f"Found similar category '{best_match_name}' for '{request.suggested_category_name}' (similarity: {similarity:.2f})")
            
            return CategoryAcceptanceResult(
                success=True,
                category_id=best_match_id,
                category_name=best_match_name,
                action_taken='merged_and_applied',
                similar_category_found=best_match_name,
                reasoning=f'Merged with similar existing category "{best_match_name}" (similarity: {similarity:.1%})',
                warnings=[f'AI suggested "{request.suggested_category_name}" but used similar existing "{best_match_name}"']
            )
        
        return None
    
    def _apply_existing_category(self, request: SingleAcceptanceRequest, category_id: str) -> CategoryAcceptanceResult:
        """Apply an existing category to the transaction"""
        conn = get_conn()
        
        try:
            # Get category name
            category_name = conn.execute(
                "SELECT name FROM category WHERE id = ?", [category_id]
            ).fetchone()[0]
            
            # Apply the categorization
            conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [request.transaction_id])
            conn.execute(
                "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
                [request.transaction_id, category_id, "user_ai_accepted"]
            )
            
            # Log the acceptance
            self._log_category_acceptance(
                request.transaction_id, category_id, request.confidence, 
                'applied_existing', request.suggested_category_name
            )
            
            return CategoryAcceptanceResult(
                success=True,
                category_id=category_id,
                category_name=category_name,
                action_taken='applied_existing',
                reasoning=f'Applied existing category "{category_name}"'
            )
            
        except Exception as e:
            logger.error(f"Error applying existing category {category_id}: {e}")
            return CategoryAcceptanceResult(
                success=False,
                action_taken='failed',
                reasoning=f'Database error applying category: {str(e)}'
            )
    
    def _create_and_apply_category(self, request: SingleAcceptanceRequest) -> CategoryAcceptanceResult:
        """Create a new category and apply it to the transaction"""
        
        try:
            # Use the smart categorization engine to create the category
            creation_result = self.smart_engine.find_or_create_category(
                request.suggested_category_name,
                confidence=request.confidence,
                auto_create=True
            )
            
            if not creation_result.category_id:
                return CategoryAcceptanceResult(
                    success=False,
                    action_taken='failed',
                    reasoning=creation_result.reason,
                    warnings=['Could not create category']
                )
            
            # Apply the categorization
            conn = get_conn()
            conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [request.transaction_id])
            conn.execute(
                "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
                [request.transaction_id, creation_result.category_id, "user_ai_accepted"]
            )
            
            # Log the acceptance
            self._log_category_acceptance(
                request.transaction_id, creation_result.category_id, request.confidence,
                'created_and_applied', request.suggested_category_name
            )
            
            action = 'created_and_applied' if creation_result.created else 'applied_existing'
            reasoning = f'Created new category "{creation_result.category_name}"' if creation_result.created else f'Found existing category "{creation_result.category_name}"'
            
            return CategoryAcceptanceResult(
                success=True,
                category_id=creation_result.category_id,
                category_name=creation_result.category_name,
                action_taken=action,
                reasoning=reasoning + f' (confidence: {request.confidence:.1%})'
            )
            
        except Exception as e:
            logger.error(f"Error creating and applying category: {e}")
            return CategoryAcceptanceResult(
                success=False,
                action_taken='failed',
                reasoning=f'Error creating category: {str(e)}'
            )
    
    def _log_category_acceptance(self, transaction_id: str, category_id: str, 
                               confidence: float, action: str, suggested_name: str):
        """Log category acceptance for tracking"""
        conn = get_conn()
        
        try:
            conn.execute("""
                INSERT INTO auto_categorization_log (
                    id, transaction_id, category_id, confidence, reasoning,
                    match_type, evidence_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                str(uuid.uuid4()), transaction_id, category_id,
                confidence, f'User accepted AI suggestion: {suggested_name}', 
                'user_acceptance',
                json.dumps({
                    'action': action, 
                    'suggested_name': suggested_name,
                    'service': 'category_acceptance'
                }), 
                datetime.now(UTC)
            ])
        except Exception as e:
            logger.warning(f"Could not log category acceptance: {e}")
    
    def get_category_suggestions_with_status(self, transaction_ids: List[str]) -> Dict[str, Dict]:
        """Get AI category suggestions with their current status in the database"""
        conn = get_conn()
        results = {}
        
        for tx_id in transaction_ids:
            # Get transaction details and AI suggestions
            tx_data = conn.execute("""
                SELECT description_norm, amount, ai_category_suggestions
                FROM [transaction] 
                WHERE id = ?
            """, [tx_id]).fetchone()
            
            if not tx_data:
                continue
                
            description, amount, ai_suggestions_json = tx_data
            
            # Parse AI suggestions
            ai_suggestions = []
            if ai_suggestions_json:
                try:
                    suggestions = json.loads(ai_suggestions_json)
                    for suggestion in suggestions:
                        category_name = suggestion.get('category_name', '')
                        confidence = suggestion.get('confidence', 0)
                        
                        # Check if category exists
                        existing_id = self._find_exact_category(category_name)
                        similar_categories = self._find_similar_categories(category_name, 0.8)
                        
                        status = 'exists' if existing_id else ('similar_exists' if similar_categories else 'needs_creation')
                        
                        ai_suggestions.append({
                            'category_name': category_name,
                            'confidence': confidence,
                            'status': status,
                            'existing_id': existing_id,
                            'similar_categories': [
                                {'id': cat_id, 'name': cat_name, 'similarity': sim}
                                for cat_id, cat_name, sim in similar_categories[:3]
                            ] if similar_categories else []
                        })
                except json.JSONDecodeError:
                    pass
            
            # Check current categorization
            current_category = conn.execute("""
                SELECT c.id, c.name 
                FROM transaction_category tc
                JOIN category c ON tc.category_id = c.id
                WHERE tc.tx_id = ?
            """, [tx_id]).fetchone()
            
            results[tx_id] = {
                'description': description,
                'amount': amount,
                'ai_suggestions': ai_suggestions,
                'current_category': {
                    'id': current_category[0],
                    'name': current_category[1]
                } if current_category else None,
                'needs_categorization': current_category is None
            }
        
        return results
    
    def preview_batch_acceptance(self, request: BatchAcceptanceRequest) -> Dict[str, any]:
        """Preview what would happen with batch acceptance without actually doing it"""
        request = _normalize_batch_request(request)
        preview = {
            'total_transactions': len(request.acceptances),
            'will_create_categories': [],
            'will_use_existing': [],
            'will_merge_similar': [],
            'potential_issues': [],
            'estimated_success_rate': 0.0
        }
        
        created_in_preview = set()
        successful_previews = 0
        
        for acceptance in request.acceptances:
            category_lower = acceptance.suggested_category_name.lower()
            
            # Check if already created in this batch
            if category_lower in created_in_preview:
                preview['will_use_existing'].append({
                    'transaction_id': acceptance.transaction_id,
                    'category': acceptance.suggested_category_name,
                    'reason': 'Will be created earlier in batch'
                })
                successful_previews += 1
                continue
            
            # Check existing
            existing_id = self._find_exact_category(acceptance.suggested_category_name)
            if existing_id:
                preview['will_use_existing'].append({
                    'transaction_id': acceptance.transaction_id,
                    'category': acceptance.suggested_category_name,
                    'existing_id': existing_id
                })
                successful_previews += 1
                continue
            
            # Check similar
            similar = self._find_similar_categories(acceptance.suggested_category_name, request.auto_merge_threshold)
            if similar and request.auto_merge_threshold > 0:
                preview['will_merge_similar'].append({
                    'transaction_id': acceptance.transaction_id,
                    'suggested': acceptance.suggested_category_name,
                    'will_use': similar[0][1],
                    'similarity': similar[0][2]
                })
                successful_previews += 1
                continue
            
            # Will create new
            if request.create_missing_categories:
                preview['will_create_categories'].append({
                    'transaction_id': acceptance.transaction_id,
                    'category': acceptance.suggested_category_name,
                    'confidence': acceptance.confidence
                })
                created_in_preview.add(category_lower)
                successful_previews += 1
            else:
                preview['potential_issues'].append({
                    'transaction_id': acceptance.transaction_id,
                    'issue': f'Category "{acceptance.suggested_category_name}" does not exist and creation is disabled'
                })
        
        preview['estimated_success_rate'] = successful_previews / max(len(request.acceptances), 1)
        
        return preview


# Global instance
_category_acceptance_service = None

def get_category_acceptance_service() -> SmartCategoryAcceptanceService:
    """Get the global category acceptance service instance"""
    global _category_acceptance_service
    if _category_acceptance_service is None:
        _category_acceptance_service = SmartCategoryAcceptanceService()
    return _category_acceptance_service


def accept_ai_category(transaction_id: str, suggested_category_name: str, 
                      confidence: float, create_if_missing: bool = True) -> CategoryAcceptanceResult:
    """Accept a single AI category suggestion - main function to use"""
    service = get_category_acceptance_service()
    request = SingleAcceptanceRequest(
        transaction_id=transaction_id,
        suggested_category_name=suggested_category_name,
        confidence=confidence,
        create_if_missing=create_if_missing
    )
    return service.accept_single_category(request)


def accept_all_ai_categories(request: BatchAcceptanceRequest) -> BatchAcceptanceResult:
    """Accept multiple AI category suggestions using the shared schema."""
    service = get_category_acceptance_service()
    return service.accept_batch_categories(request)
