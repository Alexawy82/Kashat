"""
AI-powered transaction analysis endpoints
"""

from __future__ import annotations

import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from fastapi import Body, Query

from ...ai import get_ai_service, TransactionInsights, ping_ai, reset_ai_service
from ..auth import require_admin
from ...ai_categories import get_category_matcher, auto_create_category, SmartCategorySuggestion
from ...ai import CategorySuggestion
from ...ai_dedup import get_ai_deduplicator
from ...ai_integration import TransactionProcessor, process_transactions_batch, process_all_uncategorized_transactions, run_full_detection_workflow
from ...ai_smart_categorization import (
    analyze_category_gaps, bootstrap_missing_categories, process_ai_category_suggestion,
    get_pending_category_suggestions, approve_category_suggestion, bulk_process_ai_suggestions,
    learn_from_transaction_categorization, get_merchant_memory_statistics, extract_merchant_from_description
)
from ...db import get_conn


router = APIRouter(prefix="/ai", tags=["ai"])


class TransactionAnalysisRequest(BaseModel):
    transaction_id: str


class BulkAnalysisRequest(BaseModel):
    transaction_ids: List[str]
    force_reanalysis: bool = False


class TransactionAnalysisResponse(BaseModel):
    transaction_id: str
    merchant_name: Optional[str]
    confidence: float
    category_suggestions: List[dict]
    anomaly_flags: List[str]
    processing_method: str
    provider: Optional[str] = None
    model: Optional[str] = None
    latency_ms: Optional[int] = None


class MerchantNormalizationRequest(BaseModel):
    description: str
    amount: Optional[float] = None


@router.post("/analyze/transaction/{transaction_id}")
async def analyze_transaction(transaction_id: str) -> TransactionAnalysisResponse:
    """Analyze a single transaction with AI"""
    conn = get_conn()
    
    # Get transaction details
    row = conn.execute(
        "SELECT id, description_norm, amount FROM [transaction] WHERE id = ?",
        [transaction_id]
    ).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    tx_id, description, amount = row
    
    # Get AI service and analyze
    ai_service = get_ai_service()
    insights = await ai_service.analyze_transaction(description, float(amount))
    
    # Store results in database
    await _store_ai_results(tx_id, insights)

    # Optional: auto-apply category based on settings threshold
    try:
        from ...settings import load_settings
        s = load_settings()
        auto_apply = bool(s.get("ai_auto_categorize_on_import", False))
        min_conf = float(s.get("ai_auto_categorize_min_conf", 0.7) or 0.7)
        if auto_apply and insights.category_suggestions:
            # Map provider suggestion via ai_category_mapping first
            prov = insights.provider_name or None
            best = max(insights.category_suggestions, key=lambda x: x.confidence)
            if best.confidence >= min_conf:
                # Try mapping
                mapped_id = None
                if prov is None:
                    row_map = conn.execute(
                        "SELECT category_id FROM ai_category_mapping WHERE provider IS NULL AND source_label = ?",
                        [best.category_name],
                    ).fetchone()
                else:
                    row_map = conn.execute(
                        "SELECT category_id FROM ai_category_mapping WHERE provider = ? AND source_label = ?",
                        [prov, best.category_name],
                    ).fetchone()
                    if not row_map:
                        row_map = conn.execute(
                            "SELECT category_id FROM ai_category_mapping WHERE provider IS NULL AND source_label = ?",
                            [best.category_name],
                        ).fetchone()
                if row_map:
                    mapped_id = row_map[0]
                # Apply if we have a category id
                if mapped_id:
                    conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [tx_id])
                    conn.execute(
                        "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
                        [tx_id, mapped_id, "ai_auto"],
                    )
                    # add audit
                    import json as _json
                    from datetime import datetime as _dt, UTC as _UTC
                    import uuid as _uuid
                    conn.execute(
                        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [
                            str(_uuid.uuid4()),
                            "transaction",
                            tx_id,
                            "ai_auto_category",
                            _json.dumps({"category_id": mapped_id, "source": best.category_name, "confidence": best.confidence}),
                            _dt.now(_UTC),
                            "ai_system",
                        ],
                    )
    except Exception:
        # Don't fail analysis if auto-apply misbehaves
        pass
    
    return TransactionAnalysisResponse(
        transaction_id=tx_id,
        merchant_name=insights.merchant_info.normalized_name if insights.merchant_info else None,
        confidence=insights.confidence_score,
        category_suggestions=[
            {
                "category_name": s.category_name,
                "confidence": s.confidence,
                "reasoning": s.reasoning
            }
            for s in insights.category_suggestions
        ],
        anomaly_flags=insights.anomaly_flags,
        processing_method=insights.processing_method,
        provider=insights.provider_name,
        model=insights.model_name,
        latency_ms=insights.latency_ms,
    )


@router.post("/analyze/bulk", dependencies=[Depends(require_admin)])
async def analyze_bulk_transactions(
    request: BulkAnalysisRequest,
    background_tasks: BackgroundTasks
) -> dict:
    """Analyze multiple transactions with AI (async processing)"""
    conn = get_conn()
    
    # Validate transaction IDs
    placeholders = ",".join(["?"] * len(request.transaction_ids))
    rows = conn.execute(
        f"SELECT id, description_norm, amount FROM [transaction] WHERE id IN ({placeholders})",
        request.transaction_ids
    ).fetchall()
    
    if len(rows) != len(request.transaction_ids):
        raise HTTPException(status_code=404, detail="Some transactions not found")
    
    # Start background processing
    background_tasks.add_task(
        _process_bulk_analysis,
        rows,
        request.force_reanalysis
    )
    
    return {
        "message": "Bulk analysis started",
        "transaction_count": len(rows),
        "status": "processing"
    }


@router.post("/normalize/merchant")
async def normalize_merchant(request: MerchantNormalizationRequest) -> dict:
    """Normalize a merchant name from transaction description"""
    ai_service = get_ai_service()
    
    # Use a default amount if not provided
    amount = request.amount or 0.0
    
    insights = await ai_service.analyze_transaction(request.description, amount)
    
    if insights.merchant_info:
        return {
            "original_description": request.description,
            "normalized_name": insights.merchant_info.normalized_name,
            "confidence": insights.merchant_info.confidence,
            "merchant_type": insights.merchant_info.merchant_type,
            "processing_method": insights.processing_method
        }
    else:
        return {
            "original_description": request.description,
            "normalized_name": request.description,
            "confidence": 0.0,
            "merchant_type": None,
            "processing_method": "fallback"
        }


@router.get("/suggestions/categories/{transaction_id}")
async def get_category_suggestions(transaction_id: str) -> dict:
    """Get AI-powered category suggestions for a transaction"""
    conn = get_conn()
    
    # Get transaction details
    row = conn.execute(
        "SELECT id, description_norm, amount FROM [transaction] WHERE id = ?",
        [transaction_id]
    ).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    tx_id, description, amount = row
    
    # Get AI service and analyze
    ai_service = get_ai_service()
    insights = await ai_service.analyze_transaction(description, float(amount))
    
    # Get actual categories from database for matching
    categories = conn.execute("SELECT id, name FROM category").fetchall()
    category_map = {cat[1].lower(): cat[0] for cat in categories}
    
    # Match AI suggestions to actual categories
    matched_suggestions = []
    for suggestion in insights.category_suggestions:
        category_id = category_map.get(suggestion.category_name.lower())
        matched_suggestions.append({
            "category_id": category_id,
            "category_name": suggestion.category_name,
            "confidence": suggestion.confidence,
            "reasoning": suggestion.reasoning,
            "matched_existing": category_id is not None
        })
    
    return {
        "transaction_id": tx_id,
        "suggestions": matched_suggestions,
        "merchant_info": {
            "normalized_name": insights.merchant_info.normalized_name if insights.merchant_info else None,
            "confidence": insights.merchant_info.confidence if insights.merchant_info else 0.0
        }
    }


class OptOutSuggestionRequest(BaseModel):
    merchant: str
    category_name: str


@router.post("/suggestions/opt-out")
async def opt_out_suggestion(request: OptOutSuggestionRequest) -> dict:
    """Opt out of AI suggestions for a specific merchant-category combination"""
    if not request.merchant or not request.category_name:
        raise HTTPException(status_code=400, detail="merchant and category_name required")

    conn = get_conn()
    from datetime import datetime, UTC

    # Insert or ignore if already exists (primary key constraint)
    try:
        conn.execute(
            """
            INSERT INTO ai_suggestion_opt_out (merchant, category_name, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT DO NOTHING
            """,
            [request.merchant, request.category_name, datetime.now(UTC)]
        )
    except Exception:
        # Fallback for databases without ON CONFLICT
        existing = conn.execute(
            "SELECT 1 FROM ai_suggestion_opt_out WHERE merchant = ? AND category_name = ?",
            [request.merchant, request.category_name]
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO ai_suggestion_opt_out (merchant, category_name, created_at) VALUES (?, ?, ?)",
                [request.merchant, request.category_name, datetime.now(UTC)]
            )

    return {
        "success": True,
        "merchant": request.merchant,
        "category_name": request.category_name,
        "message": f"Opted out of '{request.category_name}' suggestions for merchant '{request.merchant}'"
    }


@router.get("/stats")
async def get_ai_stats() -> dict:
    """Get AI processing statistics"""
    conn = get_conn()
    
    # Count AI-enhanced transactions
    enhanced_count = conn.execute(
        "SELECT COUNT(*) FROM [transaction] WHERE ai_merchant_name IS NOT NULL"
    ).fetchone()[0]
    
    # Total transactions
    total_count = conn.execute("SELECT COUNT(*) FROM [transaction]").fetchone()[0]
    
    # Recent processing stats
    recent_stats = conn.execute("""
        SELECT 
            COUNT(*) as processed_today,
            AVG(ai_confidence_score) as avg_confidence
        FROM [transaction] 
        WHERE ai_processed_at >= date('now', '-1 day')
        AND ai_confidence_score IS NOT NULL
    """).fetchone()
    
    return {
        "total_transactions": total_count,
        "ai_enhanced_transactions": enhanced_count,
        "enhancement_percentage": round((enhanced_count / max(total_count, 1)) * 100, 2),
        "processed_today": recent_stats[0] if recent_stats else 0,
        "average_confidence": round(recent_stats[1] or 0.0, 3),
        "ai_service_status": "active"
    }


async def _store_ai_results(transaction_id: str, insights: TransactionInsights):
    """Store AI analysis results in the database"""
    conn = get_conn()
    
    # Update transaction with AI insights
    updates = []
    params = []
    
    if insights.merchant_info:
        updates.append("ai_merchant_name = ?")
        params.append(insights.merchant_info.normalized_name)
    
    if insights.category_suggestions:
        # Store top suggestion as JSON with category_id mapping
        import json
        
        # Get existing categories to map AI suggestions
        categories = conn.execute("SELECT id, name FROM category").fetchall()
        category_map = {cat[1].lower(): cat[0] for cat in categories}
        
        suggestions_json = json.dumps([
            {
                "category_name": s.category_name,
                "category_id": category_map.get(s.category_name.lower()),
                "confidence": s.confidence,
                "reasoning": s.reasoning
            }
            for s in insights.category_suggestions[:3]  # Store top 3
        ])
        updates.append("ai_category_suggestions = ?")
        params.append(suggestions_json)
    
    updates.extend([
        "ai_confidence_score = ?",
        "ai_processed_at = CURRENT_TIMESTAMP",
        "ai_provider = ?",
        "ai_model = ?",
        "ai_latency_ms = ?",
    ])
    params.extend([
        insights.confidence_score,
        insights.provider_name,
        insights.model_name,
        insights.latency_ms or 0,
    ])
    
    if updates:
        params.append(transaction_id)
        update_sql = f"UPDATE [transaction] SET {', '.join(updates)} WHERE id = ?"
        conn.execute(update_sql, params)


async def _process_bulk_analysis(transaction_data: List[tuple], force_reanalysis: bool = False):
    """Background task for bulk transaction analysis"""
    ai_service = get_ai_service()
    
    # Prepare batch data
    batch_data = [(row[1], float(row[2])) for row in transaction_data]  # description, amount
    
    try:
        # Process in batches
        import os
        batch_size = int(os.getenv('LEDGERLOOP_AI_BATCH_SIZE', '50'))
        
        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i:i + batch_size]
            batch_ids = [row[0] for row in transaction_data[i:i + batch_size]]
            
            # Analyze batch
            import time as _time
            t0 = _time.perf_counter()
            results = await ai_service.batch_analyze_transactions(batch)
            t1 = _time.perf_counter()

            # Store results
            for tx_id, insights in zip(batch_ids, results):
                await _store_ai_results(tx_id, insights)
            
            # Dynamic backoff based on observed latency and batch size
            avg_latency_ms = 0.0
            try:
                latencies = [r.latency_ms for r in results if getattr(r, 'latency_ms', None)]
                if latencies:
                    avg_latency_ms = sum(latencies) / max(1, len(latencies))
                else:
                    avg_latency_ms = (t1 - t0) * 1000.0 / max(1, len(results))
            except Exception:
                avg_latency_ms = 600.0
            sleep_s = 0.2
            if avg_latency_ms > 800:
                sleep_s = 1.5
            elif avg_latency_ms > 400:
                sleep_s = 0.6
            await asyncio.sleep(sleep_s)
    
    except Exception as e:
        # Log error (in production, use proper logging)
        print(f"Bulk analysis error: {e}")


async def _process_bulk_enhancement_with_tracking(job_id: str, transaction_data: List[tuple]):
    """Background task for bulk transaction enhancement with progress tracking"""
    from ...settings import load_settings
    conn = get_conn()
    ai_service = get_ai_service()

    try:
        # Check if processing is paused before starting
        settings = load_settings()
        if settings.get("ai_processing_paused", False):
            conn.execute("UPDATE ai_bulk_job SET status = 'paused' WHERE id = ?", [job_id])
            return

        # Prepare batch data
        batch_data = [(row[1], float(row[2])) for row in transaction_data]  # description, amount
        total_transactions = len(transaction_data)
        processed_count = 0
        enhanced_count = 0

        # Get batch settings from config (with fallback to env var for backwards compat)
        import os
        batch_size = settings.get("ai_batch_size") or int(os.getenv('LEDGERLOOP_AI_BATCH_SIZE', '20'))
        batch_delay_ms = settings.get("ai_batch_delay_ms", 500)

        for i in range(0, len(batch_data), batch_size):
            # Reload settings each batch to respect runtime changes
            settings = load_settings()

            # Check for pause state
            if settings.get("ai_processing_paused", False):
                conn.execute("UPDATE ai_bulk_job SET status = 'paused' WHERE id = ?", [job_id])
                break

            # Check for cancellation
            status_row = conn.execute("SELECT status FROM ai_bulk_job WHERE id = ?", [job_id]).fetchone()
            if not status_row or status_row[0] not in ('processing',):
                break

            batch = batch_data[i:i + batch_size]
            batch_ids = [row[0] for row in transaction_data[i:i + batch_size]]

            # Analyze batch
            results = await ai_service.batch_analyze_transactions(batch)

            # Store results and count enhancements
            for tx_id, insights in zip(batch_ids, results):
                await _store_ai_results(tx_id, insights)
                processed_count += 1

                # Count as enhanced if we got meaningful results
                if insights.merchant_info or insights.category_suggestions:
                    enhanced_count += 1

            # Update progress
            conn.execute("""
                UPDATE ai_bulk_job
                SET processed_transactions = ?, enhanced_transactions = ?
                WHERE id = ?
            """, [processed_count, enhanced_count, job_id])

            # Use configurable delay to prevent overwhelming the system
            await asyncio.sleep(batch_delay_ms / 1000.0)
        
        # Mark as completed
        from datetime import datetime, UTC
        conn.execute("""
            UPDATE ai_bulk_job
            SET status = 'completed', completed_at = ?,
                processed_transactions = ?, enhanced_transactions = ?
            WHERE id = ?
        """, [datetime.now(UTC), processed_count, enhanced_count, job_id])

    except Exception as e:
        # Mark as failed
        from datetime import datetime, UTC
        conn.execute("""
            UPDATE ai_bulk_job
            SET status = 'failed', completed_at = ?, error_message = ?
            WHERE id = ?
        """, [datetime.now(UTC), str(e), job_id])
        print(f"Bulk enhancement error for job {job_id}: {e}")


@router.get("/suggestions/smart-categories/{transaction_id}")
async def get_smart_category_suggestions(transaction_id: str) -> dict:
    """Get enhanced category suggestions with database integration"""
    conn = get_conn()
    
    # Get transaction details
    row = conn.execute(
        "SELECT id, description_norm, amount, ai_merchant_name FROM [transaction] WHERE id = ?",
        [transaction_id]
    ).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    tx_id, description, amount, ai_merchant_name = row
    
    # Use AI merchant name if available, otherwise use description
    merchant_name = ai_merchant_name or description
    
    # Provider-driven AI suggestions mapped to existing categories
    ai_service = get_ai_service()
    insights = await ai_service.analyze_transaction(description, float(amount))
    ai_suggestions: list[CategorySuggestion] = insights.category_suggestions
    # Filter opt-outs
    try:
        opt_rows = conn.execute("SELECT category_name FROM ai_suggestion_opt_out WHERE merchant = ?", [merchant_name or ""]).fetchall()
        blocked = {r[0].lower() for r in opt_rows}
        if blocked:
            ai_suggestions = [s for s in ai_suggestions if (s.category_name or '').lower() not in blocked]
    except Exception:
        pass

    category_matcher = get_category_matcher()
    # Apply category mapping first (provider-specific, then global)
    conn = get_conn()
    mapped = []
    for s in ai_suggestions:
        src = s.category_name
        prov = insights.provider_name or None
        # DuckDB doesn't support parameterizing NULL with "IS ?". Do explicit branches.
        if prov is None:
            row = conn.execute(
                "SELECT category_id FROM ai_category_mapping WHERE provider IS NULL AND source_label = ?",
                [src],
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT category_id FROM ai_category_mapping WHERE provider = ? AND source_label = ?",
                [prov, src],
            ).fetchone()
            # Fallback to global mapping if no provider-specific mapping found
            if not row:
                row = conn.execute(
                    "SELECT category_id FROM ai_category_mapping WHERE provider IS NULL AND source_label = ?",
                    [src],
                ).fetchone()
        if row:
            cat_id = row[0]
            name_row = conn.execute("SELECT name FROM category WHERE id = ?", [cat_id]).fetchone()
            if name_row:
                mapped.append(SmartCategorySuggestion(
                    category_id=cat_id,
                    category_name=name_row[0],
                    confidence=s.confidence,
                    reasoning=f"Mapped from provider label '{src}'",
                    match_type='mapped',
                ))

    exact_matches = category_matcher.find_exact_matches(ai_suggestions)
    fuzzy_matches = category_matcher.find_fuzzy_matches(ai_suggestions)
    parent_matches = category_matcher.find_parent_category_matches(ai_suggestions)

    # Build SmartCategorySuggestion-like list
    suggestions: list[SmartCategorySuggestion] = []
    used_ids: set[str] = set()
    for m in mapped + exact_matches + fuzzy_matches:
        if m.category_id not in used_ids:
            suggestions.append(SmartCategorySuggestion(
                category_id=m.category_id,
                category_name=m.category_name,
                confidence=m.confidence,
                reasoning=m.reasoning,
                match_type=m.match_type
            ))
            used_ids.add(m.category_id)
    # New category proposals if none matched with high confidence
    for s in ai_suggestions:
        already = any(s.category_name.lower() in sg.category_name.lower() for sg in suggestions)
        if not already and s.confidence > 0.7:
            parent_id = None
            for pm in parent_matches:
                if s.category_name.lower() in pm.reasoning.lower():
                    parent_id = pm.category_id
                    break
            suggestions.append(SmartCategorySuggestion(
                category_id=None,
                category_name=s.category_name,
                confidence=s.confidence,
                reasoning=f"AI suggested new category: {s.reasoning}",
                match_type='ai_suggested',
                is_new_category=True,
                parent_category_id=parent_id,
                auto_create_confidence=s.confidence
            ))
    
    # Get transaction patterns analysis
    patterns = category_matcher.analyze_transaction_patterns(merchant_name, float(amount))
    
    return {
        "transaction_id": tx_id,
        "merchant_name": merchant_name,
        "suggestions": [
            {
                "category_id": s.category_id,
                "category_name": s.category_name,
                "confidence": s.confidence,
                "reasoning": s.reasoning,
                "match_type": s.match_type,
                "is_new_category": s.is_new_category,
                "parent_category_id": s.parent_category_id,
                "auto_create_confidence": s.auto_create_confidence
            }
            for s in suggestions
        ],
        "patterns": patterns
    }


class AutoCreateCategoryRequest(BaseModel):
    category_name: str
    parent_id: Optional[str] = None
    force_create: bool = False


@router.post("/categories/auto-create")
async def auto_create_category_endpoint(
    request: Optional[AutoCreateCategoryRequest] = None,
    category_name: Optional[str] = None,
    parent_id: Optional[str] = None,
    force_create: Optional[bool] = None,
) -> dict:
    """Auto-create a new category with AI validation.

    Accepts either JSON body (preferred) or query parameters for backward compatibility.
    """
    # Merge inputs (body takes precedence if provided)
    name = (request.category_name if request else None) or category_name
    parent = (request.parent_id if request else None) if parent_id is None else parent_id
    force = (request.force_create if request else False) if force_create is None else bool(force_create)

    if not name or not name.strip():
        raise HTTPException(status_code=422, detail="category_name is required")

    if not force:
        # Basic validation — expand as needed
        if len(name.strip()) < 3:
            raise HTTPException(status_code=400, detail="Category name too short")

    try:
        category_id = await auto_create_category(name.strip(), parent)

        if category_id:
            return {
                "category_id": category_id,
                "category_name": name.strip(),
                "parent_id": parent,
                "created": True,
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to create category")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating category: {str(e)}")


class ApplyCategoryRequest(BaseModel):
    transaction_id: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    parent_id: Optional[str] = None
    auto_create: bool = False


@router.post("/suggestions/apply-smart-category")
async def apply_smart_category_suggestion(request: ApplyCategoryRequest) -> dict:
    """Apply a smart category suggestion to a transaction"""
    conn = get_conn()
    
    # Verify transaction exists
    tx_exists = conn.execute("SELECT 1 FROM [transaction] WHERE id = ?", [request.transaction_id]).fetchone()
    if not tx_exists:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Handle category creation if needed
    final_category_id = request.category_id
    
    if not final_category_id and request.category_name and request.auto_create:
        # Create new category
        final_category_id = await auto_create_category(request.category_name, request.parent_id)
        if not final_category_id:
            raise HTTPException(status_code=400, detail="Failed to create category")
    
    if not final_category_id:
        raise HTTPException(status_code=400, detail="No valid category provided")
    
    # Verify category exists
    cat_exists = conn.execute("SELECT name FROM category WHERE id = ?", [final_category_id]).fetchone()
    if not cat_exists:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Apply category to transaction
    conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [request.transaction_id])
    conn.execute(
        "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
        [request.transaction_id, final_category_id, "ai_suggestion"]
    )
    
    # Log the action
    import json
    import uuid
    from datetime import datetime, UTC

    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            str(uuid.uuid4()),
            "transaction",
            request.transaction_id,
            "ai_category_applied",
            json.dumps({
                "category_id": final_category_id,
                "category_name": cat_exists[0],
                "auto_created": request.auto_create and (request.category_id is None)
            }),
            datetime.now(UTC),
            "ai_system"
        ]
    )
    # Merchant learning and transfer marking
    try:
        await learn_from_transaction_categorization(request.transaction_id, final_category_id)
    except Exception:
        pass
    try:
        _maybe_mark_transfer(request.transaction_id, final_category_id)
    except Exception:
        pass

    return {
        "transaction_id": request.transaction_id,
        "category_id": final_category_id,
        "category_name": cat_exists[0],
        "auto_created": request.auto_create and (request.category_id is None),
        "applied": True
    }


@router.get("/categories/usage-stats")
async def get_category_usage_stats() -> dict:
    """Get category usage statistics for better AI suggestions"""
    category_matcher = get_category_matcher()
    stats = category_matcher.get_category_usage_stats()
    
    return {
        "category_stats": stats,
        "total_categories": len(stats),
        "most_used": sorted(
            [(cat_id, info) for cat_id, info in stats.items()],
            key=lambda x: x[1]["usage_count"],
            reverse=True
        )[:10]
    }


@router.post("/enhance/uncategorized", dependencies=[Depends(require_admin)])
async def enhance_uncategorized_transactions(background_tasks: BackgroundTasks, limit: int = 200, batch_size: int = 10, force: bool = False) -> dict:
    """Enhance all uncategorized transactions with AI.

    Args:
        limit: Max transactions to process
        batch_size: Batch size for AI calls
        force: If True, reprocess even if already processed with high confidence
    """
    conn = get_conn()

    # Get uncategorized transactions
    # Cap limits to reasonable bounds
    limit = max(10, min(int(limit), 1000))

    if force:
        # Force mode: process all uncategorized regardless of AI status
        rows = conn.execute("""
            SELECT t.id, t.description_norm, t.amount
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON t.id = tc.tx_id
            WHERE tc.tx_id IS NULL
            LIMIT ?
        """, [limit]).fetchall()
    else:
        # Normal mode: only unprocessed or low confidence
        rows = conn.execute("""
            SELECT t.id, t.description_norm, t.amount
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON t.id = tc.tx_id
            WHERE tc.tx_id IS NULL
            AND (t.ai_processed_at IS NULL OR t.ai_confidence_score < 0.5)
            LIMIT ?
        """, [limit]).fetchall()
    
    if not rows:
        return {
            "message": "No uncategorized transactions to process",
            "transaction_count": 0
        }
    
    # Create a bulk processing job
    import uuid
    from datetime import datetime, UTC

    job_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO ai_bulk_job (id, job_type, total_transactions, status, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, [job_id, "enhance_uncategorized", len(rows), "processing", datetime.now(UTC)])
    
    # Start background processing
    # Export batch size via env for the worker
    import os
    os.environ['LEDGERLOOP_AI_BATCH_SIZE'] = str(int(batch_size))
    background_tasks.add_task(_process_bulk_enhancement_with_tracking, job_id, rows)
    
    return {
        "job_id": job_id,
        "message": "Started AI enhancement of uncategorized transactions",
        "transaction_count": len(rows),
        "status": "processing"
    }


@router.get("/bulk-job/{job_id}")
async def get_bulk_job_status(job_id: str) -> dict:
    """Get status of a bulk AI processing job"""
    conn = get_conn()
    
    job = conn.execute("""
        SELECT id, job_type, total_transactions, processed_transactions, 
               enhanced_transactions, status, created_at, completed_at, error_message
        FROM ai_bulk_job 
        WHERE id = ?
    """, [job_id]).fetchone()
    
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    
    total = job[2] or 0
    processed = job[3] or 0
    progress_percentage = (processed / total * 100) if total else 0.0
    
    return {
        "job_id": job[0],
        "job_type": job[1],
        "total_transactions": total,
        "processed_transactions": processed,
        "enhanced_transactions": job[4] or 0,
        "status": job[5],
        "progress_percentage": round(progress_percentage, 1),
        "created_at": job[6],
        "completed_at": job[7],
        "error_message": job[8]
    }


@router.post("/bulk-job/{job_id}/cancel", dependencies=[Depends(require_admin)])
async def cancel_bulk_job(job_id: str) -> dict:
    """Cancel a running AI bulk job (best-effort)."""
    conn = get_conn()
    job = conn.execute("SELECT status FROM ai_bulk_job WHERE id = ?", [job_id]).fetchone()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job[0] != 'processing':
        return {"job_id": job_id, "status": job[0], "message": "Job not processing"}
    from datetime import datetime, UTC
    conn.execute("UPDATE ai_bulk_job SET status = 'cancelled', completed_at = ? WHERE id = ?", [datetime.now(UTC), job_id])
    return {"job_id": job_id, "status": "cancelled"}


@router.post("/bulk-job/{job_id}/retry", dependencies=[Depends(require_admin)])
async def retry_bulk_job(job_id: str, background_tasks: BackgroundTasks) -> dict:
    """Retry a completed/failed AI bulk job by creating a new job with the same type.
    Currently supports 'enhance_uncategorized'.
    """
    conn = get_conn()
    job = conn.execute("SELECT job_type FROM ai_bulk_job WHERE id = ?", [job_id]).fetchone()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_type = job[0]
    if job_type != 'enhance_uncategorized':
        raise HTTPException(status_code=400, detail=f"Retry not supported for job type: {job_type}")

    # Recompute uncategorized set
    rows = conn.execute("""
        SELECT t.id, t.description_norm, t.amount
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        WHERE tc.tx_id IS NULL
        AND (t.ai_processed_at IS NULL OR t.ai_confidence_score < 0.5)
        LIMIT 1000
    """).fetchall()
    if not rows:
        return {"message": "No uncategorized transactions to process", "transaction_count": 0}

    import uuid
    from datetime import datetime, UTC
    new_job_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO ai_bulk_job (id, job_type, total_transactions, status, created_at) VALUES (?, ?, ?, 'processing', ?)",
        [new_job_id, job_type, len(rows), datetime.now(UTC)],
    )
    background_tasks.add_task(_process_bulk_enhancement_with_tracking, new_job_id, rows)
    return {"job_id": new_job_id, "status": "processing", "transaction_count": len(rows)}


@router.get("/bulk-jobs")
async def list_bulk_jobs(limit: int = 20) -> dict:
    """List recent bulk AI processing jobs"""
    conn = get_conn()
    
    jobs = conn.execute("""
        SELECT id, job_type, total_transactions, processed_transactions, 
               enhanced_transactions, status, created_at, completed_at
        FROM ai_bulk_job 
        ORDER BY created_at DESC
        LIMIT ?
    """, [limit]).fetchall()
    
    return {
        "jobs": [
            {
                "job_id": job[0],
                "job_type": job[1],
                "total_transactions": job[2],
                "processed_transactions": job[3] or 0,
                "enhanced_transactions": job[4] or 0,
                "status": job[5],
                "created_at": job[6],
                "completed_at": job[7],
                "progress_percentage": round((job[3] or 0) / max(job[2], 1) * 100, 1)
            }
            for job in jobs
        ]
    }


# ============== AI Queue Control Endpoints ==============

@router.get("/queue/stats")
async def get_queue_stats() -> dict:
    """Get AI processing queue statistics"""
    from ...settings import load_settings
    conn = get_conn()

    # Get counts by status from last 24 hours
    stats = conn.execute("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'processing') as active,
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            COUNT(*) FILTER (WHERE status = 'paused') as paused,
            COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled
        FROM ai_bulk_job
        WHERE created_at > (datetime('now', '-24 hours'))
    """).fetchone()

    settings = load_settings()

    return {
        "active": stats[0] or 0,
        "pending": stats[1] or 0,
        "completed": stats[2] or 0,
        "failed": stats[3] or 0,
        "paused": stats[4] or 0,
        "cancelled": stats[5] or 0,
        "is_paused": settings.get("ai_processing_paused", False),
        "batch_size": settings.get("ai_batch_size", 20),
        "batch_delay_ms": settings.get("ai_batch_delay_ms", 500),
        "auto_start_on_import": settings.get("ai_auto_start_on_import", True)
    }


@router.post("/queue/pause", dependencies=[Depends(require_admin)])
async def pause_all_jobs() -> dict:
    """Pause all AI processing - stops new jobs and pauses running ones"""
    from ...settings import load_settings, save_settings
    from datetime import datetime, UTC

    conn = get_conn()

    # Set global pause flag
    settings = load_settings()
    settings["ai_processing_paused"] = True
    save_settings(settings)

    # Count processing jobs first, then pause them
    count_result = conn.execute(
        "SELECT COUNT(*) FROM ai_bulk_job WHERE status = 'processing'"
    ).fetchone()
    jobs_to_pause = count_result[0] if count_result else 0

    # Mark all processing jobs as paused
    if jobs_to_pause > 0:
        conn.execute(
            "UPDATE ai_bulk_job SET status = 'paused' WHERE status = 'processing'"
        )

    return {
        "paused": True,
        "jobs_paused": jobs_to_pause,
        "message": f"AI processing paused. {jobs_to_pause} jobs paused."
    }


@router.post("/queue/resume", dependencies=[Depends(require_admin)])
async def resume_all_jobs() -> dict:
    """Resume AI processing - allows new jobs to start"""
    from ...settings import load_settings, save_settings

    # Clear global pause flag
    settings = load_settings()
    settings["ai_processing_paused"] = False
    save_settings(settings)

    return {
        "resumed": True,
        "message": "AI processing resumed. New jobs can now start."
    }


@router.post("/queue/settings", dependencies=[Depends(require_admin)])
async def update_queue_settings(
    batch_size: Optional[int] = Body(None, ge=5, le=100),
    batch_delay_ms: Optional[int] = Body(None, ge=0, le=5000),
    auto_start_on_import: Optional[bool] = Body(None),
    max_concurrent_jobs: Optional[int] = Body(None, ge=1, le=5),
    job_timeout_minutes: Optional[int] = Body(None, ge=1, le=120)
) -> dict:
    """Update AI processing queue settings"""
    from ...settings import load_settings, save_settings

    settings = load_settings()
    updates = {}

    if batch_size is not None:
        settings["ai_batch_size"] = batch_size
        updates["ai_batch_size"] = batch_size
    if batch_delay_ms is not None:
        settings["ai_batch_delay_ms"] = batch_delay_ms
        updates["ai_batch_delay_ms"] = batch_delay_ms
    if auto_start_on_import is not None:
        settings["ai_auto_start_on_import"] = auto_start_on_import
        updates["ai_auto_start_on_import"] = auto_start_on_import
    if max_concurrent_jobs is not None:
        settings["ai_max_concurrent_jobs"] = max_concurrent_jobs
        updates["ai_max_concurrent_jobs"] = max_concurrent_jobs
    if job_timeout_minutes is not None:
        settings["ai_job_timeout_minutes"] = job_timeout_minutes
        updates["ai_job_timeout_minutes"] = job_timeout_minutes

    if updates:
        save_settings(settings)

    return {
        "updated": True,
        "changes": updates,
        "current_settings": {
            "ai_batch_size": settings.get("ai_batch_size", 20),
            "ai_batch_delay_ms": settings.get("ai_batch_delay_ms", 500),
            "ai_auto_start_on_import": settings.get("ai_auto_start_on_import", True),
            "ai_max_concurrent_jobs": settings.get("ai_max_concurrent_jobs", 2),
            "ai_job_timeout_minutes": settings.get("ai_job_timeout_minutes", 30),
            "ai_processing_paused": settings.get("ai_processing_paused", False)
        }
    }


@router.get("/duplicates/detect")
async def detect_duplicate_transactions(
    account_id: Optional[str] = None,
    days_window: int = 30,
    min_confidence: float = 0.7
) -> dict:
    """Detect potential duplicate transactions using AI similarity"""
    deduplicator = get_ai_deduplicator()
    
    candidates = deduplicator.find_potential_duplicates(
        account_id=account_id,
        days_window=days_window,
        min_confidence=min_confidence
    )
    
    # Get transaction details for the candidates
    conn = get_conn()
    enriched_candidates = []
    
    for candidate in candidates:
        # Get transaction details
        tx1 = conn.execute("""
            SELECT id, description_norm, amount, posted_at, ai_merchant_name
            FROM [transaction] WHERE id = ?
        """, [candidate.transaction_id_1]).fetchone()
        
        tx2 = conn.execute("""
            SELECT id, description_norm, amount, posted_at, ai_merchant_name  
            FROM [transaction] WHERE id = ?
        """, [candidate.transaction_id_2]).fetchone()
        
        if tx1 and tx2:
            enriched_candidates.append({
                "candidate": {
                    "similarity_score": round(candidate.similarity_score, 3),
                    "confidence": round(candidate.confidence, 3),
                    "recommendation": candidate.recommendation,
                    "matching_factors": candidate.matching_factors
                },
                "transaction_1": {
                    "id": tx1[0],
                    "description": tx1[1],
                    "amount": tx1[2],
                    "posted_at": tx1[3],
                    "ai_merchant_name": tx1[4]
                },
                "transaction_2": {
                    "id": tx2[0], 
                    "description": tx2[1],
                    "amount": tx2[2],
                    "posted_at": tx2[3],
                    "ai_merchant_name": tx2[4]
                }
            })
    
    return {
        "duplicate_candidates": enriched_candidates,
        "total_found": len(enriched_candidates),
        "high_confidence_count": len([c for c in candidates if c.confidence > 0.9]),
        "parameters": {
            "account_id": account_id,
            "days_window": days_window,
            "min_confidence": min_confidence
        }
    }


class MergeDuplicatesRequest(BaseModel):
    keep_transaction_id: str
    remove_transaction_id: str
    user_confirmed: bool = False


@router.post("/duplicates/merge")
async def merge_duplicate_transactions(request: MergeDuplicatesRequest) -> dict:
    """Merge two duplicate transactions"""
    deduplicator = get_ai_deduplicator()
    
    try:
        result = await deduplicator.merge_duplicate_transactions(
            keep_id=request.keep_transaction_id,
            remove_id=request.remove_transaction_id,
            user_confirmed=request.user_confirmed
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error merging transactions: {str(e)}")


@router.get("/duplicates/stats")
async def get_duplicate_detection_stats() -> dict:
    """Get statistics about duplicate detection"""
    conn = get_conn()

    # Count potential duplicates in recent transactions
    try:
        recent_duplicates_count = len(get_ai_deduplicator().find_potential_duplicates(
            days_window=30,
            min_confidence=0.7
        ))
    except Exception:
        recent_duplicates_count = 0

    # Count merge operations from audit log
    try:
        merge_operations = conn.execute("""
            SELECT COUNT(*) FROM event_log
            WHERE action = 'merge_duplicate'
            AND ts >= datetime('now', '-30 days')
        """).fetchone()[0]
    except Exception:
        # Table may not exist or have different schema
        merge_operations = 0

    # Get total transaction count for context
    total_transactions = conn.execute("SELECT COUNT(*) FROM [transaction]").fetchone()[0]

    return {
        "potential_duplicates_found": recent_duplicates_count,
        "merge_operations_last_30_days": merge_operations,
        "total_transactions": total_transactions,
        "duplicate_rate_percentage": round((recent_duplicates_count / max(total_transactions, 1)) * 100, 2)
    }
@router.get("/ping")
async def ai_ping() -> dict:
    """Test connectivity to the configured AI provider(s)."""
    return await ping_ai()


@router.get("/status")
async def ai_status() -> dict:
    """Get AI provider status (alias for /ping with additional info)."""
    ping_result = await ping_ai()
    # Add additional status info
    from ...settings import load_settings
    s = load_settings()
    return {
        **ping_result,
        "settings": {
            "ai_auto_categorize_on_import": s.get("ai_auto_categorize_on_import", True),
            "ai_auto_categorize_min_conf": s.get("ai_auto_categorize_min_conf", 0.7),
        }
    }


@router.get("/categorization/status")
async def get_categorization_status() -> dict:
    """Get real-time status of AI auto-categorization.

    Returns:
    - Overall categorization stats (total, categorized, uncategorized, percent)
    - Current job status (if any job is running)
    - Progress tracking for active jobs
    """
    conn = get_conn()

    # Get overall transaction stats
    total = conn.execute("SELECT COUNT(*) FROM [transaction]").fetchone()[0]
    categorized = conn.execute("""
        SELECT COUNT(DISTINCT tx_id) FROM transaction_category
    """).fetchone()[0]
    uncategorized = total - categorized

    # Get the most recent categorization job
    job = conn.execute("""
        SELECT id, total_transactions, processed_transactions, enhanced_transactions,
               status, created_at, completed_at, error_message
        FROM ai_bulk_job
        WHERE job_type = 'auto_categorize_all'
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()

    # Build response
    response = {
        "overall": {
            "total_transactions": total,
            "categorized": categorized,
            "uncategorized": uncategorized,
            "percent_complete": round(categorized / total * 100, 1) if total > 0 else 0
        },
        "current_job": None
    }

    if job:
        job_total = job[1] or 0
        job_processed = job[2] or 0
        job_categorized = job[3] or 0
        progress_pct = round(job_processed / job_total * 100, 1) if job_total > 0 else 0

        response["current_job"] = {
            "job_id": job[0],
            "total": job_total,
            "processed": job_processed,
            "categorized": job_categorized,
            "status": job[4],
            "progress_percent": progress_pct,
            "created_at": job[5],
            "completed_at": job[6],
            "error_message": job[7]
        }

    return response


@router.post("/reset")
async def ai_reset() -> dict:
    """Reset the AI service (reloads provider settings without process restart)."""
    reset_ai_service()
    # Warm it up by accessing once
    _ = get_ai_service()
    return {"status": "reset"}


# ========================================
# NEW INTEGRATED AI + DETECTION ENDPOINTS
# ========================================

class IntegratedProcessRequest(BaseModel):
    transaction_ids: Optional[List[str]] = None
    force_reprocess: bool = False


@router.post("/process/integrated")
async def process_transactions_integrated(request: IntegratedProcessRequest = IntegratedProcessRequest()) -> dict:
    """Process transactions with integrated AI categorization + detection markers"""
    if request.transaction_ids:
        # Process specific transactions
        result = await process_transactions_batch(request.transaction_ids, request.force_reprocess)
    else:
        # Process all uncategorized transactions
        result = await process_all_uncategorized_transactions()
    
    return result


@router.post("/process/transaction/{transaction_id}")
async def process_single_transaction_integrated(transaction_id: str, force_reprocess: bool = False) -> dict:
    """Process a single transaction with integrated AI + detection"""
    processor = TransactionProcessor()
    result = await processor.process_transaction(transaction_id, force_reprocess)
    return result


@router.post("/workflow/full-detection", dependencies=[Depends(require_admin)])
async def run_full_detection_workflow_endpoint() -> dict:
    """Run the complete AI + detection workflow"""
    result = await run_full_detection_workflow()
    return result


@router.get("/detection/summary")
async def get_detection_summary() -> dict:
    """Get summary of detection markers across all transactions"""
    conn = get_conn()
    
    # Count transactions by detection type
    income_count = conn.execute("SELECT COUNT(*) FROM [transaction] WHERE is_income = TRUE").fetchone()[0]
    adjustment_count = conn.execute("SELECT COUNT(*) FROM [transaction] WHERE is_adjustment = TRUE").fetchone()[0]
    
    # Try to get transfer count (column may not exist yet)
    try:
        transfer_count = conn.execute("SELECT COUNT(*) FROM [transaction] WHERE is_transfer = TRUE").fetchone()[0]
    except:
        transfer_count = 0
    
    # Count Zelle transactions
    zelle_count = conn.execute("SELECT COUNT(*) FROM [transaction] WHERE zelle_direction IS NOT NULL").fetchone()[0]
    
    # Get recent AI processing stats
    ai_processed_count = conn.execute("SELECT COUNT(*) FROM [transaction] WHERE ai_processed_at IS NOT NULL").fetchone()[0]
    total_count = conn.execute("SELECT COUNT(*) FROM [transaction]").fetchone()[0]
    
    return {
        "detection_summary": {
            "income_transactions": income_count,
            "transfer_transactions": transfer_count,
            "adjustment_transactions": adjustment_count,
            "zelle_transactions": zelle_count
        },
        "ai_processing": {
            "ai_processed": ai_processed_count,
            "total_transactions": total_count,
            "processing_percentage": round((ai_processed_count / max(total_count, 1)) * 100, 2)
        },
        "categories": {
            "auto_created_count": conn.execute("""
                SELECT COUNT(*) FROM event_log 
                WHERE action = 'auto_create' AND entity_type = 'category'
            """).fetchone()[0]
        }
    }


class UpdateDetectionMarkersRequest(BaseModel):
    transaction_id: str
    is_income: Optional[bool] = None
    is_transfer: Optional[bool] = None
    is_adjustment: Optional[bool] = None
    zelle_direction: Optional[str] = None
    zelle_counterparty: Optional[str] = None


@router.post("/detection/update-markers")
async def update_detection_markers(request: UpdateDetectionMarkersRequest) -> dict:
    """Manually update detection markers for a transaction"""
    conn = get_conn()
    
    # Verify transaction exists
    tx_exists = conn.execute("SELECT 1 FROM [transaction] WHERE id = ?", [request.transaction_id]).fetchone()
    if not tx_exists:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Build update query
    updates = []
    params = []
    
    if request.is_income is not None:
        updates.append("is_income = ?")
        params.append(request.is_income)
    
    if request.is_transfer is not None:
        # Add column if it doesn't exist
        try:
            conn.execute("ALTER TABLE [transaction] ADD COLUMN is_transfer BOOLEAN DEFAULT FALSE")
        except:
            pass  # Column may already exist
        updates.append("is_transfer = ?")
        params.append(request.is_transfer)
    
    if request.is_adjustment is not None:
        updates.append("is_adjustment = ?")
        params.append(request.is_adjustment)
    
    if request.zelle_direction is not None:
        updates.append("zelle_direction = ?")
        params.append(request.zelle_direction)
    
    if request.zelle_counterparty is not None:
        updates.append("zelle_counterparty = ?")
        params.append(request.zelle_counterparty)
    
    if updates:
        params.append(request.transaction_id)
        update_sql = f"UPDATE [transaction] SET {', '.join(updates)} WHERE id = ?"
        conn.execute(update_sql, params)
        
        # Log the update
        import json
        import uuid
        from datetime import datetime, UTC

        conn.execute("""
            INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4()),
            "transaction",
            request.transaction_id,
            "manual_detection_update",
            json.dumps(request.dict(exclude_none=True)),
            datetime.now(UTC),
            "user"
        ])
    
    return {
        "transaction_id": request.transaction_id,
        "updated_fields": len(updates),
        "status": "updated"
    }


# ========================================
# SMART CATEGORY MANAGEMENT ENDPOINTS
# ========================================

@router.get("/categories/gap-analysis")
async def analyze_ai_category_gaps() -> dict:
    """Analyze gaps between AI suggestions and available categories - SOLVES THE 9.1% SUCCESS RATE ISSUE"""
    gap_analysis = analyze_category_gaps()
    
    return {
        "analysis": {
            "total_ai_suggestions": gap_analysis.total_ai_suggestions,
            "available_categories": gap_analysis.available_categories,
            "missing_categories_count": len(gap_analysis.missing_categories),
            "success_rate": f"{gap_analysis.success_rate:.1f}%",
            "critical_issue": gap_analysis.success_rate < 50
        },
        "missing_categories": gap_analysis.missing_categories[:20],  # Show first 20
        "suggested_actions": gap_analysis.suggested_actions,
        "recommendation": "Run bootstrap endpoint to fix this immediately" if gap_analysis.success_rate < 80 else "System working well"
    }


@router.post("/categories/bootstrap", dependencies=[Depends(require_admin)])
async def bootstrap_standard_categories() -> dict:
    """Bootstrap standard categories to fix AI suggestion failures"""
    created_count = bootstrap_missing_categories()
    
    # Re-analyze after bootstrap
    gap_analysis = analyze_category_gaps()
    
    return {
        "categories_created": created_count,
        "success": created_count > 0,
        "new_success_rate": f"{gap_analysis.success_rate:.1f}%",
        "improvement": f"+{gap_analysis.success_rate - 9.1:.1f}%" if created_count > 0 else "0%",
        "message": f"Created {created_count} standard categories. AI success rate improved to {gap_analysis.success_rate:.1f}%"
    }


class ProcessCategorySuggestionRequest(BaseModel):
    category_name: str
    confidence: float = 0.8
    auto_create: bool = True


@router.post("/categories/process-suggestion")
async def process_ai_category_suggestion_endpoint(
    body: ProcessCategorySuggestionRequest | None = Body(default=None),
    category_name: str | None = Query(default=None),
    confidence: float | None = Query(default=None),
    auto_create: bool | None = Query(default=None),
) -> dict:
    """Process a single AI category suggestion.

    Accepts either JSON body or query params for maximum compatibility.
    """
    if body is not None:
        name = body.category_name
        conf = body.confidence
        create = body.auto_create
    else:
        if not category_name:
            raise HTTPException(status_code=422, detail="category_name is required")
        name = category_name
        conf = float(confidence) if confidence is not None else 0.8
        create = True if auto_create is None else bool(auto_create)

    result = process_ai_category_suggestion(name, conf, create)
    
    return {
        "category_id": result.category_id,
        "category_name": result.category_name,
        "parent_id": result.parent_id,
        "created": result.created,
        "reason": result.reason,
        "confidence": result.confidence,
        "success": result.category_id is not None
    }


@router.get("/categories/pending-suggestions")
async def get_pending_suggestions(limit: int = 50) -> dict:
    """Get pending category suggestions for manual review"""
    suggestions = get_pending_category_suggestions(limit)
    
    return {
        "total_pending": len(suggestions),
        "suggestions": suggestions,
        "recommendation": "Approve high-confidence suggestions to improve AI success rate"
    }


class ApproveCategoryRequest(BaseModel):
    suggestion_id: str
    
    
@router.post("/categories/approve-suggestion", dependencies=[Depends(require_admin)])
async def approve_pending_suggestion(request: ApproveCategoryRequest) -> dict:
    """Approve a pending category suggestion"""
    category_id = approve_category_suggestion(request.suggestion_id)
    
    if category_id:
        return {
            "success": True,
            "category_id": category_id,
            "message": "Category suggestion approved and created"
        }
    else:
        raise HTTPException(status_code=404, detail="Suggestion not found or creation failed")


@router.post("/categories/bulk-fix", dependencies=[Depends(require_admin)])
async def bulk_fix_category_gaps(transaction_limit: int = 1000) -> dict:
    """Bulk fix category gaps - ONE-CLICK SOLUTION"""
    result = bulk_process_ai_suggestions(transaction_limit)
    
    gap_analysis = result["gap_analysis"]
    total_created = result["total_categories_added"]
    
    return {
        "success": True,
        "analysis": {
            "initial_success_rate": f"{gap_analysis.success_rate:.1f}%",
            "categories_analyzed": gap_analysis.total_ai_suggestions,
            "missing_categories_found": len(gap_analysis.missing_categories)
        },
        "actions_taken": {
            "standard_categories_created": result["standard_categories_created"],
            "pending_suggestions_processed": result["pending_suggestions_processed"],
            "total_categories_added": total_created
        },
        "message": f"Bulk fix complete! Added {total_created} categories to improve AI success rate",
        "next_steps": [
            "Re-run AI categorization on uncategorized transactions",
            "Monitor success rate improvements",
            "Review any remaining pending suggestions"
        ]
    }


@router.get("/categories/success-metrics")
async def get_category_success_metrics() -> dict:
    """Get comprehensive category success metrics"""
    gap_analysis = analyze_category_gaps()
    pending = get_pending_category_suggestions()
    
    # Get total categories
    conn = get_conn()
    total_categories = conn.execute("SELECT COUNT(*) FROM category").fetchone()[0]
    
    return {
        "current_metrics": {
            "total_categories": total_categories,
            "ai_success_rate": f"{gap_analysis.success_rate:.1f}%",
            "missing_categories": len(gap_analysis.missing_categories),
            "pending_suggestions": len(pending)
        },
        "health_status": {
            "excellent": gap_analysis.success_rate >= 90,
            "good": 80 <= gap_analysis.success_rate < 90,
            "fair": 60 <= gap_analysis.success_rate < 80,
            "poor": gap_analysis.success_rate < 60,
            "critical": gap_analysis.success_rate < 30
        },
        "recommendations": gap_analysis.suggested_actions,
        "quick_fix_available": len(gap_analysis.missing_categories) > 10
    }


# ========================================
# MERCHANT MEMORY SYSTEM ENDPOINTS
# ========================================

class LearnFromCategorizationRequest(BaseModel):
    transaction_id: str
    category_id: str

@router.post("/merchant-memory/learn")
async def learn_from_categorization_endpoint(request: LearnFromCategorizationRequest) -> dict:
    """Learn from user's manual categorization - MAIN INTEGRATION POINT"""
    conn = get_conn()
    
    # Verify transaction exists
    tx_exists = conn.execute("SELECT description_norm FROM [transaction] WHERE id = ?", [request.transaction_id]).fetchone()
    if not tx_exists:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Verify category exists
    cat_exists = conn.execute("SELECT name FROM category WHERE id = ?", [request.category_id]).fetchone()
    if not cat_exists:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Learn from the categorization
    await learn_from_transaction_categorization(request.transaction_id, request.category_id)
    
    # Extract merchant for response
    merchant_name = extract_merchant_from_description(tx_exists[0])
    
    return {
        "success": True,
        "transaction_id": request.transaction_id,
        "category_id": request.category_id,
        "category_name": cat_exists[0],
        "merchant_learned": merchant_name,
        "message": f"Learned mapping: {merchant_name} -> {cat_exists[0]}"
    }


@router.post("/merchant-memory/backfill", dependencies=[Depends(require_admin)])
async def backfill_merchant_memory(limit: int = 500) -> dict:
    """Backfill merchant memory from existing categorized transactions.

    This learns from all transactions that have categories applied,
    building the merchant->category memory for future predictions.
    """
    conn = get_conn()

    # Get all categorized transactions that we can learn from
    rows = conn.execute("""
        SELECT t.id, tc.category_id
        FROM [transaction] t
        INNER JOIN transaction_category tc ON t.id = tc.tx_id
        ORDER BY t.posted_at DESC
        LIMIT ?
    """, [limit]).fetchall()

    learned_count = 0
    errors = 0

    for tx_id, category_id in rows:
        try:
            await learn_from_transaction_categorization(tx_id, category_id)
            learned_count += 1
        except Exception as e:
            errors += 1
            if errors < 5:
                print(f"Backfill error for {tx_id}: {e}")

    # Get updated stats
    stats = get_merchant_memory_statistics()

    return {
        "success": True,
        "transactions_processed": len(rows),
        "merchants_learned": learned_count,
        "errors": errors,
        "merchant_memory_stats": stats
    }


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

@router.get("/merchant-memory/stats")
async def get_merchant_memory_stats() -> dict:
    """Get merchant memory system statistics"""
    stats = get_merchant_memory_statistics()
    
    return {
        "merchant_memory": {
            "total_learned_merchants": stats["total_learned_merchants"],
            "learning_enabled": True,
            "auto_categorization": True
        },
        "top_merchants": stats["top_merchants"],
        "recent_activity": stats["recent_activity"],
        "benefits": [
            "Remembers every merchant you categorize",
            "Auto-suggests same category for similar merchants", 
            "Increases confidence with repeated use",
            "Handles merchant name variations"
        ]
    }

@router.post("/merchant-memory/extract")
async def extract_merchant_endpoint(request: MerchantNormalizationRequest) -> dict:
    """Extract normalized merchant name from transaction description"""
    merchant_name = extract_merchant_from_description(request.description)
    
    return {
        "original_description": request.description,
        "extracted_merchant": merchant_name,
        "success": True
    }

@router.get("/merchant-memory/learned-mappings")
async def get_learned_merchant_mappings(limit: int = 50) -> dict:
    """Get learned merchant-category mappings"""
    conn = get_conn()
    
    try:
        mappings = conn.execute("""
            SELECT mcm.merchant_name, c.name as category_name, 
                   mcm.confidence, mcm.usage_count, mcm.last_used
            FROM merchant_category_mapping mcm
            JOIN category c ON c.id = mcm.category_id
            ORDER BY mcm.usage_count DESC, mcm.confidence DESC
            LIMIT ?
        """, [limit]).fetchall()
        
        return {
            "learned_mappings": [
                {
                    "merchant_name": row[0],
                    "category_name": row[1], 
                    "confidence": row[2],
                    "usage_count": row[3],
                    "last_used": row[4]
                }
                for row in mappings
            ],
            "total_mappings": len(mappings)
        }
    except Exception as e:
        return {
            "learned_mappings": [],
            "total_mappings": 0,
            "error": str(e)
        }

class DeleteMerchantMappingRequest(BaseModel):
    merchant_pattern: str
    
@router.delete("/merchant-memory/mapping", dependencies=[Depends(require_admin)])
async def delete_merchant_mapping(request: DeleteMerchantMappingRequest) -> dict:
    """Delete a learned merchant mapping"""
    conn = get_conn()
    
    # Check if mapping exists
    existing = conn.execute(
        "SELECT id FROM merchant_category_mapping WHERE merchant_pattern = ?",
        [request.merchant_pattern]
    ).fetchone()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Merchant mapping not found")
    
    # Delete the mapping
    conn.execute(
        "DELETE FROM merchant_category_mapping WHERE merchant_pattern = ?",
        [request.merchant_pattern]
    )
    
    return {
        "success": True,
        "merchant_pattern": request.merchant_pattern,
        "message": "Merchant mapping deleted successfully"
    }

@router.post("/merchant-memory/clear-all", dependencies=[Depends(require_admin)])
async def clear_all_merchant_mappings() -> dict:
    """Clear all learned merchant mappings (admin only)"""
    conn = get_conn()

    # Count before deletion
    count_before = conn.execute("SELECT COUNT(*) FROM merchant_category_mapping").fetchone()[0]

    # Clear all mappings
    conn.execute("DELETE FROM merchant_category_mapping")

    return {
        "success": True,
        "mappings_deleted": count_before,
        "message": f"Cleared {count_before} learned merchant mappings"
    }


# ========================================
# TRAINING DATASET & ENHANCED BACKFILL
# ========================================

@router.get("/training/dataset")
async def get_training_dataset(min_occurrences: int = Query(2, ge=1)) -> dict:
    """Export categorized transactions as a training dataset.

    Returns all manually categorized transactions that can be used for
    training ML models or improving categorization accuracy.
    """
    from ...ai_smart_categorization import build_training_dataset

    dataset = build_training_dataset(min_occurrences=min_occurrences)

    # Group by category for summary
    by_category = {}
    for item in dataset:
        cat = item["category_name"]
        if cat not in by_category:
            by_category[cat] = {"count": 0, "examples": []}
        by_category[cat]["count"] += 1
        if len(by_category[cat]["examples"]) < 3:
            by_category[cat]["examples"].append(item["description"][:50])

    return {
        "success": True,
        "total_entries": len(dataset),
        "unique_categories": len(by_category),
        "by_category_summary": by_category,
        "dataset": dataset[:100],  # Limit response size
    }


@router.post("/training/backfill-enhanced")
async def backfill_merchant_memory_enhanced(
    min_occurrences: int = Query(2, ge=1),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
) -> dict:
    """Enhanced merchant memory backfill from historical data.

    This builds a comprehensive merchant→category mapping from all
    existing categorized transactions, enabling better auto-categorization.
    """
    from ...ai_smart_categorization import backfill_merchant_memory as backfill_fn

    result = backfill_fn(min_occurrences=min_occurrences, min_confidence=min_confidence)

    # Get updated stats
    stats = get_merchant_memory_statistics()

    return {
        "success": True,
        "backfill_results": result,
        "merchant_memory_stats": stats,
    }


@router.post("/training/categorize-uncategorized")
async def categorize_with_training_data_endpoint(
    confidence_threshold: float = Query(0.6, ge=0.0, le=1.0),
    limit: int = Query(500, ge=1, le=5000),
    dry_run: bool = Query(False),
) -> dict:
    """Categorize uncategorized transactions using training data.

    This uses the merchant memory and description similarity to
    automatically categorize transactions without calling external AI.

    Args:
        confidence_threshold: Minimum confidence to auto-apply (default 0.6)
        limit: Maximum transactions to process
        dry_run: If True, returns what would be categorized without applying
    """
    from ...ai_smart_categorization import categorize_with_training_data

    result = categorize_with_training_data(
        confidence_threshold=confidence_threshold,
        limit=limit,
        dry_run=dry_run,
    )

    # Get remaining uncategorized count
    conn = get_conn()
    remaining = conn.execute("""
        SELECT COUNT(*)
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON tc.tx_id = t.id
        WHERE tc.tx_id IS NULL
    """).fetchone()[0]

    return {
        "success": True,
        "dry_run": dry_run,
        "total_processed": result["total_processed"],
        "categorized_by_merchant_memory": result["categorized_by_merchant_memory"],
        "categorized_by_similarity": result["categorized_by_similarity"],
        "low_confidence": result["low_confidence"],
        "errors": result["errors"],
        "remaining_uncategorized": remaining,
        "sample_categorizations": result["categorizations"][:10],
    }


@router.get("/training/merchant-map")
async def get_merchant_category_map(
    min_occurrences: int = Query(2, ge=1),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
) -> dict:
    """Get the computed merchant→category mapping.

    Shows what categories would be assigned to each merchant pattern
    based on historical categorization data.
    """
    from ...ai_smart_categorization import build_merchant_category_map

    mappings = build_merchant_category_map(
        min_occurrences=min_occurrences,
        min_confidence=min_confidence,
    )

    return {
        "success": True,
        "total_mappings": len(mappings),
        "mappings": mappings[:100],  # Limit response size
    }
