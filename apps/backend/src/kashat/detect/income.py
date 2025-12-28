from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from typing import Iterable, List, Dict


# Enhanced income pattern recognition
PAYROLL_RE = re.compile(r"\b(payroll|paycheck|direct\s+deposit|salary|wages|pay\s+stub|biweekly|weekly\s+pay)\b", re.I)
TRANSFER_INCOME_RE = re.compile(r"\b(transfer\s+from|payment\s+from|deposit\s+from|income\s+transfer)\b", re.I)
FREELANCE_RE = re.compile(r"\b(contractor|freelance|consulting|1099|invoice|payment\s+for)\b", re.I)

# Patterns to exclude from income (internal transfers)
INTERNAL_TRANSFER_RE = re.compile(r"\b(transfer\s+from\s+(sav|chk|savings|checking)\s+\d+|keep\s+the\s+change)\b", re.I)

# Business/employer patterns (likely income sources)
BUSINESS_TRANSFER_RE = re.compile(r"transfer\s+from\s+([a-z]{2,}(?:\s+\d+)?)\s+", re.I)


def mark_income(records: Iterable[Dict]) -> List[str]:
    """Return list of tx_ids identified as income.

    Heuristics: credit amounts, descriptor matches payroll keywords, and/or ~14 day cadence for same desc.
    """
    txs = list(records)
    by_desc: Dict[str, List[Dict]] = defaultdict(list)
    for t in txs:
        by_desc[t.get("description_norm", "")].append(t)
    income_ids: List[str] = []
    for desc, arr in by_desc.items():
        arr_sorted = sorted(arr, key=lambda x: x.get("posted_at"))
        
        # Check various income patterns
        is_payroll_desc = bool(PAYROLL_RE.search(desc))
        is_transfer_income = bool(TRANSFER_INCOME_RE.search(desc))
        is_freelance = bool(FREELANCE_RE.search(desc))
        
        # Check if it's an internal transfer (exclude from income)
        is_internal_transfer = bool(INTERNAL_TRANSFER_RE.search(desc))
        
        # Check if it's a business transfer (potential income)
        business_match = BUSINESS_TRANSFER_RE.search(desc)
        is_business_transfer = bool(business_match and not is_internal_transfer)
        
        credits = [t for t in arr_sorted if float(t.get("amount", 0)) > 0]
        
        # Mark as income if matches known patterns (but not internal transfers)
        if credits and not is_internal_transfer:
            if is_payroll_desc or is_freelance:
                income_ids.extend([t["id"] for t in credits])
                continue
            elif is_transfer_income or is_business_transfer:
                # For transfers, be more selective - only if looks like business/employer
                if business_match:
                    business_name = business_match.group(1)
                    # Exclude common account abbreviations
                    if business_name.lower() not in ['sav', 'chk', 'savings', 'checking']:
                        income_ids.extend([t["id"] for t in credits])
                        continue
        # cadence approx 14 days
        intervals = []
        for i in range(1, len(arr_sorted)):
            try:
                date1 = datetime.fromisoformat(arr_sorted[i-1]["posted_at"]).date()
                date2 = datetime.fromisoformat(arr_sorted[i]["posted_at"]).date()
                interval = abs((date2 - date1).days)
                intervals.append(interval)
            except (ValueError, TypeError):
                # Skip if date parsing fails
                continue
        if intervals and min(intervals) >= 13 and max(intervals) <= 15:
            income_ids.extend([t["id"] for t in credits])
    return income_ids

