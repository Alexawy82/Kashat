"""
Net Worth Enrichment - Free API integrations for asset valuation

FREE APIs used:
- metals.live - Precious metal spot prices
- Yahoo Finance - Stock prices (unofficial)
- NHTSA - VIN decoding
- FRED - Interest rates (fallback estimates)
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import urllib.request
import urllib.parse
import ssl

from .db import get_conn


# =============================================================================
# CACHING
# =============================================================================

def get_cached(cache_key: str) -> Optional[Dict]:
    """Get cached enrichment data if not expired."""
    conn = get_conn()
    try:
        row = conn.execute("""
            SELECT data, expires_at FROM enrichment_cache
            WHERE cache_key = ? AND expires_at > datetime('now')
        """, [cache_key]).fetchone()

        if row:
            return json.loads(row['data'])
    except:
        pass
    return None


def set_cached(cache_key: str, source: str, data: Dict, ttl_hours: int = 24):
    """Cache enrichment data."""
    conn = get_conn()
    expires = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()

    try:
        conn.execute("""
            INSERT OR REPLACE INTO enrichment_cache
            (id, cache_key, source, data, fetched_at, expires_at)
            VALUES (?, ?, ?, ?, datetime('now'), ?)
        """, [
            hashlib.md5(cache_key.encode()).hexdigest(),
            cache_key,
            source,
            json.dumps(data),
            expires
        ])
    except Exception as e:
        print(f"Cache error: {e}")


def _fetch_url(url: str, headers: Dict = None, timeout: int = 10) -> Optional[str]:
    """Fetch URL with basic error handling."""
    try:
        req = urllib.request.Request(url)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        # Add a user agent to avoid blocks
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        # Create SSL context
        ctx = ssl.create_default_context()

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
        return None


# =============================================================================
# PRECIOUS METALS (FREE - metals.live)
# =============================================================================

def get_metal_spot_prices() -> Dict[str, float]:
    """Get current spot prices for gold, silver, platinum, palladium.

    Uses goldprice.org API (free, no key required).
    Falls back to swissquote forex API if primary fails.
    Returns prices in USD per troy ounce.
    """
    cache_key = "metals:spot"
    cached = get_cached(cache_key)
    if cached:
        return cached

    # Primary: goldprice.org (has gold and silver)
    url = "https://data-asg.goldprice.org/dbXRates/USD"
    response = _fetch_url(url)

    prices = {}

    if response:
        try:
            data = json.loads(response)
            items = data.get('items', [{}])
            if items:
                item = items[0]
                prices['gold'] = float(item.get('xauPrice', 0))
                prices['silver'] = float(item.get('xagPrice', 0))
                prices['source'] = 'goldprice.org'
        except Exception as e:
            print(f"goldprice.org parse error: {e}")

    # If we got gold price, try to get platinum and palladium from swissquote
    if prices.get('gold', 0) > 0:
        # Swissquote for platinum
        pt_url = "https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XPT/USD"
        pt_response = _fetch_url(pt_url)
        if pt_response:
            try:
                pt_data = json.loads(pt_response)
                if pt_data and len(pt_data) > 0:
                    spreads = pt_data[0].get('spreadProfilePrices', [])
                    if spreads:
                        prices['platinum'] = float(spreads[0].get('bid', 0))
            except:
                pass

        # Swissquote for palladium
        pd_url = "https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XPD/USD"
        pd_response = _fetch_url(pd_url)
        if pd_response:
            try:
                pd_data = json.loads(pd_response)
                if pd_data and len(pd_data) > 0:
                    spreads = pd_data[0].get('spreadProfilePrices', [])
                    if spreads:
                        prices['palladium'] = float(spreads[0].get('bid', 0))
            except:
                pass

    # If primary API failed, try swissquote for gold too
    if prices.get('gold', 0) == 0:
        gold_url = "https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD"
        gold_response = _fetch_url(gold_url)
        if gold_response:
            try:
                gold_data = json.loads(gold_response)
                if gold_data and len(gold_data) > 0:
                    spreads = gold_data[0].get('spreadProfilePrices', [])
                    if spreads:
                        prices['gold'] = float(spreads[0].get('bid', 0))
                        prices['source'] = 'swissquote'
            except:
                pass

        silver_url = "https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAG/USD"
        silver_response = _fetch_url(silver_url)
        if silver_response:
            try:
                silver_data = json.loads(silver_response)
                if silver_data and len(silver_data) > 0:
                    spreads = silver_data[0].get('spreadProfilePrices', [])
                    if spreads:
                        prices['silver'] = float(spreads[0].get('bid', 0))
            except:
                pass

    # Final fallback if APIs fail
    if prices.get('gold', 0) == 0:
        return {
            "gold": 2650.00,
            "silver": 31.50,
            "platinum": 980.00,
            "palladium": 1050.00,
            "source": "fallback",
            "as_of": datetime.now().isoformat()
        }

    prices['as_of'] = datetime.now().isoformat()
    set_cached(cache_key, prices.get('source', 'api'), prices, ttl_hours=1)
    return prices


def get_metal_value(metal_type: str, weight_oz: float) -> Dict:
    """Calculate current value of metal holdings."""
    prices = get_metal_spot_prices()
    metal = metal_type.lower()

    if metal not in prices:
        return {"error": f"Unknown metal: {metal_type}", "value": 0}

    spot_price = prices[metal]
    value = spot_price * weight_oz

    return {
        "metal": metal,
        "weight_oz": weight_oz,
        "spot_price": spot_price,
        "value": round(value, 2),
        "source": prices.get('source', 'unknown'),
        "as_of": prices.get('as_of')
    }


# =============================================================================
# STOCKS (FREE - Yahoo Finance unofficial)
# =============================================================================

def get_stock_price(symbol: str) -> Dict:
    """Get current stock/ETF price from Yahoo Finance.

    Uses unofficial Yahoo Finance endpoint.
    """
    cache_key = f"stock:{symbol.upper()}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    symbol = symbol.upper()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    response = _fetch_url(url, headers)

    if not response:
        return {"error": "Failed to fetch", "symbol": symbol}

    try:
        data = json.loads(response)
        result = data.get('chart', {}).get('result', [{}])[0]
        meta = result.get('meta', {})

        price_data = {
            "symbol": symbol,
            "price": meta.get('regularMarketPrice', 0),
            "previous_close": meta.get('previousClose', 0),
            "currency": meta.get('currency', 'USD'),
            "exchange": meta.get('exchangeName', ''),
            "name": meta.get('shortName', symbol),
            "source": "yahoo",
            "as_of": datetime.now().isoformat()
        }

        # Calculate change
        if price_data['previous_close']:
            change = price_data['price'] - price_data['previous_close']
            change_pct = (change / price_data['previous_close']) * 100
            price_data['change'] = round(change, 2)
            price_data['change_percent'] = round(change_pct, 2)

        set_cached(cache_key, 'yahoo', price_data, ttl_hours=1)
        return price_data
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


def get_portfolio_value(holdings: Dict[str, float]) -> Dict:
    """Calculate total portfolio value.

    holdings: {"AAPL": 10, "GOOGL": 5, ...} (symbol: shares)
    """
    total = 0
    details = []

    for symbol, shares in holdings.items():
        price_data = get_stock_price(symbol)
        if 'error' not in price_data:
            value = price_data.get('price', 0) * shares
            total += value
            details.append({
                "symbol": symbol,
                "shares": shares,
                "price": price_data.get('price', 0),
                "value": round(value, 2),
                "change_percent": price_data.get('change_percent', 0)
            })

    return {
        "total_value": round(total, 2),
        "holdings": details,
        "as_of": datetime.now().isoformat()
    }


# =============================================================================
# PROPERTY VALUES
# =============================================================================

def get_property_estimate(address: str) -> Dict:
    """
    Get property value estimate.

    NOTE: Zillow's official API is paid. This returns structure for manual entry.
    For production, consider:
    - Attom Data API (paid)
    - RealtyMole API (has free tier)
    - Manual entry with periodic updates
    """
    cache_key = f"property:{hashlib.md5(address.lower().encode()).hexdigest()}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    # For now, return structure that user can fill in
    result = {
        "address": address,
        "status": "manual_entry_required",
        "message": "Property values require manual entry or Zillow API access",
        "fields_needed": ["estimated_value", "beds", "baths", "sqft", "year_built"],
        "source": "manual",
        "as_of": datetime.now().isoformat()
    }

    # Cache even the "needs manual" result to avoid repeated attempts
    set_cached(cache_key, 'manual', result, ttl_hours=168)  # 1 week

    return result


# =============================================================================
# VEHICLE VALUES
# =============================================================================

def get_vehicle_value(year: int, make: str, model: str, mileage: int = None) -> Dict:
    """
    Get vehicle value estimate.

    NOTE: KBB doesn't have a free API. Returns structure for manual entry
    with depreciation guidance.
    """
    cache_key = f"vehicle:{year}:{make}:{model}:{mileage or 'avg'}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    # Estimate depreciation curve (rough approximation)
    current_year = datetime.now().year
    age = current_year - year

    # Typical depreciation by year
    # Year 1: ~20%, Year 2-3: ~15%/yr, Year 4-5: ~10%/yr, 6+: ~7%/yr
    depreciation_pct = min(90, 20 + max(0, age - 1) * 12)

    result = {
        "year": year,
        "make": make,
        "model": model,
        "mileage": mileage,
        "age_years": age,
        "status": "manual_entry_required",
        "message": "Vehicle values require manual entry or KBB lookup",
        "depreciation_note": f"Typical {age}-year-old vehicle has depreciated ~{depreciation_pct}% from MSRP",
        "source": "estimate",
        "as_of": datetime.now().isoformat()
    }

    set_cached(cache_key, 'estimate', result, ttl_hours=168)
    return result


def decode_vin(vin: str) -> Dict:
    """Decode VIN using free NHTSA API."""
    cache_key = f"vin:{vin}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"
    response = _fetch_url(url)

    if not response:
        return {"error": "Failed to decode VIN", "vin": vin}

    try:
        data = json.loads(response)
        results = data.get('Results', [{}])[0]

        decoded = {
            "vin": vin,
            "year": results.get('ModelYear'),
            "make": results.get('Make'),
            "model": results.get('Model'),
            "trim": results.get('Trim'),
            "body_class": results.get('BodyClass'),
            "drive_type": results.get('DriveType'),
            "fuel_type": results.get('FuelTypePrimary'),
            "engine": results.get('DisplacementL'),
            "source": "nhtsa",
            "as_of": datetime.now().isoformat()
        }

        set_cached(cache_key, 'nhtsa', decoded, ttl_hours=8760)  # 1 year
        return decoded
    except Exception as e:
        return {"error": f"Failed to parse VIN data: {e}", "vin": vin}


# =============================================================================
# INTEREST RATES
# =============================================================================

def get_current_mortgage_rate() -> Dict:
    """Get current average 30-year fixed mortgage rate.

    Uses fallback estimates. For production, use FRED API with key.
    """
    cache_key = "rate:mortgage30"
    cached = get_cached(cache_key)
    if cached:
        return cached

    # Fallback: use recent known rate (update periodically)
    result = {
        "rate_30yr": 6.85,
        "rate_15yr": 6.10,
        "source": "estimate",
        "note": "Approximate current rates. For exact rates, check bankrate.com",
        "as_of": datetime.now().isoformat()
    }

    set_cached(cache_key, 'estimate', result, ttl_hours=24)
    return result


# =============================================================================
# UNIFIED ENRICHMENT
# =============================================================================

def enrich_asset(asset_type: str, details: Dict) -> Dict:
    """
    Enrich asset with current market data based on type.

    Returns enrichment data to be stored in asset.enrichment_data
    """
    if asset_type == 'precious_metal':
        metal = details.get('metal_type', 'gold')
        weight = details.get('weight_oz', 0)
        if weight > 0:
            return get_metal_value(metal, weight)
        return {"status": "weight_required", "message": "Enter weight in troy ounces"}

    elif asset_type == 'investment':
        holdings = details.get('holdings', {})
        if holdings:
            return get_portfolio_value(holdings)
        # Single stock
        symbol = details.get('ticker')
        shares = details.get('shares', 0)
        if symbol:
            price_data = get_stock_price(symbol)
            if 'error' not in price_data:
                price_data['shares'] = shares
                price_data['total_value'] = round(price_data.get('price', 0) * shares, 2)
            return price_data
        return {"status": "ticker_required", "message": "Enter stock ticker symbol"}

    elif asset_type == 'real_estate':
        address = details.get('address')
        if address:
            # Try scraping for property value
            try:
                from .property_scraper import get_property_value
                return get_property_value(address)
            except Exception as e:
                print(f"Property scrape failed: {e}")
                return get_property_estimate(address)
        return {"status": "address_required", "message": "Enter property address"}

    elif asset_type == 'vehicle':
        vin = details.get('vin')
        if vin:
            vin_data = decode_vin(vin)
            if 'error' not in vin_data:
                # Try scraping for vehicle value
                try:
                    from .property_scraper import get_vehicle_value_scrape
                    value_data = get_vehicle_value_scrape(
                        int(vin_data.get('year', 0) or 2020),
                        vin_data.get('make', ''),
                        vin_data.get('model', ''),
                        details.get('mileage')
                    )
                except Exception:
                    value_data = get_vehicle_value(
                        int(vin_data.get('year', 0) or 2020),
                        vin_data.get('make', ''),
                        vin_data.get('model', ''),
                        details.get('mileage')
                    )
                return {**vin_data, **value_data}
            return vin_data
        else:
            year = details.get('year', 2020)
            make = details.get('make', '')
            model = details.get('model', '')
            if year and make and model:
                # Try scraping for vehicle value
                try:
                    from .property_scraper import get_vehicle_value_scrape
                    return get_vehicle_value_scrape(year, make, model, details.get('mileage'))
                except Exception:
                    return get_vehicle_value(year, make, model, details.get('mileage'))
            return {"status": "details_required", "message": "Enter year, make, model or VIN"}

    return {"status": "no_enrichment_available", "type": asset_type}


def refresh_all_assets() -> Dict:
    """Refresh enrichment for all assets that have auto_refresh enabled."""
    conn = get_conn()
    refreshed = 0
    errors = []

    try:
        assets = conn.execute("""
            SELECT id, type, details, last_enriched_at
            FROM asset
            WHERE is_active = 1 AND auto_refresh = 1
        """).fetchall()

        for asset in assets:
            try:
                details = json.loads(asset['details'] or '{}')
                enrichment = enrich_asset(asset['type'], details)

                if 'error' not in enrichment and enrichment.get('status') != 'manual_entry_required':
                    # Update value if available
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
                    """, [json.dumps(enrichment), new_value, asset['id']])
                    refreshed += 1
            except Exception as e:
                errors.append({"asset_id": asset['id'], "error": str(e)})
    except Exception as e:
        errors.append({"error": str(e)})

    return {
        "refreshed": refreshed,
        "errors": errors,
        "as_of": datetime.now().isoformat()
    }
