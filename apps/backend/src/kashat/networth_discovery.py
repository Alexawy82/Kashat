"""
Net Worth Discovery - Scan existing data for potential assets/liabilities

REUSES:
- recurring_series table
- recurring_classifier.py classifications
- recurring.py detection results

NO NEW DETECTION - just queries what exists!
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .db import get_conn


class SuggestionType(Enum):
    PROPERTY = "property"
    VEHICLE = "vehicle"
    INVESTMENT = "investment"
    PRECIOUS_METAL = "precious_metal"
    LOAN = "loan"


@dataclass
class AssetSuggestion:
    """A suggested asset/liability from transaction patterns."""
    id: str
    type: SuggestionType
    subtype: str
    confidence: float
    source_recurring_id: Optional[str]
    source_data: Dict
    suggested_values: Dict


# Common mortgage lender patterns
MORTGAGE_PATTERNS = [
    'mortgage', 'home loan', 'wells fargo home', 'rocket mortgage',
    'quicken', 'pennymac', 'mr cooper', 'freedom mortgage', 'caliber home',
    'nationstar', 'loancare', 'cenlar', 'dovenmuehle', 'newrez',
    'flagstar', 'shellpoint', 'seterus', 'ocwen', 'phh mortgage',
    'guild mortgage', 'lakeview loan', 'roundpoint', 'homepoint',
]

# Common auto loan lender patterns
AUTO_LOAN_PATTERNS = [
    'toyota financial', 'honda financial', 'ally auto', 'capital one auto',
    'ford credit', 'gm financial', 'carmax', 'carvana', 'santander',
    'chase auto', 'us bank auto', 'westlake financial', 'exeter finance',
    'americredit', 'bmw financial', 'mercedes financial', 'vw credit',
    'hyundai capital', 'kia motors finance', 'nissan motor acceptance',
]

# Investment/retirement patterns
INVESTMENT_PATTERNS = [
    'fidelity', 'vanguard', 'schwab', 'ameritrade', 'etrade',
    '401k', 'ira', 'roth', 'retirement', 'tsp contribution',
    'betterment', 'wealthfront', 'robinhood', 'merrill',
]

# Precious metals dealers
METAL_DEALER_PATTERNS = [
    'apmex', 'jm bullion', 'sd bullion', 'money metals', 'provident metals',
    'silver gold bull', 'gainesville coins', 'goldsilver', 'bullionvault',
    'kitco', 'pmsforsale', 'monument metals', 'bgasc',
]

# Home insurance patterns (may indicate property)
HOME_INSURANCE_PATTERNS = [
    'state farm', 'allstate', 'geico home', 'progressive home',
    'farmers insurance', 'liberty mutual', 'nationwide home',
    'usaa home', 'travelers home', 'hartford home',
]


def _matches_any_pattern(text: str, patterns: List[str]) -> bool:
    """Check if text matches any of the patterns (case-insensitive)."""
    if not text:
        return False
    text_lower = text.lower()
    return any(p in text_lower for p in patterns)


def discover_potential_assets() -> List[AssetSuggestion]:
    """
    Scan recurring series for potential assets and liabilities.

    REUSES existing recurring_series with classification data.
    Returns suggestions for items not yet tracked.
    """
    conn = get_conn()
    suggestions = []

    # =========================================================================
    # MORTGAGES → Property Asset + Mortgage Liability
    # =========================================================================
    try:
        # Build pattern condition
        pattern_conditions = " OR ".join([f"rs.name LIKE '%{p}%'" for p in MORTGAGE_PATTERNS])

        mortgages = conn.execute(f"""
            SELECT
                rs.id,
                rs.name,
                rs.amount_mean,
                rs.cadence,
                COALESCE(rs.llm_confidence, rs.prediction_confidence, 0.5) as series_confidence,
                rs.first_date as first_payment,
                rs.last_date as last_payment,
                rs.occurrences as payment_count
            FROM recurring_series rs
            WHERE ({pattern_conditions})
            AND rs.status = 'confirmed'
            AND rs.id NOT IN (SELECT linked_recurring_id FROM liability WHERE linked_recurring_id IS NOT NULL)
            AND rs.id NOT IN (SELECT source_recurring_id FROM networth_suggestion WHERE source_recurring_id IS NOT NULL AND status != 'dismissed')
        """).fetchall()

        for row in mortgages:
            payment_count = row['payment_count'] or 1
            estimates = estimate_mortgage(
                monthly_payment=abs(row['amount_mean'] or 0),
                first_payment=row['first_payment'],
                payment_count=payment_count
            )

            suggestions.append(AssetSuggestion(
                id=str(uuid.uuid4()),
                type=SuggestionType.PROPERTY,
                subtype="mortgage",
                confidence=min(0.95, (row['series_confidence'] or 0.5) + 0.1),
                source_recurring_id=row['id'],
                source_data={
                    "lender": row['name'],
                    "monthly_payment": abs(row['amount_mean'] or 0),
                    "first_payment": row['first_payment'],
                    "last_payment": row['last_payment'],
                    "payment_count": payment_count
                },
                suggested_values={
                    "lender": row['name'],
                    "monthly_payment": abs(row['amount_mean'] or 0),
                    "original_amount": estimates['original_amount'],
                    "current_balance": estimates['current_balance'],
                    "interest_rate": estimates['estimated_rate'],
                    "principal_paid": estimates['principal_paid'],
                    "interest_paid": estimates['interest_paid'],
                    "term_months": estimates['term_months'],
                    "start_date": row['first_payment']
                }
            ))
    except Exception as e:
        print(f"Error discovering mortgages: {e}")

    # =========================================================================
    # AUTO LOANS → Vehicle Asset + Auto Loan Liability
    # =========================================================================
    try:
        pattern_conditions = " OR ".join([f"rs.name LIKE '%{p}%'" for p in AUTO_LOAN_PATTERNS])

        auto_loans = conn.execute(f"""
            SELECT
                rs.id,
                rs.name,
                rs.amount_mean,
                rs.first_date as first_payment,
                rs.last_date as last_payment,
                rs.occurrences as payment_count,
                COALESCE(rs.llm_confidence, rs.prediction_confidence, 0.5) as series_confidence
            FROM recurring_series rs
            WHERE ({pattern_conditions})
            AND rs.status = 'confirmed'
            AND rs.id NOT IN (SELECT linked_recurring_id FROM liability WHERE linked_recurring_id IS NOT NULL)
            AND rs.id NOT IN (SELECT source_recurring_id FROM networth_suggestion WHERE source_recurring_id IS NOT NULL AND status != 'dismissed')
        """).fetchall()

        for row in auto_loans:
            payment_count = row['payment_count'] or 1
            estimates = estimate_auto_loan(
                monthly_payment=abs(row['amount_mean'] or 0),
                first_payment=row['first_payment'],
                payment_count=payment_count
            )

            suggestions.append(AssetSuggestion(
                id=str(uuid.uuid4()),
                type=SuggestionType.VEHICLE,
                subtype="auto_loan",
                confidence=min(0.90, (row['series_confidence'] or 0.5) + 0.05),
                source_recurring_id=row['id'],
                source_data={
                    "lender": row['name'],
                    "monthly_payment": abs(row['amount_mean'] or 0),
                    "first_payment": row['first_payment'],
                    "payment_count": payment_count
                },
                suggested_values={
                    "lender": row['name'],
                    "monthly_payment": abs(row['amount_mean'] or 0),
                    "original_amount": estimates['original_amount'],
                    "current_balance": estimates['current_balance'],
                    "interest_rate": estimates['estimated_rate'],
                    "term_months": estimates['term_months'],
                    "start_date": row['first_payment']
                }
            ))
    except Exception as e:
        print(f"Error discovering auto loans: {e}")

    # =========================================================================
    # INVESTMENT CONTRIBUTIONS → Investment Asset
    # =========================================================================
    try:
        pattern_conditions = " OR ".join([f"rs.name LIKE '%{p}%'" for p in INVESTMENT_PATTERNS])

        investments = conn.execute(f"""
            SELECT
                rs.id,
                rs.name,
                rs.amount_mean,
                rs.first_date as first_contribution,
                rs.last_date as last_contribution,
                rs.occurrences as contribution_count
            FROM recurring_series rs
            WHERE ({pattern_conditions})
            AND rs.amount_mean < 0
            AND rs.status = 'confirmed'
            AND rs.id NOT IN (SELECT linked_recurring_id FROM asset WHERE linked_recurring_id IS NOT NULL)
            AND rs.id NOT IN (SELECT source_recurring_id FROM networth_suggestion WHERE source_recurring_id IS NOT NULL AND status != 'dismissed')
        """).fetchall()

        for row in investments:
            contribution_count = row['contribution_count'] or 1
            total_contributed = abs(row['amount_mean'] or 0) * contribution_count

            # Determine subtype
            name_lower = (row['name'] or '').lower()
            subtype = "brokerage"
            if any(k in name_lower for k in ['401k', 'ira', 'roth', 'retirement', 'tsp']):
                subtype = "retirement"

            suggestions.append(AssetSuggestion(
                id=str(uuid.uuid4()),
                type=SuggestionType.INVESTMENT,
                subtype=subtype,
                confidence=0.75,  # Lower confidence - we only know contributions
                source_recurring_id=row['id'],
                source_data={
                    "institution": row['name'],
                    "contribution_amount": abs(row['amount_mean'] or 0),
                    "first_contribution": row['first_contribution'],
                    "contribution_count": contribution_count,
                    "total_contributed": total_contributed
                },
                suggested_values={
                    "institution": row['name'],
                    "contribution_amount": abs(row['amount_mean'] or 0),
                    "total_contributed": total_contributed,
                    "note": "Balance must be entered manually or connected via API"
                }
            ))
    except Exception as e:
        print(f"Error discovering investments: {e}")

    # =========================================================================
    # PRECIOUS METAL PURCHASES → Precious Metal Asset
    # =========================================================================
    try:
        pattern_conditions = " OR ".join([f"t.description_norm LIKE '%{p}%'" for p in METAL_DEALER_PATTERNS])

        metal_purchases = conn.execute(f"""
            SELECT
                t.id,
                t.description_norm,
                t.amount,
                t.posted_at
            FROM [transaction] t
            WHERE ({pattern_conditions})
            AND t.amount < -50
            AND t.id NOT IN (
                SELECT json_extract(details, '$.source_transaction_id')
                FROM asset
                WHERE type = 'precious_metal'
                AND json_extract(details, '$.source_transaction_id') IS NOT NULL
            )
            ORDER BY t.posted_at DESC
            LIMIT 20
        """).fetchall()

        # Group by purchase date (same day = same purchase session)
        from collections import defaultdict
        purchases_by_date = defaultdict(list)
        for row in metal_purchases:
            if row['posted_at']:
                date_key = row['posted_at'][:10]
                purchases_by_date[date_key].append(row)

        for date_str, purchases in purchases_by_date.items():
            total = sum(abs(p['amount'] or 0) for p in purchases)
            desc = purchases[0]['description_norm'] or ''
            merchant = desc.split()[0] if desc else "Unknown"

            suggestions.append(AssetSuggestion(
                id=str(uuid.uuid4()),
                type=SuggestionType.PRECIOUS_METAL,
                subtype="unknown",  # User will specify gold/silver/etc.
                confidence=0.85,
                source_recurring_id=None,
                source_data={
                    "merchant": merchant,
                    "purchase_date": date_str,
                    "purchase_amount": total,
                    "transaction_ids": [p['id'] for p in purchases]
                },
                suggested_values={
                    "purchase_date": date_str,
                    "purchase_amount": total,
                    "merchant": merchant,
                    "note": "Please specify: metal type, weight, and form"
                }
            ))
    except Exception as e:
        print(f"Error discovering metal purchases: {e}")

    # =========================================================================
    # HOMEOWNERS INSURANCE → May indicate property (if no mortgage detected)
    # =========================================================================
    try:
        # Only suggest if no property already detected
        existing_property = conn.execute("""
            SELECT COUNT(*) FROM networth_suggestion WHERE type = 'property' AND status != 'dismissed'
        """).fetchone()[0]

        existing_asset = conn.execute("""
            SELECT COUNT(*) FROM asset WHERE type = 'real_estate' AND is_active = 1
        """).fetchone()[0]

        if existing_property == 0 and existing_asset == 0:
            pattern_conditions = " OR ".join([f"rs.name LIKE '%{p}%'" for p in HOME_INSURANCE_PATTERNS])

            home_insurance = conn.execute(f"""
                SELECT
                    rs.id,
                    rs.name,
                    rs.amount_mean
                FROM recurring_series rs
                WHERE ({pattern_conditions})
                AND rs.amount_mean BETWEEN -500 AND -50
                AND rs.status = 'confirmed'
            """).fetchall()

            for row in home_insurance:
                suggestions.append(AssetSuggestion(
                    id=str(uuid.uuid4()),
                    type=SuggestionType.PROPERTY,
                    subtype="homeowners_insurance",
                    confidence=0.60,  # Lower confidence - just insurance, no mortgage
                    source_recurring_id=row['id'],
                    source_data={
                        "insurer": row['name'],
                        "monthly_premium": abs(row['amount_mean'] or 0)
                    },
                    suggested_values={
                        "note": "Home insurance detected but no mortgage. Do you own a property outright?"
                    }
                ))
    except Exception as e:
        print(f"Error discovering home insurance: {e}")

    return suggestions


def estimate_mortgage(
    monthly_payment: float,
    first_payment: str,
    payment_count: int,
    assumed_rate: float = 0.065,  # 6.5% default
    assumed_term: int = 360       # 30 years default
) -> Dict:
    """Estimate mortgage details from payment history."""

    if monthly_payment <= 0:
        return {
            "original_amount": 0,
            "current_balance": 0,
            "principal_paid": 0,
            "interest_paid": 0,
            "estimated_rate": assumed_rate,
            "term_months": assumed_term,
            "payments_remaining": assumed_term
        }

    # Calculate original loan amount using payment formula
    # P = L[c(1 + c)^n]/[(1 + c)^n - 1]
    # L = P * [(1 + c)^n - 1] / [c(1 + c)^n]

    c = assumed_rate / 12  # Monthly rate
    n = assumed_term        # Total months

    # Original loan amount
    try:
        original = monthly_payment * ((1 + c)**n - 1) / (c * (1 + c)**n)
    except:
        original = monthly_payment * n * 0.7  # Fallback estimate

    # Current balance after N payments
    payments_made = min(payment_count, n)

    # Remaining balance formula
    # B = L[(1 + c)^n - (1 + c)^p] / [(1 + c)^n - 1]
    if payments_made >= n:
        current_balance = 0
    else:
        try:
            current_balance = original * ((1 + c)**n - (1 + c)**payments_made) / ((1 + c)**n - 1)
        except:
            current_balance = original * (1 - payments_made / n)

    # Calculate total paid
    total_paid = monthly_payment * payments_made
    principal_paid = original - current_balance
    interest_paid = total_paid - principal_paid

    return {
        "original_amount": round(original, 2),
        "current_balance": round(max(0, current_balance), 2),
        "principal_paid": round(max(0, principal_paid), 2),
        "interest_paid": round(max(0, interest_paid), 2),
        "estimated_rate": assumed_rate,
        "term_months": assumed_term,
        "payments_remaining": max(0, assumed_term - payments_made)
    }


def estimate_auto_loan(
    monthly_payment: float,
    first_payment: str,
    payment_count: int,
    assumed_rate: float = 0.07,  # 7% default for auto
    assumed_term: int = 60       # 5 years default
) -> Dict:
    """Estimate auto loan details from payment history."""

    if monthly_payment <= 0:
        return {
            "original_amount": 0,
            "current_balance": 0,
            "estimated_rate": assumed_rate,
            "term_months": assumed_term,
            "payments_remaining": assumed_term
        }

    c = assumed_rate / 12
    n = assumed_term

    try:
        original = monthly_payment * ((1 + c)**n - 1) / (c * (1 + c)**n)
    except:
        original = monthly_payment * n * 0.85

    payments_made = min(payment_count, n)

    if payments_made >= n:
        current_balance = 0
    else:
        try:
            current_balance = original * ((1 + c)**n - (1 + c)**payments_made) / ((1 + c)**n - 1)
        except:
            current_balance = original * (1 - payments_made / n)

    return {
        "original_amount": round(original, 2),
        "current_balance": round(max(0, current_balance), 2),
        "estimated_rate": assumed_rate,
        "term_months": assumed_term,
        "payments_remaining": max(0, assumed_term - payments_made)
    }


def save_suggestions(suggestions: List[AssetSuggestion]) -> int:
    """Save suggestions to database."""
    conn = get_conn()
    count = 0

    for s in suggestions:
        try:
            # Check if similar suggestion already exists
            if s.source_recurring_id:
                existing = conn.execute("""
                    SELECT id FROM networth_suggestion
                    WHERE source_recurring_id = ? AND status = 'pending'
                """, [s.source_recurring_id]).fetchone()

                if existing:
                    continue

            conn.execute("""
                INSERT INTO networth_suggestion
                (id, type, subtype, confidence, source_recurring_id, source_data, suggested_values, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """, [
                s.id,
                s.type.value,
                s.subtype,
                s.confidence,
                s.source_recurring_id,
                json.dumps(s.source_data),
                json.dumps(s.suggested_values)
            ])
            count += 1
        except Exception as e:
            print(f"Error saving suggestion: {e}")

    return count


def get_pending_suggestions() -> List[Dict]:
    """Get all pending suggestions for user review."""
    conn = get_conn()

    try:
        rows = conn.execute("""
            SELECT
                ns.*,
                rs.name as recurring_name,
                rs.amount_mean as recurring_amount
            FROM networth_suggestion ns
            LEFT JOIN recurring_series rs ON ns.source_recurring_id = rs.id
            WHERE ns.status = 'pending'
            OR (ns.status = 'snoozed' AND ns.snoozed_until < datetime('now'))
            ORDER BY ns.confidence DESC, ns.created_at DESC
        """).fetchall()

        results = []
        for row in rows:
            d = dict(row)
            # Parse JSON fields
            if d.get('source_data'):
                try:
                    d['source_data'] = json.loads(d['source_data'])
                except:
                    pass
            if d.get('suggested_values'):
                try:
                    d['suggested_values'] = json.loads(d['suggested_values'])
                except:
                    pass
            results.append(d)

        return results
    except Exception as e:
        print(f"Error getting suggestions: {e}")
        return []


def get_suggestion_count() -> int:
    """Get count of pending suggestions."""
    conn = get_conn()
    try:
        row = conn.execute("""
            SELECT COUNT(*) FROM networth_suggestion
            WHERE status = 'pending'
            OR (status = 'snoozed' AND snoozed_until < datetime('now'))
        """).fetchone()
        return row[0] if row else 0
    except:
        return 0


def accept_suggestion(suggestion_id: str, overrides: Optional[Dict] = None) -> Dict:
    """Accept a suggestion and create asset/liability."""
    from datetime import datetime

    conn = get_conn()

    suggestion = conn.execute(
        "SELECT * FROM networth_suggestion WHERE id = ?",
        [suggestion_id]
    ).fetchone()

    if not suggestion:
        return {"error": "Suggestion not found"}

    suggestion = dict(suggestion)
    suggested = json.loads(suggestion.get('suggested_values') or '{}')
    if overrides:
        suggested.update(overrides)

    stype = suggestion['type']

    # Create asset and/or liability based on type
    if stype in ('property', 'vehicle'):
        # Create both asset and liability
        asset_id = str(uuid.uuid4())
        liability_id = str(uuid.uuid4())

        asset_type = 'real_estate' if stype == 'property' else 'vehicle'
        liability_type = 'mortgage' if stype == 'property' else 'auto_loan'

        # Asset
        conn.execute("""
            INSERT INTO asset (id, type, subtype, name, current_value, purchase_price,
                              linked_recurring_id, linked_liability_id, suggestion_id, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            asset_id,
            asset_type,
            suggestion['subtype'],
            suggested.get('name') or suggested.get('lender', 'Asset'),
            suggested.get('estimated_value'),
            suggested.get('purchase_price'),
            suggestion['source_recurring_id'],
            liability_id,
            suggestion_id,
            json.dumps(suggested)
        ])

        # Liability
        conn.execute("""
            INSERT INTO liability (id, type, name, lender, original_amount, current_balance,
                                  interest_rate, monthly_payment, term_months, start_date,
                                  linked_recurring_id, linked_asset_id, suggestion_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            liability_id,
            liability_type,
            suggested.get('lender', 'Loan'),
            suggested.get('lender'),
            suggested.get('original_amount'),
            suggested.get('current_balance'),
            suggested.get('interest_rate'),
            suggested.get('monthly_payment'),
            suggested.get('term_months'),
            suggested.get('start_date'),
            suggestion['source_recurring_id'],
            asset_id,
            suggestion_id
        ])

        # Link recurring series
        if suggestion['source_recurring_id']:
            conn.execute("""
                UPDATE recurring_series
                SET linked_asset_id = ?, linked_liability_id = ?
                WHERE id = ?
            """, [asset_id, liability_id, suggestion['source_recurring_id']])

    elif stype == 'investment':
        asset_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO asset (id, type, subtype, name, current_value,
                              linked_recurring_id, suggestion_id, details)
            VALUES (?, 'investment', ?, ?, ?, ?, ?, ?)
        """, [
            asset_id,
            suggestion['subtype'],
            suggested.get('institution', 'Investment'),
            suggested.get('total_contributed'),
            suggestion['source_recurring_id'],
            suggestion_id,
            json.dumps(suggested)
        ])

    elif stype == 'precious_metal':
        asset_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO asset (id, type, subtype, name, purchase_price, purchase_date,
                              suggestion_id, details)
            VALUES (?, 'precious_metal', ?, ?, ?, ?, ?, ?)
        """, [
            asset_id,
            suggested.get('metal_type', 'unknown'),
            f"{suggested.get('metal_type', 'Metal')} - {suggested.get('weight_oz', '?')} oz",
            suggested.get('purchase_amount'),
            suggested.get('purchase_date'),
            suggestion_id,
            json.dumps(suggested)
        ])

    # Mark suggestion as accepted
    conn.execute("""
        UPDATE networth_suggestion
        SET status = 'accepted', resolved_at = datetime('now')
        WHERE id = ?
    """, [suggestion_id])

    return {"status": "accepted", "suggestion_id": suggestion_id}


def dismiss_suggestion(suggestion_id: str) -> Dict:
    """Dismiss a suggestion."""
    conn = get_conn()
    conn.execute("""
        UPDATE networth_suggestion
        SET status = 'dismissed', resolved_at = datetime('now')
        WHERE id = ?
    """, [suggestion_id])
    return {"status": "dismissed"}


def snooze_suggestion(suggestion_id: str, days: int = 7) -> Dict:
    """Snooze a suggestion for later."""
    conn = get_conn()
    snooze_until = (datetime.now() + timedelta(days=days)).isoformat()
    conn.execute("""
        UPDATE networth_suggestion
        SET status = 'snoozed', snoozed_until = ?
        WHERE id = ?
    """, [snooze_until, suggestion_id])
    return {"status": "snoozed", "until": snooze_until}
