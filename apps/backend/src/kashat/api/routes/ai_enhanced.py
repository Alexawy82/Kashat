"""
Enhanced AI Enhancement Endpoints

Provides improved AI categorization using the enhanced categorization system
instead of the basic "purchase" fallback system.
"""

from __future__ import annotations

import json
import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, UTC

from ...ai_enhanced_categorization import categorize_transaction_enhanced
from ...ai_smart_categorization import process_ai_category_suggestion
from ...db import get_conn

router = APIRouter(prefix="/ai-enhanced", tags=["ai-enhanced"])


class EnhancementRequest(BaseModel):
    """Request to enhance transactions with improved AI"""
    transaction_ids: Optional[List[str]] = None
    enhance_all_unprocessed: bool = False
    auto_apply_high_confidence: bool = False
    confidence_threshold: float = 0.85


class EnhancementResult(BaseModel):
    """Result of AI enhancement"""
    transaction_id: str
    success: bool
    suggestions: List[dict]
    auto_applied: bool = False
    error: Optional[str] = None


@router.post("/enhance-transactions")
async def enhance_transactions(request: EnhancementRequest) -> dict:
    """Enhance transactions with improved AI categorization"""
    
    conn = get_conn()
    results = []
    
    # Determine which transactions to enhance
    if request.enhance_all_unprocessed:
        # Get all unprocessed transactions
        transactions = conn.execute("""
            SELECT id, description_norm, amount, account_id, posted_at
            FROM [transaction] 
            WHERE ai_category_suggestions IS NULL 
               OR ai_category_suggestions = ''
               OR json_extract(ai_category_suggestions, '$[0].category_name') = 'purchase'
            ORDER BY posted_at DESC
            LIMIT 100
        """).fetchall()
    elif request.transaction_ids:
        # Get specific transactions
        placeholders = ','.join(['?' for _ in request.transaction_ids])
        transactions = conn.execute(f"""
            SELECT id, description_norm, amount, account_id, posted_at
            FROM [transaction] 
            WHERE id IN ({placeholders})
        """, request.transaction_ids).fetchall()
    else:
        return {"error": "Must specify transaction_ids or enhance_all_unprocessed"}
    
    enhanced_count = 0
    auto_applied_count = 0
    
    for tx_id, description, amount, account_id, posted_at in transactions:
        try:
            # Get enhanced AI suggestions
            suggestions = categorize_transaction_enhanced(description, amount)
            
            if suggestions:
                # Format suggestions for storage
                suggestions_json = [
                    {
                        "category_name": s.category_name,
                        "confidence": s.confidence,
                        "reasoning": s.reasoning
                    }
                    for s in suggestions
                ]
                
                # Store AI suggestions in transaction
                conn.execute("""
                    UPDATE [transaction] 
                    SET ai_category_suggestions = ?,
                        ai_confidence_score = ?,
                        ai_processed_at = ?,
                        ai_provider = 'enhanced_ai',
                        ai_model = 'enhanced_categorization_v2'
                    WHERE id = ?
                """, [
                    json.dumps(suggestions_json),
                    suggestions[0].confidence,
                    datetime.now(UTC),
                    tx_id
                ])
                
                enhanced_count += 1
                auto_applied = False
                
                # Auto-apply if high confidence and enabled
                if (request.auto_apply_high_confidence and 
                    suggestions[0].confidence >= request.confidence_threshold):
                    
                    try:
                        # Use smart categorization to create/find category
                        result = process_ai_category_suggestion(
                            suggestions[0].category_name,
                            confidence=suggestions[0].confidence,
                            auto_create=True
                        )
                        
                        if result and result.category_id:
                            # Apply the categorization
                            conn.execute("""
                                INSERT INTO transaction_category
                                (tx_id, category_id, applied_by)
                                VALUES (?, ?, ?)
                                ON CONFLICT (tx_id) DO UPDATE SET category_id = EXCLUDED.category_id, applied_by = EXCLUDED.applied_by
                            """, [tx_id, result.category_id, "ai_enhanced_auto"])
                            
                            auto_applied = True
                            auto_applied_count += 1
                    
                    except Exception as e:
                        # Log but don't fail the enhancement
                        print(f"Auto-apply failed for {tx_id}: {e}")
                
                results.append(EnhancementResult(
                    transaction_id=tx_id,
                    success=True,
                    suggestions=suggestions_json,
                    auto_applied=auto_applied
                ))
            else:
                results.append(EnhancementResult(
                    transaction_id=tx_id,
                    success=False,
                    suggestions=[],
                    error="No AI suggestions generated"
                ))
        
        except Exception as e:
            results.append(EnhancementResult(
                transaction_id=tx_id,
                success=False,
                suggestions=[],
                error=str(e)
            ))
    
    return {
        "total_processed": len(transactions),
        "successfully_enhanced": enhanced_count,
        "auto_applied": auto_applied_count,
        "results": [r.dict() for r in results],
        "summary": f"Enhanced {enhanced_count}/{len(transactions)} transactions"
    }


@router.get("/reenhance-all")
async def reenhance_all_transactions(background_tasks: BackgroundTasks) -> dict:
    """Re-enhance all transactions with improved AI (background job)"""
    
    # Start background enhancement
    background_tasks.add_task(_reenhance_all_background)
    
    return {
        "status": "started",
        "message": "Re-enhancement job started in background",
        "estimated_duration": "2-5 minutes for typical datasets"
    }


@router.post("/fix-purchase-categories")
async def fix_purchase_categories() -> dict:
    """Fix transactions that were categorized as generic 'purchase'"""
    
    conn = get_conn()
    
    # Find transactions with "purchase" suggestions
    transactions = conn.execute("""
        SELECT id, description_norm, amount, ai_category_suggestions
        FROM [transaction] 
        WHERE ai_category_suggestions IS NOT NULL
        AND (
            json_extract(ai_category_suggestions, '$[0].category_name') = 'purchase'
            OR json_extract(ai_category_suggestions, '$[0].category_name') = 'Purchase'
        )
        ORDER BY posted_at DESC
        LIMIT 50
    """).fetchall()
    
    fixed_count = 0
    
    for tx_id, description, amount, old_suggestions in transactions:
        try:
            # Get new enhanced suggestions
            suggestions = categorize_transaction_enhanced(description, amount)
            
            if suggestions and suggestions[0].category_name.lower() != 'purchase':
                # Update with better suggestions
                suggestions_json = [
                    {
                        "category_name": s.category_name,
                        "confidence": s.confidence,
                        "reasoning": s.reasoning
                    }
                    for s in suggestions
                ]
                
                conn.execute("""
                    UPDATE [transaction] 
                    SET ai_category_suggestions = ?,
                        ai_confidence_score = ?,
                        ai_processed_at = ?,
                        ai_provider = 'enhanced_ai_fix',
                        ai_model = 'enhanced_categorization_v2'
                    WHERE id = ?
                """, [
                    json.dumps(suggestions_json),
                    suggestions[0].confidence,
                    datetime.now(UTC),
                    tx_id
                ])
                
                fixed_count += 1
        
        except Exception as e:
            print(f"Error fixing transaction {tx_id}: {e}")
    
    return {
        "transactions_found": len(transactions),
        "transactions_fixed": fixed_count,
        "message": f"Fixed {fixed_count} transactions that had generic 'purchase' categorization"
    }


@router.get("/test-enhanced/{transaction_id}")
async def test_enhanced_categorization(transaction_id: str) -> dict:
    """Test enhanced categorization on a specific transaction"""
    
    conn = get_conn()
    
    # Get transaction
    tx = conn.execute("""
        SELECT description_norm, amount, ai_category_suggestions
        FROM [transaction] 
        WHERE id = ?
    """, [transaction_id]).fetchone()
    
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    description, amount, current_suggestions = tx
    
    # Get enhanced suggestions
    enhanced_suggestions = categorize_transaction_enhanced(description, amount)
    
    # Parse current suggestions
    current_parsed = []
    if current_suggestions:
        try:
            current_parsed = json.loads(current_suggestions)
        except:
            pass
    
    return {
        "transaction_id": transaction_id,
        "description": description,
        "amount": amount,
        "current_suggestions": current_parsed,
        "enhanced_suggestions": [
            {
                "category_name": s.category_name,
                "confidence": s.confidence,
                "reasoning": s.reasoning
            }
            for s in enhanced_suggestions
        ],
        "improvement": {
            "better_categories": len(enhanced_suggestions) > 0 and (
                not current_parsed or 
                enhanced_suggestions[0].category_name.lower() != 'purchase'
            ),
            "higher_confidence": len(enhanced_suggestions) > 0 and len(current_parsed) > 0 and (
                enhanced_suggestions[0].confidence > current_parsed[0].get('confidence', 0)
            )
        }
    }


async def _reenhance_all_background():
    """Background task to re-enhance all transactions"""
    
    try:
        conn = get_conn()
        
        # Get all transactions
        transactions = conn.execute("""
            SELECT id, description_norm, amount 
            FROM [transaction] 
            ORDER BY posted_at DESC
        """).fetchall()
        
        enhanced_count = 0
        
        for tx_id, description, amount in transactions:
            try:
                # Get enhanced suggestions
                suggestions = categorize_transaction_enhanced(description, amount)
                
                if suggestions:
                    suggestions_json = [
                        {
                            "category_name": s.category_name,
                            "confidence": s.confidence,
                            "reasoning": s.reasoning
                        }
                        for s in suggestions
                    ]
                    
                    # Update transaction
                    conn.execute("""
                        UPDATE [transaction] 
                        SET ai_category_suggestions = ?,
                            ai_confidence_score = ?,
                            ai_processed_at = ?,
                            ai_provider = 'enhanced_ai_bulk',
                            ai_model = 'enhanced_categorization_v2'
                        WHERE id = ?
                    """, [
                        json.dumps(suggestions_json),
                        suggestions[0].confidence,
                        datetime.now(UTC),
                        tx_id
                    ])
                    
                    enhanced_count += 1
            
            except Exception as e:
                print(f"Error enhancing transaction {tx_id}: {e}")
        
        print(f"Background re-enhancement completed: {enhanced_count} transactions enhanced")
    
    except Exception as e:
        print(f"Background re-enhancement failed: {e}")


@router.get("/enhancement-stats")
async def get_enhancement_stats() -> dict:
    """Get statistics about AI enhancement quality"""
    
    conn = get_conn()
    
    # Overall stats
    total_txns = conn.execute("SELECT COUNT(*) FROM [transaction]").fetchone()[0]
    
    # Enhanced transactions
    enhanced_txns = conn.execute("""
        SELECT COUNT(*) FROM [transaction] 
        WHERE ai_category_suggestions IS NOT NULL 
        AND ai_category_suggestions != ''
    """).fetchone()[0]
    
    # Purchase-only transactions (weak categorization)
    purchase_only = conn.execute("""
        SELECT COUNT(*) FROM [transaction] 
        WHERE json_extract(ai_category_suggestions, '$[0].category_name') IN ('purchase', 'Purchase')
    """).fetchone()[0]
    
    # High confidence transactions
    high_confidence = conn.execute("""
        SELECT COUNT(*) FROM [transaction] 
        WHERE ai_confidence_score >= 0.8
    """).fetchone()[0]
    
    # Enhanced AI transactions (using our improved system)
    enhanced_ai = conn.execute("""
        SELECT COUNT(*) FROM [transaction] 
        WHERE ai_provider IN ('enhanced_ai', 'enhanced_ai_fix', 'enhanced_ai_bulk')
    """).fetchone()[0]
    
    # Category diversity
    unique_suggestions = conn.execute("""
        SELECT COUNT(DISTINCT json_extract(ai_category_suggestions, '$[0].category_name'))
        FROM [transaction] 
        WHERE ai_category_suggestions IS NOT NULL
    """).fetchone()[0]
    
    return {
        "total_transactions": total_txns,
        "enhanced_transactions": enhanced_txns,
        "enhancement_rate": round((enhanced_txns / max(total_txns, 1)) * 100, 1),
        "weak_categorization": {
            "purchase_only_count": purchase_only,
            "percentage": round((purchase_only / max(enhanced_txns, 1)) * 100, 1)
        },
        "quality_metrics": {
            "high_confidence_count": high_confidence,
            "high_confidence_rate": round((high_confidence / max(enhanced_txns, 1)) * 100, 1),
            "category_diversity": unique_suggestions
        },
        "enhanced_ai_coverage": {
            "using_enhanced_ai": enhanced_ai,
            "percentage": round((enhanced_ai / max(total_txns, 1)) * 100, 1)
        },
        "recommendations": _get_recommendations(purchase_only, enhanced_txns, enhanced_ai, total_txns)
    }


def _get_recommendations(purchase_only: int, enhanced_txns: int, enhanced_ai: int, total_txns: int) -> List[str]:
    """Generate recommendations based on stats"""
    recommendations = []
    
    if purchase_only > enhanced_txns * 0.3:
        recommendations.append("High number of generic 'purchase' categorizations - run /fix-purchase-categories")
    
    if enhanced_ai < total_txns * 0.5:
        recommendations.append("Less than 50% using enhanced AI - run /reenhance-all for better categorization")
    
    if enhanced_txns < total_txns * 0.8:
        recommendations.append("Many transactions lack AI suggestions - run bulk enhancement")
    
    if not recommendations:
        recommendations.append("Categorization quality looks good!")
    
    return recommendations