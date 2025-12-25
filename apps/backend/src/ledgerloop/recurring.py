from __future__ import annotations

import json
import hashlib
import math
import re
import statistics
import uuid
from collections import defaultdict, Counter
from dataclasses import dataclass
from datetime import date, datetime, UTC
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class Tx:
    id: str
    account_id: str
    posted_at: date
    amount: float
    description_norm: str


_RE_PMNT_PREFIX = re.compile(r"^(pmnt\s+(?:sent|rcvd)\s+\d{4})\s+", re.I)
_RE_TXTYPE_DATE_PREFIX = re.compile(
    r"^(?:checkcard|purchase|pos|debit|debit\s+card|card|ach|payment|recurring)\s+\d{4}\s+",
    re.I,
)
_RE_TRAILING_LONG_NUM = re.compile(r"\s+\d{8,}\s*$")
_RE_TRAILING_CONF = re.compile(r"\s+conf(?:#|irmation)?\s*[:#]?\s*[a-z0-9]+\s*$", re.I)

# Additional patterns to strip for better recurring grouping
_RE_DES_BLOCK = re.compile(r"\s+des:\S+", re.I)  # des:web_pay, des:draft, des:mortgage, etc.
_RE_ID_BLOCK = re.compile(r"\s+id:\S+", re.I)  # id:46921652011525
_RE_INDN_BLOCK = re.compile(r"\s+indn:\S+(\s+co)?", re.I)  # indn:marwan moftah co
_RE_SHORT_RANDOM_CODE = re.compile(r"\s+[a-z0-9]{5,8}\s+", re.I)  # sjw6xw, vslcqr, 3nkg2w
_RE_HELPPAY_SUFFIX = re.compile(r"\s+g\.co/helppay#\S*", re.I)  # g.co/helppay#ca
_RE_LOCATION_SUFFIX = re.compile(r"\s+(mountain\s+view|los\s+gatos|san\s+francisco)\s*[a-z]{2}$", re.I)
_RE_PHONE_SUFFIX = re.compile(r"\s+\d{3}[-.]?\d{3}[-.]?\d{4}\s*[a-z]{2}$", re.I)  # 800-841-3000 dc
_RE_TRAILING_STATE = re.compile(r"\s+[a-z]{2}$", re.I)  # Trailing state codes


def normalize_recurring_key(desc_norm: str, amount: float | None = None) -> str:
    """Return a stable key for recurring grouping from a normalized description.

    Goal: avoid fragmentation from statement artifacts (dates, reference numbers, IDs).
    Aggressively strips dynamic elements to group the same merchant together.
    """
    from .detect.p2p import parse_p2p_descriptor

    d = (desc_norm or "").strip().lower()
    if not d:
        return ""

    p2p = parse_p2p_descriptor(d, amount=amount)
    if p2p:
        provider = p2p.get("provider") or "p2p"
        counterparty = (p2p.get("counterparty") or "").strip()
        if counterparty:
            return f"{provider} {counterparty}".strip()
        return provider

    # Strip common dynamic prefixes
    d = _RE_PMNT_PREFIX.sub("", d).strip()
    d = _RE_TXTYPE_DATE_PREFIX.sub("", d).strip()

    # Strip ACH/bank transfer artifacts (des:, id:, indn:)
    d = _RE_DES_BLOCK.sub("", d).strip()
    d = _RE_ID_BLOCK.sub("", d).strip()
    d = _RE_INDN_BLOCK.sub("", d).strip()

    # Strip confirmation numbers and trailing long numbers
    d = _RE_TRAILING_CONF.sub("", d).strip()
    d = _RE_TRAILING_LONG_NUM.sub("", d).strip()

    # Strip short random codes (e.g., sjw6xw in "google fiber sjw6xw")
    d = _RE_SHORT_RANDOM_CODE.sub(" ", d).strip()

    # Strip Google help URLs
    d = _RE_HELPPAY_SUFFIX.sub("", d).strip()

    # Normalize location suffixes to just merchant name
    # Keep phone number but strip if at end with state
    d = _RE_PHONE_SUFFIX.sub("", d).strip()

    # Clean up extra whitespace
    d = re.sub(r"\s+", " ", d).strip()

    return d


def _amount_bucket(amount: float, tol: float = 0.10) -> Tuple[int, int]:
    """Bucket amounts using a relative tolerance.

    Groups amounts that are within ±(tol * amount) of each other into the same bucket.
    Returns a tuple (sign, bucket_index) where bucket_index is based on cents and
    a dynamic bucket size derived from the magnitude of the amount.
    """
    sign = 1 if amount > 0 else -1 if amount < 0 else 0
    cents = abs(amount) * 100.0
    # Derive a bucket size in cents as a percentage of the amount, with sensible floors/ceilings
    # Ensures small amounts still group (min 1 cent), and very large amounts don't over-group
    bucket_size_cents = max(1.0, cents * max(0.0, float(tol)))
    rounded = int(round(cents / bucket_size_cents))
    return (sign, rounded)


def cadence_from_intervals(days: List[int], allow_short_cadence: bool = False) -> Optional[str]:
    """Detect cadence from a list of interval days between transactions.

    Args:
        days: List of day intervals between consecutive transactions
        allow_short_cadence: If True, allows weekly/biweekly detection (default False)

    Returns:
        Cadence string or None if no pattern matches
    """
    if not days:
        return None
    med = statistics.median(days)

    # Weekly: 6-8 day median
    if 6 <= med <= 8:
        return "weekly" if allow_short_cadence else None

    # Biweekly: 13-15 days (strict - all intervals must match)
    if 13 <= med <= 15 and all(13 <= d <= 15 for d in days):
        return "biweekly" if allow_short_cadence else None

    # Monthly: 28-35 days (slightly relaxed upper bound for month variations)
    if 28 <= med <= 35:
        return "monthly"

    # Quarterly: 85-100 days
    if 85 <= med <= 100:
        return "quarterly"

    # Semi-annual: 175-195 days (~6 months)
    if 175 <= med <= 195:
        return "semi_annual"

    # Annual: 350-380 days
    if 350 <= med <= 380:
        return "annual"

    return None


def detect_recurring_candidates(
    txs: Iterable[Tx],
    min_occurrences: int = 3,
    tol: float = 0.15,
    price_hike_threshold: float = 0.10,
    allow_short_cadence: bool = False,
) -> List[Dict]:
    """Group transactions by a normalized description and detect cadence.

    For stable-amount series (most subscriptions), we additionally bucket by amount to avoid mixing
    unrelated merchants that share a noisy descriptor. For variable-amount series (common for utilities),
    we allow amount variation and group by merchant/descriptor only.

    Args:
        txs: Transactions to analyze
        min_occurrences: Minimum number of transactions to form a pattern
        tol: Amount tolerance for bucketing (e.g., 0.15 = 15%)
        price_hike_threshold: Threshold for detecting price increases
        allow_short_cadence: If True, detect weekly/biweekly patterns too

    Returns candidate dicts:
      {"desc": str, "amount_mean": float, "amount_sd": float, "cadence": str, "tx_ids": [...], "anchor_day": int, "variable_amount": bool}
    """
    desc_groups: Dict[str, List[Tx]] = defaultdict(list)
    for t in txs:
        key_desc = normalize_recurring_key(t.description_norm, amount=t.amount)
        if not key_desc:
            continue
        desc_groups[key_desc].append(t)

    candidates: List[Dict] = []
    VARIABLE_AMOUNT_RATIO = 0.20

    def _build_candidate(desc: str, arr: List[Tx], variable_amount: bool) -> Optional[Dict]:
        if len(arr) < min_occurrences:
            return None
        arr_sorted = sorted(arr, key=lambda x: x.posted_at)
        intervals = [
            abs((arr_sorted[i].posted_at - arr_sorted[i - 1].posted_at).days)
            for i in range(1, len(arr_sorted))
        ]
        cad = cadence_from_intervals(intervals, allow_short_cadence=allow_short_cadence)
        if not cad:
            return None

        amounts = [t.amount for t in arr_sorted]
        mean = statistics.fmean(amounts)
        sd = statistics.pstdev(amounts) if len(amounts) > 1 else 0.0

        # For weekly, anchor is weekday (0-6); otherwise day of month (1-31)
        if cad == "weekly":
            anchor = Counter([t.posted_at.weekday() for t in arr_sorted]).most_common(1)[0][0]
        else:
            anchor = Counter([t.posted_at.day for t in arr_sorted]).most_common(1)[0][0]

        # Detect price hike (last vs previous)
        price_hike = False
        if len(arr_sorted) >= 2:
            a_last = abs(arr_sorted[-1].amount)
            a_prev = abs(arr_sorted[-2].amount)
            if a_prev > 0 and (a_last - a_prev) / a_prev > price_hike_threshold:
                price_hike = True

        occurrences = len(arr_sorted)

        # Calculate interval stability (how consistent the spacing is)
        if intervals:
            spread = (max(intervals) - min(intervals))
            interval_stability = 1.0 - min(1.0, spread / max(1.0, sum(intervals) / len(intervals)))
        else:
            interval_stability = 0.5

        # Calculate amount stability (lower variance = more stable)
        amount_stability = 1.0 - min(1.0, abs(sd) / max(1.0, abs(mean))) if mean else 0.5

        # Confidence formula: base + occurrence bonus + interval stability + amount stability
        # Cap occurrences bonus at 10 occurrences
        occ_factor = min(occurrences, 10) / 10.0
        confidence = max(0.0, min(1.0, 0.2 + 0.15 * occ_factor + 0.35 * interval_stability + 0.3 * amount_stability))

        # Calculate predicted next amount (use mean for stable, apply trend for variable)
        next_predicted_amount = mean
        if variable_amount and len(arr_sorted) >= 3:
            # Use simple linear trend from last 3 values
            recent = amounts[-3:]
            trend = (recent[-1] - recent[0]) / 2
            next_predicted_amount = recent[-1] + trend

        return {
            "desc": desc,
            "amount_mean": mean,
            "amount_sd": sd,
            "cadence": cad,
            "tx_ids": [t.id for t in arr_sorted],
            "anchor_day": int(anchor),
            "price_hike": price_hike,
            "confidence": confidence,
            "variable_amount": bool(variable_amount),
            "next_predicted_amount": next_predicted_amount,
            "last_date": arr_sorted[-1].posted_at,
        }

    for desc, arr in desc_groups.items():
        if len(arr) < min_occurrences:
            continue
        amounts_all = [t.amount for t in arr]
        mean_all = statistics.fmean(amounts_all) if amounts_all else 0.0
        sd_all = statistics.pstdev(amounts_all) if len(amounts_all) > 1 else 0.0
        ratio = abs(sd_all) / max(1.0, abs(mean_all)) if mean_all else 0.0
        is_variable = ratio >= VARIABLE_AMOUNT_RATIO and len(set(round(abs(a), 2) for a in amounts_all)) >= 2

        if is_variable:
            cand = _build_candidate(desc, arr, variable_amount=True)
            if cand:
                candidates.append(cand)
            continue

        # Stable-amount: keep amount bucketing to avoid merging different subscriptions.
        by_bucket: Dict[Tuple[int, int], List[Tx]] = defaultdict(list)
        for t in arr:
            by_bucket[_amount_bucket(t.amount, tol)].append(t)
        for _, bucket_arr in by_bucket.items():
            cand = _build_candidate(desc, bucket_arr, variable_amount=False)
            if cand:
                candidates.append(cand)
    return candidates


def _next_date(last: date, cadence: str, anchor_day: int | None = None) -> date:
    """Calculate next expected date based on cadence and anchor day.

    For monthly/quarterly/semi-annual/annual, uses anchor_day (day of month)
    to predict the actual next occurrence date rather than naive day addition.
    """
    from datetime import timedelta
    import calendar

    if cadence == 'weekly':
        return last + timedelta(days=7)
    if cadence == 'biweekly':
        return last + timedelta(days=14)

    # For monthly+ cadences, use proper month arithmetic with anchor_day
    if cadence in ('monthly', 'quarterly', 'semi_annual', 'annual'):
        # Determine how many months to add
        months_to_add = {
            'monthly': 1,
            'quarterly': 3,
            'semi_annual': 6,
            'annual': 12,
        }.get(cadence, 1)

        # Calculate target month/year
        target_month = last.month + months_to_add
        target_year = last.year
        while target_month > 12:
            target_month -= 12
            target_year += 1

        # Use anchor_day if provided, otherwise use last's day
        day = anchor_day if anchor_day else last.day

        # Clamp to valid day for target month (e.g., Jan 31 -> Feb 28)
        max_day = calendar.monthrange(target_year, target_month)[1]
        day = min(day, max_day)

        return date(target_year, target_month, day)

    # Fallback for unknown cadences
    return last + timedelta(days=30)


def _cadence_days(cadence: str) -> int:
    """Return expected interval in days for a cadence."""
    return {
        'weekly': 7,
        'biweekly': 14,
        'monthly': 30,
        'quarterly': 91,
        'semi_annual': 182,
        'annual': 365,
    }.get(cadence, 30)


def calculate_series_status(
    last_date: date | None,
    next_date: date | None,
    cadence: str | None,
    today: date | None = None,
) -> Dict[str, any]:
    """Calculate the health status of a recurring series.

    Returns:
        {
            "status": "active" | "overdue" | "likely_cancelled",
            "days_since_last": int,
            "days_overdue": int | None,
            "missed_payments": int,
            "health_score": float (0-1)
        }
    """
    if today is None:
        today = date.today()

    if not last_date:
        return {
            "status": "unknown",
            "days_since_last": None,
            "days_overdue": None,
            "missed_payments": 0,
            "health_score": 0.5,
        }

    days_since = (today - last_date).days
    expected_interval = _cadence_days(cadence or 'monthly')

    # Calculate expected next date if not provided
    if next_date:
        days_until_next = (next_date - today).days
    else:
        days_until_next = expected_interval - days_since

    # Determine status
    grace_period = max(7, expected_interval * 0.25)  # 25% grace period, min 7 days

    if days_until_next >= -grace_period:
        # Payment is on time or within grace period
        status = "active"
        days_overdue = None
        missed_payments = 0
        health_score = 1.0
    else:
        # Payment is overdue
        days_overdue = abs(days_until_next)
        missed_payments = max(1, int(days_overdue / expected_interval))

        if missed_payments >= 3:
            status = "likely_cancelled"
            health_score = 0.1
        elif missed_payments >= 2:
            status = "overdue"
            health_score = 0.3
        else:
            status = "overdue"
            health_score = 0.6

    return {
        "status": status,
        "days_since_last": days_since,
        "days_overdue": days_overdue,
        "missed_payments": missed_payments,
        "health_score": health_score,
    }


def extract_merchant_name_ai(description: str, use_ai: bool = True, use_llm: bool = False) -> str:
    """Extract a clean, human-friendly merchant name from a bank description.

    Uses pattern matching first, then optionally LLM for unknown merchants.

    Args:
        description: Raw bank description (e.g., "dukeenergycorpor des:web_pay id:123")
        use_ai: Whether to try heuristic extraction (legacy param, always True)
        use_llm: Whether to try LLM extraction for unknown merchants

    Returns:
        Clean merchant name (e.g., "Duke Energy")
    """
    # Known merchant mappings for common recurring payments
    MERCHANT_MAP = {
        # Utilities
        r"duke\s*energy|dukeenergycorpor": "Duke Energy",
        r"dominion\s*(s|energy)": "Dominion Energy",
        r"city\s+of(?:\s+raleigh)?": "City of Raleigh Water",
        r"spectrum": "Spectrum",
        # Internet/Phone
        r"google\s*\*?\s*fiber": "Google Fiber",
        r"google\s*\*?\s*fi\b": "Google Fi",
        r"google\s*\*?\s*youtub": "YouTube Premium",
        r"at\s*&\s*t|att\s+mobility": "AT&T",
        r"verizon": "Verizon",
        # Insurance
        r"geico\s*[\*]?\s*auto": "GEICO Insurance",
        r"geico": "GEICO Insurance",
        r"progressive": "Progressive Insurance",
        r"state\s+farm": "State Farm",
        # Streaming
        r"netflix": "Netflix",
        r"spotify": "Spotify",
        r"hulu": "Hulu",
        r"disney\s*\+?": "Disney+",
        r"hbo\s*max": "HBO Max",
        r"apple\s*tv": "Apple TV+",
        r"amazon\s*prime": "Amazon Prime",
        r"plex": "Plex",
        r"nebula": "Nebula",
        # Financial
        r"carrington\s*(mortgage|s)?": "Carrington Mortgage",
        r"rocket\s+money": "Rocket Money",
        r"albert\s+(pymnts|genius)": "Albert",
        r"avant\s+llc": "Avant",
        r"citi\s+(card|moftah)": "Citi Card",
        r"ally\s+(?:moftah|auto)?": "Ally Auto",
        r"bank\s+of\s+(?:america|pay)": "Bank of America",
        r"paypal\s*\*?\s*([a-z0-9]+)": "PayPal",  # Will extract vendor below
        r"affirm": "Affirm",
        # Services
        r"iiq\*identityiq|identityiq": "IdentityIQ",
        r"roadrunner\s*fina": "Roadrunner Financial",
        r"amz\*amazon\s+payments": "Amazon Payments",
        r"musoramedia": "Musora Media",
        r"ea\s+inc": "EA Games",
        r"easynews": "Easynews",
        r"cursor.*ide|cursor\.ai": "Cursor AI",
        r"threecolts": "ThreeColts",
        # P2P Payments - extract counterparty
        r"venmo": "Venmo",
        r"cash\s*app": "Cash App",
        r"zelle": "Zelle",
    }

    desc = (description or "").strip().lower()
    if not desc:
        return "Unknown"

    # Special handling for PayPal - extract vendor FIRST to avoid generic matching
    if "paypal" in desc:
        # PayPal with asterisk vendor (e.g., "paypal *steam games")
        m = re.search(r"paypal\s*\*\s*([a-z0-9\s\.]+?)(?:\s+\d{3}|\s+(?:des|id|indn|co):|$)", desc, re.I)
        if m:
            vendor = m.group(1).strip().title()
            if vendor and len(vendor) > 2:
                return f"PayPal ({vendor})"
        # PayPal xfer with vendor in id field
        m = re.search(r"paypal\s+(?:des:\S+\s+)?id:([a-z]+)", desc, re.I)
        if m:
            vendor = m.group(1).strip().title()
            if vendor and len(vendor) > 2 and vendor.lower() not in ("p", "inst"):
                return f"PayPal ({vendor})"
        return "PayPal Transfer"

    # Try known mappings (fast, no AI needed)
    for pattern, merchant in MERCHANT_MAP.items():
        if re.search(pattern, desc, re.I):
            return merchant

    # Fallback: Clean up the description using heuristics
    cleaned = desc

    # Remove common prefixes
    cleaned = re.sub(r"^(?:ach|pos|debit|credit|purchase|payment|checkcard)\s+\d*\s*", "", cleaned, flags=re.I)

    # Remove ACH metadata blocks
    cleaned = re.sub(r"\s+(?:des|id|indn|co):\S+", "", cleaned, flags=re.I)

    # Remove confirmation numbers, dates, reference numbers
    cleaned = re.sub(r"\s+conf[#:]?\s*[a-z0-9]+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+\d{8,}", "", cleaned)  # Long numbers
    cleaned = re.sub(r"\s+[a-z0-9]{5,8}(?:\s+|$)", " ", cleaned, flags=re.I)  # Short codes

    # Remove location/state suffixes
    cleaned = re.sub(r"\s+(?:mountain\s+view|los\s+gatos|san\s+francisco)?\s*[a-z]{2}$", "", cleaned, flags=re.I)

    # Remove phone numbers
    cleaned = re.sub(r"\s+\d{3}[-.]?\d{3}[-.]?\d{4}", "", cleaned)

    # Clean up whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Title case the result
    if cleaned:
        # Don't title case if it's all caps and short (like acronyms)
        if len(cleaned) > 5 or not cleaned.isupper():
            cleaned = cleaned.title()

        # If we got a generic/short result, try LLM for better extraction
        if use_llm and len(cleaned) < 8 and cleaned.lower() not in ("unknown",):
            try:
                from .merchant_intelligence import extract_merchant_name_llm
                llm_result = extract_merchant_name_llm(description, 0.0, use_cache=True)
                if llm_result and len(llm_result) > len(cleaned):
                    return llm_result
            except Exception:
                pass  # Fall through to return cleaned

        return cleaned

    # Final fallback: try LLM if enabled
    if use_llm:
        try:
            from .merchant_intelligence import extract_merchant_name_llm
            llm_result = extract_merchant_name_llm(description, 0.0, use_cache=True)
            if llm_result and llm_result != "Unknown":
                return llm_result
        except Exception:
            pass

    return description[:30].title() if description else "Unknown"


# =============================================================================
# PHASE 1: ENHANCED RECURRING TYPE DETECTION
# =============================================================================

class RecurringTypeClassifier:
    """Classifies recurring transactions into types: subscription, bill, loan, credit_card."""

    # Loan lender patterns with sub-categories
    LOAN_PATTERNS = {
        # Auto loans
        r"ally\s*(auto|bank|moftah)?": ("loan", "auto_loan", "Ally Auto", True),
        r"toyota\s+financial": ("loan", "auto_loan", "Toyota Financial", True),
        r"honda\s+financial": ("loan", "auto_loan", "Honda Financial", True),
        r"capital\s+one\s+auto": ("loan", "auto_loan", "Capital One Auto", True),
        r"santander\s+(consumer|auto)?": ("loan", "auto_loan", "Santander", True),
        r"carmax\s+(auto)?": ("loan", "auto_loan", "CarMax Auto", True),
        r"ford\s+(motor\s+)?credit": ("loan", "auto_loan", "Ford Credit", True),
        r"gm\s+financial": ("loan", "auto_loan", "GM Financial", True),
        r"bmw\s+financial": ("loan", "auto_loan", "BMW Financial", True),
        r"mercedes\s+benz\s+financial": ("loan", "auto_loan", "Mercedes-Benz Financial", True),
        r"nissan\s+motor\s+accept": ("loan", "auto_loan", "Nissan Motor Acceptance", True),
        r"hyundai\s+(capital|motor)": ("loan", "auto_loan", "Hyundai Capital", True),
        r"chrysler\s+capital": ("loan", "auto_loan", "Chrysler Capital", True),
        r"westlake\s+financial": ("loan", "auto_loan", "Westlake Financial", True),
        r"roadrunner\s*fina": ("loan", "auto_loan", "Roadrunner Financial", True),

        # Mortgage
        r"carrington\s*(mortgage|s)?": ("loan", "mortgage", "Carrington Mortgage", True),
        r"rocket\s+(mortgage|homes)": ("loan", "mortgage", "Rocket Mortgage", True),
        r"quicken\s+loans": ("loan", "mortgage", "Quicken Loans", True),
        r"wells\s+fargo\s+home": ("loan", "mortgage", "Wells Fargo Home", True),
        r"chase\s+home": ("loan", "mortgage", "Chase Home", True),
        r"bank\s+of\s+america\s+mort": ("loan", "mortgage", "Bank of America Mortgage", True),
        r"nationstar|mr\s+cooper": ("loan", "mortgage", "Mr. Cooper", True),
        r"pennymac": ("loan", "mortgage", "PennyMac", True),
        r"freedom\s+mortgage": ("loan", "mortgage", "Freedom Mortgage", True),
        r"loancare": ("loan", "mortgage", "LoanCare", True),
        r"newrez|shellpoint": ("loan", "mortgage", "NewRez", True),
        r"escrow": ("loan", "mortgage", None, True),

        # Personal loans
        r"sofi\s*(loans?)?": ("loan", "personal_loan", "SoFi", True),
        r"lending\s*club": ("loan", "personal_loan", "LendingClub", True),
        r"prosper\s*(marketplace)?": ("loan", "personal_loan", "Prosper", True),
        r"upstart": ("loan", "personal_loan", "Upstart", True),
        r"marcus\s+(by\s+gs)?": ("loan", "personal_loan", "Marcus", True),
        r"avant\s+(llc)?": ("loan", "personal_loan", "Avant", True),
        r"best\s+egg": ("loan", "personal_loan", "Best Egg", True),
        r"lightstream": ("loan", "personal_loan", "LightStream", True),
        r"upgrade\s*(inc)?": ("loan", "personal_loan", "Upgrade", True),
        r"affirm": ("loan", "bnpl", "Affirm", False),  # Buy Now Pay Later
        r"klarna": ("loan", "bnpl", "Klarna", False),
        r"afterpay": ("loan", "bnpl", "Afterpay", False),

        # Student loans
        r"navient": ("loan", "student_loan", "Navient", True),
        r"nelnet": ("loan", "student_loan", "Nelnet", True),
        r"fed\s*loan|fedloan": ("loan", "student_loan", "FedLoan", True),
        r"great\s+lakes": ("loan", "student_loan", "Great Lakes", True),
        r"mohela": ("loan", "student_loan", "MOHELA", True),
        r"aidvantage": ("loan", "student_loan", "Aidvantage", True),
        r"sallie\s+mae": ("loan", "student_loan", "Sallie Mae", True),
        r"dept\s+of\s+ed|education\s+dep": ("loan", "student_loan", "Dept of Education", True),
    }

    # Credit card issuer patterns
    CREDIT_CARD_PATTERNS = {
        r"chase\s+(card|pymt|payment)": ("credit_card", "chase", "Chase Card", True),
        r"amex|american\s+express": ("credit_card", "amex", "American Express", True),
        r"capital\s+one(?!\s+auto)": ("credit_card", "capital_one", "Capital One", True),
        r"citi\s*(card|bank|moftah)?": ("credit_card", "citi", "Citi Card", True),
        r"discover\s+(card|financial)?": ("credit_card", "discover", "Discover", True),
        r"wells\s+fargo\s+card": ("credit_card", "wells_fargo", "Wells Fargo Card", True),
        r"bank\s+of\s+america\s+(card|pay)": ("credit_card", "boa", "Bank of America Card", True),
        r"usaa\s+(card)?": ("credit_card", "usaa", "USAA Card", True),
        r"navy\s+federal\s+(card)?": ("credit_card", "navy_fed", "Navy Federal", True),
        r"synchrony": ("credit_card", "synchrony", "Synchrony", False),
        r"barclays?\s*(card)?": ("credit_card", "barclays", "Barclays", True),
        r"apple\s+card": ("credit_card", "apple", "Apple Card", True),
    }

    # Household bill patterns
    BILL_PATTERNS = {
        # Electric/Gas utilities
        r"duke\s*energy|dukeenergycorpor": ("bill", "utility_electric", "Duke Energy", True),
        r"dominion\s*(energy)?": ("bill", "utility_electric", "Dominion Energy", True),
        r"pge|pacific\s+gas": ("bill", "utility_electric", "PG&E", True),
        r"con\s*ed(ison)?": ("bill", "utility_electric", "Con Edison", True),
        r"fpl|florida\s+power": ("bill", "utility_electric", "FPL", True),
        r"sce|southern\s+calif\s+edison": ("bill", "utility_electric", "SCE", True),
        r"xcel\s+energy": ("bill", "utility_electric", "Xcel Energy", True),
        r"national\s+grid": ("bill", "utility_gas", "National Grid", True),
        r"atmos\s+energy": ("bill", "utility_gas", "Atmos Energy", True),
        r"centerpoint": ("bill", "utility_gas", "CenterPoint", True),

        # Water/Sewer
        r"city\s+of(?:\s+\w+)?\s*water": ("bill", "utility_water", None, True),
        r"water\s*(dept|department|utility)": ("bill", "utility_water", None, True),
        r"municipal\s+water": ("bill", "utility_water", None, True),
        r"sewer": ("bill", "utility_sewer", None, True),

        # Internet/Phone/Cable
        r"spectrum": ("bill", "internet", "Spectrum", True),
        r"comcast|xfinity": ("bill", "internet", "Xfinity", True),
        r"google\s*\*?\s*fiber": ("bill", "internet", "Google Fiber", True),
        r"at\s*&\s*t|att\s+": ("bill", "telecom", "AT&T", True),
        r"verizon(?!\s+wireless)": ("bill", "internet", "Verizon Fios", True),
        r"verizon\s+wireless": ("bill", "phone", "Verizon Wireless", True),
        r"t-?\s*mobile": ("bill", "phone", "T-Mobile", True),
        r"google\s*\*?\s*fi\b": ("bill", "phone", "Google Fi", True),
        r"cox\s+comm": ("bill", "internet", "Cox", True),
        r"frontier\s+comm": ("bill", "internet", "Frontier", True),
        r"centurylink|lumen": ("bill", "internet", "Lumen", True),

        # Insurance
        r"geico\s*[\*]?\s*(auto)?": ("bill", "insurance_auto", "GEICO", True),
        r"progressive": ("bill", "insurance_auto", "Progressive", True),
        r"state\s+farm": ("bill", "insurance", "State Farm", True),
        r"allstate": ("bill", "insurance", "Allstate", True),
        r"farmers\s+ins": ("bill", "insurance", "Farmers", True),
        r"liberty\s+mutual": ("bill", "insurance", "Liberty Mutual", True),
        r"usaa\s+ins": ("bill", "insurance", "USAA Insurance", True),
        r"nationwide\s+ins": ("bill", "insurance", "Nationwide", True),
        r"amica": ("bill", "insurance", "Amica", True),
        r"travelers\s+ins": ("bill", "insurance", "Travelers", True),
        r"lemonade\s+ins": ("bill", "insurance_renters", "Lemonade", False),

        # Property
        r"hoa\s*(fee|dues)?": ("bill", "hoa", None, True),
        r"property\s+tax": ("bill", "property_tax", None, True),
        r"waste\s+management|republic\s+services": ("bill", "trash", None, True),
    }

    # Subscription patterns
    SUBSCRIPTION_PATTERNS = {
        # Streaming video
        r"netflix": ("subscription", "streaming", "Netflix", False),
        r"hulu": ("subscription", "streaming", "Hulu", False),
        r"disney\s*\+?": ("subscription", "streaming", "Disney+", False),
        r"hbo\s*max|max\.com": ("subscription", "streaming", "Max", False),
        r"amazon\s*prime\s*video": ("subscription", "streaming", "Prime Video", False),
        r"peacock": ("subscription", "streaming", "Peacock", False),
        r"paramount\s*\+": ("subscription", "streaming", "Paramount+", False),
        r"apple\s*tv\s*\+?": ("subscription", "streaming", "Apple TV+", False),
        r"youtube\s*(premium|tv)": ("subscription", "streaming", "YouTube Premium", False),
        r"crunchyroll": ("subscription", "streaming", "Crunchyroll", False),
        r"fubo": ("subscription", "streaming", "FuboTV", False),
        r"sling\s*tv": ("subscription", "streaming", "Sling TV", False),
        r"plex": ("subscription", "streaming", "Plex", False),
        r"nebula": ("subscription", "streaming", "Nebula", False),

        # Streaming music
        r"spotify": ("subscription", "music", "Spotify", False),
        r"apple\s*music": ("subscription", "music", "Apple Music", False),
        r"tidal": ("subscription", "music", "Tidal", False),
        r"pandora": ("subscription", "music", "Pandora", False),
        r"amazon\s*music": ("subscription", "music", "Amazon Music", False),
        r"deezer": ("subscription", "music", "Deezer", False),
        r"sirius\s*xm": ("subscription", "music", "SiriusXM", False),

        # Cloud/Storage
        r"icloud|apple\.com/bill": ("subscription", "cloud", "iCloud", False),
        r"google\s*(one|drive|storage)": ("subscription", "cloud", "Google One", False),
        r"dropbox": ("subscription", "cloud", "Dropbox", False),
        r"microsoft\s*365|office\s*365": ("subscription", "productivity", "Microsoft 365", False),

        # Software/SaaS
        r"adobe": ("subscription", "software", "Adobe", False),
        r"github": ("subscription", "software", "GitHub", False),
        r"jetbrains": ("subscription", "software", "JetBrains", False),
        r"cursor.*ide|cursor\.ai": ("subscription", "software", "Cursor AI", False),
        r"notion": ("subscription", "software", "Notion", False),
        r"slack": ("subscription", "software", "Slack", False),
        r"zoom\s*(video)?": ("subscription", "software", "Zoom", False),
        r"1password|onepassword": ("subscription", "software", "1Password", False),
        r"lastpass": ("subscription", "software", "LastPass", False),
        r"nordvpn": ("subscription", "software", "NordVPN", False),
        r"expressvpn": ("subscription", "software", "ExpressVPN", False),

        # Fitness/Health
        r"planet\s+fitness": ("subscription", "fitness", "Planet Fitness", False),
        r"la\s+fitness": ("subscription", "fitness", "LA Fitness", False),
        r"anytime\s+fitness": ("subscription", "fitness", "Anytime Fitness", False),
        r"24\s+hour\s+fitness": ("subscription", "fitness", "24 Hour Fitness", False),
        r"peloton": ("subscription", "fitness", "Peloton", False),
        r"headspace": ("subscription", "wellness", "Headspace", False),
        r"calm": ("subscription", "wellness", "Calm", False),
        r"noom": ("subscription", "wellness", "Noom", False),

        # News/Media
        r"new\s+york\s+times|nytimes": ("subscription", "news", "NY Times", False),
        r"washington\s+post": ("subscription", "news", "Washington Post", False),
        r"wall\s+street\s+journal|wsj": ("subscription", "news", "WSJ", False),
        r"the\s+athletic": ("subscription", "news", "The Athletic", False),
        r"substack": ("subscription", "news", "Substack", False),
        r"patreon": ("subscription", "creator", "Patreon", False),

        # Gaming
        r"xbox\s*(live|game\s*pass)": ("subscription", "gaming", "Xbox", False),
        r"playstation\s*(plus|now)": ("subscription", "gaming", "PlayStation", False),
        r"nintendo\s*(online|switch)": ("subscription", "gaming", "Nintendo", False),
        r"ea\s+(play|inc)": ("subscription", "gaming", "EA Games", False),
        r"steam": ("subscription", "gaming", "Steam", False),

        # Financial services
        r"rocket\s+money": ("subscription", "fintech", "Rocket Money", False),
        r"ynab|you\s+need\s+a\s+budget": ("subscription", "fintech", "YNAB", False),
        r"mint": ("subscription", "fintech", "Mint", False),
        r"identityiq|iiq": ("subscription", "identity", "IdentityIQ", False),
        r"lifelock": ("subscription", "identity", "LifeLock", False),
        r"experian": ("subscription", "identity", "Experian", False),

        # Other
        r"amazon\s+prime(?!\s*video)": ("subscription", "membership", "Amazon Prime", False),
        r"costco\s+(membership)?": ("subscription", "membership", "Costco", False),
        r"sams?\s+club": ("subscription", "membership", "Sam's Club", False),
        r"aaa\s+(membership)?": ("subscription", "membership", "AAA", False),
    }

    @classmethod
    def classify(cls, description: str, amount: float = 0.0) -> dict:
        """Classify a recurring transaction based on description.

        Returns:
            dict with keys: recurring_type, sub_category, clean_name, is_essential
        """
        desc = (description or "").lower().strip()
        if not desc:
            return {"recurring_type": "unknown", "sub_category": None, "clean_name": None, "is_essential": False}

        # Check loans first (most specific patterns)
        for pattern, (rec_type, sub_cat, clean_name, essential) in cls.LOAN_PATTERNS.items():
            if re.search(pattern, desc, re.I):
                return {
                    "recurring_type": rec_type,
                    "sub_category": sub_cat,
                    "clean_name": clean_name,
                    "is_essential": essential,
                }

        # Check credit cards
        for pattern, (rec_type, sub_cat, clean_name, essential) in cls.CREDIT_CARD_PATTERNS.items():
            if re.search(pattern, desc, re.I):
                return {
                    "recurring_type": rec_type,
                    "sub_category": sub_cat,
                    "clean_name": clean_name,
                    "is_essential": essential,
                }

        # Check household bills
        for pattern, (rec_type, sub_cat, clean_name, essential) in cls.BILL_PATTERNS.items():
            if re.search(pattern, desc, re.I):
                return {
                    "recurring_type": rec_type,
                    "sub_category": sub_cat,
                    "clean_name": clean_name,
                    "is_essential": essential,
                }

        # Check subscriptions
        for pattern, (rec_type, sub_cat, clean_name, essential) in cls.SUBSCRIPTION_PATTERNS.items():
            if re.search(pattern, desc, re.I):
                return {
                    "recurring_type": rec_type,
                    "sub_category": sub_cat,
                    "clean_name": clean_name,
                    "is_essential": essential,
                }

        # Fallback: try to infer from amount patterns
        abs_amount = abs(amount)

        # Very small recurring amounts are usually subscriptions
        if abs_amount > 0 and abs_amount < 20:
            return {"recurring_type": "subscription", "sub_category": None, "clean_name": None, "is_essential": False}

        # Large fixed amounts often indicate loans
        if abs_amount >= 200 and abs_amount <= 3000:
            # Could be loan or bill - check for common bill amounts
            if abs_amount < 400:
                return {"recurring_type": "bill", "sub_category": None, "clean_name": None, "is_essential": True}

        return {"recurring_type": "unknown", "sub_category": None, "clean_name": None, "is_essential": False}

    @classmethod
    def estimate_loan_term(cls, amount: float, sub_category: str | None) -> dict:
        """Estimate remaining term for a loan based on typical loan characteristics.

        Returns:
            dict with estimated_remaining (payments) and predicted_end_date
        """
        from datetime import date, timedelta

        # Typical loan terms by category
        TYPICAL_TERMS = {
            "auto_loan": (48, 72),  # 4-6 years
            "mortgage": (180, 360),  # 15-30 years
            "personal_loan": (24, 60),  # 2-5 years
            "student_loan": (120, 240),  # 10-20 years
            "bnpl": (3, 12),  # 3-12 months
        }

        today = date.today()

        if sub_category and sub_category in TYPICAL_TERMS:
            min_term, max_term = TYPICAL_TERMS[sub_category]
            # Estimate we're halfway through on average
            estimated_remaining = (min_term + max_term) // 4
            predicted_end = today + timedelta(days=estimated_remaining * 30)
            return {
                "estimated_remaining": estimated_remaining,
                "predicted_end_date": predicted_end.isoformat(),
            }

        return {"estimated_remaining": None, "predicted_end_date": None}

    @classmethod
    def calculate_annual_cost(cls, amount_mean: float, cadence: str) -> float:
        """Calculate annual cost based on average amount and cadence."""
        multipliers = {
            "weekly": 52,
            "biweekly": 26,
            "monthly": 12,
            "quarterly": 4,
            "semi_annual": 2,
            "annual": 1,
        }
        return abs(amount_mean) * multipliers.get(cadence, 12)


def classify_recurring_type(description: str, amount: float = 0.0, use_llm: bool = False) -> dict:
    """Convenience function to classify a recurring transaction type.

    Uses the enhanced recurring_classifier module with 400+ patterns,
    with optional LLM fallback for unknown merchants.

    Args:
        description: Transaction description
        amount: Transaction amount (helps with classification)
        use_llm: Whether to use LLM for unknown classifications

    Returns:
        dict with: recurring_type, sub_category, clean_name, is_essential, confidence
    """
    # Use the new comprehensive classifier first
    try:
        from .recurring_classifier import classify_recurring_type as classify_v2
        result = classify_v2(description, amount)
    except ImportError:
        # Fallback to legacy classifier
        result = RecurringTypeClassifier.classify(description, amount)

    # Add confidence scoring based on pattern matching
    if result.get("recurring_type") == "unknown":
        result["confidence"] = 0.3
    else:
        result["confidence"] = 0.8  # High confidence for pattern match

    result["provider"] = "pattern"
    result["from_cache"] = False

    # If unknown and LLM is enabled, try LLM classification
    if use_llm and result.get("recurring_type") == "unknown":
        try:
            from .merchant_intelligence import classify_recurring_type_llm
            llm_result = classify_recurring_type_llm(description, amount, use_cache=True)
            if llm_result.get("recurring_type") != "unknown":
                return llm_result
        except Exception:
            pass  # Fall through to pattern result

    return result


def _series_key_raw(name: str | None, cadence: str | None, amount_mean: float | None) -> str:
    cents = int(round(float(amount_mean or 0.0) * 100.0))
    return f"{(name or '').strip()}|{(cadence or '').strip()}|{cents}"


def compute_series_key(name: str | None, cadence: str | None, amount_mean: float | None) -> str:
    raw = _series_key_raw(name, cadence, amount_mean)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def infer_display_name(name: str | None) -> str | None:
    """Infer a human-friendly display name from raw merchant description.

    Uses the enhanced extract_merchant_name_ai function for better cleaning.
    """
    if not name:
        return None
    s = str(name).strip()
    if not s:
        return None

    # Use the AI/heuristic extraction
    result = extract_merchant_name_ai(s, use_ai=False)  # Use heuristics only for speed
    return result if result and result != "Unknown" else s


def _ensure_recurring_series_columns(conn) -> None:
    for sql in (
        "ALTER TABLE recurring_series ADD COLUMN series_key TEXT",
        "ALTER TABLE recurring_series ADD COLUMN display_name TEXT",
    ):
        try:
            conn.execute(sql)
        except Exception:
            pass


def _backfill_recurring_series_keys(conn) -> None:
    try:
        rows = conn.execute(
            """
            SELECT id, name, cadence, amount_mean, series_key, display_name
            FROM recurring_series
            WHERE series_key IS NULL OR trim(series_key) = ''
               OR display_name IS NULL OR trim(display_name) = ''
            """
        ).fetchall()
    except Exception:
        return
    for sid, name, cadence, amount_mean, series_key, display_name in rows:
        updates = {}
        if not series_key or not str(series_key).strip():
            updates["series_key"] = compute_series_key(name, cadence, amount_mean)
        if not display_name or not str(display_name).strip():
            updates["display_name"] = infer_display_name(name) or name
        if updates:
            sets = ", ".join([f"{k} = ?" for k in updates.keys()])
            conn.execute(f"UPDATE recurring_series SET {sets} WHERE id = ?", list(updates.values()) + [sid])


def dedupe_recurring_series(conn) -> int:
    """Merge duplicate recurring_series rows that share the same series_key.

    Keeps the "best" row (confirmed > pending > rejected; then most memberships; then newest decided_at),
    merges recurring_tx memberships, then deletes the extra series rows.
    """
    _ensure_recurring_series_columns(conn)
    _backfill_recurring_series_keys(conn)

    try:
        counts = {
            sid: int(cnt or 0)
            for sid, cnt in conn.execute("SELECT series_id, COUNT(*) FROM recurring_tx GROUP BY series_id").fetchall()
        }
        rows = conn.execute(
            """
            SELECT id, series_key, status, decided_at
            FROM recurring_series
            WHERE series_key IS NOT NULL AND trim(series_key) <> ''
            """
        ).fetchall()
    except Exception:
        return 0

    by_key: Dict[str, List[tuple]] = defaultdict(list)
    for sid, skey, status, decided_at in rows:
        by_key[str(skey)].append((sid, status, decided_at))

    def status_rank(s: str | None) -> int:
        if s == "confirmed":
            return 3
        if s == "pending":
            return 2
        if s == "rejected":
            return 1
        return 0

    removed = 0
    for skey, group in by_key.items():
        if len(group) <= 1:
            continue

        group_sorted = sorted(
            group,
            key=lambda x: (
                status_rank(x[1]),
                counts.get(x[0], 0),
                x[2] is not None,
                x[2] or datetime.min.replace(tzinfo=UTC),
                x[0],
            ),
            reverse=True,
        )
        keep_id = group_sorted[0][0]
        for sid, _, _ in group_sorted[1:]:
            try:
                conn.execute(
                    "INSERT INTO recurring_tx (series_id, tx_id) SELECT ?, tx_id FROM recurring_tx WHERE series_id = ? ON CONFLICT DO NOTHING",
                    [keep_id, sid],
                )
            except Exception:
                pass
            try:
                conn.execute("DELETE FROM recurring_tx WHERE series_id = ?", [sid])
            except Exception:
                pass
            try:
                conn.execute("DELETE FROM recurring_series WHERE id = ?", [sid])
                removed += 1
            except Exception:
                pass
    return removed


def merge_duplicate_merchants(conn) -> Dict[str, any]:
    """Merge recurring series that have the same AI-extracted merchant name and cadence.

    This handles cases like:
    - "google *fiber viewca" and "google *fiber" both becoming "Google Fiber"
    - Different description variations of the same merchant

    Returns:
        Dict with merge stats: {"merged": int, "details": [...]}
    """
    from .db import get_conn
    if conn is None:
        conn = get_conn()

    # Get all series with their AI-extracted names
    try:
        rows = conn.execute(
            """
            SELECT id, name, cadence, status, amount_mean, decided_at
            FROM recurring_series
            ORDER BY status DESC, decided_at DESC NULLS LAST
            """
        ).fetchall()
    except Exception as e:
        return {"merged": 0, "error": str(e)}

    # Group by (ai_merchant_name, cadence)
    groups: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        sid, name, cadence, status, amount_mean, decided_at = row
        ai_name = extract_merchant_name_ai(name or "")
        # Create group key from AI name + cadence
        group_key = f"{ai_name.lower()}|{cadence or 'monthly'}"
        groups[group_key].append({
            "id": sid,
            "name": name,
            "ai_name": ai_name,
            "cadence": cadence,
            "status": status,
            "amount_mean": amount_mean,
            "decided_at": decided_at,
        })

    # Get transaction counts for each series
    try:
        counts = {
            sid: int(cnt or 0)
            for sid, cnt in conn.execute(
                "SELECT series_id, COUNT(*) FROM recurring_tx GROUP BY series_id"
            ).fetchall()
        }
    except Exception:
        counts = {}

    def status_rank(s: str | None) -> int:
        if s == "confirmed":
            return 3
        if s == "pending":
            return 2
        if s == "rejected":
            return 1
        return 0

    merged_count = 0
    details = []

    for group_key, group in groups.items():
        if len(group) <= 1:
            continue

        # Sort to find the "best" series to keep
        # Priority: confirmed > pending > rejected, then most transactions, then newest
        group_sorted = sorted(
            group,
            key=lambda x: (
                status_rank(x["status"]),
                counts.get(x["id"], 0),
                x["decided_at"] is not None,
                x["decided_at"] or datetime.min.replace(tzinfo=UTC),
            ),
            reverse=True,
        )

        keep = group_sorted[0]
        keep_id = keep["id"]
        to_merge = group_sorted[1:]

        for item in to_merge:
            merge_id = item["id"]
            try:
                # Move all transactions to the kept series
                conn.execute(
                    """
                    INSERT INTO recurring_tx (series_id, tx_id)
                    SELECT ?, tx_id FROM recurring_tx WHERE series_id = ?
                    ON CONFLICT DO NOTHING
                    """,
                    [keep_id, merge_id],
                )
                # Delete old transaction links
                conn.execute("DELETE FROM recurring_tx WHERE series_id = ?", [merge_id])
                # Delete the duplicate series
                conn.execute("DELETE FROM recurring_series WHERE id = ?", [merge_id])
                merged_count += 1
                details.append({
                    "merged": item["name"],
                    "into": keep["name"],
                    "ai_name": keep["ai_name"],
                })
            except Exception as e:
                details.append({
                    "error": str(e),
                    "series": item["name"],
                })

        # Update the kept series with the best display name and recalculated stats
        if to_merge:
            try:
                # Recalculate occurrences and amount stats
                stats = conn.execute(
                    """
                    SELECT COUNT(*), AVG(t.amount), MIN(t.amount), MAX(t.amount),
                           MIN(t.posted_at), MAX(t.posted_at)
                    FROM recurring_tx r
                    JOIN transaction t ON t.id = r.tx_id
                    WHERE r.series_id = ?
                    """,
                    [keep_id],
                ).fetchone()
                if stats and stats[0]:
                    occ, avg_amt, min_amt, max_amt, first_date, last_date = stats
                    # Calculate amount SD
                    amounts = conn.execute(
                        """
                        SELECT t.amount FROM recurring_tx r
                        JOIN transaction t ON t.id = r.tx_id
                        WHERE r.series_id = ?
                        """,
                        [keep_id],
                    ).fetchall()
                    if amounts and len(amounts) > 1:
                        amt_list = [a[0] for a in amounts]
                        amt_sd = statistics.stdev(amt_list)
                    else:
                        amt_sd = 0

                    conn.execute(
                        """
                        UPDATE recurring_series
                        SET occurrences = ?,
                            amount_mean = ?,
                            amount_sd = ?,
                            first_date = ?,
                            last_date = ?,
                            display_name = ?
                        WHERE id = ?
                        """,
                        [occ, avg_amt, amt_sd, first_date, last_date, keep["ai_name"], keep_id],
                    )
            except Exception:
                pass

    return {"merged": merged_count, "details": details}


def suggest_recurring(
    min_occurrences: int = 3,
    tol: float = 0.10,
    limit: int = 1000,
    allow_short_cadence: bool = False,
) -> Dict[str, int]:
    """Scan database for recurring candidates and insert pending series and membership links.

    Args:
        min_occurrences: Minimum transactions to form a pattern
        tol: Amount tolerance for bucketing
        limit: Max transactions to scan
        allow_short_cadence: If True, also detect weekly/biweekly patterns

    Excludes confirmed transfer transactions from consideration.
    """
    from .db import get_conn

    conn = get_conn()
    # Ensure schema extensions exist, and proactively clean duplicates once per run.
    _ensure_recurring_series_columns(conn)
    _backfill_recurring_series_keys(conn)
    dedupe_recurring_series(conn)

    # Build query - if allowing short cadence, don't filter by category
    if allow_short_cadence:
        # More permissive query for short cadence detection
        rows = conn.execute(
            """
            SELECT t.id, t.account_id, t.posted_at, t.amount, t.description_norm
            FROM transaction t
            LEFT JOIN match_transfer mt
              ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id)
            WHERE mt.left_tx_id IS NULL AND mt.right_tx_id IS NULL
              AND t.p2p_provider IS NULL
              AND NOT regexp_matches(lower(t.description_norm), '(online banking transfer|automatic transfer)')
            LIMIT ?
            """,
            [limit],
        ).fetchall()
    else:
        # Standard query - focus on bills/subscriptions
        rows = conn.execute(
            """
            SELECT t.id, t.account_id, t.posted_at, t.amount, t.description_norm
            FROM transaction t
            LEFT JOIN match_transfer mt
              ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id)
            LEFT JOIN transaction_category tc ON tc.tx_id = t.id
            LEFT JOIN category c ON c.id = tc.category_id
            WHERE mt.left_tx_id IS NULL AND mt.right_tx_id IS NULL
              AND t.p2p_provider IS NULL
              -- Exclude common non-subscription transfer patterns
              AND NOT regexp_matches(lower(t.description_norm), '(online banking transfer|automatic transfer)')
              AND NOT regexp_matches(lower(COALESCE(c.name, '')), '(transfer|zelle|venmo|cash app|western union)')
              -- Focus on likely bills/subscriptions/utilities
              AND (
                regexp_matches(lower(COALESCE(c.name, '')), '(bill|utilit|insurance|mortgage|rent|subscription|financial|phone|internet)')
                OR regexp_matches(lower(t.description_norm), '(subscription|recurring|autopay|auto pay|mortgage|insurance|premium|membership|duke|energy|electric|water|spectrum|fiber|internet|netflix|spotify|hulu|apple\\.com/bill|google\\s*\\*)')
              )
            LIMIT ?
            """,
            [limit],
        ).fetchall()

    txs = [Tx(*r) for r in rows]
    cands = detect_recurring_candidates(
        txs,
        min_occurrences=min_occurrences,
        tol=tol,
        allow_short_cadence=allow_short_cadence,
    )

    created = 0
    skipped = 0
    for c in cands:
        series_key = compute_series_key(c["desc"], c["cadence"], c["amount_mean"])
        display_name = infer_display_name(c["desc"]) or c["desc"]

        row = conn.execute(
            "SELECT id FROM recurring_series WHERE series_key = ? LIMIT 1",
            [series_key],
        ).fetchone()
        sid = row[0] if row else None

        if not sid:
            sid = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO recurring_series (id, name, display_name, cadence, anchor_day, amount_mean, amount_sd, status, decided_at, series_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [sid, c["desc"], display_name, c["cadence"], c["anchor_day"], c["amount_mean"], c["amount_sd"], "pending", None, series_key],
            )
            created += 1
        else:
            # Ensure new columns are populated for older rows.
            conn.execute(
                "UPDATE recurring_series SET display_name = COALESCE(display_name, ?), series_key = COALESCE(series_key, ?) WHERE id = ?",
                [display_name, series_key, sid],
            )
            skipped += 1

        for tx_id in c["tx_ids"]:
            conn.execute(
                "INSERT INTO recurring_tx (series_id, tx_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
                [sid, tx_id],
            )

        # Update extra fields including predictions
        last_date = c.get("last_date")
        if not last_date:
            row = conn.execute(
                "SELECT MAX(t.posted_at) FROM transaction t JOIN recurring_tx r ON r.tx_id = t.id WHERE r.series_id = ?",
                [sid]
            ).fetchone()
            last_date = row[0] if row else None

        # Calculate next date using anchor_day for accurate prediction
        anchor_day = c.get("anchor_day")
        next_d = _next_date(last_date, c["cadence"], anchor_day) if last_date else None

        # Get prediction values from candidate
        confidence = c.get("confidence", 0.5)
        next_predicted_amount = c.get("next_predicted_amount", c["amount_mean"])

        # Classify recurring type using enhanced detector
        type_info = classify_recurring_type(c["desc"], c["amount_mean"])
        recurring_type = type_info["recurring_type"]
        sub_category = type_info["sub_category"]
        is_essential = type_info["is_essential"]
        lender_name = type_info.get("clean_name")

        # Calculate annual cost
        annual_cost = RecurringTypeClassifier.calculate_annual_cost(c["amount_mean"], c["cadence"])

        # For loans, estimate remaining term
        # Note: New classifier returns "loan_payments" (Plaid-style)
        estimated_remaining = None
        predicted_end_date = None
        if recurring_type in ("loan", "loan_payments"):
            loan_term = RecurringTypeClassifier.estimate_loan_term(c["amount_mean"], sub_category)
            estimated_remaining = loan_term.get("estimated_remaining")
            # Convert ISO string to date object for DuckDB
            pred_end_str = loan_term.get("predicted_end_date")
            if pred_end_str:
                try:
                    predicted_end_date = date.fromisoformat(pred_end_str)
                except (ValueError, TypeError):
                    predicted_end_date = None

        # Update all fields in one query
        # Note: Always overwrite recurring_type, sub_category, is_essential to ensure
        # the latest classifier patterns are applied (v2 Plaid-style categories)
        conn.execute(
            """
            UPDATE recurring_series SET
                price_hike = ?,
                last_date = COALESCE(?, last_date),
                next_date = COALESCE(?, next_date),
                prediction_confidence = ?,
                next_predicted_amount = ?,
                recurring_type = ?,
                sub_category = ?,
                is_essential = ?,
                annual_cost = ?,
                lender_name = COALESCE(lender_name, ?),
                estimated_remaining = COALESCE(estimated_remaining, ?),
                predicted_end_date = COALESCE(predicted_end_date, ?)
            WHERE id = ?
            """,
            [
                bool(c.get("price_hike")),
                last_date,
                next_d,
                confidence,
                next_predicted_amount,
                recurring_type,
                sub_category,
                is_essential,
                annual_cost,
                lender_name,
                estimated_remaining,
                predicted_end_date,
                sid,
            ],
        )
    return {"created": created, "skipped": skipped}


def list_recurring(status: str = "pending") -> List[Dict]:
    from .db import get_conn

    conn = get_conn()
    _ensure_recurring_series_columns(conn)
    _backfill_recurring_series_keys(conn)
    where = {
        "pending": "rs.status = 'pending'",
        "confirmed": "rs.status = 'confirmed'",
        "rejected": "rs.status = 'rejected'",
        "all": "1=1",
    }.get(status, "rs.status = 'pending'")
    # Hide non-subscription transfer-like series from the recurring UI by default.
    # These can be generated from internal transfer descriptors and are usually noise.
    exclude_noise = "NOT (rs.status = 'pending' AND regexp_matches(lower(rs.name), '(online banking transfer|automatic transfer)'))"
    # Also hide obvious day-to-day spending patterns from the pending list (restaurants/groceries/etc.).
    # Users want subscriptions & bills here, not frequent discretionary merchants.
    exclude_discretionary = """
      NOT (
        rs.status = 'pending'
        AND regexp_matches(
          lower(
            COALESCE(
              (
                SELECT c.name
                FROM recurring_tx r2
                JOIN transaction_category tc2 ON tc2.tx_id = r2.tx_id
                JOIN category c ON c.id = tc2.category_id
                WHERE r2.series_id = rs.id
                GROUP BY c.name
                ORDER BY COUNT(*) DESC
                LIMIT 1
              ),
              ''
            )
          ),
          '(restaurant|grocer|gas|automotive|travel)'
        )
      )
    """
    exclude_short_cadence = "NOT (rs.status = 'pending' AND rs.cadence IN ('weekly','biweekly'))"
    rows = conn.execute(
        f"""
        SELECT
               rs.id, rs.name, rs.display_name, rs.cadence, rs.anchor_day,
               rs.amount_mean, rs.amount_sd, rs.status, rs.decided_at,
               rs.last_date, rs.next_date,
               rs.price_hike, rs.prediction_confidence, rs.next_predicted_amount,
               rs.recurring_type, rs.sub_category, rs.is_essential,
               rs.annual_cost, rs.lender_name, rs.estimated_remaining, rs.predicted_end_date,
               COUNT(rtx.tx_id) AS occurrences,
               (
                 SELECT c.id
                 FROM recurring_tx r2
                 JOIN transaction_category tc2 ON tc2.tx_id = r2.tx_id
                 JOIN category c ON c.id = tc2.category_id
                 WHERE r2.series_id = rs.id
                 GROUP BY c.id
                 ORDER BY COUNT(*) DESC
                 LIMIT 1
               ) AS category_id,
               (
                 SELECT c.name
                 FROM recurring_tx r2
                 JOIN transaction_category tc2 ON tc2.tx_id = r2.tx_id
                 JOIN category c ON c.id = tc2.category_id
                 WHERE r2.series_id = rs.id
                 GROUP BY c.name
                 ORDER BY COUNT(*) DESC
                 LIMIT 1
               ) AS category_name
        FROM recurring_series rs
        LEFT JOIN recurring_tx rtx ON rtx.series_id = rs.id
        WHERE {where} AND {exclude_noise} AND {exclude_discretionary} AND {exclude_short_cadence}
        GROUP BY rs.id, rs.name, rs.display_name, rs.cadence, rs.anchor_day, rs.amount_mean, rs.amount_sd, rs.status, rs.decided_at, rs.last_date, rs.next_date, rs.price_hike, rs.prediction_confidence, rs.next_predicted_amount, rs.recurring_type, rs.sub_category, rs.is_essential, rs.annual_cost, rs.lender_name, rs.estimated_remaining, rs.predicted_end_date
        ORDER BY COALESCE(rs.decided_at, TIMESTAMP '1970-01-01') DESC
        """
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


def confirm_series(series_id: str) -> Dict[str, str]:
    from .db import get_conn

    conn = get_conn()
    now = datetime.now(UTC)
    conn.execute(
        "UPDATE recurring_series SET status = 'confirmed', decided_at = ? WHERE id = ?",
        [now, series_id],
    )
    # Use ON CONFLICT to handle edge cases (e.g., rapid double-clicks)
    try:
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
            [str(uuid.uuid4()), "recurring_series", series_id, "confirm", json.dumps({}), now, "user"],
        )
    except Exception:
        pass  # Event logging is non-critical
    return {"id": series_id, "status": "confirmed"}


def reject_series(series_id: str) -> Dict[str, str]:
    from .db import get_conn

    conn = get_conn()
    now = datetime.now(UTC)
    conn.execute(
        "UPDATE recurring_series SET status = 'rejected', decided_at = COALESCE(decided_at, ?) WHERE id = ?",
        [now, series_id],
    )
    # Use ON CONFLICT to handle edge cases (e.g., rapid double-clicks)
    try:
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
            [str(uuid.uuid4()), "recurring_series", series_id, "reject", json.dumps({}), now, "user"],
        )
    except Exception:
        pass  # Event logging is non-critical
    return {"id": series_id, "status": "rejected"}
