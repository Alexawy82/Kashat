from __future__ import annotations

import re

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ...recurring import (
    suggest_recurring, list_recurring, confirm_series, reject_series,
    calculate_series_status, extract_merchant_name_ai, merge_duplicate_merchants,
    classify_recurring_type, RecurringTypeClassifier, infer_display_name,
    auto_link_transactions_to_series
)
from ...db import get_conn
from datetime import date, timedelta
from typing import Optional


def calculate_next_due_date(last_date: date, cadence: str) -> date:
    """Calculate the next expected payment date based on last_date and cadence.

    If last_date is in the past, projects forward to find the next upcoming date.
    """
    if not last_date or not cadence:
        return None

    # Cadence intervals in days (approximate for month-based)
    intervals = {
        'weekly': 7,
        'biweekly': 14,
        'monthly': 30,
        'quarterly': 91,
        'semi_annual': 182,
        'annual': 365,
    }

    days = intervals.get(cadence, 30)  # Default to monthly
    today = date.today()

    # Start from last_date and keep adding interval until we're in the future
    next_date = last_date + timedelta(days=days)
    while next_date < today:
        next_date += timedelta(days=days)

    return next_date


router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.post("/suggest")
def suggest(
    min_occurrences: int = Query(3, ge=2, le=12),
    tol: float = Query(0.10, ge=0.0, le=0.5),
    limit: int = Query(5000, ge=10, le=100000),
    include_short_cadence: bool = Query(False, description="Include weekly/biweekly patterns"),
):
    """Run recurring detection and return pending series with summary fields.

    Returns detected series with fields: series_id, merchant, cadence, avg_amount, confidence, next_date, tx_count.
    Tolerance default is 10% to catch subscriptions with price variations.

    Set include_short_cadence=true to also detect weekly/biweekly patterns (gym, paycheck, etc.)
    """
    # Run detection (idempotent-ish via skip logic in service)
    suggest_recurring(
        min_occurrences=min_occurrences,
        tol=tol,
        limit=limit,
        allow_short_cadence=include_short_cadence,
    )
    # audit
    try:
        from ...db import get_conn
        import uuid, json
        from datetime import datetime, UTC
        conn = get_conn()
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), "recurring_series", "batch", "suggest", json.dumps({"min_occurrences": min_occurrences, "tol": tol, "limit": limit}), datetime.now(UTC), "user"],
        )
    except Exception:
        pass
    # Return current pending list mapped to expected keys (with aliases for frontend compatibility)
    rows = list_("pending")
    candidates = []
    for r in rows:
        candidates.append({
            # Primary keys
            "series_id": r.get("id"),
            "id": r.get("id"),  # Alias for frontend
            "merchant": r.get("name"),
            "merchant_name": r.get("name"),  # Alias for frontend
            "payee": r.get("name"),  # Alias for frontend
            "cadence": r.get("cadence"),
            "avg_amount": r.get("amount_mean"),
            "amount_mean": r.get("amount_mean"),  # Alias for frontend
            "amount": r.get("amount_mean"),  # Alias for frontend
            "confidence": r.get("confidence"),
            "next_date": r.get("next_date"),
            "tx_count": r.get("occurrences"),
        })
    return {"candidates": candidates, "total": len(candidates)}


def _enrich_series(rows: list) -> list:
    """Add confidence scores, predictions, and standardized field names."""
    out = []
    for r in rows:
        # Use stored prediction_confidence if available, otherwise calculate
        stored_confidence = r.get("prediction_confidence")
        if stored_confidence is not None:
            confidence = float(stored_confidence)
        else:
            occ = int(r.get("occurrences", 0) or 0)
            sd = float(r.get("amount_sd", 0) or 0)
            mean = float(r.get("amount_mean", 0) or 0)
            amount_stability = 1.0 - min(1.0, abs(sd) / max(1.0, abs(mean))) if mean else 0.5
            confidence = max(0.0, min(1.0, 0.2 + 0.2*min(occ,10)/10.0 + 0.6*amount_stability))

        r["confidence"] = round(confidence, 3)

        # Standardized primary fields with AI-enhanced merchant name extraction
        raw_name = r.get("name") or ""
        stored_display = r.get("display_name") or ""
        # Always try AI extraction to get cleaner names
        ai_name = extract_merchant_name_ai(raw_name)
        # Use AI-extracted name if it looks cleaner (different from raw, not "Unknown")
        # Also check if it has proper capitalization (first letter uppercase)
        ai_is_clean = (
            ai_name and
            ai_name != "Unknown" and
            (ai_name != raw_name or (ai_name[0].isupper() and not raw_name[0].isupper()))
        )
        if ai_is_clean:
            display_name = ai_name
        else:
            display_name = stored_display or ai_name or raw_name
        r["series_id"] = r.get("id")
        r["merchant"] = display_name
        r["merchant_name"] = display_name  # Alias
        r["payee"] = raw_name  # Raw name for reference
        r["amount"] = r.get("amount_mean")

        # Prediction fields
        r["predicted_amount"] = r.get("next_predicted_amount") or r.get("amount_mean")
        r["is_variable"] = (
            r.get("amount_sd") and r.get("amount_mean") and
            abs(float(r.get("amount_sd", 0))) / max(1.0, abs(float(r.get("amount_mean", 0)))) > 0.15
        )

        # Cadence display
        cadence = r.get("cadence", "monthly")
        r["cadence_label"] = {
            "weekly": "Weekly",
            "biweekly": "Bi-weekly",
            "monthly": "Monthly",
            "quarterly": "Quarterly",
            "semi_annual": "Semi-Annual",
            "annual": "Annual",
        }.get(cadence, cadence.title() if cadence else "Monthly")

        # Status detection (active/late/likely_cancelled)
        last_date_str = r.get("last_date")
        next_date_str = r.get("next_date")
        try:
            last_date_val = date.fromisoformat(str(last_date_str)) if last_date_str else None
        except (ValueError, TypeError):
            last_date_val = None
        try:
            next_date_val = date.fromisoformat(str(next_date_str)) if next_date_str else None
        except (ValueError, TypeError):
            next_date_val = None

        status_info = calculate_series_status(last_date_val, next_date_val, cadence)
        r["status"] = status_info["status"]
        r["days_since_last"] = status_info["days_since_last"]
        r["days_late"] = status_info["days_late"]
        r["missed_payments"] = status_info["missed_payments"]
        r["health_score"] = status_info["health_score"]

        # Enhanced type classification (Phase 1)
        # Use stored values if available, otherwise classify dynamically
        stored_type = r.get("recurring_type")
        if stored_type and stored_type != "unknown":
            r["recurring_type"] = stored_type
            r["sub_category"] = r.get("sub_category")
            r["is_essential"] = bool(r.get("is_essential"))
        else:
            # Classify dynamically if not stored
            # Try with display_name first (more complete from AI extraction),
            # fall back to raw_name if display_name doesn't match
            type_info = classify_recurring_type(display_name, float(r.get("amount_mean") or 0))
            if type_info["recurring_type"] == "unknown" and display_name != raw_name:
                type_info = classify_recurring_type(raw_name, float(r.get("amount_mean") or 0))
            r["recurring_type"] = type_info["recurring_type"]
            r["sub_category"] = type_info["sub_category"]
            r["is_essential"] = type_info["is_essential"]
            # Use clean_name from classifier if better
            if type_info.get("clean_name") and not ai_is_clean:
                r["merchant"] = type_info["clean_name"]
                r["merchant_name"] = type_info["clean_name"]

        # Normalize Plaid-style category names to internal names
        category_normalization = {
            # Plaid-style → internal
            "loan_payments": "loan",
            "rent_and_utilities": "bill",
            "subscriptions": "subscription",
            "insurance": "insurance",  # New category
            "income": "income",
            "transfers": "transfer",
            # Already normalized
            "loan": "loan",
            "bill": "bill",
            "subscription": "subscription",
            "credit_card": "credit_card",
            "unknown": "unknown",
        }
        raw_type = r["recurring_type"]
        normalized_type = category_normalization.get(raw_type, raw_type or "unknown")

        # Special handling: credit_card subcategory gets its own type
        if r.get("sub_category") == "credit_card":
            normalized_type = "credit_card"

        r["recurring_type"] = normalized_type

        # Type-specific display labels
        type_labels = {
            "subscription": "Subscription",
            "bill": "Bill",
            "loan": "Loan",
            "credit_card": "Credit Card",
            "insurance": "Insurance",
            "income": "Income",
            "transfer": "Transfer",
            "unknown": "Other",
        }
        r["recurring_type_label"] = type_labels.get(normalized_type, "Other")

        # Sub-category display labels (aligned with Plaid + legacy)
        sub_category_labels = {
            # Loans
            "auto_loan": "Auto Loan",
            "mortgage": "Mortgage",
            "personal_loan": "Personal Loan",
            "student_loan": "Student Loan",
            "credit_card": "Credit Card",
            "bnpl": "Buy Now Pay Later",
            "other_loan": "Other Loan",
            # Utilities (Plaid-style)
            "rent": "Rent",
            "electric": "Electric",
            "gas": "Gas",
            "water": "Water",
            "sewage": "Sewage",
            "trash": "Trash",
            "internet": "Internet",
            "cable": "Cable",
            "phone": "Phone",
            "other_utility": "Other Utility",
            # Legacy bill subcategories
            "utility_electric": "Electric",
            "utility_gas": "Gas",
            "utility_water": "Water",
            "utility_sewer": "Sewer",
            "telecom": "Telecom",
            "hoa": "HOA",
            "property_tax": "Property Tax",
            # Insurance
            "auto": "Auto Insurance",
            "home": "Home Insurance",
            "renters": "Renters Insurance",
            "life": "Life Insurance",
            "health": "Health Insurance",
            "pet": "Pet Insurance",
            "other_insurance": "Other Insurance",
            "insurance": "Insurance",
            "insurance_auto": "Auto Insurance",
            "insurance_renters": "Renters Insurance",
            # Subscriptions (Plaid-style)
            "streaming_video": "Streaming Video",
            "streaming_music": "Streaming Music",
            "cloud_storage": "Cloud Storage",
            "software": "Software",
            "ai_services": "AI Services",
            "gaming": "Gaming",
            "fitness": "Fitness",
            "wellness": "Wellness",
            "news_media": "News & Media",
            "creator_platforms": "Creator Platform",
            "membership": "Membership",
            "identity_protection": "Identity Protection",
            "fintech": "Financial Tech",
            "education": "Education",
            "pet_services": "Pet Services",
            "other_subscription": "Other",
            # Legacy subscription subcategories
            "streaming": "Streaming",
            "music": "Music",
            "cloud": "Cloud Storage",
            "productivity": "Productivity",
            "news": "News",
            "creator": "Creator",
            "identity": "Identity Protection",
            # Credit card issuers
            "chase": "Chase",
            "amex": "Amex",
            "capital_one": "Capital One",
            "citi": "Citi",
            "discover": "Discover",
        }
        r["sub_category_label"] = sub_category_labels.get(r.get("sub_category"), r.get("sub_category"))

        # Annual cost calculation
        annual_cost = r.get("annual_cost")
        if annual_cost and isinstance(annual_cost, str):
            try:
                annual_cost = float(annual_cost)
            except (ValueError, TypeError):
                annual_cost = None
        if not annual_cost and r.get("amount_mean"):
            annual_cost = RecurringTypeClassifier.calculate_annual_cost(
                float(r.get("amount_mean") or 0),
                cadence
            )
        r["annual_cost"] = round(float(annual_cost), 2) if annual_cost else None

        # Loan-specific fields
        r["lender_name"] = r.get("lender_name")
        r["estimated_remaining"] = r.get("estimated_remaining")
        r["predicted_end_date"] = str(r.get("predicted_end_date")) if r.get("predicted_end_date") else None

        out.append(r)
    return out


@router.get("")
def list_(status: str = Query("pending", pattern="^(pending|confirmed|rejected|all)$")):
    """List recurring series with a computed confidence score.

    Confidence is computed heuristically from occurrences and amount/cadence stability.
    """
    rows = list_recurring(status=status)
    return _enrich_series(rows)


@router.get("/confirmed")
def list_confirmed():
    """List confirmed recurring series (subscriptions).

    This is an alias for GET /recurring?status=confirmed for frontend compatibility.
    """
    rows = list_recurring(status="confirmed")
    return _enrich_series(rows)


@router.get("/pending")
def list_pending():
    """List pending recurring series (needs review).

    This is an alias for GET /recurring?status=pending for frontend compatibility.
    """
    rows = list_recurring(status="pending")
    return _enrich_series(rows)


class SeriesBody(BaseModel):
    series_id: str


class SeriesBulkBody(BaseModel):
    series_id: str | None = None
    series_ids: list[str] | None = None


@router.post("/confirm")
def confirm(body: SeriesBulkBody):
    """Confirm one or more series. Accepts {series_id} or {series_ids: []}."""
    if body.series_ids:
        return {"confirmed": [confirm_series(sid) for sid in body.series_ids]}
    assert body.series_id, "series_id or series_ids required"
    return confirm_series(body.series_id)


@router.post("/reject")
def reject(body: SeriesBulkBody):
    """Reject one or more series. Accepts {series_id} or {series_ids: []}."""
    if body.series_ids:
        return {"rejected": [reject_series(sid) for sid in body.series_ids]}
    assert body.series_id, "series_id or series_ids required"
    return reject_series(body.series_id)


@router.get("/{series_id}/transactions")
def series_transactions(series_id: str, limit: int = Query(24, ge=1, le=200)):
    """Return last N transaction amounts/dates for a recurring series (for sparklines)."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT t.posted_at, t.amount
        FROM recurring_tx r
        JOIN [transaction] t ON t.id = r.tx_id
        WHERE r.series_id = ?
        ORDER BY t.posted_at DESC
        LIMIT ?
        """,
        [series_id, limit],
    ).fetchall()
    return [{"date": str(r[0]), "amount": float(r[1])} for r in rows]


@router.post("/reclassify")
def reclassify_all():
    """Force reclassify all recurring series using the latest classifier patterns.

    This is useful when classifier patterns have been updated and you want to
    apply the new classifications to existing series.
    """
    conn = get_conn()
    # Get all series with their names and amounts
    rows = conn.execute("""
        SELECT id, name, amount_mean FROM recurring_series
    """).fetchall()

    updated = 0
    for row in rows:
        series_id, name, amount_mean = row
        if not name:
            continue

        # Extract clean merchant name using AI/pattern matching
        clean_name = extract_merchant_name_ai(name)

        # Try clean name first, fall back to raw name if no match
        type_info = classify_recurring_type(clean_name, float(amount_mean or 0))
        if type_info["recurring_type"] == "unknown" and clean_name != name:
            type_info = classify_recurring_type(name, float(amount_mean or 0))

        # Also update display_name with the clean extracted name
        conn.execute("""
            UPDATE recurring_series SET
                recurring_type = ?,
                sub_category = ?,
                is_essential = ?,
                display_name = COALESCE(display_name, ?)
            WHERE id = ?
        """, [
            type_info["recurring_type"],
            type_info["sub_category"],
            type_info["is_essential"],
            clean_name if clean_name != "Unknown" else None,
            series_id,
        ])
        updated += 1

    return {"updated": updated, "message": f"Reclassified {updated} series with latest patterns"}


@router.post("/merge-duplicates")
def merge_duplicates():
    """Merge recurring series that have the same AI-extracted merchant name.

    This deduplicates series like:
    - "google *fiber viewca" and "google *fiber" → single "Google Fiber" series
    - Different description variations of the same merchant

    Keeps the "best" series (confirmed > pending > rejected, most transactions),
    moves all transactions to it, and deletes the duplicates.
    """
    conn = get_conn()
    result = merge_duplicate_merchants(conn)
    return result


# =============================================================================
# PHASE 1: TYPE-FILTERED ENDPOINTS
# =============================================================================

@router.get("/by-type/{recurring_type}")
def list_by_type(
    recurring_type: str,
    status: str = Query("confirmed", pattern="^(pending|confirmed|rejected|all)$"),
):
    """List recurring series filtered by type.

    Valid types: subscription, bill, loan, credit_card
    """
    all_rows = list_recurring(status=status)
    enriched = _enrich_series(all_rows)
    # Filter by type
    filtered = [r for r in enriched if r.get("recurring_type") == recurring_type]
    return filtered


@router.get("/loans")
def list_loans():
    """List all loan payments (auto, mortgage, personal, student).

    Returns confirmed loan series with estimated payoff info.
    """
    all_rows = list_recurring(status="confirmed")
    enriched = _enrich_series(all_rows)
    loans = [r for r in enriched if r.get("recurring_type") == "loan"]
    # Sort by amount (highest first)
    loans.sort(key=lambda x: abs(float(x.get("amount_mean") or 0)), reverse=True)
    return loans


@router.get("/bills")
def list_bills():
    """List household bills (utilities, insurance, internet, etc.).

    Returns confirmed bill series.
    """
    all_rows = list_recurring(status="confirmed")
    enriched = _enrich_series(all_rows)
    bills = [r for r in enriched if r.get("recurring_type") == "bill"]
    # Sort by is_essential first, then by amount
    bills.sort(key=lambda x: (not x.get("is_essential", False), abs(float(x.get("amount_mean") or 0))), reverse=True)
    return bills


@router.get("/subscriptions")
def list_subscriptions():
    """List subscription services (streaming, software, memberships).

    Returns confirmed subscription series.
    """
    all_rows = list_recurring(status="confirmed")
    enriched = _enrich_series(all_rows)
    subs = [r for r in enriched if r.get("recurring_type") == "subscription"]
    # Sort by annual_cost (highest first)
    subs.sort(key=lambda x: float(x.get("annual_cost") or 0), reverse=True)
    return subs


@router.get("/credit-cards")
def list_credit_cards():
    """List credit card payments.

    Returns confirmed credit card payment series.
    """
    all_rows = list_recurring(status="confirmed")
    enriched = _enrich_series(all_rows)
    cards = [r for r in enriched if r.get("recurring_type") == "credit_card"]
    # Sort by amount (highest first)
    cards.sort(key=lambda x: abs(float(x.get("amount_mean") or 0)), reverse=True)
    return cards


@router.get("/insurance")
def list_insurance():
    """List insurance payments (auto, home, health, life, pet).

    Returns confirmed insurance series.
    """
    all_rows = list_recurring(status="confirmed")
    enriched = _enrich_series(all_rows)
    insurance = [r for r in enriched if r.get("recurring_type") == "insurance"]
    # Sort by amount (highest first)
    insurance.sort(key=lambda x: abs(float(x.get("amount_mean") or 0)), reverse=True)
    return insurance


@router.get("/summary")
def get_recurring_summary():
    """Get a summary of all recurring charges by type.

    Returns counts and totals for each type (subscriptions, bills, loans, credit cards).
    """
    all_rows = list_recurring(status="confirmed")
    enriched = _enrich_series(all_rows)

    summary = {
        "total_series": len(enriched),
        "total_monthly": 0.0,
        "total_annual": 0.0,
        "by_type": {},
        "essential_monthly": 0.0,
        "discretionary_monthly": 0.0,
    }

    type_buckets = {
        "subscription": {"count": 0, "monthly": 0.0, "annual": 0.0, "series": []},
        "bill": {"count": 0, "monthly": 0.0, "annual": 0.0, "series": []},
        "loan": {"count": 0, "monthly": 0.0, "annual": 0.0, "series": []},
        "credit_card": {"count": 0, "monthly": 0.0, "annual": 0.0, "series": []},
        "insurance": {"count": 0, "monthly": 0.0, "annual": 0.0, "series": []},
        "unknown": {"count": 0, "monthly": 0.0, "annual": 0.0, "series": []},
    }

    for r in enriched:
        rec_type = r.get("recurring_type", "unknown")
        if rec_type not in type_buckets:
            rec_type = "unknown"

        amount = abs(float(r.get("amount_mean") or 0))
        annual = float(r.get("annual_cost") or 0)
        cadence = r.get("cadence", "monthly")

        # Calculate monthly equivalent
        monthly_multipliers = {
            "weekly": 4.33,
            "biweekly": 2.17,
            "monthly": 1,
            "quarterly": 0.33,
            "semi_annual": 0.17,
            "annual": 0.083,
        }
        monthly = amount * monthly_multipliers.get(cadence, 1)

        type_buckets[rec_type]["count"] += 1
        type_buckets[rec_type]["monthly"] += monthly
        type_buckets[rec_type]["annual"] += annual
        type_buckets[rec_type]["series"].append({
            "merchant": r.get("merchant"),
            "amount": amount,
            "cadence": cadence,
            "sub_category": r.get("sub_category"),
        })

        summary["total_monthly"] += monthly
        summary["total_annual"] += annual

        if r.get("is_essential"):
            summary["essential_monthly"] += monthly
        else:
            summary["discretionary_monthly"] += monthly

    # Clean up series lists (just top 5 by amount for each type)
    for rec_type in type_buckets:
        type_buckets[rec_type]["series"] = sorted(
            type_buckets[rec_type]["series"],
            key=lambda x: x["amount"],
            reverse=True
        )[:5]
        type_buckets[rec_type]["monthly"] = round(type_buckets[rec_type]["monthly"], 2)
        type_buckets[rec_type]["annual"] = round(type_buckets[rec_type]["annual"], 2)

    summary["by_type"] = type_buckets
    summary["total_monthly"] = round(summary["total_monthly"], 2)
    summary["total_annual"] = round(summary["total_annual"], 2)
    summary["essential_monthly"] = round(summary["essential_monthly"], 2)
    summary["discretionary_monthly"] = round(summary["discretionary_monthly"], 2)

    return summary


@router.get("/essential")
def list_essential():
    """List all essential recurring charges (bills that must be paid).

    Returns confirmed series marked as essential.
    """
    all_rows = list_recurring(status="confirmed")
    enriched = _enrich_series(all_rows)
    essential = [r for r in enriched if r.get("is_essential")]
    # Sort by amount (highest first)
    essential.sort(key=lambda x: abs(float(x.get("amount_mean") or 0)), reverse=True)
    return essential


@router.get("/discretionary")
def list_discretionary():
    """List all discretionary recurring charges (optional subscriptions).

    Returns confirmed series NOT marked as essential.
    """
    all_rows = list_recurring(status="confirmed")
    enriched = _enrich_series(all_rows)
    discretionary = [r for r in enriched if not r.get("is_essential")]
    # Sort by annual_cost (highest first)
    discretionary.sort(key=lambda x: float(x.get("annual_cost") or 0), reverse=True)
    return discretionary


# =============================================================================
# PHASE 2: LLM INTELLIGENCE ENDPOINTS
# =============================================================================

@router.get("/intelligence/cache-stats")
def get_intelligence_cache_stats():
    """Get statistics about the merchant intelligence cache.

    Returns cache size, hit rate, and provider distribution.
    """
    try:
        from ...merchant_intelligence import get_cache_stats
        return get_cache_stats()
    except Exception as e:
        return {"error": str(e), "total_entries": 0}


class AnalyzeRequest(BaseModel):
    description: str
    amount: float = 0.0
    use_cache: bool = True


@router.post("/intelligence/analyze")
async def analyze_merchant(body: AnalyzeRequest):
    """Analyze a single transaction description using LLM.

    This endpoint tests the LLM integration by analyzing a description
    and returning the extracted merchant info and classification.

    Args:
        description: Transaction description to analyze
        amount: Transaction amount (helps with classification)
        use_cache: Whether to use the merchant intelligence cache

    Returns:
        MerchantIntelligence result with clean_merchant_name, recurring_type, etc.
    """
    try:
        from ...merchant_intelligence import analyze_merchant_with_llm

        result = await analyze_merchant_with_llm(
            body.description,
            body.amount,
            use_cache=body.use_cache,
        )

        return {
            "clean_merchant_name": result.clean_merchant_name,
            "recurring_type": result.recurring_type,
            "sub_category": result.sub_category,
            "is_essential": result.is_essential,
            "confidence": result.confidence,
            "provider": result.provider,
            "model": result.model,
            "latency_ms": result.latency_ms,
            "from_cache": result.from_cache,
        }
    except Exception as e:
        return {"error": str(e), "description": body.description}


@router.post("/reclassify-with-llm")
async def reclassify_with_llm(limit: int = Query(100, ge=1, le=1000)):
    """Reclassify unknown recurring series using LLM.

    This uses the LLM to classify series that pattern matching couldn't identify.
    Results are cached to avoid redundant LLM calls.

    Args:
        limit: Maximum number of unknown series to reclassify

    Returns:
        Count of series reclassified and details
    """
    conn = get_conn()

    # Find series with unknown type
    rows = conn.execute("""
        SELECT id, name, amount_mean
        FROM recurring_series
        WHERE recurring_type IS NULL OR recurring_type = 'unknown'
        LIMIT ?
    """, [limit]).fetchall()

    if not rows:
        return {"reclassified": 0, "message": "No unknown series to classify"}

    try:
        from ...merchant_intelligence import analyze_merchant_with_llm

        reclassified = 0
        details = []

        for row in rows:
            series_id, name, amount_mean = row
            if not name:
                continue

            try:
                result = await analyze_merchant_with_llm(
                    name,
                    float(amount_mean or 0),
                    use_cache=True,
                )

                if result.recurring_type != "unknown" and result.confidence >= 0.5:
                    # Update the series with LLM classification
                    conn.execute("""
                        UPDATE recurring_series SET
                            recurring_type = ?,
                            sub_category = ?,
                            is_essential = ?,
                            display_name = COALESCE(display_name, ?),
                            llm_confidence = ?,
                            llm_provider = ?,
                            llm_classified_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, [
                        result.recurring_type,
                        result.sub_category,
                        result.is_essential,
                        result.clean_merchant_name if result.clean_merchant_name != "Unknown" else None,
                        result.confidence,
                        result.provider,
                        series_id,
                    ])
                    reclassified += 1
                    details.append({
                        "series_id": series_id,
                        "name": name,
                        "new_type": result.recurring_type,
                        "confidence": result.confidence,
                        "provider": result.provider,
                        "from_cache": result.from_cache,
                    })

            except Exception as e:
                details.append({
                    "series_id": series_id,
                    "name": name,
                    "error": str(e),
                })

        return {
            "reclassified": reclassified,
            "total_processed": len(rows),
            "details": details,
        }

    except ImportError as e:
        return {"error": f"LLM module not available: {e}", "reclassified": 0}


@router.post("/intelligence/cleanup-cache")
def cleanup_intelligence_cache(max_age_days: int = Query(60, ge=7, le=365)):
    """Remove expired entries from the merchant intelligence cache.

    Args:
        max_age_days: Remove entries older than this many days

    Returns:
        Count of entries removed
    """
    try:
        from ...merchant_intelligence import cleanup_expired_cache
        removed = cleanup_expired_cache(max_age_days=max_age_days)
        return {"removed": removed, "max_age_days": max_age_days}
    except Exception as e:
        return {"error": str(e), "removed": 0}


# =============================================================================
# PHASE 3: INSIGHTS ENGINE ENDPOINTS
# =============================================================================

@router.get("/insights")
def get_recurring_insights(limit: int = Query(10, ge=1, le=50)):
    """Get natural language insights about recurring charges.

    Returns prioritized insights including:
    - Total recurring spend summary
    - Upcoming payments
    - Price increase alerts
    - Cancellation risk warnings
    - Savings opportunities

    Args:
        limit: Maximum number of insights to return
    """
    try:
        from ...recurring_insights import get_recurring_insights_engine
        engine = get_recurring_insights_engine()
        insights = engine.generate_insights(limit=limit)

        return [
            {
                "id": i.insight_id,
                "type": i.insight_type.value,
                "title": i.title,
                "message": i.message,
                "data": i.data,
                "priority": i.priority,
                "expires_at": i.expires_at.isoformat() if i.expires_at else None,
                "actionable": i.actionable,
                "action_label": i.action_label,
                "action_series_id": i.action_series_id,
            }
            for i in insights
        ]
    except Exception as e:
        return {"error": str(e), "insights": []}


@router.get("/insights/cash-flow")
def get_cash_flow_forecast(
    months: int = Query(3, ge=1, le=12),
    include_pending: bool = Query(False),
):
    """Get cash flow forecast including recurring charges.

    Projects income, recurring expenses, and discretionary spending
    for the next N months.

    Args:
        months: Number of months to forecast (1-12)
        include_pending: Include pending (unconfirmed) recurring series
    """
    try:
        from ...recurring_insights import get_recurring_insights_engine
        engine = get_recurring_insights_engine()
        forecasts = engine.forecast_cash_flow(months=months, include_pending=include_pending)

        return [
            {
                "month": f.forecast_date.isoformat(),
                "expected_income": round(f.expected_income, 2),
                "expected_recurring": round(f.expected_recurring, 2),
                "expected_discretionary": round(f.expected_discretionary, 2),
                "net_cash_flow": round(f.net_cash_flow, 2),
                "recurring_breakdown": f.recurring_breakdown,
                "confidence": f.confidence,
            }
            for f in forecasts
        ]
    except Exception as e:
        return {"error": str(e), "forecasts": []}


@router.get("/insights/cancellation-risks")
def get_cancellation_risks(limit: int = Query(20, ge=1, le=100)):
    """Get cancellation risk scores for recurring charges.

    Analyzes factors like price hikes, usage patterns, and cost
    to predict likelihood of cancellation.

    Args:
        limit: Maximum number of results
    """
    try:
        from ...recurring_insights import get_recurring_insights_engine
        engine = get_recurring_insights_engine()
        risks = engine.calculate_cancellation_risks(limit=limit)

        return [
            {
                "series_id": r.series_id,
                "merchant": r.merchant,
                "risk_level": r.risk_level.value,
                "risk_score": r.risk_score,
                "risk_factors": r.risk_factors,
                "recommendation": r.recommendation,
                "potential_annual_savings": round(r.potential_savings, 2),
            }
            for r in risks
        ]
    except Exception as e:
        return {"error": str(e), "risks": []}


@router.get("/insights/optimizations")
def get_optimization_suggestions(limit: int = Query(10, ge=1, le=50)):
    """Get optimization suggestions for recurring charges.

    Suggests ways to save money including:
    - Consolidating similar services
    - Switching to annual billing
    - Downgrading plans
    - Negotiating rates

    Args:
        limit: Maximum number of suggestions
    """
    try:
        from ...recurring_insights import get_recurring_insights_engine
        engine = get_recurring_insights_engine()
        suggestions = engine.generate_optimization_suggestions(limit=limit)

        return [
            {
                "id": s.suggestion_id,
                "title": s.title,
                "description": s.description,
                "category": s.category,
                "affected_series": s.affected_series,
                "potential_monthly_savings": round(s.potential_monthly_savings, 2),
                "potential_annual_savings": round(s.potential_annual_savings, 2),
                "confidence": s.confidence,
                "action_steps": s.action_steps,
                "priority": s.priority,
            }
            for s in suggestions
        ]
    except Exception as e:
        return {"error": str(e), "suggestions": []}


@router.get("/insights/upcoming")
def get_upcoming_payments(days: int = Query(30, ge=1, le=90)):
    """Get upcoming recurring payments.

    Lists all confirmed recurring charges expected in the next N days.
    Dynamically calculates next due date based on last_date and cadence.

    Args:
        days: Number of days to look ahead
    """
    today = date.today()
    end_date = today + timedelta(days=days)

    conn = get_conn()
    # Fetch all confirmed series - prefer stored next_date over calculated
    result = conn.execute("""
        SELECT
            rs.id, rs.display_name, rs.name, rs.amount_mean,
            rs.last_date, rs.cadence, rs.recurring_type, rs.is_essential,
            rs.next_date
        FROM recurring_series rs
        WHERE rs.status = 'confirmed'
          AND (rs.next_date IS NOT NULL OR (rs.last_date IS NOT NULL AND rs.cadence IS NOT NULL))
    """).fetchall()

    upcoming = []
    for r in result:
        series_id = r[0]
        display_name = r[1] or r[2]
        amount_mean = r[3]
        last_date_str = r[4]
        cadence = r[5]
        recurring_type = r[6]
        is_essential = r[7]
        stored_next_date = r[8]

        # Use stored next_date if available, otherwise calculate from last_date
        next_due = None
        if stored_next_date:
            try:
                if isinstance(stored_next_date, date):
                    next_due = stored_next_date
                elif isinstance(stored_next_date, str):
                    next_due = date.fromisoformat(stored_next_date.split('T')[0])
            except (ValueError, TypeError):
                pass

        # Fall back to calculated date if no stored next_date
        if not next_due and last_date_str and cadence:
            try:
                if isinstance(last_date_str, date):
                    last_date_val = last_date_str
                elif isinstance(last_date_str, str):
                    last_date_val = date.fromisoformat(last_date_str.split('T')[0])
                else:
                    continue
                next_due = calculate_next_due_date(last_date_val, cadence)
            except (ValueError, TypeError):
                continue

        if not next_due:
            continue

        # Filter to the requested date range
        if next_due >= today and next_due <= end_date:
            # Normalize type to new format
            type_map = {
                "subscriptions": "subscription",
                "rent_and_utilities": "bill",
                "loan_payments": "loan",
            }
            normalized_type = type_map.get(recurring_type, recurring_type)

            upcoming.append({
                "series_id": series_id,
                "name": display_name,  # Frontend expects 'name'
                "merchant": display_name,  # Keep for backwards compat
                "amount": round(abs(float(amount_mean or 0)), 2),
                "date": next_due.isoformat(),
                "cadence": cadence,
                "type": normalized_type,
                "is_essential": bool(is_essential),
            })

    # Sort by date
    upcoming.sort(key=lambda x: x["date"])
    return upcoming


@router.get("/insights/spending-by-type")
def get_spending_by_type():
    """Get recurring spending breakdown by type.

    Returns monthly and annual totals for each recurring type
    (subscription, bill, loan, credit_card, insurance).
    """
    conn = get_conn()

    result = conn.execute("""
        SELECT
            COALESCE(recurring_type, 'unknown') as type,
            COUNT(*) as count,
            SUM(CASE
                WHEN cadence = 'monthly' THEN ABS(amount_mean)
                WHEN cadence = 'weekly' THEN ABS(amount_mean) * 4.33
                WHEN cadence = 'biweekly' THEN ABS(amount_mean) * 2.17
                WHEN cadence = 'quarterly' THEN ABS(amount_mean) / 3
                WHEN cadence = 'semi_annual' THEN ABS(amount_mean) / 6
                WHEN cadence = 'annual' THEN ABS(amount_mean) / 12
                ELSE ABS(amount_mean)
            END) as monthly_total,
            SUM(COALESCE(annual_cost, ABS(amount_mean) * 12)) as annual_total
        FROM recurring_series
        WHERE status = 'confirmed'
        GROUP BY COALESCE(recurring_type, 'unknown')
        ORDER BY monthly_total DESC
    """).fetchall()

    types = []
    grand_monthly = 0.0
    grand_annual = 0.0

    for row in result:
        monthly = float(row[2] or 0)
        annual = float(row[3] or 0)
        grand_monthly += monthly
        grand_annual += annual
        types.append({
            "type": row[0],
            "count": int(row[1]),
            "monthly_total": round(monthly, 2),
            "annual_total": round(annual, 2),
        })

    return {
        "by_type": types,
        "total_monthly": round(grand_monthly, 2),
        "total_annual": round(grand_annual, 2),
    }


# =============================================================================
# PHASE 3.5: AI WORKFLOW & LEARNING ENDPOINTS
# =============================================================================

class FeedbackRequest(BaseModel):
    series_id: str
    original_type: str
    corrected_type: Optional[str] = None
    was_correct: bool
    merchant_pattern: Optional[str] = None
    is_essential: bool = False
    corrected_is_essential: Optional[bool] = None


@router.post("/ai-workflow/feedback")
async def submit_recurring_feedback(body: FeedbackRequest):
    """Submit feedback to train the recurring AI system.

    When a user confirms or corrects a recurring classification,
    this endpoint learns from that feedback to improve future accuracy.

    Args:
        series_id: The recurring series ID
        original_type: The original classification (subscription, bill, loan, etc.)
        corrected_type: If incorrect, the correct type
        was_correct: Whether the original classification was correct
        merchant_pattern: The merchant name/pattern to learn from
        is_essential: Whether the original was marked essential
        corrected_is_essential: If incorrect, the correct essential flag
    """
    try:
        from ...recurring_ai_workflow import learn_from_recurring_feedback

        # Get merchant pattern from series if not provided
        merchant = body.merchant_pattern
        if not merchant:
            conn = get_conn()
            row = conn.execute(
                "SELECT COALESCE(display_name, name) FROM recurring_series WHERE id = ?",
                [body.series_id]
            ).fetchone()
            merchant = row[0] if row else ""

        result = await learn_from_recurring_feedback(
            series_id=body.series_id,
            original_type=body.original_type,
            corrected_type=body.corrected_type,
            was_correct=body.was_correct,
            merchant_pattern=merchant or "",
            is_essential=body.is_essential,
            corrected_is_essential=body.corrected_is_essential
        )

        return result

    except Exception as e:
        return {"error": str(e), "status": "failed"}


@router.get("/ai-workflow/stats")
def get_ai_learning_stats():
    """Get statistics about the recurring AI learning system.

    Returns information about:
    - Merchant memory size and quality
    - Feedback accuracy rates
    - AI review counts
    - Recent learning activity
    """
    try:
        from ...recurring_ai_workflow import get_recurring_learning_stats
        return get_recurring_learning_stats()
    except Exception as e:
        return {"error": str(e)}


class ReviewRequest(BaseModel):
    series_id: str
    merchant_name: str
    description: str
    amount: float
    recurring_type: str
    pattern_confidence: float
    cadence: str = "monthly"
    use_llm: bool = True


@router.post("/ai-workflow/review")
async def review_with_ai(body: ReviewRequest):
    """Review a recurring classification with AI.

    Takes pattern-based classification results and enhances them with:
    - Merchant memory lookup (learned patterns)
    - LLM review for low-confidence cases

    Returns enhanced classification with AI reasoning.
    """
    try:
        from ...recurring_ai_workflow import review_recurring_with_ai

        result = await review_recurring_with_ai(
            series_id=body.series_id,
            merchant_name=body.merchant_name,
            description=body.description,
            amount=body.amount,
            recurring_type=body.recurring_type,
            pattern_confidence=body.pattern_confidence,
            cadence=body.cadence,
            use_llm=body.use_llm
        )

        return result

    except Exception as e:
        return {"error": str(e)}


@router.post("/ai-workflow/batch-review")
async def batch_review_pending(
    limit: int = Query(50, ge=1, le=200),
    use_llm: bool = Query(True)
):
    """Batch review pending/low-confidence recurring series with AI.

    Processes series that need review and enhances their classifications.
    Uses merchant memory first, then LLM for unknowns.

    Args:
        limit: Maximum series to review
        use_llm: Whether to use LLM for unknown classifications
    """
    try:
        from ...recurring_ai_workflow import get_recurring_ai_workflow

        engine = get_recurring_ai_workflow()
        result = await engine.batch_review_pending_series(limit=limit, use_llm=use_llm)

        return result

    except Exception as e:
        return {"error": str(e)}


@router.post("/ai-workflow/backfill-memory")
async def backfill_merchant_memory():
    """Backfill merchant memory from existing recurring series.

    This bootstraps the learning system by extracting patterns
    from confirmed recurring series. Use this to initialize
    the AI learning system.
    """
    try:
        from ...recurring_ai_workflow import get_recurring_ai_workflow

        engine = get_recurring_ai_workflow()
        result = await engine.backfill_merchant_memory()

        return result

    except Exception as e:
        return {"error": str(e)}


@router.get("/ai-workflow/accuracy")
def get_accuracy_by_type():
    """Get classification accuracy broken down by recurring type.

    Returns accuracy rates for subscriptions, bills, loans, etc.
    based on user feedback.
    """
    try:
        from ...recurring_ai_workflow import get_recurring_ai_workflow

        engine = get_recurring_ai_workflow()
        return engine.get_accuracy_by_type()

    except Exception as e:
        return {"error": str(e)}


@router.post("/confirm/{series_id}/with-learning")
async def confirm_with_learning(series_id: str):
    """Confirm a recurring series AND learn from it.

    This confirms the series and also records positive feedback
    to train the AI system.
    """
    # First confirm normally (call service directly, not the route handler)
    result = confirm_series(series_id)

    # Then record feedback
    try:
        from ...recurring_ai_workflow import learn_from_recurring_feedback

        conn = get_conn()
        row = conn.execute("""
            SELECT COALESCE(display_name, name), recurring_type, is_essential
            FROM recurring_series WHERE id = ?
        """, [series_id]).fetchone()

        if row:
            await learn_from_recurring_feedback(
                series_id=series_id,
                original_type=row[1] or "unknown",
                corrected_type=None,
                was_correct=True,
                merchant_pattern=row[0] or "",
                is_essential=bool(row[2]),
                corrected_is_essential=None
            )
    except Exception as e:
        # Don't fail the confirm if learning fails
        pass

    return result


@router.post("/fix-next-dates")
def fix_all_next_dates():
    """Recalculate next_date for all active series based on last_date + cadence.

    This fixes stale next_date values that are in the past.
    Processes both 'confirmed' and 'pending' series.
    """
    conn = get_conn()
    today = date.today()

    rows = conn.execute("""
        SELECT id, last_date, cadence, anchor_day
        FROM recurring_series
        WHERE status IN ('confirmed', 'pending') AND last_date IS NOT NULL
    """).fetchall()

    updated = 0
    fixed_details = []

    for row in rows:
        series_id, last_date_str, cadence, anchor_day = row

        # Parse last_date
        try:
            if isinstance(last_date_str, date):
                last_date_val = last_date_str
            elif isinstance(last_date_str, str):
                last_date_val = date.fromisoformat(str(last_date_str)[:10])
            else:
                continue
        except (ValueError, TypeError):
            continue

        # Calculate next_date by projecting forward until future
        next_date = calculate_next_due_date(last_date_val, cadence or 'monthly')

        if next_date:
            conn.execute(
                "UPDATE recurring_series SET next_date = ? WHERE id = ?",
                [next_date.isoformat(), series_id]
            )
            updated += 1
            fixed_details.append({
                "series_id": series_id,
                "last_date": str(last_date_val),
                "new_next_date": next_date.isoformat()
            })

    return {
        "updated": updated,
        "message": f"Fixed {updated} series next_date values",
        "details": fixed_details[:20]  # Return first 20 for verification
    }


@router.post("/normalize-types")
def normalize_recurring_types():
    """Normalize Plaid-style recurring types to internal format.

    Converts:
    - rent_and_utilities → bill
    - loan_payments → loan
    - subscriptions → subscription
    """
    conn = get_conn()

    # Define normalizations
    normalizations = [
        ("rent_and_utilities", "bill"),
        ("loan_payments", "loan"),
        ("subscriptions", "subscription"),
    ]

    total_updated = 0
    details = []

    for old_type, new_type in normalizations:
        result = conn.execute(
            "UPDATE recurring_series SET recurring_type = ? WHERE recurring_type = ?",
            [new_type, old_type]
        )
        count = result.rowcount
        total_updated += count
        if count > 0:
            details.append({"from": old_type, "to": new_type, "count": count})

    return {
        "updated": total_updated,
        "message": f"Normalized {total_updated} series",
        "details": details
    }


@router.get("/detect-cancelled")
def detect_cancelled_services():
    """Detect recurring services that appear to have been cancelled.

    Uses intelligence based on:
    - Number of missed expected payments (missed_cycles)
    - Time since last transaction vs expected cadence

    Rules:
    - If missed_cycles >= 2, flag as likely cancelled
    - Weekly: no payment in 3+ weeks
    - Biweekly: no payment in 5+ weeks
    - Monthly: no payment in 2+ months
    - Quarterly: no payment in 6+ months
    - Annual: no payment in 14+ months
    """
    conn = get_conn()
    today = date.today()

    # Cadence to days mapping
    cadence_days = {
        'weekly': 7,
        'biweekly': 14,
        'monthly': 30,
        'quarterly': 91,
        'semi_annual': 182,
        'annual': 365,
    }

    rows = conn.execute("""
        SELECT id, name, display_name, last_date, cadence, recurring_type, amount_mean, status
        FROM recurring_series
        WHERE status IN ('confirmed', 'pending')
          AND last_date IS NOT NULL
        ORDER BY last_date
    """).fetchall()

    likely_cancelled = []
    still_active = []

    for row in rows:
        series_id, name, display_name, last_date_str, cadence, rec_type, amount, status = row

        # Parse last_date
        try:
            if isinstance(last_date_str, date):
                last_date_val = last_date_str
            else:
                last_date_val = date.fromisoformat(str(last_date_str)[:10])
        except (ValueError, TypeError):
            continue

        days_since = (today - last_date_val).days
        cadence_interval = cadence_days.get(cadence, 30)
        missed_cycles = days_since / cadence_interval

        series_info = {
            "id": series_id,
            "name": display_name or name,
            "last_date": last_date_val.isoformat(),
            "days_since": days_since,
            "cadence": cadence,
            "missed_cycles": round(missed_cycles, 1),
            "amount": abs(float(amount or 0)),
            "recurring_type": rec_type,
            "status": status,
        }

        # Flag as likely cancelled if 2+ cycles missed
        if missed_cycles >= 2:
            series_info["reason"] = f"No payment in {days_since} days ({missed_cycles:.1f} missed {cadence} cycles)"
            likely_cancelled.append(series_info)
        else:
            still_active.append(series_info)

    return {
        "likely_cancelled": likely_cancelled,
        "likely_cancelled_count": len(likely_cancelled),
        "still_active_count": len(still_active),
        "total_analyzed": len(rows),
        "note": "Review 'likely_cancelled' items and use POST /recurring/{id}/cancel to mark as cancelled"
    }


@router.post("/{series_id}/cancel")
def cancel_series(series_id: str):
    """Mark a recurring series as cancelled.

    Sets status to 'cancelled' so it no longer appears in bills/calendar.
    """
    conn = get_conn()

    # Verify series exists
    row = conn.execute(
        "SELECT name, display_name, status FROM recurring_series WHERE id = ?",
        [series_id]
    ).fetchone()

    if not row:
        return {"error": "Series not found", "id": series_id}

    if row[2] == 'cancelled':
        return {"message": "Already cancelled", "id": series_id, "name": row[1] or row[0]}

    conn.execute(
        "UPDATE recurring_series SET status = 'cancelled' WHERE id = ?",
        [series_id]
    )

    return {
        "message": "Series cancelled",
        "id": series_id,
        "name": row[1] or row[0]
    }


@router.post("/bulk-cancel")
def bulk_cancel_series(series_ids: list[str]):
    """Cancel multiple recurring series at once."""
    conn = get_conn()

    cancelled = []
    errors = []

    for series_id in series_ids:
        row = conn.execute(
            "SELECT name, display_name FROM recurring_series WHERE id = ?",
            [series_id]
        ).fetchone()

        if not row:
            errors.append({"id": series_id, "error": "Not found"})
            continue

        conn.execute(
            "UPDATE recurring_series SET status = 'cancelled' WHERE id = ?",
            [series_id]
        )
        cancelled.append({"id": series_id, "name": row[1] or row[0]})

    return {
        "cancelled": cancelled,
        "cancelled_count": len(cancelled),
        "errors": errors
    }


@router.post("/auto-cancel-detected")
def auto_cancel_detected():
    """Detect and auto-cancel recurring services that appear to have been cancelled.

    Uses the detect-cancelled logic (missed_cycles >= 2) to find likely cancelled
    services and marks them as cancelled.

    Returns the list of cancelled items and savings info.
    """
    conn = get_conn()
    today = date.today()

    cadence_days = {
        'weekly': 7,
        'biweekly': 14,
        'monthly': 30,
        'quarterly': 91,
        'semiannual': 182,
        'annual': 365,
    }

    # Get all confirmed/pending series
    rows = conn.execute("""
        SELECT id, name, display_name, cadence, last_date, amount_mean
        FROM recurring_series
        WHERE status IN ('confirmed', 'pending')
        AND last_date IS NOT NULL
    """).fetchall()

    cancelled = []
    total_monthly_savings = 0.0

    cadence_multipliers = {
        'weekly': 4.33,
        'biweekly': 2.17,
        'monthly': 1,
        'quarterly': 0.33,
        'semiannual': 0.167,
        'annual': 0.083,
    }

    for row in rows:
        series_id = row[0]
        name = row[1] or row[2]
        cadence = row[3] or 'monthly'
        last_date_str = row[4]
        amount = abs(row[5] or 0)

        if not last_date_str:
            continue

        last_dt = date.fromisoformat(last_date_str)
        days_since = (today - last_dt).days
        cadence_interval = cadence_days.get(cadence, 30)
        missed_cycles = days_since / cadence_interval

        # If 2+ cycles missed, mark as cancelled
        if missed_cycles >= 2:
            conn.execute(
                "UPDATE recurring_series SET status = 'cancelled' WHERE id = ?",
                [series_id]
            )

            monthly_amount = amount * cadence_multipliers.get(cadence, 1)
            total_monthly_savings += monthly_amount

            cancelled.append({
                "id": series_id,
                "name": name,
                "amount": round(amount, 2),
                "cadence": cadence,
                "missed_cycles": round(missed_cycles, 1),
                "monthly_equivalent": round(monthly_amount, 2),
            })

    return {
        "cancelled": cancelled,
        "cancelled_count": len(cancelled),
        "monthly_savings": round(total_monthly_savings, 2),
        "annual_savings": round(total_monthly_savings * 12, 2),
        "message": f"Auto-cancelled {len(cancelled)} inactive recurring series"
    }


@router.post("/auto-link")
def auto_link_transactions():
    """Auto-link unlinked transactions to existing recurring series.

    Finds transactions that match existing series by merchant pattern
    but aren't linked yet. Updates last_date for affected series.

    Should be called after importing new transactions to keep
    recurring series up-to-date.
    """
    result = auto_link_transactions_to_series()
    return result


@router.post("/cleanup-duplicates")
def cleanup_duplicate_series():
    """Find and remove duplicate recurring series by merchant.

    Keeps the series with the most recent last_date for each merchant,
    deletes older duplicates.
    """
    conn = get_conn()

    # Find duplicates: same display_name (case-insensitive) and status=confirmed
    duplicates = conn.execute("""
        SELECT
            LOWER(COALESCE(display_name, name)) as merchant_key,
            GROUP_CONCAT(id) as ids,
            COUNT(*) as cnt
        FROM recurring_series
        WHERE status = 'confirmed'
        GROUP BY LOWER(COALESCE(display_name, name))
        HAVING COUNT(*) > 1
    """).fetchall()

    deleted_count = 0
    deleted_ids = []

    for dup in duplicates:
        merchant_key, ids_str, count = dup
        ids = ids_str.split(',')

        # Get details for each duplicate to pick the best one
        series_data = conn.execute(f"""
            SELECT id, last_date, occurrences, amount_mean
            FROM recurring_series
            WHERE id IN ({','.join(['?'] * len(ids))})
            ORDER BY last_date DESC NULLS LAST, occurrences DESC
        """, ids).fetchall()

        if len(series_data) > 1:
            # Keep the first (most recent), delete the rest
            keep_id = series_data[0][0]
            for row in series_data[1:]:
                delete_id = row[0]
                # Get transactions from the duplicate series
                dup_txs = conn.execute(
                    "SELECT tx_id FROM recurring_tx WHERE series_id = ?",
                    [delete_id]
                ).fetchall()

                for tx_row in dup_txs:
                    tx_id = tx_row[0]
                    # Check if this tx is already linked to the kept series
                    exists = conn.execute(
                        "SELECT 1 FROM recurring_tx WHERE series_id = ? AND tx_id = ?",
                        [keep_id, tx_id]
                    ).fetchone()
                    if not exists:
                        # Move the transaction to the kept series
                        conn.execute(
                            "UPDATE recurring_tx SET series_id = ? WHERE series_id = ? AND tx_id = ?",
                            [keep_id, delete_id, tx_id]
                        )
                    else:
                        # Already exists, just delete the duplicate link
                        conn.execute(
                            "DELETE FROM recurring_tx WHERE series_id = ? AND tx_id = ?",
                            [delete_id, tx_id]
                        )

                # Delete the duplicate series
                conn.execute("DELETE FROM recurring_series WHERE id = ?", [delete_id])
                deleted_count += 1
                deleted_ids.append({"deleted": delete_id, "kept": keep_id, "merchant": merchant_key})

    return {
        "deleted": deleted_count,
        "message": f"Removed {deleted_count} duplicate series",
        "details": deleted_ids
    }


@router.post("/{series_id}/mark-paid")
def mark_series_paid(series_id: str):
    """Mark a recurring series as paid for the current period.

    Updates the last_date to today and recalculates next_date based on cadence.
    """
    conn = get_conn()
    today = date.today()

    # Get current series info
    row = conn.execute("""
        SELECT cadence FROM recurring_series WHERE id = ?
    """, [series_id]).fetchone()

    if not row:
        return {"error": "Series not found", "success": False}

    cadence = row[0] or "monthly"
    next_due = calculate_next_due_date(today, cadence)

    # Update last_date and next_date
    conn.execute("""
        UPDATE recurring_series
        SET last_date = ?, next_date = ?
        WHERE id = ?
    """, [today.isoformat(), next_due.isoformat() if next_due else None, series_id])

    return {
        "success": True,
        "series_id": series_id,
        "marked_paid_date": today.isoformat(),
        "next_due_date": next_due.isoformat() if next_due else None,
    }


@router.post("/{series_id}/skip-next")
def skip_next_payment(series_id: str):
    """Skip the next scheduled payment and advance next_date by one cycle.

    Useful when you've already paid outside the system or want to skip a payment.
    """
    conn = get_conn()

    # Get current series info
    row = conn.execute("""
        SELECT cadence, next_date, name, merchant FROM recurring_series WHERE id = ?
    """, [series_id]).fetchone()

    if not row:
        return {"error": "Series not found", "success": False}

    cadence = row[0] or "monthly"
    current_next = row[1]
    name = row[2] or row[3]

    # Calculate next date from current next_date (skip one cycle)
    if current_next:
        base_date = date.fromisoformat(current_next)
    else:
        base_date = date.today()

    new_next = calculate_next_due_date(base_date, cadence)

    # Update next_date
    conn.execute("""
        UPDATE recurring_series SET next_date = ? WHERE id = ?
    """, [new_next.isoformat() if new_next else None, series_id])

    return {
        "success": True,
        "series_id": series_id,
        "name": name,
        "skipped_date": current_next,
        "new_next_date": new_next.isoformat() if new_next else None,
        "message": f"Skipped payment, next due: {new_next.isoformat() if new_next else 'unknown'}"
    }


@router.post("/{series_id}/pause")
def pause_series(series_id: str):
    """Pause a recurring series temporarily.

    Sets status to 'paused'. The series won't appear in bills/calendar until resumed.
    """
    conn = get_conn()

    row = conn.execute("""
        SELECT name, merchant, status FROM recurring_series WHERE id = ?
    """, [series_id]).fetchone()

    if not row:
        return {"error": "Series not found", "success": False}

    name = row[0] or row[1]
    current_status = row[2]

    if current_status == 'paused':
        return {"message": "Already paused", "success": True, "id": series_id, "name": name}

    conn.execute("""
        UPDATE recurring_series SET status = 'paused' WHERE id = ?
    """, [series_id])

    return {
        "success": True,
        "series_id": series_id,
        "name": name,
        "previous_status": current_status,
        "new_status": "paused",
        "message": f"'{name}' has been paused"
    }


@router.post("/{series_id}/resume")
def resume_series(series_id: str):
    """Resume a paused recurring series.

    Sets status back to 'confirmed' and recalculates next_date if needed.
    """
    conn = get_conn()

    row = conn.execute("""
        SELECT name, merchant, status, cadence, last_date FROM recurring_series WHERE id = ?
    """, [series_id]).fetchone()

    if not row:
        return {"error": "Series not found", "success": False}

    name = row[0] or row[1]
    current_status = row[2]
    cadence = row[3] or "monthly"
    last_date_str = row[4]

    if current_status != 'paused':
        return {"message": f"Series is not paused (status: {current_status})", "success": False}

    # Recalculate next_date from last_date
    today = date.today()
    if last_date_str:
        last_dt = date.fromisoformat(last_date_str)
        next_dt = calculate_next_due_date(last_dt, cadence)
        # Project forward if next_date is in the past
        while next_dt and next_dt < today:
            next_dt = calculate_next_due_date(next_dt, cadence)
    else:
        next_dt = calculate_next_due_date(today, cadence)

    conn.execute("""
        UPDATE recurring_series SET status = 'confirmed', next_date = ? WHERE id = ?
    """, [next_dt.isoformat() if next_dt else None, series_id])

    return {
        "success": True,
        "series_id": series_id,
        "name": name,
        "new_status": "confirmed",
        "next_date": next_dt.isoformat() if next_dt else None,
        "message": f"'{name}' has been resumed"
    }


@router.post("/reject/{series_id}/with-learning")
async def reject_with_learning(series_id: str, reason: Optional[str] = None):
    """Reject a recurring series AND learn from it.

    This rejects the series and also records negative feedback
    to train the AI system.
    """
    # First reject normally (call service directly, not the route handler)
    result = reject_series(series_id)

    # Then record feedback
    try:
        from ...recurring_ai_workflow import learn_from_recurring_feedback

        conn = get_conn()
        row = conn.execute("""
            SELECT COALESCE(display_name, name), recurring_type, is_essential
            FROM recurring_series WHERE id = ?
        """, [series_id]).fetchone()

        if row:
            await learn_from_recurring_feedback(
                series_id=series_id,
                original_type=row[1] or "unknown",
                corrected_type=reason,  # Use rejection reason as the correction hint
                was_correct=False,
                merchant_pattern=row[0] or "",
                is_essential=bool(row[2]),
                corrected_is_essential=None
            )
    except Exception as e:
        # Don't fail the reject if learning fails
        pass

    return result


# =============================================================================
# Data Quality & Maintenance Endpoints
# =============================================================================

@router.post("/reclassify-all")
def reclassify_all_series():
    """Reclassify all recurring series using the latest pattern matching.

    This re-runs classify_recurring_type() on all series and updates:
    - recurring_type
    - sub_category
    - is_essential

    Useful after updating classification patterns.
    """
    conn = get_conn()

    rows = conn.execute("""
        SELECT id, name, display_name, amount_mean, recurring_type, sub_category
        FROM recurring_series
        WHERE status IN ('pending', 'confirmed')
    """).fetchall()

    updated = []
    unchanged = []

    for row in rows:
        series_id = row[0]
        name = row[1]
        display_name = row[2]
        amount = float(row[3] or 0)
        old_type = row[4]
        old_sub = row[5]

        # Try display_name first, then raw name
        desc = display_name or name or ""
        result = classify_recurring_type(desc, amount)

        # Fall back to raw name if unknown
        if result["recurring_type"] == "unknown" and display_name and name and display_name != name:
            result = classify_recurring_type(name, amount)

        new_type = result["recurring_type"]
        new_sub = result["sub_category"]
        is_essential = result.get("is_essential", False)

        # Only update if something changed
        if new_type != old_type or new_sub != old_sub:
            conn.execute("""
                UPDATE recurring_series
                SET recurring_type = ?, sub_category = ?, is_essential = ?
                WHERE id = ?
            """, [new_type, new_sub, 1 if is_essential else 0, series_id])

            updated.append({
                "id": series_id,
                "name": display_name or name,
                "old_type": old_type,
                "new_type": new_type,
                "old_sub": old_sub,
                "new_sub": new_sub,
            })
        else:
            unchanged.append(series_id)

    return {
        "updated_count": len(updated),
        "unchanged_count": len(unchanged),
        "updated": updated,
        "message": f"Reclassified {len(updated)} series, {len(unchanged)} unchanged"
    }


# False positive patterns - things that are NOT actually recurring subscriptions
FALSE_POSITIVE_PATTERNS = [
    # Gas stations / convenience stores
    r"sheetz",
    r"wawa",
    r"7[-\s]?eleven",
    r"circle\s*k",
    r"speedway",
    r"quiktrip",
    r"racetrac",
    r"pilot\s*flying",
    r"loves\s*travel",
    r"bp\s+\d",
    r"shell\s+\d",
    r"exxon",
    r"chevron",
    r"marathon\s+gas",
    # Tobacco / vape
    r"tobacco",
    r"smoke\s*shop",
    r"vape",
    r"cigar",
    # Fast food (unless it's delivery subscription)
    r"mcdonald",
    r"burger\s*king",
    r"wendy'?s",
    r"taco\s*bell",
    r"chick[-\s]?fil[-\s]?a",
    r"popeyes",
    r"kfc",
    r"arby'?s",
    r"sonic\s*drive",
    r"jack\s*in\s*the\s*box",
    # Generic retail stores
    r"dollar\s*(general|tree)",
    r"family\s*dollar",
    r"big\s*lots",
    # Restaurants (generic, not recurring)
    r"restaurant\s*\d",
    r"pizz",  # Pizza places
]


@router.post("/cleanup-false-positives")
def cleanup_false_positives():
    """Identify and reject series that are likely false positives.

    Matches against known non-recurring patterns like:
    - Gas stations (Sheetz, Wawa, etc.)
    - Fast food restaurants
    - Convenience stores
    - Tobacco shops

    Does NOT auto-reject - returns list for review with option to confirm.
    """
    conn = get_conn()

    rows = conn.execute("""
        SELECT id, name, display_name, amount_mean, cadence, occurrences, status
        FROM recurring_series
        WHERE status IN ('pending', 'confirmed')
    """).fetchall()

    flagged = []

    for row in rows:
        series_id = row[0]
        name = (row[1] or "").lower()
        display_name = (row[2] or "").lower()
        amount = abs(row[3] or 0)
        cadence = row[4]
        occurrences = row[5] or 0
        status = row[6]

        desc = display_name or name

        # Check against false positive patterns
        for pattern in FALSE_POSITIVE_PATTERNS:
            if re.search(pattern, desc, re.I):
                flagged.append({
                    "id": series_id,
                    "name": row[2] or row[1],
                    "matched_pattern": pattern,
                    "amount": round(amount, 2),
                    "cadence": cadence,
                    "occurrences": occurrences,
                    "status": status,
                })
                break

    return {
        "flagged_count": len(flagged),
        "flagged": flagged,
        "message": f"Found {len(flagged)} likely false positives. Use /reject-bulk to remove them."
    }


@router.post("/reject-false-positives")
def reject_false_positives():
    """Auto-reject all identified false positives.

    Runs cleanup-false-positives logic and rejects all matched series.
    """
    conn = get_conn()

    rows = conn.execute("""
        SELECT id, name, display_name
        FROM recurring_series
        WHERE status IN ('pending', 'confirmed')
    """).fetchall()

    rejected = []

    for row in rows:
        series_id = row[0]
        name = (row[1] or "").lower()
        display_name = (row[2] or "").lower()
        desc = display_name or name

        for pattern in FALSE_POSITIVE_PATTERNS:
            if re.search(pattern, desc, re.I):
                conn.execute(
                    "UPDATE recurring_series SET status = 'rejected' WHERE id = ?",
                    [series_id]
                )
                rejected.append({
                    "id": series_id,
                    "name": row[2] or row[1],
                    "matched_pattern": pattern,
                })
                break

    return {
        "rejected_count": len(rejected),
        "rejected": rejected,
        "message": f"Rejected {len(rejected)} false positives"
    }


# =============================================================================
# Consolidated Enriched Endpoint
# =============================================================================

@router.get("/all-enriched")
def get_all_enriched():
    """Get all recurring data in a single consolidated response.

    Returns:
    - all: All confirmed series
    - by_type: Series grouped by normalized type
    - summary: Counts and totals per type
    - pending_count: Number of pending suggestions

    This consolidates 6+ API calls into 1, reducing frontend overhead.
    """
    # Get all confirmed
    all_rows = list_recurring(status="confirmed")
    enriched = _enrich_series(all_rows)

    # Get pending count
    pending_rows = list_recurring(status="pending")
    pending_count = len(pending_rows)

    # Group by type
    by_type = {
        "subscription": [],
        "bill": [],
        "loan": [],
        "credit_card": [],
        "insurance": [],
        "unknown": [],
    }

    # Summary accumulators
    summary = {
        "total_count": 0,
        "total_monthly": 0.0,
        "essential_monthly": 0.0,
        "discretionary_monthly": 0.0,
        "by_type": {},
    }

    cadence_multipliers = {
        "weekly": 4.33,
        "biweekly": 2.17,
        "monthly": 1.0,
        "quarterly": 0.33,
        "semiannual": 0.167,
        "annual": 0.083,
    }

    for item in enriched:
        rec_type = item.get("recurring_type", "unknown")
        amount = abs(float(item.get("amount_mean") or 0))
        cadence = item.get("cadence", "monthly")
        is_essential = item.get("is_essential", False)

        # Calculate monthly equivalent
        multiplier = cadence_multipliers.get(cadence, 1.0)
        monthly = amount * multiplier
        item["monthly_equivalent"] = round(monthly, 2)

        # Add to type bucket
        if rec_type in by_type:
            by_type[rec_type].append(item)
        else:
            by_type["unknown"].append(item)

        # Update summary
        summary["total_count"] += 1
        summary["total_monthly"] += monthly
        if is_essential:
            summary["essential_monthly"] += monthly
        else:
            summary["discretionary_monthly"] += monthly

        # Per-type summary
        if rec_type not in summary["by_type"]:
            summary["by_type"][rec_type] = {"count": 0, "monthly": 0.0}
        summary["by_type"][rec_type]["count"] += 1
        summary["by_type"][rec_type]["monthly"] += monthly

    # Round summary values
    summary["total_monthly"] = round(summary["total_monthly"], 2)
    summary["essential_monthly"] = round(summary["essential_monthly"], 2)
    summary["discretionary_monthly"] = round(summary["discretionary_monthly"], 2)
    for t in summary["by_type"]:
        summary["by_type"][t]["monthly"] = round(summary["by_type"][t]["monthly"], 2)

    # Sort each type by amount
    for t in by_type:
        by_type[t].sort(key=lambda x: abs(float(x.get("amount_mean") or 0)), reverse=True)

    return {
        "all": enriched,
        "by_type": by_type,
        "summary": summary,
        "pending_count": pending_count,
    }
