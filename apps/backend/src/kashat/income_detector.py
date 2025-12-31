"""
Income Detection - Automatically detect income sources from transactions

DETECTS:
- Salary/paycheck (regular, large deposits)
- Side income (irregular but recurring)
- Investment income (dividends, interest)
- Transfer income (Zelle, Venmo received)
- Refunds (one-time credits)
"""

from __future__ import annotations

import re
import uuid
import statistics
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

from .db import get_conn


class IncomeType(Enum):
    SALARY = "salary"
    SIDE_INCOME = "side_income"
    INVESTMENT = "investment"
    TRANSFER = "transfer"
    REFUND = "refund"
    OTHER = "other"


class IncomeFrequency(Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"  # 1st and 15th
    MONTHLY = "monthly"
    IRREGULAR = "irregular"


@dataclass
class DetectedIncome:
    """A detected income source."""
    id: str
    name: str
    type: IncomeType
    avg_amount: float
    frequency: IncomeFrequency
    confidence: float
    pattern: str
    last_date: date
    occurrence_count: int
    transactions: List[str]  # Transaction IDs

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'avg_amount': self.avg_amount,
            'frequency': self.frequency.value,
            'confidence': self.confidence,
            'pattern': self.pattern,
            'last_date': self.last_date.isoformat() if isinstance(self.last_date, date) else self.last_date,
            'occurrence_count': self.occurrence_count,
            'transactions': self.transactions,
        }


# =============================================================================
# INCOME PATTERNS
# =============================================================================

INCOME_PATTERNS = {
    # Salary/Paycheck patterns
    r"(payroll|direct\s*dep|salary|paycheck|wages)": IncomeType.SALARY,
    r"(ach\s*credit.*employer|company\s*payroll)": IncomeType.SALARY,
    r"(adp|paychex|gusto|quickbooks\s*payroll)": IncomeType.SALARY,

    # Bank ACH credits (often payroll or business deposits)
    r"(bank\s*of\s*america|wells\s*fargo|chase|citi).*des:": IncomeType.SALARY,
    r"des:bank\s*of\s*am": IncomeType.SALARY,  # BoA specific ACH credit

    # Specific employers (common patterns)
    r"(bank\s*of\s*america|wells\s*fargo|chase).*payroll": IncomeType.SALARY,

    # Investment income
    r"(dividend|interest\s*payment|capital\s*gain)": IncomeType.INVESTMENT,
    r"(fidelity|vanguard|schwab|etrade).*(?:div|int|dist)": IncomeType.INVESTMENT,

    # Transfer income (receiving money) - NOTE: self-transfers filtered in _is_self_transfer()
    r"zelle\s*payment\s*from": IncomeType.TRANSFER,
    r"(zelle|venmo|paypal|cash\s*app).*(from|received|credit)": IncomeType.TRANSFER,
    r"(venmo|paypal)\s*(payment|transfer)\s*from": IncomeType.TRANSFER,
    r"cash\s*app.*received": IncomeType.TRANSFER,

    # Check deposits (not ATM cash - that's excluded)
    r"mobile\s*check\s*deposit": IncomeType.OTHER,

    # Refunds (excluded from budgetable income)
    r"(refund|rebate|cashback)": IncomeType.REFUND,
    r"(amazon|walmart|target).*refund": IncomeType.REFUND,
    r"preferred\s*rewards.*rebate": IncomeType.REFUND,
    r"credit\s*adj": IncomeType.REFUND,

    # Side income / Freelance
    r"(stripe|square|shopify)\s*(payout|transfer|deposit)": IncomeType.SIDE_INCOME,
    r"(upwork|fiverr|freelancer)\s*payment": IncomeType.SIDE_INCOME,
    r"(youtube|adsense|amazon\s*associates)": IncomeType.SIDE_INCOME,
    r"(royalt|commission)": IncomeType.SIDE_INCOME,

    # Government payments
    r"(irs\s*treas|tax\s*refund|social\s*security|soc\s*sec)": IncomeType.SALARY,
}

# Patterns that indicate NOT income (even if positive amount)
NOT_INCOME_PATTERNS = [
    r"transfer\s*from\s*(sav|savings|chk|checking)",  # Internal account transfers
    r"online\s*banking\s*transfer\s*from",  # Internal transfers
    r"keep\s*the\s*change",  # Savings round-up returns
    r"reversal",  # Bank reversals
    r"nsf\s*fee\s*refund",  # NSF refund
    r"overdraft.*refund",  # Overdraft refund
    r"correction",  # Account corrections
    r"acctverify",  # Bank account verification micro-deposits
    r"verification",  # Verification deposits
    r"(atm|mobile)\s*deposit",  # ATM/mobile check deposits (not income, just cash)
    r"bkofamerica\s*atm.*deposit",  # BoA ATM deposits
    r"geico.*auto",  # GEICO refunds (insurance adjustments)
    r"google.*nest",  # Google Nest refunds
    r"cashreward",  # Bank cashback rewards (debatable, but excluding)
    r"preferred\s*rewards",  # Bank rewards programs
]

# Amount-based classification thresholds
SALARY_MIN_AMOUNT = 500  # Minimum for salary detection
SALARY_TYPICAL_MIN = 1500  # Typical salary minimum
SIDE_INCOME_MIN = 50  # Minimum for side income
INVESTMENT_MIN = 1  # Dividends can be small


def detect_income_sources(
    lookback_days: int = 180,
    min_occurrences: int = 2,
    adaptive: bool = True
) -> List[DetectedIncome]:
    """
    Detect income sources from transaction history.

    Uses pattern matching and amount/frequency analysis.

    Args:
        lookback_days: Default days to look back
        min_occurrences: Minimum occurrences for detection
        adaptive: If True, uses all available data if default lookback yields nothing
    """
    conn = get_conn()

    cutoff_date = (date.today() - timedelta(days=lookback_days)).isoformat()

    # Get all positive transactions (income)
    transactions = conn.execute("""
        SELECT
            t.id,
            t.description_norm,
            t.amount,
            t.posted_at,
            t.account_id
        FROM [transaction] t
        WHERE t.amount > 0
          AND t.posted_at >= ?
          AND (t.is_adjustment IS NULL OR t.is_adjustment = 0)
        ORDER BY t.posted_at DESC
    """, [cutoff_date]).fetchall()

    # Adaptive: if no transactions in default lookback, get ALL positive transactions
    if not transactions and adaptive:
        transactions = conn.execute("""
            SELECT
                t.id,
                t.description_norm,
                t.amount,
                t.posted_at,
                t.account_id
            FROM [transaction] t
            WHERE t.amount > 0
              AND (t.is_adjustment IS NULL OR t.is_adjustment = 0)
            ORDER BY t.posted_at DESC
        """).fetchall()

    if not transactions:
        return []

    # Group transactions by normalized description pattern
    income_groups: Dict[str, List[Dict]] = defaultdict(list)

    for tx in transactions:
        tx_dict = {
            'id': tx[0],
            'description': tx[1],
            'amount': float(tx[2]),
            'date': tx[3],
            'account_id': tx[4]
        }

        # Normalize description for grouping
        norm_key = _normalize_for_grouping(tx_dict['description'])
        income_groups[norm_key].append(tx_dict)

    detected = []

    for pattern_key, txs in income_groups.items():
        if len(txs) < min_occurrences:
            continue

        # Analyze this income group
        income = _analyze_income_group(pattern_key, txs)
        if income and income.confidence >= 0.4:
            detected.append(income)

    # Sort by confidence and amount
    detected.sort(key=lambda x: (x.confidence, x.avg_amount), reverse=True)

    return detected


def _normalize_for_grouping(description: str) -> str:
    """Normalize description for grouping similar transactions."""
    if not description:
        return ""
    desc = description.lower().strip()

    # Remove common variable parts
    desc = re.sub(r'\d{4,}', 'XXXX', desc)  # Account/reference numbers
    desc = re.sub(r'\d{1,2}/\d{1,2}(/\d{2,4})?', 'DATE', desc)  # Dates
    desc = re.sub(r'\$[\d,]+\.?\d*', '$XXX', desc)  # Dollar amounts
    desc = re.sub(r'\s+', ' ', desc)  # Multiple spaces

    # Keep first 50 chars for grouping
    return desc[:50].strip()


def _analyze_income_group(pattern_key: str, transactions: List[Dict]) -> Optional[DetectedIncome]:
    """Analyze a group of similar transactions to detect income pattern."""

    amounts = [tx['amount'] for tx in transactions]
    dates = []
    for tx in transactions:
        if isinstance(tx['date'], str):
            try:
                dates.append(datetime.fromisoformat(tx['date'].replace('Z', '+00:00')).date())
            except:
                dates.append(datetime.strptime(tx['date'][:10], '%Y-%m-%d').date())
        else:
            dates.append(tx['date'])

    avg_amount = statistics.mean(amounts)
    amount_std = statistics.stdev(amounts) if len(amounts) > 1 else 0

    # Skip small amounts
    if avg_amount < SIDE_INCOME_MIN:
        return None

    # Detect income type from pattern
    income_type = _detect_income_type(pattern_key, avg_amount)

    # Skip refunds (they're income but not budgetable)
    if income_type == IncomeType.REFUND:
        return None

    # Calculate frequency
    frequency, freq_confidence = _calculate_frequency(dates)

    # Calculate overall confidence
    confidence = _calculate_confidence(
        income_type=income_type,
        avg_amount=avg_amount,
        amount_std=amount_std,
        occurrence_count=len(transactions),
        frequency=frequency,
        freq_confidence=freq_confidence
    )

    # Generate a clean name
    name = _generate_income_name(pattern_key, income_type, avg_amount)

    return DetectedIncome(
        id=str(uuid.uuid4()),
        name=name,
        type=income_type,
        avg_amount=round(avg_amount, 2),
        frequency=frequency,
        confidence=round(confidence, 2),
        pattern=pattern_key,
        last_date=max(dates),
        occurrence_count=len(transactions),
        transactions=[tx['id'] for tx in transactions]
    )


def _get_user_names() -> List[str]:
    """Get user's name variations from settings for self-transfer detection."""
    conn = get_conn()
    names = []

    # Try to get owner name from networth_settings
    try:
        row = conn.execute(
            "SELECT value FROM networth_settings WHERE key = 'owner_name'"
        ).fetchone()
        if row and row[0]:
            names.append(row[0].lower())
            parts = row[0].lower().split()
            names.extend(parts)
    except:
        pass

    # Fallback: Extract most common Zelle sender name that also appears as receiver
    # (If same person sends AND receives via Zelle, likely account owner)
    if not names:
        try:
            # Get Zelle senders
            zelle_senders = conn.execute("""
                SELECT description_norm FROM [transaction]
                WHERE description_norm LIKE '%zelle%from%'
                AND amount > 0
                LIMIT 20
            """).fetchall()

            # Extract sender names
            sender_counts = {}
            for row in zelle_senders:
                match = re.search(r"zelle\s*payment\s*from\s+(.+?)(?:\s*conf|$)", row[0].lower())
                if match:
                    sender = match.group(1).strip()
                    sender_counts[sender] = sender_counts.get(sender, 0) + 1

            # Most frequent sender is likely the owner
            if sender_counts:
                most_common = max(sender_counts, key=sender_counts.get)
                names.append(most_common)
                names.extend(re.findall(r'\b[a-z]+\b', most_common))
        except:
            pass

    return names


def _is_self_transfer(pattern: str) -> bool:
    """Check if this looks like a transfer from self (between own accounts)."""
    pattern_lower = pattern.lower()

    # Check for Zelle/Venmo from self patterns
    zelle_from_match = re.search(r"zelle\s*payment\s*from\s+(.+?)(?:\s*conf|$)", pattern_lower)
    if zelle_from_match:
        sender_name = zelle_from_match.group(1).strip()
        user_names = _get_user_names()

        # Check if sender matches any of user's names
        for name in user_names:
            if name in sender_name or sender_name in name:
                return True

        # Check for common self-transfer patterns (same first+last name)
        # e.g., "marwan s moftah" sending to "marwan moftah" account
        sender_parts = set(re.findall(r'\b[a-z]+\b', sender_name))
        if len(sender_parts) >= 2:
            # If we have user names and there's significant overlap, it's likely self
            for name in user_names:
                name_parts = set(re.findall(r'\b[a-z]+\b', name))
                if len(sender_parts & name_parts) >= 2:
                    return True

    return False


def _is_not_income(pattern: str) -> bool:
    """Check if pattern matches NOT_INCOME patterns (internal transfers, etc.)."""
    pattern_lower = pattern.lower()

    # First check explicit NOT_INCOME patterns
    for not_income_regex in NOT_INCOME_PATTERNS:
        if re.search(not_income_regex, pattern_lower, re.IGNORECASE):
            return True

    # Check for self-transfers (Zelle/Venmo from own name)
    if _is_self_transfer(pattern):
        return True

    return False


def _detect_income_type(pattern: str, avg_amount: float) -> IncomeType:
    """Detect income type from pattern and amount."""
    pattern_lower = pattern.lower()

    # First check if this is NOT income (internal transfers, etc.)
    if _is_not_income(pattern):
        return IncomeType.REFUND  # Treated same as refund - excluded

    # Check against known patterns
    for regex, income_type in INCOME_PATTERNS.items():
        if re.search(regex, pattern_lower, re.IGNORECASE):
            return income_type

    # Amount-based heuristics
    if avg_amount >= SALARY_TYPICAL_MIN:
        return IncomeType.SALARY
    elif avg_amount >= SALARY_MIN_AMOUNT:
        return IncomeType.SIDE_INCOME

    return IncomeType.OTHER


def _calculate_frequency(dates: List[date]) -> Tuple[IncomeFrequency, float]:
    """Calculate the frequency of income occurrences."""
    if len(dates) < 2:
        return IncomeFrequency.IRREGULAR, 0.3

    # Sort dates and calculate gaps
    sorted_dates = sorted(dates)
    gaps = [(sorted_dates[i+1] - sorted_dates[i]).days
            for i in range(len(sorted_dates) - 1)]

    if not gaps:
        return IncomeFrequency.IRREGULAR, 0.3

    avg_gap = statistics.mean(gaps)
    gap_std = statistics.stdev(gaps) if len(gaps) > 1 else avg_gap * 0.5

    # Coefficient of variation for regularity
    cv = gap_std / avg_gap if avg_gap > 0 else 1.0
    regularity = max(0, 1 - cv)  # Higher is more regular

    # Determine frequency based on average gap
    if 5 <= avg_gap <= 9:  # Weekly (7 days ± 2)
        return IncomeFrequency.WEEKLY, regularity
    elif 12 <= avg_gap <= 16:  # Biweekly (14 days ± 2)
        return IncomeFrequency.BIWEEKLY, regularity
    elif 13 <= avg_gap <= 17:  # Semimonthly (15 days ± 2)
        return IncomeFrequency.SEMIMONTHLY, regularity
    elif 26 <= avg_gap <= 35:  # Monthly (30 days ± 5)
        return IncomeFrequency.MONTHLY, regularity
    else:
        return IncomeFrequency.IRREGULAR, min(regularity, 0.5)


def _calculate_confidence(
    income_type: IncomeType,
    avg_amount: float,
    amount_std: float,
    occurrence_count: int,
    frequency: IncomeFrequency,
    freq_confidence: float
) -> float:
    """Calculate overall confidence score for income detection."""

    # Base confidence by type
    type_confidence = {
        IncomeType.SALARY: 0.8,
        IncomeType.SIDE_INCOME: 0.6,
        IncomeType.INVESTMENT: 0.7,
        IncomeType.TRANSFER: 0.5,
        IncomeType.OTHER: 0.4,
    }.get(income_type, 0.4)

    # Amount consistency (lower std = higher confidence)
    cv = amount_std / avg_amount if avg_amount > 0 else 1.0
    amount_consistency = max(0, 1 - cv)

    # Occurrence count factor (more occurrences = higher confidence)
    occurrence_factor = min(1.0, occurrence_count / 6)  # Max out at 6 occurrences

    # Regular frequency bonus
    frequency_bonus = 0.2 if frequency != IncomeFrequency.IRREGULAR else 0

    # Combine factors
    confidence = (
        type_confidence * 0.3 +
        amount_consistency * 0.2 +
        freq_confidence * 0.25 +
        occurrence_factor * 0.15 +
        frequency_bonus
    )

    return min(1.0, max(0.0, confidence))


def _generate_income_name(pattern: str, income_type: IncomeType, avg_amount: float) -> str:
    """Generate a human-readable name for the income source."""

    # Try to extract a meaningful name from the pattern
    pattern_lower = pattern.lower()

    # Known payroll providers
    payroll_providers = ['adp', 'paychex', 'gusto', 'quickbooks']
    for provider in payroll_providers:
        if provider in pattern_lower:
            return f"Payroll ({provider.title()})"

    # Generic names by type
    type_names = {
        IncomeType.SALARY: "Salary/Paycheck",
        IncomeType.SIDE_INCOME: "Side Income",
        IncomeType.INVESTMENT: "Investment Income",
        IncomeType.TRANSFER: "Transfer Received",
        IncomeType.OTHER: "Other Income",
    }

    base_name = type_names.get(income_type, "Income")

    # Try to add context from pattern
    if 'direct dep' in pattern_lower or 'payroll' in pattern_lower:
        return "Direct Deposit"
    if 'dividend' in pattern_lower:
        return "Dividends"
    if 'interest' in pattern_lower:
        return "Interest Income"
    if 'zelle' in pattern_lower:
        return "Zelle Received"
    if 'venmo' in pattern_lower:
        return "Venmo Received"

    return base_name


def get_total_monthly_income(include_irregular: bool = False) -> Dict:
    """
    Get the total monthly income from all detected sources.

    Returns:
        Dict with total, by_type breakdown, and sources list
    """
    conn = get_conn()

    # First check for saved income sources
    saved_sources = conn.execute("""
        SELECT id, name, type, avg_amount, frequency, confidence,
               user_confirmed, user_amount_override
        FROM income_source
        WHERE is_active = 1
    """).fetchall()

    if saved_sources:
        return _calculate_from_saved_sources(saved_sources, include_irregular)

    # Detect from transactions
    detected = detect_income_sources()
    if not detected:
        return {
            'total_monthly': 0,
            'by_type': {},
            'sources': [],
            'confidence': 0
        }

    return _calculate_from_detected(detected, include_irregular)


def _calculate_from_saved_sources(sources: List, include_irregular: bool) -> Dict:
    """Calculate monthly income from saved sources."""
    total = 0.0
    by_type = defaultdict(float)
    source_list = []

    for src in sources:
        amount = src[7] if src[7] is not None else src[3]  # user_override or avg_amount
        freq = src[4]

        if freq == 'irregular' and not include_irregular:
            continue

        monthly = _to_monthly_amount(amount, freq)
        total += monthly
        by_type[src[2]] += monthly

        source_list.append({
            'id': src[0],
            'name': src[1],
            'type': src[2],
            'amount': amount,
            'monthly_amount': monthly,
            'frequency': freq,
            'confidence': src[5],
            'user_confirmed': bool(src[6])
        })

    avg_confidence = sum(s['confidence'] for s in source_list) / len(source_list) if source_list else 0

    return {
        'total_monthly': round(total, 2),
        'by_type': dict(by_type),
        'sources': source_list,
        'confidence': round(avg_confidence, 2)
    }


def _calculate_from_detected(detected: List[DetectedIncome], include_irregular: bool) -> Dict:
    """Calculate monthly income from detected sources."""
    total = 0.0
    by_type = defaultdict(float)
    source_list = []

    for income in detected:
        if income.frequency == IncomeFrequency.IRREGULAR and not include_irregular:
            continue

        monthly = _to_monthly_amount(income.avg_amount, income.frequency.value)
        total += monthly
        by_type[income.type.value] += monthly

        source_list.append({
            'id': income.id,
            'name': income.name,
            'type': income.type.value,
            'amount': income.avg_amount,
            'monthly_amount': monthly,
            'frequency': income.frequency.value,
            'confidence': income.confidence,
            'user_confirmed': False
        })

    avg_confidence = sum(s['confidence'] for s in source_list) / len(source_list) if source_list else 0

    return {
        'total_monthly': round(total, 2),
        'by_type': dict(by_type),
        'sources': source_list,
        'confidence': round(avg_confidence, 2)
    }


def _to_monthly_amount(amount: float, frequency: str) -> float:
    """Convert an amount to monthly equivalent."""
    multipliers = {
        'weekly': 4.33,
        'biweekly': 2.17,
        'semimonthly': 2.0,
        'monthly': 1.0,
        'irregular': 1.0,  # Assume monthly for irregular
    }
    return amount * multipliers.get(frequency, 1.0)


def save_income_sources(sources: List[DetectedIncome]) -> int:
    """
    Save detected income sources to the database.

    Returns number of sources saved.
    """
    conn = get_conn()
    saved = 0

    for src in sources:
        try:
            conn.execute("""
                INSERT OR REPLACE INTO income_source (
                    id, name, type, avg_amount, frequency, confidence,
                    pattern_description, last_detected_at, occurrence_count,
                    is_active, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
            """, [
                src.id,
                src.name,
                src.type.value,
                src.avg_amount,
                src.frequency.value,
                src.confidence,
                src.pattern,
                src.last_date.isoformat() if isinstance(src.last_date, date) else src.last_date,
                src.occurrence_count
            ])
            saved += 1
        except Exception as e:
            print(f"Error saving income source: {e}")

    return saved


def update_income_source(
    source_id: str,
    user_confirmed: Optional[bool] = None,
    user_amount_override: Optional[float] = None,
    user_name_override: Optional[str] = None,
    is_active: Optional[bool] = None
) -> bool:
    """Update an income source with user overrides."""
    conn = get_conn()

    updates = []
    params = []

    if user_confirmed is not None:
        updates.append("user_confirmed = ?")
        params.append(user_confirmed)

    if user_amount_override is not None:
        updates.append("user_amount_override = ?")
        params.append(user_amount_override)

    if user_name_override is not None:
        updates.append("user_name_override = ?")
        params.append(user_name_override)

    if is_active is not None:
        updates.append("is_active = ?")
        params.append(is_active)

    if not updates:
        return False

    updates.append("updated_at = datetime('now')")
    params.append(source_id)

    try:
        conn.execute(f"""
            UPDATE income_source
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        return True
    except Exception as e:
        print(f"Error updating income source: {e}")
        return False


def get_saved_income_sources() -> List[Dict]:
    """Get all saved income sources from the database."""
    conn = get_conn()

    rows = conn.execute("""
        SELECT id, name, type, avg_amount, frequency, confidence,
               pattern_description, last_detected_at, occurrence_count,
               user_confirmed, user_amount_override, user_name_override,
               is_active, created_at, updated_at
        FROM income_source
        WHERE is_active = 1
        ORDER BY confidence DESC, avg_amount DESC
    """).fetchall()

    return [
        {
            'id': r[0],
            'name': r[11] or r[1],  # user_name_override or name
            'type': r[2],
            'avg_amount': r[10] or r[3],  # user_amount_override or avg_amount
            'original_amount': r[3],
            'frequency': r[4],
            'confidence': r[5],
            'pattern': r[6],
            'last_detected_at': r[7],
            'occurrence_count': r[8],
            'user_confirmed': bool(r[9]),
            'has_override': r[10] is not None or r[11] is not None,
            'is_active': bool(r[12]),
            'created_at': r[13],
            'updated_at': r[14]
        }
        for r in rows
    ]


# =============================================================================
# TRANSACTION INCOME MARKING
# =============================================================================

def mark_transaction_income(tx_id: str, is_income: bool = True) -> Dict:
    """
    Mark a transaction as income (or not income).

    Args:
        tx_id: Transaction ID
        is_income: True to mark as income, False to unmark

    Returns:
        Dict with success status and transaction details
    """
    conn = get_conn()

    # Get the transaction
    tx = conn.execute("""
        SELECT id, description_norm, amount, posted_at
        FROM [transaction]
        WHERE id = ?
    """, [tx_id]).fetchone()

    if not tx:
        return {'success': False, 'error': 'Transaction not found'}

    # Update the transaction
    conn.execute(
        "UPDATE [transaction] SET is_income = ? WHERE id = ?",
        [1 if is_income else 0, tx_id]
    )

    return {
        'success': True,
        'tx_id': tx_id,
        'is_income': is_income,
        'description': tx[1],
        'amount': tx[2]
    }


def backfill_income_transactions() -> Dict:
    """
    Scan all positive transactions and mark likely income.

    Uses pattern matching to identify income vs internal transfers/refunds.

    Returns:
        Dict with statistics about what was marked
    """
    conn = get_conn()

    # Get all positive transactions not yet reviewed
    txns = conn.execute("""
        SELECT id, description_norm, amount
        FROM [transaction]
        WHERE amount > 0
          AND (is_income IS NULL OR is_income = 0)
    """).fetchall()

    results = {
        'scanned': len(txns),
        'marked_income': 0,
        'marked_not_income': 0,
        'skipped': 0,
        'by_type': defaultdict(int),
        'examples': []
    }

    for tx in txns:
        tx_id, desc, amount = tx[0], tx[1] or '', tx[2]

        # Check if it's NOT income
        if _is_not_income(desc):
            results['marked_not_income'] += 1
            results['by_type']['internal_transfer'] += 1
            continue

        # Check income type
        income_type = _detect_income_type(desc, amount)

        if income_type == IncomeType.REFUND:
            results['marked_not_income'] += 1
            results['by_type']['refund'] += 1
            continue

        # Mark as income
        conn.execute(
            "UPDATE [transaction] SET is_income = 1 WHERE id = ?",
            [tx_id]
        )
        results['marked_income'] += 1
        results['by_type'][income_type.value] += 1

        # Store examples (first 5)
        if len(results['examples']) < 5:
            results['examples'].append({
                'id': tx_id,
                'description': desc[:60],
                'amount': amount,
                'type': income_type.value
            })

    results['by_type'] = dict(results['by_type'])
    return results


def reset_income_flags() -> Dict:
    """
    Reset all is_income flags and rerun detection.

    Returns:
        Dict with reset count and new detection results
    """
    conn = get_conn()

    # Count current income-flagged transactions
    old_count = conn.execute(
        "SELECT COUNT(*) FROM [transaction] WHERE is_income = 1"
    ).fetchone()[0]

    # Reset all income flags
    conn.execute("UPDATE [transaction] SET is_income = 0 WHERE is_income = 1")

    # Rerun backfill with improved logic
    results = backfill_income_transactions()

    return {
        'reset_count': old_count,
        'new_detection': results
    }


def detect_and_save_income() -> Dict:
    """
    Detect income sources and save them to the database.

    Returns:
        Dict with detection results and total monthly income
    """
    # Detect income sources
    sources = detect_income_sources(adaptive=True)

    if not sources:
        return {
            'detected': 0,
            'saved': 0,
            'sources': [],
            'total_monthly': 0
        }

    # Save to database
    saved = save_income_sources(sources)

    # Calculate totals
    total_monthly = sum(
        _to_monthly_amount(s.avg_amount, s.frequency.value)
        for s in sources
        if s.type != IncomeType.REFUND and s.frequency != IncomeFrequency.IRREGULAR
    )

    return {
        'detected': len(sources),
        'saved': saved,
        'sources': [s.to_dict() for s in sources],
        'total_monthly': round(total_monthly, 2)
    }
