"""
Property Value Scraper

Scrapes property values from public sources since Zillow API is paid.
Uses multiple sources with fallbacks:
1. Zillow (zestimate) - primary
2. Redfin - fallback
3. County tax assessor - fallback

Note: Web scraping may break if sites change. Handle gracefully.
"""

import re
import json
import hashlib
import urllib.request
import urllib.parse
from typing import Dict, Optional
from datetime import datetime, timedelta
import ssl

from .db import get_conn


def _fetch_with_headers(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch URL with browser-like headers to avoid blocks."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    try:
        req = urllib.request.Request(url, headers=headers)

        # Try with default SSL first
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                return response.read().decode('utf-8')
        except ssl.SSLError:
            # Fallback: disable verification (less secure but works)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                return response.read().decode('utf-8')

    except Exception as e:
        print(f"Fetch error: {e}")
        return None


def scrape_zillow_zestimate(address: str) -> Optional[Dict]:
    """
    Scrape Zillow Zestimate for a property.

    Note: Zillow may block scrapers. This is best-effort.
    """
    try:
        # Format address for URL
        formatted = address.lower().replace(' ', '-').replace(',', '').replace('.', '')
        formatted = re.sub(r'-+', '-', formatted)

        # Try Zillow search
        search_url = f"https://www.zillow.com/homes/{urllib.parse.quote(formatted)}_rb/"

        html = _fetch_with_headers(search_url)
        if not html:
            return None

        # Look for preloaded data (Zillow embeds JSON in page)
        # Pattern: "zestimate":123456
        zestimate_match = re.search(r'"zestimate"\s*:\s*(\d+)', html)
        if zestimate_match:
            zestimate = int(zestimate_match.group(1))

            # Try to get more details
            beds_match = re.search(r'"bedrooms"\s*:\s*(\d+)', html)
            baths_match = re.search(r'"bathrooms"\s*:\s*([\d.]+)', html)
            sqft_match = re.search(r'"livingArea"\s*:\s*(\d+)', html)
            year_match = re.search(r'"yearBuilt"\s*:\s*(\d+)', html)

            return {
                'estimated_value': zestimate,
                'beds': int(beds_match.group(1)) if beds_match else None,
                'baths': float(baths_match.group(1)) if baths_match else None,
                'sqft': int(sqft_match.group(1)) if sqft_match else None,
                'year_built': int(year_match.group(1)) if year_match else None,
                'source': 'zillow_scrape',
                'confidence': 'medium',
                'as_of': datetime.now().isoformat(),
            }

        return None

    except Exception as e:
        print(f"Zillow scrape error: {e}")
        return None


def scrape_redfin_estimate(address: str) -> Optional[Dict]:
    """
    Scrape Redfin estimate as fallback.
    """
    try:
        # Redfin search
        search_url = f"https://www.redfin.com/stingray/do/location-autocomplete?location={urllib.parse.quote(address)}&v=2"

        response = _fetch_with_headers(search_url)
        if not response:
            return None

        # Parse autocomplete response
        data = json.loads(response.replace('{}&&', ''))

        if data.get('payload', {}).get('sections'):
            for section in data['payload']['sections']:
                for row in section.get('rows', []):
                    if row.get('type') == 'homeAddress':
                        url = row.get('url')
                        if url:
                            # Fetch property page
                            prop_html = _fetch_with_headers(f"https://www.redfin.com{url}")
                            if prop_html:
                                # Look for estimate
                                estimate_match = re.search(r'"avm"\s*:\s*{\s*"value"\s*:\s*(\d+)', prop_html)
                                if estimate_match:
                                    return {
                                        'estimated_value': int(estimate_match.group(1)),
                                        'source': 'redfin_scrape',
                                        'confidence': 'medium',
                                        'as_of': datetime.now().isoformat(),
                                    }

        return None

    except Exception as e:
        print(f"Redfin scrape error: {e}")
        return None


def estimate_from_tax_assessment(address: str, state: str) -> Optional[Dict]:
    """
    Estimate value from typical tax assessment ratio.

    Tax assessments are usually 70-100% of market value.
    This is a very rough estimate.
    """
    # This would require scraping county assessor sites which vary by location
    # For now, return guidance for manual entry
    return {
        'estimated_value': None,
        'source': 'manual_required',
        'guidance': 'Check your county tax assessor website or recent tax bill. Market value is typically 1.0-1.4x the assessed value.',
        'as_of': datetime.now().isoformat(),
    }


def get_property_value(address: str) -> Dict:
    """
    Get property value using multiple sources with fallbacks.

    Priority:
    1. Zillow Zestimate
    2. Redfin Estimate
    3. Manual guidance

    Caches results for 30 days.
    """
    # Check cache
    cache_key = f"property:{hashlib.md5(address.lower().encode()).hexdigest()}"

    conn = get_conn()
    try:
        cached = conn.execute("""
            SELECT data, expires_at FROM enrichment_cache
            WHERE cache_key = ? AND expires_at > datetime('now')
        """, [cache_key]).fetchone()

        if cached:
            return json.loads(cached['data'])
    except:
        pass

    # Try sources in order
    result = None

    # 1. Try Zillow
    result = scrape_zillow_zestimate(address)

    # 2. Try Redfin if Zillow failed
    if not result or not result.get('estimated_value'):
        result = scrape_redfin_estimate(address)

    # 3. Fall back to manual guidance
    if not result or not result.get('estimated_value'):
        result = estimate_from_tax_assessment(address, '')

    # Cache for 30 days
    if result:
        try:
            expires = (datetime.now() + timedelta(days=30)).isoformat()
            conn.execute("""
                INSERT OR REPLACE INTO enrichment_cache
                (id, cache_key, source, data, fetched_at, expires_at)
                VALUES (?, ?, ?, ?, datetime('now'), ?)
            """, [
                hashlib.md5(cache_key.encode()).hexdigest(),
                cache_key,
                result.get('source', 'unknown'),
                json.dumps(result),
                expires
            ])
        except:
            pass

    return result or {'source': 'error', 'message': 'Could not estimate property value'}


def get_vehicle_value_scrape(year: int, make: str, model: str, mileage: int = None) -> Dict:
    """
    Scrape vehicle value from NADA or similar.

    Note: KBB blocks scrapers heavily. This is best-effort.
    """
    try:
        # Try NADA Guides (slightly less protected)
        make_lower = make.lower().replace(' ', '-')
        model_lower = model.lower().replace(' ', '-')

        url = f"https://www.nadaguides.com/Cars/{year}/{make_lower}/{model_lower}"

        html = _fetch_with_headers(url)
        if html:
            # Look for price range
            low_match = re.search(r'Low Retail[^\d]*\$?([\d,]+)', html)
            high_match = re.search(r'Average Retail[^\d]*\$?([\d,]+)', html)

            if low_match or high_match:
                low = int(low_match.group(1).replace(',', '')) if low_match else None
                high = int(high_match.group(1).replace(',', '')) if high_match else None
                avg = ((low or 0) + (high or 0)) // 2 if (low or high) else None

                # Adjust for mileage (rough: -$0.10 per mile over 12k/year)
                if avg and mileage:
                    expected_miles = (datetime.now().year - year) * 12000
                    excess = mileage - expected_miles
                    if excess > 0:
                        avg = max(1000, avg - int(excess * 0.10))

                return {
                    'estimated_value': avg,
                    'low_estimate': low,
                    'high_estimate': high,
                    'mileage_adjusted': mileage is not None,
                    'source': 'nada_scrape',
                    'confidence': 'medium',
                    'as_of': datetime.now().isoformat(),
                }

        # Fallback: depreciation estimate
        current_year = datetime.now().year
        age = current_year - year
        # Typical car loses 60% in first 5 years, then 10%/year
        if age <= 5:
            remaining_pct = 1 - (age * 0.12)  # ~12% per year first 5 years
        else:
            remaining_pct = 0.40 - ((age - 5) * 0.07)  # ~7% per year after
        remaining_pct = max(0.10, remaining_pct)  # Floor at 10%

        return {
            'estimated_value': None,
            'depreciation_estimate': f"{int(remaining_pct * 100)}% of original MSRP",
            'source': 'depreciation_formula',
            'confidence': 'low',
            'guidance': 'Check KBB.com or Edmunds.com for accurate value',
            'as_of': datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"Vehicle scrape error: {e}")
        return {
            'source': 'error',
            'message': str(e),
            'guidance': 'Enter value manually from KBB.com',
        }
