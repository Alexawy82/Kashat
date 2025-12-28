"""
AI Category Management API Routes

Provides endpoints for accepting AI category suggestions with automatic creation
and duplicate prevention. Supports both single and batch operations.
"""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from ...ai_category_acceptance import (
    get_category_acceptance_service,
    accept_ai_category,
    accept_all_ai_categories
)
from ...ai_category_schemas import SingleAcceptanceRequest, BatchAcceptanceRequest
from ...ai_smart_categorization import learn_from_transaction_categorization
from ...db import get_conn
from ...ai_enhanced_categorization import categorize_transaction_enhanced
from ...db import get_conn

router = APIRouter(prefix="/ai-categories", tags=["ai-categories"])


class TransactionCategorizeRequest(BaseModel):
    """Request to get AI categorization for transactions"""
    transaction_ids: List[str]
    apply_high_confidence: bool = False
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


@router.post("/accept-single")
async def accept_single_category(request: SingleAcceptanceRequest):
    """Accept a single AI category suggestion with smart duplicate handling"""
    
    try:
        result = accept_ai_category(
            transaction_id=request.transaction_id,
            suggested_category_name=request.suggested_category_name,
            confidence=request.confidence,
            create_if_missing=request.create_if_missing
        )
        # Merchant learning + transfer flag if applicable
        if result.success and result.category_id:
            try:
                await learn_from_transaction_categorization(request.transaction_id, result.category_id)
            except Exception:
                pass
            # Train provider label mapping if given
            try:
                if request.provider and request.suggested_category_name:
                    _upsert_provider_mapping(request.provider, request.suggested_category_name, result.category_id)
            except Exception:
                pass
            try:
                _maybe_mark_transfer(request.transaction_id, result.category_id)
            except Exception:
                pass

        return {
            "success": result.success,
            "category_id": result.category_id,
            "category_name": result.category_name,
            "action_taken": result.action_taken,
            "reasoning": result.reasoning,
            "warnings": result.warnings or [],
            "similar_category_found": result.similar_category_found
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accepting category: {str(e)}")


@router.post("/accept-batch")
async def accept_batch_categories(request: BatchAcceptanceRequest):
    """Accept multiple AI category suggestions in batch - 'Accept All' functionality"""
    
    try:
        result = accept_all_ai_categories(request)
        # Post-process: learn merchants + mark transfers + provider mapping for successful items
        try:
            for i, acc in enumerate(request.acceptances):
                try:
                    det = result.details[i]
                except Exception:
                    continue
                if getattr(det, 'success', False) and getattr(det, 'category_id', None):
                    try:
                        await learn_from_transaction_categorization(acc.transaction_id, det.category_id)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    try:
                        _maybe_mark_transfer(acc.transaction_id, det.category_id)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    try:
                        if getattr(acc, 'provider', None):
                            _upsert_provider_mapping(acc.provider, acc.suggested_category_name, det.category_id)  # type: ignore[attr-defined]
                    except Exception:
                        pass
        except Exception:
            pass

        return {
            "success": result.failed_applications == 0,
            "total_requested": result.total_requested,
            "successful_applications": result.successful_applications,
            "categories_created": result.categories_created,
            "categories_merged": result.categories_merged,
            "failed_applications": result.failed_applications,
            "new_categories": result.new_categories,
            "warnings": result.warnings,
            "details": [
                {
                    "transaction_id": request.acceptances[i].transaction_id if i < len(request.acceptances) else None,
                    "category_id": detail.category_id,
                    "success": detail.success,
                    "category_name": detail.category_name,
                    "action_taken": detail.action_taken,
                    "reasoning": detail.reasoning
                }
                for i, detail in enumerate(result.details)
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in batch acceptance: {str(e)}")


@router.get("/metrics")
async def get_ai_categorization_metrics() -> Dict[str, Any]:
    """Return key metrics: acceptances, provider mappings, known-merchant usage, transfer flags."""
    conn = get_conn()
    try:
        acceptances = conn.execute(
            "SELECT COUNT(*) FROM auto_categorization_log WHERE match_type = 'user_acceptance'"
        ).fetchone()[0]
    except Exception:
        acceptances = 0
    try:
        mappings = conn.execute(
            "SELECT COUNT(*) FROM ai_category_mapping"
        ).fetchone()[0]
    except Exception:
        mappings = 0
    try:
        learned_merchants = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(usage_count),0) FROM merchant_category_mapping"
        ).fetchone()
        merchant_total = int(learned_merchants[0]) if learned_merchants else 0
        merchant_uses = int(learned_merchants[1]) if learned_merchants else 0
    except Exception:
        merchant_total, merchant_uses = 0, 0
    try:
        transfer_flagged = conn.execute(
            "SELECT COUNT(*) FROM [transaction] WHERE is_transfer = TRUE"
        ).fetchone()[0]
    except Exception:
        transfer_flagged = 0

    # Heuristic: how many transactions have mapped suggestions stored
    try:
        mapped_suggestions = conn.execute(
            "SELECT COUNT(*) FROM [transaction] WHERE ai_category_suggestions LIKE '%\"category_id\":%'"
        ).fetchone()[0]
    except Exception:
        mapped_suggestions = 0

    return {
        "acceptances": acceptances,
        "provider_mappings": mappings,
        "known_merchants": merchant_total,
        "merchant_total_uses": merchant_uses,
        "transfer_flagged": transfer_flagged,
        "mapped_suggestions": mapped_suggestions,
    }


@router.post("/backfill-provider-mappings")
async def backfill_provider_mappings() -> Dict[str, Any]:
    """Backfill provider->category mappings using acceptance logs and transaction provider info."""
    conn = get_conn()
    created = 0
    try:
        rows = conn.execute(
            """
            SELECT l.id, t.ai_provider, json_extract(l.evidence_json, '$.suggested_name') AS suggested
            FROM auto_categorization_log l
            JOIN [transaction] t ON t.id = l.transaction_id
            WHERE l.match_type = 'user_acceptance'
            """
        ).fetchall()
    except Exception:
        rows = []
    for row in rows:
        try:
            prov = row[1]
            src = row[2]
            if not src:
                continue
            # Find applied category from the log record
            cat = conn.execute(
                "SELECT category_id FROM auto_categorization_log WHERE id = ?",
                [row[0]]
            ).fetchone()
            if not cat:
                continue
            category_id = cat[0]
            try:
                conn.execute(
                    "DELETE FROM ai_category_mapping WHERE provider IS ? AND source_label = ?",
                    [prov, src]
                )
            except Exception:
                pass
            try:
                conn.execute(
                    "INSERT INTO ai_category_mapping (provider, source_label, category_id) VALUES (?, ?, ?)",
                    [prov, src, category_id]
                )
                created += 1
            except Exception:
                pass
        except Exception:
            continue
    return {"mappings_created": created}


def _maybe_mark_transfer(transaction_id: str, category_id: str) -> None:
    """Mark a transaction as transfer when the applied category implies it."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT name FROM category WHERE id = ?", [category_id]).fetchone()
        if not row:
            return
        name = (row[0] or '').lower()
        is_transfer = any(k in name for k in (
            'transfer', 'zelle', 'venmo', 'cash app', 'internal transfer', 'external transfer', 'personal transfers'
        ))
        if is_transfer:
            try:
                conn.execute("ALTER TABLE [transaction] ADD COLUMN IF NOT EXISTS is_transfer BOOLEAN DEFAULT FALSE")
            except Exception:
                pass
            try:
                conn.execute("UPDATE [transaction] SET is_transfer = TRUE WHERE id = ?", [transaction_id])
            except Exception:
                pass
    except Exception:
        pass

def _upsert_provider_mapping(provider: str, source_label: str, category_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "DELETE FROM ai_category_mapping WHERE provider IS ? AND source_label = ?",
            [provider, source_label]
        )
    except Exception:
        pass
    try:
        conn.execute(
            "INSERT INTO ai_category_mapping (provider, source_label, category_id) VALUES (?, ?, ?)",
            [provider, source_label, category_id]
        )
    except Exception:
        pass


@router.post("/preview-batch")
async def preview_batch_acceptance(request: BatchAcceptanceRequest):
    """Preview what would happen with batch acceptance without actually doing it"""
    
    try:
        service = get_category_acceptance_service()
        preview = service.preview_batch_acceptance(request)
        
        return {
            "preview": preview,
            "recommendations": _generate_batch_recommendations(preview)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error previewing batch: {str(e)}")


@router.post("/categorize-transactions")
async def categorize_transactions(request: TransactionCategorizeRequest):
    """Get AI categorization suggestions for multiple transactions"""
    
    try:
        conn = get_conn()
        results = {}
        
        for tx_id in request.transaction_ids:
            # Get transaction details
            tx_data = conn.execute("""
                SELECT description_norm, amount, account_id, posted_at
                FROM [transaction] 
                WHERE id = ?
            """, [tx_id]).fetchone()
            
            if not tx_data:
                results[tx_id] = {"error": "Transaction not found"}
                continue
            
            description, amount, account_id, posted_at = tx_data
            
            # Get AI suggestions
            suggestions = categorize_transaction_enhanced(description, amount)
            
            # Check current categorization
            current_category = conn.execute("""
                SELECT c.id, c.name 
                FROM transaction_category tc
                JOIN category c ON tc.category_id = c.id
                WHERE tc.tx_id = ?
            """, [tx_id]).fetchone()
            
            # Format suggestions with status
            formatted_suggestions = []
            for suggestion in suggestions:
                # Check if category exists
                existing_id = _find_category_id(suggestion.category_name)
                similar_categories = _find_similar_categories(suggestion.category_name)
                
                formatted_suggestions.append({
                    "category_name": suggestion.category_name,
                    "confidence": suggestion.confidence,
                    "reasoning": suggestion.reasoning,
                    "exists_in_db": existing_id is not None,
                    "existing_id": existing_id,
                    "similar_categories": similar_categories,
                    "can_auto_apply": suggestion.confidence >= request.confidence_threshold
                })
            
            results[tx_id] = {
                "description": description,
                "amount": amount,
                "suggestions": formatted_suggestions,
                "current_category": {
                    "id": current_category[0],
                    "name": current_category[1]
                } if current_category else None,
                "needs_categorization": current_category is None
            }
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error categorizing transactions: {str(e)}")


@router.get("/suggestions-status/{transaction_id}")
async def get_suggestions_status(transaction_id: str):
    """Get the status of AI suggestions for a specific transaction"""
    
    try:
        service = get_category_acceptance_service()
        results = service.get_category_suggestions_with_status([transaction_id])
        
        if transaction_id not in results:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return results[transaction_id]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting suggestions status: {str(e)}")


@router.post("/auto-categorize-uncategorized")
async def auto_categorize_uncategorized(
    background_tasks: BackgroundTasks,
    account_id: Optional[str] = None,
    limit: int = 50,
    confidence_threshold: float = 0.85
):
    """Auto-categorize uncategorized transactions with high confidence"""
    
    try:
        from ...ai_auto_categorization import batch_auto_categorize
        
        # Run in background for large batches
        if limit > 20:
            background_tasks.add_task(
                _background_auto_categorize, 
                account_id, limit, confidence_threshold
            )
            return {
                "status": "started",
                "message": f"Auto-categorization started for up to {limit} transactions",
                "background": True
            }
        else:
            # Run immediately for small batches
            results = await batch_auto_categorize(account_id, limit)
            return {
                "status": "completed",
                "results": results,
                "background": False
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in auto-categorization: {str(e)}")


@router.post("/categorize-all")
async def categorize_all_transactions(
    background_tasks: BackgroundTasks,
    batch_size: int = 50
):
    """Start a job to categorize ALL uncategorized transactions.

    Unlike /auto-categorize-uncategorized which can have race conditions
    when called multiple times, this endpoint:

    1. Pre-fetches all uncategorized transaction IDs upfront
    2. Creates a tracked job in ai_bulk_job table
    3. Processes all transactions sequentially (no race conditions)
    4. Provides real-time progress tracking

    Use GET /api/ai/categorization/status to monitor progress.
    Use GET /api/ai/bulk-job/{job_id} for detailed job status.
    """

    try:
        from ...ai_auto_categorization import start_categorize_all_job, process_categorization_job

        # Start the job (pre-fetches all uncategorized IDs)
        job_id, tx_ids = start_categorize_all_job(batch_size)

        if job_id is None:
            return {
                "status": "no_work",
                "message": "No uncategorized transactions to process"
            }

        if not tx_ids:
            # Job already exists and is running
            return {
                "status": "already_running",
                "job_id": job_id,
                "message": "A categorization job is already in progress"
            }

        # Start background processing
        background_tasks.add_task(
            process_categorization_job,
            job_id, tx_ids, batch_size
        )

        return {
            "status": "started",
            "job_id": job_id,
            "total_transactions": len(tx_ids),
            "batch_size": batch_size,
            "message": f"Categorization job started for {len(tx_ids)} transactions"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting categorization job: {str(e)}")


@router.get("/category-coverage")
async def get_category_coverage():
    """Get AI category coverage statistics"""
    
    try:
        from ...ai_smart_categorization import analyze_category_gaps
        conn = get_conn()
        gap_analysis = analyze_category_gaps()

        total_transactions = conn.execute("SELECT COUNT(*) FROM [transaction]").fetchone()[0]
        categorized_count = conn.execute("""
            SELECT COUNT(*)
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON t.id = tc.tx_id
            WHERE tc.tx_id IS NOT NULL
        """).fetchone()[0]
        uncategorized_count = max(0, total_transactions - categorized_count)
        coverage_percent = round((categorized_count / total_transactions) * 100, 2) if total_transactions else 0

        return {
            "total_transactions": total_transactions,
            "categorized_count": categorized_count,
            "uncategorized_count": uncategorized_count,
            "coverage_percent": coverage_percent,
            "total_ai_suggestions": gap_analysis.total_ai_suggestions,
            "available_categories": gap_analysis.available_categories,
            "success_rate": gap_analysis.success_rate,
            "missing_categories": gap_analysis.missing_categories[:20],  # Limit for API response
            "suggested_actions": gap_analysis.suggested_actions
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing coverage: {str(e)}")


# Helper functions

def _find_category_id(category_name: str) -> Optional[str]:
    """Find category ID by name"""
    conn = get_conn()
    result = conn.execute(
        "SELECT id FROM category WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))",
        [category_name]
    ).fetchone()
    return result[0] if result else None


def _find_similar_categories(category_name: str, threshold: float = 0.8) -> List[Dict]:
    """Find similar categories"""
    from difflib import SequenceMatcher
    
    conn = get_conn()
    categories = conn.execute("SELECT id, name FROM category").fetchall()
    
    similar = []
    for cat_id, cat_name in categories:
        similarity = SequenceMatcher(None, category_name.lower(), cat_name.lower()).ratio()
        if similarity >= threshold:
            similar.append({
                "id": cat_id,
                "name": cat_name,
                "similarity": similarity
            })
    
    return sorted(similar, key=lambda x: x["similarity"], reverse=True)[:5]


def _generate_batch_recommendations(preview: Dict) -> List[str]:
    """Generate recommendations based on batch preview"""
    recommendations = []
    
    if len(preview["will_create_categories"]) > 10:
        recommendations.append("Consider reviewing category names before creation - many new categories will be created")
    
    if len(preview["will_merge_similar"]) > 0:
        recommendations.append("Some categories will be merged with similar existing ones - review the merges")
    
    if len(preview["potential_issues"]) > 0:
        recommendations.append("Some transactions cannot be categorized - enable category creation or review manually")
    
    if preview["estimated_success_rate"] < 0.8:
        recommendations.append("Success rate is low - consider enabling category creation or adjusting merge threshold")
    
    if not recommendations:
        recommendations.append("Batch looks good to proceed!")
    
    return recommendations


async def _background_auto_categorize(account_id: Optional[str], limit: int, confidence_threshold: float):
    """Background task for auto-categorization"""
    try:
        from ...ai_auto_categorization import batch_auto_categorize
        results = await batch_auto_categorize(account_id, limit)
        # Could store results in a task results table or send notification
        print(f"Background auto-categorization completed: {results}")
    except Exception as e:
        print(f"Background auto-categorization failed: {e}")
