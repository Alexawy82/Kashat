"""
Net Worth API - Calculate and track net worth across accounts

Provides:
- Current net worth calculation (assets - liabilities)
- Breakdown by account type
- Historical net worth tracking
"""

import logging
from datetime import date, datetime, UTC, timedelta
from typing import Optional, List
import uuid

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ...db import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/networth", tags=["networth"])


# =============================================================================
# Models
# =============================================================================

class AccountBalance(BaseModel):
    """Account with balance for net worth calculation."""
    id: str
    name: str
    account_type: str
    balance: float


class NetWorthBreakdown(BaseModel):
    """Net worth breakdown by account type."""
    checking: float = 0.0
    savings: float = 0.0
    investment: float = 0.0
    asset: float = 0.0
    credit_card: float = 0.0
    loan: float = 0.0


class NetWorthResponse(BaseModel):
    """Current net worth response."""
    assets: float
    liabilities: float
    net_worth: float
    by_type: NetWorthBreakdown
    accounts: List[AccountBalance]
    as_of: str


class NetWorthPoint(BaseModel):
    """A point in net worth history."""
    date: str
    assets: float
    liabilities: float
    net_worth: float


# =============================================================================
# Helper Functions
# =============================================================================

def _calculate_account_balance(conn, account_id: str) -> float:
    """Calculate current balance for an account from transactions."""
    result = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0) as balance
        FROM [transaction]
        WHERE account_id = ?
        """,
        [account_id]
    ).fetchone()
    return float(result[0]) if result else 0.0


def _get_account_type(account_type: Optional[str]) -> str:
    """Normalize account type with fallback."""
    valid_types = {'checking', 'savings', 'credit_card', 'loan', 'investment', 'asset'}
    if account_type and account_type.lower() in valid_types:
        return account_type.lower()
    return 'checking'


# =============================================================================
# Endpoints
# =============================================================================

@router.get("")
def get_net_worth() -> NetWorthResponse:
    """Calculate current net worth from all accounts."""
    conn = get_conn()

    # Get all accounts with their types
    rows = conn.execute(
        """
        SELECT id, name, COALESCE(account_type, 'checking') as account_type
        FROM account
        ORDER BY name
        """
    ).fetchall()

    accounts = []
    breakdown = NetWorthBreakdown()
    total_assets = 0.0
    total_liabilities = 0.0

    for row in rows:
        account_id, name, account_type = row[0], row[1], row[2]
        account_type = _get_account_type(account_type)
        balance = _calculate_account_balance(conn, account_id)

        accounts.append(AccountBalance(
            id=account_id,
            name=name,
            account_type=account_type,
            balance=balance
        ))

        # Update breakdown
        if account_type == 'checking':
            breakdown.checking += balance
        elif account_type == 'savings':
            breakdown.savings += balance
        elif account_type == 'investment':
            breakdown.investment += balance
        elif account_type == 'asset':
            breakdown.asset += balance
        elif account_type == 'credit_card':
            breakdown.credit_card += balance
        elif account_type == 'loan':
            breakdown.loan += balance

        # Categorize as asset or liability
        if account_type in ('checking', 'savings', 'investment', 'asset'):
            total_assets += balance
        elif account_type in ('credit_card', 'loan'):
            # For liabilities, we take absolute value of negative balances
            total_liabilities += abs(balance) if balance < 0 else balance

    return NetWorthResponse(
        assets=round(total_assets, 2),
        liabilities=round(total_liabilities, 2),
        net_worth=round(total_assets - total_liabilities, 2),
        by_type=breakdown,
        accounts=accounts,
        as_of=datetime.now(UTC).isoformat()
    )


@router.get("/history")
def get_net_worth_history(
    months: int = Query(12, ge=1, le=60, description="Number of months to look back")
) -> List[NetWorthPoint]:
    """Get net worth over time (monthly snapshots).

    Calculates historical net worth by looking at transaction balances
    at the end of each month.
    """
    conn = get_conn()

    # Get all accounts
    accounts = conn.execute(
        "SELECT id, COALESCE(account_type, 'checking') as account_type FROM account"
    ).fetchall()

    if not accounts:
        return []

    history = []
    today = date.today()

    for i in range(months):
        # Calculate end of month going back
        month_offset = months - 1 - i
        target_date = today.replace(day=1) - timedelta(days=1)  # Last day of previous month
        for _ in range(month_offset):
            target_date = target_date.replace(day=1) - timedelta(days=1)

        month_end = target_date.isoformat()

        total_assets = 0.0
        total_liabilities = 0.0

        for account_id, account_type in accounts:
            account_type = _get_account_type(account_type)

            # Calculate balance as of month end
            result = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) as balance
                FROM [transaction]
                WHERE account_id = ? AND posted_at <= ?
                """,
                [account_id, month_end]
            ).fetchone()

            balance = float(result[0]) if result else 0.0

            if account_type in ('checking', 'savings', 'investment', 'asset'):
                total_assets += balance
            elif account_type in ('credit_card', 'loan'):
                total_liabilities += abs(balance) if balance < 0 else balance

        history.append(NetWorthPoint(
            date=month_end[:7],  # YYYY-MM format
            assets=round(total_assets, 2),
            liabilities=round(total_liabilities, 2),
            net_worth=round(total_assets - total_liabilities, 2)
        ))

    return history


@router.post("/snapshot")
def create_snapshot() -> dict:
    """Create a net worth snapshot for the current date."""
    conn = get_conn()

    # Calculate current net worth
    nw = get_net_worth()

    snapshot_id = str(uuid.uuid4())
    today = date.today().isoformat()

    # Check if snapshot already exists for today
    existing = conn.execute(
        "SELECT id FROM networth_snapshot WHERE snapshot_date = ?",
        [today]
    ).fetchone()

    if existing:
        # Update existing
        conn.execute(
            """
            UPDATE networth_snapshot
            SET total_assets = ?, total_liabilities = ?, net_worth = ?,
                breakdown_json = ?, created_at = ?
            WHERE snapshot_date = ?
            """,
            [nw.assets, nw.liabilities, nw.net_worth,
             nw.by_type.model_dump_json(), datetime.now(UTC).isoformat(), today]
        )
        return {"status": "updated", "date": today}
    else:
        # Create new
        conn.execute(
            """
            INSERT INTO networth_snapshot (id, snapshot_date, total_assets, total_liabilities, net_worth, breakdown_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [snapshot_id, today, nw.assets, nw.liabilities, nw.net_worth, nw.by_type.model_dump_json()]
        )
        return {"status": "created", "id": snapshot_id, "date": today}


@router.get("/snapshots")
def get_snapshots(
    limit: int = Query(12, ge=1, le=120)
) -> List[NetWorthPoint]:
    """Get stored net worth snapshots."""
    conn = get_conn()

    rows = conn.execute(
        """
        SELECT snapshot_date, total_assets, total_liabilities, net_worth
        FROM networth_snapshot
        ORDER BY snapshot_date DESC
        LIMIT ?
        """,
        [limit]
    ).fetchall()

    return [
        NetWorthPoint(
            date=row[0],
            assets=row[1],
            liabilities=row[2],
            net_worth=row[3]
        )
        for row in reversed(rows)  # Return in chronological order
    ]


# =============================================================================
# NET WORTH INTELLIGENCE - SUGGESTIONS
# =============================================================================

@router.get("/suggestions")
def get_suggestions():
    """Get pending asset/liability suggestions for user review."""
    from ...networth_discovery import (
        discover_potential_assets,
        save_suggestions,
        get_pending_suggestions,
        get_suggestion_count
    )

    # Refresh suggestions
    try:
        new_suggestions = discover_potential_assets()
        save_suggestions(new_suggestions)
    except Exception as e:
        logger.error(f"Error discovering assets: {e}")

    # Return all pending
    suggestions = get_pending_suggestions()

    return {
        "suggestions": suggestions,
        "count": len(suggestions)
    }


@router.get("/suggestions/count")
def get_suggestions_count():
    """Get count of pending suggestions for badge display."""
    from ...networth_discovery import get_suggestion_count
    return {"count": get_suggestion_count()}


@router.post("/suggestions/{suggestion_id}/accept")
def accept_suggestion_route(suggestion_id: str, overrides: dict = None):
    """Accept a suggestion and create asset/liability."""
    from ...networth_discovery import accept_suggestion
    return accept_suggestion(suggestion_id, overrides)


@router.post("/suggestions/{suggestion_id}/dismiss")
def dismiss_suggestion_route(suggestion_id: str):
    """Dismiss a suggestion."""
    from ...networth_discovery import dismiss_suggestion
    return dismiss_suggestion(suggestion_id)


@router.post("/suggestions/{suggestion_id}/snooze")
def snooze_suggestion_route(suggestion_id: str, days: int = 7):
    """Snooze a suggestion for later."""
    from ...networth_discovery import snooze_suggestion
    return snooze_suggestion(suggestion_id, days)


# =============================================================================
# ASSETS CRUD
# =============================================================================

@router.get("/assets")
def list_assets(asset_type: Optional[str] = Query(None)):
    """List all assets with optional type filter."""
    import json
    from ...networth_relationships import get_relationship_type, calculate_equity, get_enrichment_status

    conn = get_conn()

    query = """
        SELECT a.*,
               l.id as linked_liability_id,
               l.current_balance as liability_balance,
               l.name as liability_name,
               l.type as liability_type
        FROM asset a
        LEFT JOIN liability l ON a.linked_liability_id = l.id
        WHERE a.is_active = 1
    """
    params = []

    if asset_type:
        query += " AND a.type = ?"
        params.append(asset_type)

    query += " ORDER BY a.current_value DESC NULLS LAST"

    rows = conn.execute(query, params).fetchall()

    assets = []
    for r in rows:
        d = dict(r)
        # Parse JSON fields
        for field in ['details', 'enrichment_data', 'milestones_json']:
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except:
                    pass

        # Add relationship type
        rel_type = get_relationship_type(asset_type=d.get('type'))
        d['relationship_type'] = rel_type.value

        # Add enrichment status
        d['enrichment_status'] = get_enrichment_status(d)

        # If paired with liability, calculate equity
        if d.get('liability_balance'):
            d['equity_info'] = calculate_equity(
                d.get('current_value', 0) or 0,
                d.get('liability_balance', 0) or 0
            )

        assets.append(d)

    return {"assets": assets}


@router.get("/assets/summary")
def get_assets_summary():
    """Get summary of assets by type."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            type,
            COUNT(*) as count,
            SUM(COALESCE(current_value, 0)) as total_value
        FROM asset
        WHERE is_active = 1
        GROUP BY type
    """).fetchall()

    total = sum(r['total_value'] or 0 for r in rows)

    return {
        "summary": [dict(r) for r in rows],
        "total_value": total,
        "total_assets": sum(r['count'] for r in rows)
    }


@router.post("/assets")
def create_asset(asset: dict):
    """Manually create an asset."""
    import json
    conn = get_conn()
    asset_id = str(uuid.uuid4())

    # Accept both 'type' and 'asset_type' for compatibility
    asset_type = asset.get('type') or asset.get('asset_type')

    # Build details from extra fields
    details = asset.get('details', {})
    extra_fields = ['weight_oz', 'weight_unit', 'metal_type', 'premium_paid', 'address',
                    'property_type', 'year', 'make', 'model', 'vin', 'institution',
                    'account_type', 'ticker', 'shares', 'cost_basis', 'valuation_method',
                    'monthly_revenue', 'multiplier']
    for field in extra_fields:
        if asset.get(field) is not None:
            details[field] = asset.get(field)

    conn.execute("""
        INSERT INTO asset (id, type, subtype, name, current_value, purchase_price, purchase_date, details, notes, auto_refresh)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        asset_id,
        asset_type,
        asset.get('subtype'),
        asset.get('name'),
        asset.get('current_value'),
        asset.get('purchase_price'),
        asset.get('purchase_date'),
        json.dumps(details) if details else None,
        asset.get('notes'),
        1 if asset.get('auto_update', True) else 0
    ])

    return {"id": asset_id, "status": "created"}


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str):
    """Get a single asset."""
    import json
    conn = get_conn()
    row = conn.execute("SELECT * FROM asset WHERE id = ?", [asset_id]).fetchone()
    if not row:
        raise HTTPException(404, "Asset not found")

    d = dict(row)
    for field in ['details', 'enrichment_data', 'milestones_json']:
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except:
                pass
    return d


@router.put("/assets/{asset_id}")
def update_asset(asset_id: str, updates: dict):
    """Update an asset."""
    import json
    conn = get_conn()

    # Build update query dynamically
    allowed = ['name', 'current_value', 'purchase_price', 'details', 'notes', 'subtype']
    sets = []
    values = []

    for key in allowed:
        if key in updates:
            sets.append(f"{key} = ?")
            val = updates[key]
            if key == 'details' and isinstance(val, dict):
                val = json.dumps(val)
            values.append(val)

    if sets:
        values.append(asset_id)
        conn.execute(f"""
            UPDATE asset SET {', '.join(sets)}, updated_at = datetime('now')
            WHERE id = ?
        """, values)

    return {"status": "updated"}


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: str):
    """Soft delete an asset."""
    conn = get_conn()
    conn.execute("UPDATE asset SET is_active = 0 WHERE id = ?", [asset_id])
    return {"status": "deleted"}


@router.post("/assets/{asset_id}/update-value")
def quick_update_value(asset_id: str, value: float = Query(...)):
    """Quick update just the current_value of an asset."""
    conn = get_conn()
    conn.execute("""
        UPDATE asset
        SET current_value = ?,
            enrichment_source = 'manual',
            updated_at = datetime('now')
        WHERE id = ?
    """, [value, asset_id])
    return {"status": "updated", "asset_id": asset_id, "new_value": value}


# =============================================================================
# LIABILITIES CRUD
# =============================================================================

@router.get("/liabilities")
def list_liabilities(liability_type: Optional[str] = Query(None)):
    """List all liabilities with optional type filter."""
    import json
    from ...networth_relationships import get_relationship_type, calculate_equity

    conn = get_conn()

    query = """
        SELECT l.*,
               a.id as linked_asset_id,
               a.name as asset_name,
               a.current_value as asset_value,
               a.type as asset_type
        FROM liability l
        LEFT JOIN asset a ON l.linked_asset_id = a.id
        WHERE l.is_active = 1
    """
    params = []

    if liability_type:
        query += " AND l.type = ?"
        params.append(liability_type)

    query += " ORDER BY l.current_balance DESC NULLS LAST"

    rows = conn.execute(query, params).fetchall()

    liabilities = []
    for r in rows:
        d = dict(r)
        # Parse JSON fields
        if d.get('milestones_json'):
            try:
                d['milestones_json'] = json.loads(d['milestones_json'])
            except:
                pass

        # Add relationship type
        rel_type = get_relationship_type(liability_type=d.get('type'))
        d['relationship_type'] = rel_type.value

        # If paired with asset, calculate equity
        if d.get('asset_value'):
            d['equity_info'] = calculate_equity(
                d.get('asset_value', 0) or 0,
                d.get('current_balance', 0) or 0
            )

        liabilities.append(d)

    return {"liabilities": liabilities}


@router.post("/liabilities")
def create_liability(liability: dict):
    """Manually create a liability."""
    conn = get_conn()
    liability_id = str(uuid.uuid4())

    # Accept both 'type' and 'liability_type' for compatibility
    liability_type = liability.get('type') or liability.get('liability_type')

    # Get linked_asset_id if provided
    linked_asset_id = liability.get('linked_asset_id')

    conn.execute("""
        INSERT INTO liability (id, type, name, lender, original_amount, current_balance,
                              interest_rate, monthly_payment, term_months, start_date, notes,
                              linked_asset_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        liability_id,
        liability_type,
        liability.get('name'),
        liability.get('lender'),
        liability.get('original_amount'),
        liability.get('current_balance'),
        liability.get('interest_rate'),
        liability.get('monthly_payment'),
        liability.get('term_months'),
        liability.get('start_date'),
        liability.get('notes'),
        linked_asset_id
    ])

    # If linked to asset, also link asset back to liability
    if linked_asset_id:
        conn.execute("""
            UPDATE asset SET linked_liability_id = ? WHERE id = ?
        """, [liability_id, linked_asset_id])

    return {"id": liability_id, "status": "created"}


@router.get("/liabilities/{liability_id}")
def get_liability(liability_id: str):
    """Get a single liability."""
    import json
    conn = get_conn()
    row = conn.execute("SELECT * FROM liability WHERE id = ?", [liability_id]).fetchone()
    if not row:
        raise HTTPException(404, "Liability not found")

    d = dict(row)
    if d.get('milestones_json'):
        try:
            d['milestones_json'] = json.loads(d['milestones_json'])
        except:
            pass
    return d


@router.put("/liabilities/{liability_id}")
def update_liability(liability_id: str, updates: dict):
    """Update a liability."""
    conn = get_conn()

    allowed = ['name', 'lender', 'current_balance', 'interest_rate', 'monthly_payment', 'notes']
    sets = []
    values = []

    for key in allowed:
        if key in updates:
            sets.append(f"{key} = ?")
            values.append(updates[key])

    if sets:
        values.append(liability_id)
        conn.execute(f"""
            UPDATE liability SET {', '.join(sets)}, updated_at = datetime('now')
            WHERE id = ?
        """, values)

    return {"status": "updated"}


@router.delete("/liabilities/{liability_id}")
def delete_liability(liability_id: str):
    """Soft delete a liability."""
    conn = get_conn()
    conn.execute("UPDATE liability SET is_active = 0 WHERE id = ?", [liability_id])
    return {"status": "deleted"}


# =============================================================================
# ENRICHMENT
# =============================================================================

@router.post("/assets/{asset_id}/enrich")
def enrich_asset_route(asset_id: str):
    """Fetch latest enrichment data for an asset."""
    import json
    from ...networth_enrichment import enrich_asset

    conn = get_conn()
    asset = conn.execute("SELECT * FROM asset WHERE id = ?", [asset_id]).fetchone()

    if not asset:
        raise HTTPException(404, "Asset not found")

    details = {}
    if asset['details']:
        try:
            details = json.loads(asset['details'])
        except:
            pass

    enrichment = enrich_asset(asset['type'], details)

    # Update asset with enrichment
    new_value = (
        enrichment.get('value') or
        enrichment.get('total_value') or
        enrichment.get('estimated_value')
    )

    conn.execute("""
        UPDATE asset
        SET enrichment_data = ?,
            last_enriched_at = datetime('now'),
            current_value = COALESCE(?, current_value),
            updated_at = datetime('now')
        WHERE id = ?
    """, [
        json.dumps(enrichment),
        new_value,
        asset_id
    ])

    return {"enrichment": enrichment}


@router.get("/metals/spot")
def get_spot_prices():
    """Get current precious metal spot prices."""
    from ...networth_enrichment import get_metal_spot_prices
    return get_metal_spot_prices()


@router.post("/metals/refresh")
def refresh_metal_prices():
    """Clear metal price cache and fetch fresh prices."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM enrichment_cache WHERE cache_key LIKE 'metals:%'")
    except:
        pass

    from ...networth_enrichment import get_metal_spot_prices
    prices = get_metal_spot_prices()
    return prices


@router.post("/discover")
def trigger_discovery():
    """Manually trigger asset/liability discovery from transactions."""
    try:
        from ...networth_discovery import discover_potential_assets, save_suggestions
        suggestions = discover_potential_assets()
        if suggestions:
            save_suggestions(suggestions)
        return {
            "status": "ok",
            "suggestions_created": len(suggestions) if suggestions else 0,
            "types_found": list(set(s.get('type', 'unknown') for s in (suggestions or [])))
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/stock/{symbol}")
def get_stock_quote(symbol: str):
    """Get current stock price."""
    from ...networth_enrichment import get_stock_price
    return get_stock_price(symbol)


@router.post("/vin/decode")
def decode_vin_route(vin: str):
    """Decode a VIN number."""
    from ...networth_enrichment import decode_vin
    return decode_vin(vin)


@router.get("/address/autocomplete")
def address_autocomplete(q: str = Query(..., min_length=3)):
    """
    Autocomplete address using OpenStreetMap Nominatim API.
    Free, no API key required. Rate limited to 1 req/sec.
    """
    import urllib.request
    import urllib.parse
    import json
    import ssl

    if len(q) < 3:
        return {"suggestions": []}

    try:
        # Use Nominatim (OpenStreetMap) - free, no API key
        encoded_query = urllib.parse.quote(q)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&addressdetails=1&limit=5&countrycodes=us"

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Kashat/1.0 (Personal Finance App)')

        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))

        suggestions = []
        for item in data:
            address = item.get('address', {})

            # Build formatted address
            parts = []
            if address.get('house_number'):
                parts.append(address['house_number'])
            if address.get('road'):
                parts.append(address['road'])

            street = ' '.join(parts) if parts else ''

            city = address.get('city') or address.get('town') or address.get('village') or address.get('municipality') or ''
            state = address.get('state', '')
            postcode = address.get('postcode', '')

            # Format: "123 Main St, Houston, TX 77001"
            formatted = item.get('display_name', '')
            short_format = f"{street}, {city}, {state} {postcode}".strip(', ')

            if street or city:
                suggestions.append({
                    "display": formatted,
                    "short": short_format if short_format else formatted,
                    "street": street,
                    "city": city,
                    "state": state,
                    "postcode": postcode,
                    "country": address.get('country', 'USA'),
                    "lat": item.get('lat'),
                    "lon": item.get('lon'),
                })

        return {"suggestions": suggestions}

    except Exception as e:
        logger.error(f"Address autocomplete error: {e}")
        return {"suggestions": [], "error": str(e)}


@router.post("/refresh-all")
def refresh_all_assets_route():
    """Refresh enrichment for all assets with auto_refresh enabled."""
    from ...networth_enrichment import refresh_all_assets
    return refresh_all_assets()


# =============================================================================
# COMPLETE NET WORTH (Enhanced with assets/liabilities)
# =============================================================================

@router.get("/complete")
def get_complete_networth():
    """Get complete net worth including bank accounts, assets, and liabilities."""
    import json
    conn = get_conn()

    # Bank accounts (from transactions)
    bank = conn.execute("""
        SELECT
            a.id, a.name, a.account_type,
            COALESCE(SUM(t.amount), 0) as balance
        FROM account a
        LEFT JOIN [transaction] t ON t.account_id = a.id
        GROUP BY a.id
    """).fetchall()

    bank_total = sum(b['balance'] for b in bank)
    bank_accounts = [dict(b) for b in bank]

    # Manual assets
    assets = conn.execute("""
        SELECT * FROM asset WHERE is_active = 1
    """).fetchall()

    assets_by_type = {}
    assets_total = 0
    assets_list = []
    for a in assets:
        d = dict(a)
        atype = d['type']
        if atype not in assets_by_type:
            assets_by_type[atype] = {"total": 0, "items": []}
        value = d['current_value'] or 0
        assets_by_type[atype]['total'] += value
        assets_by_type[atype]['items'].append({
            "id": d['id'],
            "name": d['name'],
            "value": value,
            "subtype": d.get('subtype')
        })
        assets_total += value
        assets_list.append(d)

    # Liabilities
    liabilities = conn.execute("""
        SELECT * FROM liability WHERE is_active = 1
    """).fetchall()

    liabilities_by_type = {}
    liabilities_total = 0
    liabilities_list = []
    for l in liabilities:
        d = dict(l)
        ltype = d['type']
        if ltype not in liabilities_by_type:
            liabilities_by_type[ltype] = {"total": 0, "items": []}
        balance = d['current_balance'] or 0
        liabilities_by_type[ltype]['total'] += balance
        liabilities_by_type[ltype]['items'].append({
            "id": d['id'],
            "name": d['name'],
            "balance": balance,
            "lender": d.get('lender')
        })
        liabilities_total += balance
        liabilities_list.append(d)

    # Net worth
    total_assets = bank_total + assets_total
    net_worth = total_assets - liabilities_total

    # Get history
    history = []
    try:
        history_rows = conn.execute("""
            SELECT snapshot_date, total_assets, total_liabilities, net_worth
            FROM networth_snapshot
            ORDER BY snapshot_date DESC
            LIMIT 12
        """).fetchall()
        history = [
            {
                "date": r['snapshot_date'],
                "assets": r['total_assets'],
                "liabilities": r['total_liabilities'],
                "net_worth": r['net_worth']
            }
            for r in reversed(history_rows)
        ]
    except:
        pass

    return {
        "net_worth": round(net_worth, 2),
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(liabilities_total, 2),
        "bank_accounts": round(bank_total, 2),
        "breakdown": {
            "bank_accounts": {
                "total": round(bank_total, 2),
                "accounts": bank_accounts
            },
            "assets": assets_by_type,
            "liabilities": liabilities_by_type
        },
        "assets": assets_list,
        "liabilities": liabilities_list,
        "history": history,
        "as_of": datetime.now(UTC).isoformat()
    }
