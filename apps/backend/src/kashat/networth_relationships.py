"""
Net Worth Relationship Logic

Handles the relationship between assets and liabilities:
- House is an asset, mortgage is a liability (linked)
- Car is an asset, auto loan is a liability (linked)
- Stocks are assets with no liability
- Credit cards are liabilities with no asset
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum


class AssetLiabilityRelation(Enum):
    """Types of asset-liability relationships."""
    PAIRED = "paired"           # Asset has linked liability (house+mortgage)
    ASSET_ONLY = "asset_only"   # Asset with no liability (stocks, gold)
    LIABILITY_ONLY = "liability_only"  # Liability with no asset (credit card, student loan)


# Which asset types typically have linked liabilities?
ASSET_LIABILITY_PAIRS = {
    # asset_type: liability_type
    "real_estate": "mortgage",
    "vehicle": "auto_loan",
}

# Asset types that never have liabilities
ASSET_ONLY_TYPES = [
    "precious_metal",
    "investment",
    "crypto",
    "cash",
    "collectible",
    "jewelry",
    "business",
    "other",
]

# Liability types that never have assets
LIABILITY_ONLY_TYPES = [
    "credit_card",
    "student_loan",
    "personal_loan",
    "medical_debt",
    "tax_debt",
    "other",
]


def get_relationship_type(
    asset_type: Optional[str] = None,
    liability_type: Optional[str] = None
) -> AssetLiabilityRelation:
    """Determine the relationship type for an asset or liability."""
    if asset_type:
        if asset_type in ASSET_LIABILITY_PAIRS:
            return AssetLiabilityRelation.PAIRED
        return AssetLiabilityRelation.ASSET_ONLY

    if liability_type:
        if liability_type in ASSET_LIABILITY_PAIRS.values():
            return AssetLiabilityRelation.PAIRED
        return AssetLiabilityRelation.LIABILITY_ONLY

    return AssetLiabilityRelation.ASSET_ONLY


def should_prompt_for_liability(asset_type: str) -> Tuple[bool, str]:
    """When creating an asset, should we ask about a linked liability?"""
    if asset_type in ASSET_LIABILITY_PAIRS:
        liability_type = ASSET_LIABILITY_PAIRS[asset_type]
        prompts = {
            "real_estate": "Do you have a mortgage on this property?",
            "vehicle": "Do you have a loan on this vehicle?",
        }
        return True, prompts.get(asset_type, f"Do you have a {liability_type} for this?")
    return False, ""


def should_prompt_for_asset(liability_type: str) -> Tuple[bool, str]:
    """When creating a liability, should we ask about a linked asset?"""
    # Reverse lookup
    for asset_type, liab_type in ASSET_LIABILITY_PAIRS.items():
        if liab_type == liability_type:
            prompts = {
                "mortgage": "What property is this mortgage for?",
                "auto_loan": "What vehicle is this loan for?",
            }
            return True, prompts.get(liability_type, f"What asset is this for?")
    return False, ""


def calculate_equity(asset_value: float, liability_balance: float) -> Dict:
    """Calculate equity for a paired asset-liability."""
    equity = asset_value - liability_balance
    equity_percent = (equity / asset_value * 100) if asset_value > 0 else 0
    ltv = (liability_balance / asset_value * 100) if asset_value > 0 else 0

    return {
        "asset_value": asset_value,
        "liability_balance": liability_balance,
        "equity": round(equity, 2),
        "equity_percent": round(equity_percent, 1),
        "loan_to_value": round(ltv, 1),
    }


def get_net_contribution(
    asset_value: float,
    liability_balance: float,
    relation: AssetLiabilityRelation
) -> float:
    """Get net contribution to net worth."""
    if relation == AssetLiabilityRelation.PAIRED:
        return asset_value - liability_balance  # Equity
    elif relation == AssetLiabilityRelation.ASSET_ONLY:
        return asset_value
    else:  # LIABILITY_ONLY
        return -liability_balance


def get_enrichment_status(asset: dict) -> dict:
    """Get enrichment status for UI display."""
    asset_type = asset.get('type', '')
    enrichment_data = asset.get('enrichment_data')
    last_enriched = asset.get('last_enriched_at')
    auto_refresh = asset.get('auto_refresh', False)

    # Determine enrichment capability
    auto_capable = asset_type in ['precious_metal', 'investment']
    scrape_capable = asset_type in ['real_estate', 'vehicle']
    manual_only = not auto_capable and not scrape_capable

    # Determine current status
    if enrichment_data and last_enriched:
        source = 'auto' if auto_capable else ('scraped' if scrape_capable else 'manual')
        status = 'enriched'
    else:
        status = 'pending' if auto_capable or scrape_capable else 'manual_required'
        source = None

    return {
        'status': status,  # enriched, pending, manual_required
        'source': source,  # auto, scraped, manual
        'auto_capable': auto_capable,
        'scrape_capable': scrape_capable,
        'manual_only': manual_only,
        'last_updated': last_enriched,
        'auto_refresh_enabled': auto_refresh,
    }


def get_paired_liability_type(asset_type: str) -> Optional[str]:
    """Get the liability type that pairs with an asset type."""
    return ASSET_LIABILITY_PAIRS.get(asset_type)


def get_paired_asset_type(liability_type: str) -> Optional[str]:
    """Get the asset type that pairs with a liability type."""
    for asset_type, liab_type in ASSET_LIABILITY_PAIRS.items():
        if liab_type == liability_type:
            return asset_type
    return None
