from __future__ import annotations

from fastapi import APIRouter, Query, BackgroundTasks
from pydantic import BaseModel

from ...transfers import suggest_transfers_v2, suggest_transfers_v3, list_transfers, confirm_transfer, reject_transfer


router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.get("")
def list_(status: str = Query("pending", pattern="^(pending|confirmed|all)$")):
    return list_transfers(status=status)

@router.post("/group/{group_id}/analytics")
def set_group_analytics(group_id: str, include: bool = Query(True)):
    from ...db import get_conn
    import json, uuid
    from datetime import datetime, UTC
    conn = get_conn()
    conn.execute("UPDATE match_transfer SET include_in_analytics = ? WHERE group_id = ?", [include, group_id])
    # audit
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), "transfer_group", group_id, "analytics_toggle", json.dumps({"include": include}), datetime.now(UTC), "user"],
    )
    return {"group_id": group_id, "include_in_analytics": include}


class ConfirmBody(BaseModel):
    left_tx_id: str | None = None
    right_tx_id: str | None = None
    group_ids: list[str] | None = None


@router.post("/confirm")
def confirm(body: ConfirmBody):
    """Confirm by left/right or in bulk by group_ids."""
    if body.group_ids:
        from ...db import get_conn
        conn = get_conn()
        out = []
        for gid in body.group_ids:
            # confirm all pairs in this group (set decided_at)
            rows = conn.execute(
                "SELECT left_tx_id, right_tx_id FROM match_transfer WHERE group_id = ?",
                [gid],
            ).fetchall()
            for a, b in rows:
                out.append(confirm_transfer(a, b))
        return {"confirmed": out}
    assert body.left_tx_id and body.right_tx_id, "left_tx_id/right_tx_id or group_ids required"
    return confirm_transfer(body.left_tx_id, body.right_tx_id)


class RejectBody(BaseModel):
    left_tx_id: str | None = None
    right_tx_id: str | None = None
    group_ids: list[str] | None = None


@router.post("/reject")
def reject(body: RejectBody):
    """Reject by left/right or in bulk by group_ids (pending only)."""
    if body.group_ids:
        from ...db import get_conn
        conn = get_conn()
        count = 0
        for gid in body.group_ids:
            rows = conn.execute(
                "SELECT left_tx_id, right_tx_id FROM match_transfer WHERE group_id = ? AND decided_at IS NULL",
                [gid],
            ).fetchall()
            for a, b in rows:
                reject_transfer(a, b)
                count += 1
        return {"rejected": count}
    assert body.left_tx_id and body.right_tx_id, "left_tx_id/right_tx_id or group_ids required"
    return reject_transfer(body.left_tx_id, body.right_tx_id)
@router.post("/suggest_v2")
def suggest_v2(max_days: int = Query(2, ge=0, le=200), amount_tolerance: float = Query(0.01, ge=0.0), limit: int = Query(5000, ge=1, le=20000)):
    """Detect transfer pairs and return created candidates with basic details."""
    # Run detection
    res = suggest_transfers_v2(max_days=max_days, amount_tolerance=amount_tolerance, limit=limit)
    # audit
    try:
        from ...db import get_conn
        import uuid, json
        from datetime import datetime, UTC
        conn = get_conn()
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), "transfer", "batch", "suggest_v2", json.dumps({"max_days": max_days, "amount_tolerance": amount_tolerance, "limit": limit, "created": res.get("suggested", 0)}), datetime.now(UTC), "user"],
        )
    except Exception:
        pass
    # Return pending list as candidates summary
    items = list_("pending")
    cands = []
    for it in items:
        cands.append({
            "group_id": it.get("group_id"),
            "tx_ids": [it.get("left_tx_id"), it.get("right_tx_id")],
            "confidence": it.get("score"),
            "amount": abs((it.get("left_amount") or 0) or 0),
            "date_range": [str(it.get("left_date")), str(it.get("right_date"))],
        })
    return {"created": res.get("suggested", 0), "candidates": cands}


@router.post("/suggest")
@router.post("/suggest_v3")
def suggest_v3(
    max_days: int = Query(3, ge=0, le=14),
    amount_tolerance_pct: float = Query(0.02, ge=0.0, le=0.1),
    min_score: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(5000, ge=1, le=20000),
):
    """Hybrid transfer detection using category awareness and fuzzy matching.

    This is the recommended endpoint for transfer detection. It combines:
    - Transactions categorized as Internal Transfer, Zelle, Venmo, etc.
    - Transactions with transfer-related keywords in description
    - Fuzzy amount matching with percentage tolerance
    - Multi-factor scoring based on category, description, date proximity

    Args:
        max_days: Maximum days apart for a potential pair (default 3)
        amount_tolerance_pct: Percentage tolerance for amount matching (default 2%)
        min_score: Minimum score to suggest a pair (default 0.5)
        limit: Maximum transactions to scan (default 5000)
    """
    res = suggest_transfers_v3(
        max_days=max_days,
        amount_tolerance_pct=amount_tolerance_pct,
        min_score=min_score,
        limit=limit,
    )
    # Audit log
    try:
        from ...db import get_conn
        import uuid, json
        from datetime import datetime, UTC
        conn = get_conn()
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                str(uuid.uuid4()),
                "transfer",
                "batch",
                "suggest_v3",
                json.dumps({
                    "max_days": max_days,
                    "amount_tolerance_pct": amount_tolerance_pct,
                    "min_score": min_score,
                    "limit": limit,
                    "created": res.get("suggested", 0),
                    "candidates_scanned": res.get("candidates_scanned", 0),
                }),
                datetime.now(UTC),
                "user",
            ],
        )
    except Exception:
        pass

    # Return pending list as candidates summary
    items = list_("pending")
    cands = []
    for it in items:
        cands.append({
            "group_id": it.get("group_id"),
            "tx_ids": [it.get("left_tx_id"), it.get("right_tx_id")],
            "confidence": it.get("score"),
            "method": it.get("method"),
            "amount": abs((it.get("left_amount") or 0)),
            "left_desc": it.get("left_desc"),
            "right_desc": it.get("right_desc"),
            "date_range": [str(it.get("left_date")), str(it.get("right_date"))],
        })

    return {
        "created": res.get("suggested", 0),
        "skipped_existing": res.get("skipped_existing", 0),
        "skipped_low_score": res.get("skipped_low_score", 0),
        "candidates_scanned": res.get("candidates_scanned", 0),
        "candidates": cands,
    }


# =============================================================================
# AI-Enhanced Transfer Detection Endpoints
# =============================================================================

@router.post("/ai/detect")
async def ai_detect_transfers(
    limit: int = Query(5000, ge=1, le=20000),
    use_ai: bool = Query(True, description="Use AI for analysis (fallback to heuristics if False)"),
    background_tasks: BackgroundTasks = None,
):
    """
    Start AI-enhanced transfer detection job.

    Combines heuristic pre-filtering with AI analysis for higher accuracy.
    Returns immediately with a job_id for tracking progress.
    """
    from ...ai_transfer_detection import get_transfer_detection_service

    service = get_transfer_detection_service()

    # Create job
    result = service.create_detection_job(limit=limit)

    if result[0] is None:
        return {
            "status": "no_work",
            "message": "No transfer candidates found",
            "total_pairs": 0,
        }

    job_id, candidates = result

    # Process in background
    if background_tasks:
        background_tasks.add_task(
            service.process_detection_job,
            job_id,
            candidates,
            use_ai=use_ai
        )

        return {
            "status": "started",
            "job_id": job_id,
            "total_pairs": len(candidates),
            "message": f"AI transfer detection started for {len(candidates)} candidate pairs",
        }
    else:
        # Synchronous processing for testing
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.process_detection_job(job_id, candidates, use_ai=use_ai)
        )
        return {
            "status": "completed",
            "job_id": job_id,
            "total_pairs": result.total_pairs,
            "transfers_found": result.transfers_found,
            "high_confidence": result.high_confidence,
            "medium_confidence": result.medium_confidence,
        }


@router.get("/ai/job/{job_id}")
def get_ai_detection_job(job_id: str):
    """Get status of an AI transfer detection job."""
    from ...db import get_conn
    conn = get_conn()

    job = conn.execute(
        """
        SELECT id, job_type, total_transactions, processed_transactions,
               enhanced_transactions, status, created_at, completed_at, error_message
        FROM ai_bulk_job
        WHERE id = ? AND job_type = 'transfer_detection'
        """,
        [job_id],
    ).fetchone()

    if not job:
        return {"error": "Job not found", "job_id": job_id}

    total = job[2] or 1
    processed = job[3] or 0

    return {
        "job_id": job[0],
        "job_type": job[1],
        "total_pairs": job[2],
        "processed_pairs": job[3],
        "transfers_found": job[4],
        "status": job[5],
        "created_at": job[6],
        "completed_at": job[7],
        "error_message": job[8],
        "progress_percent": round((processed / total) * 100, 1),
    }


@router.post("/ai/job/{job_id}/cancel")
def cancel_ai_detection_job(job_id: str):
    """Cancel a running AI transfer detection job."""
    from ...db import get_conn
    from datetime import datetime, UTC

    conn = get_conn()
    conn.execute(
        "UPDATE ai_bulk_job SET status = 'cancelled', completed_at = ? WHERE id = ?",
        [datetime.now(UTC).isoformat(), job_id],
    )
    return {"job_id": job_id, "status": "cancelled"}


@router.get("/ai/stats")
def get_ai_detection_stats():
    """Get AI-enhanced transfer detection statistics."""
    from ...ai_transfer_detection import get_transfer_detection_service

    service = get_transfer_detection_service()
    return service.get_detection_stats()


@router.post("/ai/analyze-pair")
async def analyze_transfer_pair(
    left_id: str = Query(..., description="Left transaction ID"),
    right_id: str = Query(..., description="Right transaction ID"),
):
    """
    Analyze a specific transaction pair using AI.

    Returns detailed analysis of whether the pair represents a transfer.
    """
    from ...db import get_conn
    from ...ai_transfer_detection import (
        get_transfer_detection_service,
        TransferCandidate,
    )
    from ...transfers import _canonical_pair, jaccard_similarity

    conn = get_conn()

    # Fetch transaction details
    left = conn.execute(
        """
        SELECT t.id, t.account_id, t.posted_at, t.amount, t.description_norm,
               COALESCE(c.name, '') as category
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON tc.tx_id = t.id
        LEFT JOIN category c ON tc.category_id = c.id
        WHERE t.id = ?
        """,
        [left_id],
    ).fetchone()

    right = conn.execute(
        """
        SELECT t.id, t.account_id, t.posted_at, t.amount, t.description_norm,
               COALESCE(c.name, '') as category
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON tc.tx_id = t.id
        LEFT JOIN category c ON tc.category_id = c.id
        WHERE t.id = ?
        """,
        [right_id],
    ).fetchone()

    if not left or not right:
        return {"error": "Transaction not found", "left_id": left_id, "right_id": right_id}

    # Calculate heuristic score
    day_diff = abs((right[2] - left[2]).days)
    abs_a = abs(left[3])
    abs_b = abs(right[3])
    amount_diff = abs(abs_a - abs_b)
    tolerance = max(0.01, (abs_a + abs_b) / 2 * 0.02)

    date_score = 1.0 - (day_diff / 3) if day_diff <= 3 else 0.0
    amount_score = 1.0 - (amount_diff / max(tolerance, 0.01)) if amount_diff <= tolerance else 0.0
    desc_sim = jaccard_similarity(left[4] or "", right[4] or "")

    heuristic_score = 0.25 * date_score + 0.30 * amount_score + 0.25 * desc_sim

    # Create candidate
    canonical = _canonical_pair(left_id, right_id)
    candidate = TransferCandidate(
        left_id=canonical[0],
        right_id=canonical[1],
        left_description=left[4] or "",
        right_description=right[4] or "",
        left_amount=float(left[3]),
        right_amount=float(right[3]),
        left_account=left[1],
        right_account=right[1],
        left_date=str(left[2]),
        right_date=str(right[2]),
        left_category=left[5],
        right_category=right[5],
        heuristic_score=heuristic_score,
    )

    # Run AI analysis
    service = get_transfer_detection_service()
    result = await service.analyze_pair_with_ai(candidate)

    return {
        "left_id": result.left_id,
        "right_id": result.right_id,
        "is_transfer": result.is_transfer,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "method": result.method,
        "heuristic_score": heuristic_score,
        "scores": {
            "date_proximity": date_score,
            "amount_match": amount_score,
            "description_similarity": desc_sim,
        },
        "provider": result.provider,
        "latency_ms": result.latency_ms,
    }


@router.post("/ai/feedback")
def submit_transfer_feedback(
    left_id: str = Query(...),
    right_id: str = Query(...),
    was_correct: bool = Query(...),
    user_action: str = Query(..., pattern="^(confirmed|rejected)$"),
):
    """
    Submit feedback on transfer detection accuracy.

    Used to improve future detection through learning.
    """
    from ...ai_transfer_detection import get_transfer_detection_service

    service = get_transfer_detection_service()
    service.record_feedback(left_id, right_id, was_correct, user_action)

    return {
        "status": "recorded",
        "left_id": left_id,
        "right_id": right_id,
        "was_correct": was_correct,
        "user_action": user_action,
    }
