"""
Assets & Liabilities API - Full net worth tracking

Endpoints:
- GET /api/assets - List all assets
- POST /api/assets - Create asset
- GET /api/assets/{id} - Get single asset
- PUT /api/assets/{id} - Update asset
- DELETE /api/assets/{id} - Delete asset
- POST /api/assets/{id}/update-value - Update current value
- GET /api/assets/summary - Asset breakdown by type

- GET /api/liabilities - List all liabilities
- POST /api/liabilities - Create liability
- GET /api/liabilities/{id} - Get single liability
- PUT /api/liabilities/{id} - Update liability
- DELETE /api/liabilities/{id} - Delete liability

- GET /api/networth/complete - Full net worth with assets + liabilities
- GET /api/metals/spot - Get live precious metal prices
- POST /api/metals/refresh - Refresh all metal asset prices
"""

import logging
import uuid
import httpx
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ...db import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(tags=["assets"])


# =============================================================================
# Enums
# =============================================================================

class AssetType(str, Enum):
    REAL_ESTATE = "real_estate"
    VEHICLE = "vehicle"
    PRECIOUS_METAL = "precious_metal"
    INVESTMENT = "investment"
    BUSINESS = "business"
    OTHER = "other"


class LiabilityType(str, Enum):
    MORTGAGE = "mortgage"
    AUTO_LOAN = "auto_loan"
    PERSONAL_LOAN = "personal_loan"
    STUDENT_LOAN = "student_loan"
    CREDIT_CARD = "credit_card"
    OTHER = "other"


class MetalType(str, Enum):
    GOLD = "gold"
    SILVER = "silver"
    PLATINUM = "platinum"
    PALLADIUM = "palladium"


# =============================================================================
# Models
# =============================================================================

class AssetCreate(BaseModel):
    name: str
    asset_type: AssetType
    subtype: Optional[str] = None
    current_value: float = 0.0
    purchase_price: Optional[float] = None
    purchase_date: Optional[str] = None

    # Precious metals
    weight_oz: Optional[float] = None
    weight_unit: str = "oz"
    metal_type: Optional[str] = None
    premium_paid: Optional[float] = None

    # Real estate
    address: Optional[str] = None
    property_type: Optional[str] = None

    # Vehicle
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    vin: Optional[str] = None

    # Investment
    institution: Optional[str] = None
    account_type: Optional[str] = None

    # Business
    valuation_method: Optional[str] = None
    monthly_revenue: Optional[float] = None
    multiplier: Optional[float] = None

    # Meta
    notes: Optional[str] = None
    is_liquid: bool = False
    auto_update: bool = False
    update_source: Optional[str] = None
    update_reminder: Optional[str] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[AssetType] = None
    subtype: Optional[str] = None
    current_value: Optional[float] = None
    purchase_price: Optional[float] = None
    purchase_date: Optional[str] = None
    weight_oz: Optional[float] = None
    weight_unit: Optional[str] = None
    metal_type: Optional[str] = None
    premium_paid: Optional[float] = None
    address: Optional[str] = None
    property_type: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    vin: Optional[str] = None
    institution: Optional[str] = None
    account_type: Optional[str] = None
    valuation_method: Optional[str] = None
    monthly_revenue: Optional[float] = None
    multiplier: Optional[float] = None
    notes: Optional[str] = None
    is_liquid: Optional[bool] = None
    auto_update: Optional[bool] = None
    update_source: Optional[str] = None
    update_reminder: Optional[str] = None


class AssetResponse(BaseModel):
    id: str
    name: str
    asset_type: str
    subtype: Optional[str] = None
    current_value: float
    purchase_price: Optional[float] = None
    purchase_date: Optional[str] = None
    weight_oz: Optional[float] = None
    weight_unit: Optional[str] = None
    spot_price: Optional[float] = None
    premium_paid: Optional[float] = None
    metal_type: Optional[str] = None
    address: Optional[str] = None
    property_type: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    vin: Optional[str] = None
    institution: Optional[str] = None
    account_type: Optional[str] = None
    valuation_method: Optional[str] = None
    monthly_revenue: Optional[float] = None
    multiplier: Optional[float] = None
    notes: Optional[str] = None
    is_liquid: bool = False
    auto_update: bool = False
    update_source: Optional[str] = None
    last_updated: Optional[str] = None
    update_reminder: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class LiabilityCreate(BaseModel):
    name: str
    liability_type: LiabilityType
    original_amount: Optional[float] = None
    current_balance: float = 0.0
    interest_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    linked_asset_id: Optional[str] = None
    start_date: Optional[str] = None
    expected_payoff_date: Optional[str] = None
    lender: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None
    auto_calculate: bool = False
    linked_account_id: Optional[str] = None


class LiabilityUpdate(BaseModel):
    name: Optional[str] = None
    liability_type: Optional[LiabilityType] = None
    original_amount: Optional[float] = None
    current_balance: Optional[float] = None
    interest_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    linked_asset_id: Optional[str] = None
    start_date: Optional[str] = None
    expected_payoff_date: Optional[str] = None
    lender: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None
    auto_calculate: Optional[bool] = None
    linked_account_id: Optional[str] = None


class LiabilityResponse(BaseModel):
    id: str
    name: str
    liability_type: str
    original_amount: Optional[float] = None
    current_balance: float
    interest_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    linked_asset_id: Optional[str] = None
    start_date: Optional[str] = None
    expected_payoff_date: Optional[str] = None
    lender: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None
    auto_calculate: bool = False
    linked_account_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AssetSummary(BaseModel):
    total_value: float
    by_type: Dict[str, float]
    count_by_type: Dict[str, int]


class MetalSpotPrices(BaseModel):
    gold: Optional[float] = None
    silver: Optional[float] = None
    platinum: Optional[float] = None
    palladium: Optional[float] = None
    as_of: str
    source: str = "metals.live"


class CompleteNetWorthResponse(BaseModel):
    total_assets: float
    bank_accounts: float
    manual_assets: float
    total_liabilities: float
    net_worth: float
    asset_breakdown: Dict[str, float]
    liability_breakdown: Dict[str, float]
    assets: List[AssetResponse]
    liabilities: List[LiabilityResponse]
    as_of: str


# =============================================================================
# Helper Functions
# =============================================================================

def _row_to_asset(row) -> AssetResponse:
    """Convert database row to AssetResponse."""
    return AssetResponse(
        id=row["id"],
        name=row["name"],
        asset_type=row["asset_type"],
        subtype=row["subtype"],
        current_value=row["current_value"] or 0,
        purchase_price=row["purchase_price"],
        purchase_date=row["purchase_date"],
        weight_oz=row["weight_oz"],
        weight_unit=row["weight_unit"],
        spot_price=row["spot_price"],
        premium_paid=row["premium_paid"],
        metal_type=row["metal_type"],
        address=row["address"],
        property_type=row["property_type"],
        year=row["year"],
        make=row["make"],
        model=row["model"],
        vin=row["vin"],
        institution=row["institution"],
        account_type=row["account_type"],
        valuation_method=row["valuation_method"],
        monthly_revenue=row["monthly_revenue"],
        multiplier=row["multiplier"],
        notes=row["notes"],
        is_liquid=bool(row["is_liquid"]),
        auto_update=bool(row["auto_update"]),
        update_source=row["update_source"],
        last_updated=row["last_updated"],
        update_reminder=row["update_reminder"],
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )


def _row_to_liability(row) -> LiabilityResponse:
    """Convert database row to LiabilityResponse."""
    return LiabilityResponse(
        id=row["id"],
        name=row["name"],
        liability_type=row["liability_type"],
        original_amount=row["original_amount"],
        current_balance=row["current_balance"] or 0,
        interest_rate=row["interest_rate"],
        monthly_payment=row["monthly_payment"],
        linked_asset_id=row["linked_asset_id"],
        start_date=row["start_date"],
        expected_payoff_date=row["expected_payoff_date"],
        lender=row["lender"],
        account_number=row["account_number"],
        notes=row["notes"],
        auto_calculate=bool(row["auto_calculate"]),
        linked_account_id=row["linked_account_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )


def _calculate_bank_balances(conn) -> float:
    """Calculate total balance from bank accounts."""
    result = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0) as total
        FROM [transaction]
        """
    ).fetchone()
    return float(result["total"]) if result else 0.0


async def _fetch_metal_spot_price(metal: str) -> Optional[float]:
    """Fetch current spot price for a metal from metals.live API."""
    # metals.live provides free API
    url = f"https://api.metals.live/v1/spot/{metal}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                # API returns array of objects with price field
                if isinstance(data, list) and len(data) > 0:
                    return float(data[0].get("price", 0))
                elif isinstance(data, dict):
                    return float(data.get("price", 0))
            logger.warning(f"Metal API returned status {response.status_code} for {metal}")
    except Exception as e:
        logger.error(f"Failed to fetch {metal} price: {e}")

    return None


# =============================================================================
# Asset Endpoints
# =============================================================================

@router.get("/assets", response_model=List[AssetResponse])
def list_assets(
    asset_type: Optional[str] = Query(None, description="Filter by asset type")
) -> List[AssetResponse]:
    """List all assets, optionally filtered by type."""
    conn = get_conn()

    if asset_type:
        rows = conn.execute(
            "SELECT * FROM asset WHERE asset_type = ? ORDER BY current_value DESC",
            [asset_type]
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM asset ORDER BY current_value DESC"
        ).fetchall()

    return [_row_to_asset(row) for row in rows]


@router.post("/assets", response_model=AssetResponse)
def create_asset(data: AssetCreate) -> AssetResponse:
    """Create a new asset."""
    conn = get_conn()

    asset_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    conn.execute(
        """
        INSERT INTO asset (
            id, name, asset_type, subtype, current_value, purchase_price, purchase_date,
            weight_oz, weight_unit, metal_type, premium_paid,
            address, property_type, year, make, model, vin,
            institution, account_type, valuation_method, monthly_revenue, multiplier,
            notes, is_liquid, auto_update, update_source, update_reminder,
            created_at, updated_at, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            asset_id, data.name, data.asset_type.value, data.subtype, data.current_value,
            data.purchase_price, data.purchase_date,
            data.weight_oz, data.weight_unit, data.metal_type, data.premium_paid,
            data.address, data.property_type, data.year, data.make, data.model, data.vin,
            data.institution, data.account_type, data.valuation_method, data.monthly_revenue, data.multiplier,
            data.notes, 1 if data.is_liquid else 0, 1 if data.auto_update else 0,
            data.update_source, data.update_reminder, now, now, now
        ]
    )

    row = conn.execute("SELECT * FROM asset WHERE id = ?", [asset_id]).fetchone()
    return _row_to_asset(row)


@router.get("/assets/summary", response_model=AssetSummary)
def get_asset_summary() -> AssetSummary:
    """Get asset summary by type."""
    conn = get_conn()

    rows = conn.execute(
        """
        SELECT asset_type, SUM(current_value) as total, COUNT(*) as count
        FROM asset
        GROUP BY asset_type
        """
    ).fetchall()

    by_type = {}
    count_by_type = {}
    total = 0.0

    for row in rows:
        by_type[row["asset_type"]] = row["total"] or 0
        count_by_type[row["asset_type"]] = row["count"]
        total += row["total"] or 0

    return AssetSummary(
        total_value=total,
        by_type=by_type,
        count_by_type=count_by_type
    )


@router.get("/assets/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: str) -> AssetResponse:
    """Get a single asset by ID."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM asset WHERE id = ?", [asset_id]).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")

    return _row_to_asset(row)


@router.put("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: str, data: AssetUpdate) -> AssetResponse:
    """Update an existing asset."""
    conn = get_conn()

    # Check exists
    existing = conn.execute("SELECT * FROM asset WHERE id = ?", [asset_id]).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Build update query
    updates = []
    params = []

    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            if field == "asset_type":
                value = value.value if hasattr(value, "value") else value
            elif field in ("is_liquid", "auto_update"):
                value = 1 if value else 0
            updates.append(f"{field} = ?")
            params.append(value)

    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.now(UTC).isoformat())
        params.append(asset_id)

        conn.execute(
            f"UPDATE asset SET {', '.join(updates)} WHERE id = ?",
            params
        )

    row = conn.execute("SELECT * FROM asset WHERE id = ?", [asset_id]).fetchone()
    return _row_to_asset(row)


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: str) -> dict:
    """Delete an asset."""
    conn = get_conn()

    existing = conn.execute("SELECT * FROM asset WHERE id = ?", [asset_id]).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Clear linked liabilities
    conn.execute("UPDATE liability SET linked_asset_id = NULL WHERE linked_asset_id = ?", [asset_id])

    conn.execute("DELETE FROM asset WHERE id = ?", [asset_id])

    return {"deleted": True, "id": asset_id}


@router.post("/assets/{asset_id}/update-value", response_model=AssetResponse)
def update_asset_value(asset_id: str, value: float = Query(..., description="New value")) -> AssetResponse:
    """Quick update of asset current value."""
    conn = get_conn()

    existing = conn.execute("SELECT * FROM asset WHERE id = ?", [asset_id]).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Asset not found")

    now = datetime.now(UTC).isoformat()
    conn.execute(
        "UPDATE asset SET current_value = ?, last_updated = ?, updated_at = ? WHERE id = ?",
        [value, now, now, asset_id]
    )

    row = conn.execute("SELECT * FROM asset WHERE id = ?", [asset_id]).fetchone()
    return _row_to_asset(row)


# =============================================================================
# Liability Endpoints
# =============================================================================

@router.get("/liabilities", response_model=List[LiabilityResponse])
def list_liabilities(
    liability_type: Optional[str] = Query(None, description="Filter by liability type")
) -> List[LiabilityResponse]:
    """List all liabilities, optionally filtered by type."""
    conn = get_conn()

    if liability_type:
        rows = conn.execute(
            "SELECT * FROM liability WHERE liability_type = ? ORDER BY current_balance DESC",
            [liability_type]
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM liability ORDER BY current_balance DESC"
        ).fetchall()

    return [_row_to_liability(row) for row in rows]


@router.post("/liabilities", response_model=LiabilityResponse)
def create_liability(data: LiabilityCreate) -> LiabilityResponse:
    """Create a new liability."""
    conn = get_conn()

    liability_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    conn.execute(
        """
        INSERT INTO liability (
            id, name, liability_type, original_amount, current_balance,
            interest_rate, monthly_payment, linked_asset_id,
            start_date, expected_payoff_date, lender, account_number,
            notes, auto_calculate, linked_account_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            liability_id, data.name, data.liability_type.value, data.original_amount, data.current_balance,
            data.interest_rate, data.monthly_payment, data.linked_asset_id,
            data.start_date, data.expected_payoff_date, data.lender, data.account_number,
            data.notes, 1 if data.auto_calculate else 0, data.linked_account_id, now, now
        ]
    )

    row = conn.execute("SELECT * FROM liability WHERE id = ?", [liability_id]).fetchone()
    return _row_to_liability(row)


@router.get("/liabilities/{liability_id}", response_model=LiabilityResponse)
def get_liability(liability_id: str) -> LiabilityResponse:
    """Get a single liability by ID."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM liability WHERE id = ?", [liability_id]).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Liability not found")

    return _row_to_liability(row)


@router.put("/liabilities/{liability_id}", response_model=LiabilityResponse)
def update_liability(liability_id: str, data: LiabilityUpdate) -> LiabilityResponse:
    """Update an existing liability."""
    conn = get_conn()

    existing = conn.execute("SELECT * FROM liability WHERE id = ?", [liability_id]).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Liability not found")

    updates = []
    params = []

    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            if field == "liability_type":
                value = value.value if hasattr(value, "value") else value
            elif field == "auto_calculate":
                value = 1 if value else 0
            updates.append(f"{field} = ?")
            params.append(value)

    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.now(UTC).isoformat())
        params.append(liability_id)

        conn.execute(
            f"UPDATE liability SET {', '.join(updates)} WHERE id = ?",
            params
        )

    row = conn.execute("SELECT * FROM liability WHERE id = ?", [liability_id]).fetchone()
    return _row_to_liability(row)


@router.delete("/liabilities/{liability_id}")
def delete_liability(liability_id: str) -> dict:
    """Delete a liability."""
    conn = get_conn()

    existing = conn.execute("SELECT * FROM liability WHERE id = ?", [liability_id]).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Liability not found")

    conn.execute("DELETE FROM liability WHERE id = ?", [liability_id])

    return {"deleted": True, "id": liability_id}


# =============================================================================
# Metal Spot Prices
# =============================================================================

@router.get("/metals/spot", response_model=MetalSpotPrices)
async def get_metal_spot_prices() -> MetalSpotPrices:
    """Get current spot prices for precious metals."""
    prices = MetalSpotPrices(as_of=datetime.now(UTC).isoformat())

    for metal in ["gold", "silver", "platinum", "palladium"]:
        price = await _fetch_metal_spot_price(metal)
        if price:
            setattr(prices, metal, price)

    return prices


@router.post("/metals/refresh")
async def refresh_metal_prices() -> dict:
    """Refresh all precious metal asset values with current spot prices."""
    conn = get_conn()

    # Get all metal assets
    metals = conn.execute(
        "SELECT id, metal_type, weight_oz FROM asset WHERE asset_type = 'precious_metal' AND metal_type IS NOT NULL"
    ).fetchall()

    if not metals:
        return {"updated": 0, "message": "No precious metal assets found"}

    updated = 0
    now = datetime.now(UTC).isoformat()

    # Get current spot prices
    spot_prices = {}
    for metal in ["gold", "silver", "platinum", "palladium"]:
        price = await _fetch_metal_spot_price(metal)
        if price:
            spot_prices[metal] = price

    for row in metals:
        asset_id = row["id"]
        metal_type = row["metal_type"].lower() if row["metal_type"] else None
        weight = row["weight_oz"] or 0

        if metal_type in spot_prices:
            spot = spot_prices[metal_type]
            new_value = spot * weight

            conn.execute(
                "UPDATE asset SET spot_price = ?, current_value = ?, last_updated = ?, updated_at = ? WHERE id = ?",
                [spot, new_value, now, now, asset_id]
            )
            updated += 1

    return {
        "updated": updated,
        "spot_prices": spot_prices,
        "as_of": now
    }


# =============================================================================
# Complete Net Worth
# =============================================================================

@router.get("/networth/complete", response_model=CompleteNetWorthResponse)
def get_complete_net_worth() -> CompleteNetWorthResponse:
    """Get comprehensive net worth including bank accounts, manual assets, and liabilities."""
    conn = get_conn()

    # Bank account balances (from transactions)
    bank_total = _calculate_bank_balances(conn)

    # Manual assets
    asset_rows = conn.execute("SELECT * FROM asset ORDER BY current_value DESC").fetchall()
    assets = [_row_to_asset(row) for row in asset_rows]
    assets_total = sum(a.current_value for a in assets)

    # Asset breakdown by type
    asset_breakdown = {}
    for asset in assets:
        t = asset.asset_type
        asset_breakdown[t] = asset_breakdown.get(t, 0) + asset.current_value

    # Liabilities
    liability_rows = conn.execute("SELECT * FROM liability ORDER BY current_balance DESC").fetchall()
    liabilities = [_row_to_liability(row) for row in liability_rows]
    liabilities_total = sum(l.current_balance for l in liabilities)

    # Liability breakdown by type
    liability_breakdown = {}
    for liability in liabilities:
        t = liability.liability_type
        liability_breakdown[t] = liability_breakdown.get(t, 0) + liability.current_balance

    return CompleteNetWorthResponse(
        total_assets=round(bank_total + assets_total, 2),
        bank_accounts=round(bank_total, 2),
        manual_assets=round(assets_total, 2),
        total_liabilities=round(liabilities_total, 2),
        net_worth=round((bank_total + assets_total) - liabilities_total, 2),
        asset_breakdown=asset_breakdown,
        liability_breakdown=liability_breakdown,
        assets=assets,
        liabilities=liabilities,
        as_of=datetime.now(UTC).isoformat()
    )
