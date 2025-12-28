"""Unified P2P payment detection service.

Detects and tracks P2P transactions (Venmo, Zelle, CashApp, PayPal, Wire, Western Union)
with counterparty intelligence, AI enrichment, and transaction type classification.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any

from .db import get_conn
from .detect.p2p import parse_p2p_descriptor

logger = logging.getLogger(__name__)


class TransactionType(str, Enum):
    """Type of P2P transaction."""
    P2P_TRANSFER = "p2p_transfer"      # True person-to-person transfer
    SUBSCRIPTION = "subscription"       # Recurring payment via P2P service
    PURCHASE = "purchase"               # One-time purchase via P2P service
    UNKNOWN = "unknown"


class CounterpartyType(str, Enum):
    """Type of counterparty."""
    PERSON = "person"
    BUSINESS = "business"
    UNKNOWN = "unknown"


# Known business/merchant patterns for quick classification
KNOWN_BUSINESSES = {
    # Streaming & Entertainment
    "netflix", "spotify", "amazon", "steam", "apple", "google", "microsoft",
    "hulu", "disney", "hbo", "youtube", "twitch", "patreon", "curiositystream",
    # Software & Tech Services
    "shopify", "godaddy", "github", "adobe", "dropbox", "slack", "zoom",
    "linkedin", "canva", "notion", "figma", "openai", "anthropic",
    # Ride & Delivery
    "uber", "lyft", "doordash", "grubhub", "instacart", "postmates",
    # Retail & E-commerce
    "walmart", "target", "ebay", "etsy", "bestbuy", "costco", "homedepot",
    # Gaming & Sim Racing
    "playstation", "xbox", "nintendo", "epicgames", "roblox", "blizzard",
    "apex racing", "iracing", "fanatec",
    # Finance & Insurance
    "venmo", "cashapp", "paypal", "stripe", "square",
    # Other common services
    "privateinternet", "nordvpn", "expressvpn", "musoramedia", "plex",
    "easynews", "fiverr", "geekhub",
}

# Patterns that indicate INTERNAL transfers (not P2P) - should be excluded
INTERNAL_TRANSFER_PATTERNS = [
    # Keep the Change / Round-up savings programs
    re.compile(r"keep\s+the\s+change\s+transfer", re.I),
    re.compile(r"round\s*up\s+transfer", re.I),
    re.compile(r"save\s+the\s+change", re.I),
    # Internal account transfers (to/from savings, checking, etc.)
    re.compile(r"online\s+banking\s+transfer\s+(?:to|from)\s+(?:sav|chk|savings|checking)\s*\d+", re.I),
    re.compile(r"transfer\s+(?:to|from)\s+(?:sav|chk|savings|checking)\s*\d+", re.I),
    re.compile(r"transfer\s+to\s+acct\s*\d+", re.I),
    re.compile(r"(?:internal|account)\s+transfer", re.I),
    re.compile(r"transfer\s+(?:to|from)\s+(?:x+)?\d{4}", re.I),  # transfer to xxxx1234
    # Bank overdraft protection, linked account transfers
    re.compile(r"overdraft\s+(?:protection|transfer)", re.I),
    re.compile(r"linked\s+account\s+transfer", re.I),
    # Mobile deposit / ATM
    re.compile(r"mobile\s+deposit", re.I),
    re.compile(r"atm\s+(?:deposit|withdrawal|transfer)", re.I),
]

# Fee patterns - these are bank fees, not P2P transactions
FEE_PATTERNS = [
    re.compile(r"wire\s+transfer\s+fee", re.I),
    re.compile(r"(?:incoming|outgoing)\s+wire\s+fee", re.I),
    re.compile(r"international\s+wire\s+fee", re.I),
    re.compile(r"remittance\s+fee", re.I),
    re.compile(r"(?:wu|western\s+union)\s*.*\s*fee", re.I),
    re.compile(r"service\s+fee", re.I),
    re.compile(r"transfer\s+fee", re.I),
    re.compile(r"(?:paypal|venmo|zelle|cashapp)\s+fee", re.I),
]

# Autopay/bill pay patterns - these are recurring bills, not P2P transfers
AUTOPAY_PATTERNS = [
    re.compile(r"\bautopay\b", re.I),
    re.compile(r"\bauto\s*pay\b", re.I),
    re.compile(r"\bciti\s+autopay\b", re.I),
    re.compile(r"\brocket\s+money\b", re.I),
    re.compile(r"\balbert\s+genius\b", re.I),
    re.compile(r"\bgoogle\s+store\s+des:payment\b", re.I),
    re.compile(r"\bedi\s+pymnts?\b", re.I),
    re.compile(r"\bbill\s*pay\b", re.I),
    re.compile(r"\bautomatic\s+payment\b", re.I),
    re.compile(r"\bscheduled\s+payment\b", re.I),
    re.compile(r"\brecurring\s+payment\b", re.I),
]


def is_fee_transaction(description: str) -> bool:
    """Check if a transaction is a fee (not a P2P transfer)."""
    for pattern in FEE_PATTERNS:
        if pattern.search(description):
            return True
    return False


def is_autopay_transaction(description: str) -> bool:
    """Check if a transaction is an autopay/bill pay (not a P2P transfer)."""
    for pattern in AUTOPAY_PATTERNS:
        if pattern.search(description):
            return True
    return False

# Patterns for counterparties that are actually account references, not people
INVALID_COUNTERPARTY_PATTERNS = [
    re.compile(r"^acct\s*\d+$", re.I),          # "ACCT 3454"
    re.compile(r"^sav\s*\d+$", re.I),           # "SAV 3454"
    re.compile(r"^chk\s*\d+$", re.I),           # "CHK 1234"
    re.compile(r"^(?:x+)?\d{4,}$", re.I),       # "3454" or "xxxx3454"
    re.compile(r"^unknown$", re.I),              # "UNKNOWN"
    re.compile(r"^confirmation#?\s*\d+$", re.I), # "CONFIRMATION# 123456"
    re.compile(r"^p[0-9a-f]{8,}$", re.I),       # "P3342F784C" (payment IDs)
    re.compile(r"^pxx+$", re.I),                 # "PXXXXXXXXX"
    re.compile(r"^ref\s*#?\d+$", re.I),          # "REF #123456"
    re.compile(r"^id\s*#?\d+$", re.I),           # "ID #123456"
]


def is_internal_transfer(description: str) -> bool:
    """Check if a transaction description indicates an internal transfer."""
    for pattern in INTERNAL_TRANSFER_PATTERNS:
        if pattern.search(description):
            return True
    return False


def is_invalid_counterparty(counterparty: str) -> bool:
    """Check if a counterparty name is actually an account reference."""
    if not counterparty:
        return True
    for pattern in INVALID_COUNTERPARTY_PATTERNS:
        if pattern.match(counterparty.strip()):
            return True
    return False


def find_similar_counterparty(normalized: str, conn) -> Optional[tuple]:
    """Find an existing counterparty that matches the given name using fuzzy logic.

    Returns (counterparty_id, name_normalized) if found, None otherwise.

    Matching strategies:
    1. Exact match
    2. Prefix match (if one is prefix of another, merge into longer name)
    3. First name match for person names (2-word names where first word matches)
    """
    if not normalized or len(normalized) < 2:
        return None

    # Strategy 1: Exact match
    exact = conn.execute(
        "SELECT id, name_normalized FROM counterparty WHERE name_normalized = ?",
        [normalized]
    ).fetchone()
    if exact:
        return (exact[0], exact[1])

    # Strategy 2: Prefix matching
    # If existing "MAI MEDHAT" and we're adding "MAI", merge into existing
    # If existing "MAI" and we're adding "MAI MEDHAT", update existing to longer name
    words = normalized.split()
    if len(words) >= 1:
        first_word = words[0]
        if len(first_word) >= 3:  # Only prefix match on names with 3+ chars
            # Find counterparties that start with the same first word
            prefix_matches = conn.execute(
                "SELECT id, name_normalized FROM counterparty WHERE name_normalized LIKE ? ORDER BY LENGTH(name_normalized) DESC",
                [f"{first_word}%"]
            ).fetchall()

            for match_id, match_name in prefix_matches:
                match_words = match_name.split()
                # Check if one is a prefix/truncation of the other
                if normalized.startswith(match_name) or match_name.startswith(normalized):
                    # Return the longer name as the canonical one
                    if len(match_name) >= len(normalized):
                        return (match_id, match_name)
                    else:
                        # We have a longer name - update the existing record
                        conn.execute(
                            "UPDATE counterparty SET name_normalized = ? WHERE id = ?",
                            [normalized, match_id]
                        )
                        return (match_id, normalized)

                # Also match if first name is same and both have 2+ words
                if len(words) >= 2 and len(match_words) >= 2 and words[0] == match_words[0]:
                    # Same first name, likely same person - use the one with more transactions
                    return (match_id, match_name)

    return None


@dataclass
class P2PResult:
    """Result of P2P detection."""
    service: str
    direction: str  # "to", "from", "unknown"
    counterparty_raw: Optional[str] = None
    counterparty_normalized: Optional[str] = None
    confidence: float = 1.0
    detection_method: str = "heuristic"
    # New enrichment fields
    transaction_type: TransactionType = TransactionType.UNKNOWN
    counterparty_type: CounterpartyType = CounterpartyType.UNKNOWN
    merchant_category: Optional[str] = None
    is_recurring: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CounterpartyInfo:
    """Information about a P2P counterparty."""
    id: str
    name_normalized: str
    aliases: List[str]
    total_sent: float
    total_received: float
    transaction_count: int
    first_seen: Optional[str]
    last_seen: Optional[str]
    is_recurring: bool = False
    counterparty_type: str = "unknown"


class P2PDetectionService:
    """Unified P2P payment detection service."""

    def __init__(self):
        self._ai_service = None

    def _get_ai_service(self):
        """Lazy load AI service to avoid circular imports."""
        if self._ai_service is None:
            try:
                from .ai import get_ai_service
                self._ai_service = get_ai_service()
            except Exception as e:
                logger.warning(f"AI service not available: {e}")
        return self._ai_service

    def detect_p2p_transaction(self, tx: Dict[str, Any]) -> Optional[P2PResult]:
        """Run P2P detection on a transaction.

        Args:
            tx: Transaction dict with 'description_norm' and optionally 'amount'

        Returns:
            P2PResult if detected, None otherwise
        """
        desc = tx.get("description_norm", "")
        amount = tx.get("amount")

        # FILTER 1: Skip internal transfers (keep the change, account-to-account, etc.)
        if is_internal_transfer(desc):
            logger.debug(f"Skipping internal transfer: {desc[:60]}")
            return None

        # FILTER 2: Skip fee transactions (wire fees, service fees, etc.)
        if is_fee_transaction(desc):
            logger.debug(f"Skipping fee transaction: {desc[:60]}")
            return None

        # FILTER 3: Skip autopay/bill pay transactions (utilities, subscriptions via ACH)
        if is_autopay_transaction(desc):
            logger.debug(f"Skipping autopay transaction: {desc[:60]}")
            return None

        result = parse_p2p_descriptor(desc, amount)
        if not result:
            return None

        counterparty_raw = result.get("counterparty")
        counterparty_normalized = self._normalize_counterparty(counterparty_raw) if counterparty_raw else None

        # FILTER 4: Skip invalid counterparties (account references like "ACCT 3454")
        if counterparty_normalized and is_invalid_counterparty(counterparty_normalized):
            logger.debug(f"Skipping invalid counterparty: {counterparty_normalized}")
            return None

        # Quick heuristic classification based on counterparty name
        tx_type, cp_type, category = self._quick_classify(counterparty_normalized, tx.get("description_norm", ""))

        # FILTER 5: Skip PayPal business purchases/subscriptions - those belong in recurring, not P2P
        # Only keep PayPal if it's a true person-to-person transfer
        service = result.get("provider", "unknown")
        if service == "paypal" and cp_type == CounterpartyType.BUSINESS:
            logger.debug(f"Skipping PayPal business transaction: {counterparty_normalized}")
            return None

        return P2PResult(
            service=result.get("provider", "unknown"),
            direction=result.get("direction", "unknown"),
            counterparty_raw=counterparty_raw,
            counterparty_normalized=counterparty_normalized,
            confidence=1.0,
            detection_method="heuristic",
            transaction_type=tx_type,
            counterparty_type=cp_type,
            merchant_category=category,
        )

    def _quick_classify(
        self, counterparty: Optional[str], description: str
    ) -> tuple[TransactionType, CounterpartyType, Optional[str]]:
        """Quick heuristic classification based on known patterns.

        Returns:
            Tuple of (transaction_type, counterparty_type, merchant_category)
        """
        if not counterparty:
            # No counterparty - likely a purchase or unknown
            desc_lower = description.lower()
            for biz in KNOWN_BUSINESSES:
                if biz in desc_lower:
                    return TransactionType.PURCHASE, CounterpartyType.BUSINESS, None
            return TransactionType.UNKNOWN, CounterpartyType.UNKNOWN, None

        cp_lower = counterparty.lower()

        # Check if counterparty is a known business
        for biz in KNOWN_BUSINESSES:
            if biz in cp_lower:
                # Could be subscription or purchase - check description for clues
                desc_lower = description.lower()
                if any(kw in desc_lower for kw in ["subscription", "monthly", "recurring", "membership"]):
                    return TransactionType.SUBSCRIPTION, CounterpartyType.BUSINESS, None
                return TransactionType.PURCHASE, CounterpartyType.BUSINESS, None

        # Check for business indicators in the name
        business_indicators = ["inc", "llc", "corp", "ltd", "co", "company", "store", "shop", "games", "media", "software", "tech"]
        if any(ind in cp_lower.split() for ind in business_indicators):
            return TransactionType.PURCHASE, CounterpartyType.BUSINESS, None

        # All caps single word is likely a business (e.g., "GODADDYCOM", "MUSORAMEDIA")
        if len(counterparty.split()) == 1 and counterparty.isupper() and len(counterparty) > 6:
            return TransactionType.PURCHASE, CounterpartyType.BUSINESS, None

        # Check for person name patterns (2-3 word names with common name patterns)
        words = cp_lower.split()
        if len(words) >= 2 and len(words) <= 3 and all(w.isalpha() and len(w) >= 2 for w in words):
            # Likely a person's name
            return TransactionType.P2P_TRANSFER, CounterpartyType.PERSON, None

        # Single word that looks like a first name (3-10 chars, alpha)
        if len(words) == 1 and words[0].isalpha() and 3 <= len(words[0]) <= 10:
            return TransactionType.P2P_TRANSFER, CounterpartyType.PERSON, None

        # Default to unknown
        return TransactionType.UNKNOWN, CounterpartyType.UNKNOWN, None

    def _normalize_counterparty(self, name: str) -> str:
        """Normalize counterparty name for matching.

        - Uppercase
        - Remove punctuation except spaces
        - Collapse multiple spaces
        - Remove common titles
        """
        if not name:
            return ""

        s = name.upper()
        # Remove common titles
        s = re.sub(r"\b(MR|MRS|MS|DR|JR|SR|III|II|IV)\b\.?", "", s)
        # Remove punctuation except spaces
        s = re.sub(r"[^A-Z0-9\s]", "", s)
        # Collapse multiple spaces
        s = re.sub(r"\s+", " ", s).strip()
        return s

    async def analyze_with_ai(self, tx: Dict[str, Any]) -> Optional[P2PResult]:
        """Use AI to detect P2P when heuristics fail but transaction looks like it might be P2P.

        Args:
            tx: Transaction dict with 'description_norm' and 'amount'

        Returns:
            P2PResult if AI detects P2P, None otherwise
        """
        ai_service = self._get_ai_service()
        if not ai_service:
            return None

        desc = tx.get("description_norm", "")
        amount = abs(tx.get("amount", 0))

        # FILTER: Skip internal transfers, fees, and autopay even for AI detection
        if is_internal_transfer(desc):
            logger.debug(f"AI skip internal transfer: {desc[:60]}")
            return None

        if is_fee_transaction(desc):
            logger.debug(f"AI skip fee transaction: {desc[:60]}")
            return None

        if is_autopay_transaction(desc):
            logger.debug(f"AI skip autopay transaction: {desc[:60]}")
            return None

        # Quick check: might this be P2P?
        might_be_p2p = (
            amount in [5, 10, 15, 20, 25, 50, 100, 150, 200, 250, 500] or
            "payment" in desc.lower() or
            "transfer" in desc.lower() or
            "send" in desc.lower() or
            "received" in desc.lower() or
            "p2p" in desc.lower()
        )

        if not might_be_p2p:
            return None

        prompt = f"""Analyze this bank transaction for P2P payment patterns:

Description: {desc}
Amount: ${amount}

Is this a P2P payment (Venmo, Zelle, CashApp, PayPal, wire transfer, Western Union)?
If yes, extract:
- Service name (venmo, zelle, cashapp, paypal, wire, western_union, or "unknown" if unclear)
- Counterparty name (person or business receiving/sending money)
- Direction: "to" if money was sent, "from" if money was received

Respond ONLY with a JSON object:
{{"is_p2p": true/false, "service": "...", "counterparty": "...", "direction": "to/from/unknown", "confidence": 0.0-1.0}}
"""

        try:
            result = await ai_service.analyze_with_prompt(prompt, max_tokens=200, task_type="p2p_detection")
            # Parse JSON from response
            json_match = re.search(r'\{[^}]+\}', result)
            if not json_match:
                return None

            data = json.loads(json_match.group())
            if not data.get("is_p2p"):
                return None

            counterparty_raw = data.get("counterparty")
            counterparty_normalized = self._normalize_counterparty(counterparty_raw) if counterparty_raw else None

            # FILTER: Validate AI-detected counterparty isn't an account reference
            if counterparty_normalized and is_invalid_counterparty(counterparty_normalized):
                logger.debug(f"AI detected invalid counterparty: {counterparty_normalized}")
                return None

            return P2PResult(
                service=data.get("service", "unknown"),
                direction=data.get("direction", "unknown"),
                counterparty_raw=counterparty_raw,
                counterparty_normalized=counterparty_normalized,
                confidence=data.get("confidence", 0.7),
                detection_method="ai",
            )
        except Exception as e:
            logger.error(f"AI P2P detection failed: {e}")
            return None

    def save_p2p_transaction(self, tx_id: str, result: P2PResult) -> str:
        """Save a P2P detection result to the database.

        Args:
            tx_id: Transaction ID
            result: P2PResult from detection

        Returns:
            ID of the created p2p_transaction record
        """
        conn = get_conn()
        p2p_id = str(uuid.uuid4())

        conn.execute(
            """
            INSERT INTO p2p_transaction (id, tx_id, service, counterparty_raw, counterparty_normalized,
                                         direction, confidence, detection_method, metadata, created_at,
                                         transaction_type, counterparty_type, merchant_category, is_recurring)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                service = excluded.service,
                counterparty_raw = excluded.counterparty_raw,
                counterparty_normalized = excluded.counterparty_normalized,
                direction = excluded.direction,
                confidence = excluded.confidence,
                detection_method = excluded.detection_method,
                metadata = excluded.metadata,
                transaction_type = excluded.transaction_type,
                counterparty_type = excluded.counterparty_type,
                merchant_category = excluded.merchant_category,
                is_recurring = excluded.is_recurring
            """,
            [
                p2p_id,
                tx_id,
                result.service,
                result.counterparty_raw,
                result.counterparty_normalized,
                result.direction,
                result.confidence,
                result.detection_method,
                json.dumps(result.metadata) if result.metadata else None,
                datetime.now(timezone.utc).isoformat(),
                result.transaction_type.value if isinstance(result.transaction_type, TransactionType) else result.transaction_type,
                result.counterparty_type.value if isinstance(result.counterparty_type, CounterpartyType) else result.counterparty_type,
                result.merchant_category,
                1 if result.is_recurring else 0,
            ],
        )

        # Update counterparty if we have one
        if result.counterparty_normalized:
            self._update_counterparty(
                result.counterparty_normalized,
                result.counterparty_raw,
                result.direction,
                tx_id,
                result.counterparty_type,
            )

        return p2p_id

    def _update_counterparty(
        self,
        normalized: str,
        raw: Optional[str],
        direction: str,
        tx_id: str,
        counterparty_type: CounterpartyType = CounterpartyType.UNKNOWN,
    ) -> str:
        """Update or create counterparty record.

        Args:
            normalized: Normalized counterparty name
            raw: Raw counterparty name
            direction: Payment direction
            tx_id: Transaction ID for fetching amount
            counterparty_type: Type of counterparty (person, business, unknown)

        Returns:
            Counterparty ID
        """
        conn = get_conn()

        # Get transaction amount
        tx_row = conn.execute("SELECT amount, posted_at FROM [transaction] WHERE id = ?", [tx_id]).fetchone()
        amount = abs(tx_row[0]) if tx_row else 0
        posted_at = tx_row[1] if tx_row else datetime.now(timezone.utc).isoformat()

        cp_type_str = counterparty_type.value if isinstance(counterparty_type, CounterpartyType) else counterparty_type

        # Try to find existing counterparty using fuzzy matching
        similar = find_similar_counterparty(normalized, conn)
        if similar:
            counterparty_id, canonical_name = similar
            existing = conn.execute(
                "SELECT id, aliases, total_sent, total_received, transaction_count, first_seen, counterparty_type FROM counterparty WHERE id = ?",
                [counterparty_id]
            ).fetchone()
        else:
            existing = None

        if existing:
            counterparty_id = existing[0]
            aliases = json.loads(existing[1]) if existing[1] else []
            total_sent = existing[2] or 0
            total_received = existing[3] or 0
            tx_count = existing[4] or 0
            first_seen = existing[5]
            existing_type = existing[6]

            # Add alias if new
            if raw and raw not in aliases:
                aliases.append(raw)

            # Update amounts
            if direction == "to":
                total_sent += amount
            elif direction == "from":
                total_received += amount

            # Only update type if not already set
            new_type = existing_type if existing_type else cp_type_str

            conn.execute(
                """
                UPDATE counterparty SET
                    aliases = ?,
                    total_sent = ?,
                    total_received = ?,
                    transaction_count = ?,
                    last_seen = ?,
                    counterparty_type = ?
                WHERE id = ?
                """,
                [
                    json.dumps(aliases),
                    total_sent,
                    total_received,
                    tx_count + 1,
                    posted_at,
                    new_type,
                    counterparty_id,
                ],
            )
        else:
            counterparty_id = str(uuid.uuid4())
            aliases = [raw] if raw else []
            total_sent = amount if direction == "to" else 0
            total_received = amount if direction == "from" else 0

            conn.execute(
                """
                INSERT INTO counterparty (id, name_normalized, aliases, total_sent, total_received,
                                          transaction_count, first_seen, last_seen, counterparty_type)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                [
                    counterparty_id,
                    normalized,
                    json.dumps(aliases),
                    total_sent,
                    total_received,
                    posted_at,
                    posted_at,
                    cp_type_str,
                ],
            )

        return counterparty_id

    def get_p2p_transactions(
        self,
        service: Optional[str] = None,
        counterparty: Optional[str] = None,
        direction: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get P2P transactions with optional filters.

        Args:
            service: Filter by service (venmo, zelle, etc.)
            counterparty: Filter by counterparty name (partial match)
            direction: Filter by direction (to, from)
            limit: Max results
            offset: Pagination offset

        Returns:
            List of P2P transaction records with transaction details
        """
        conn = get_conn()

        where_clauses = []
        params = []

        if service:
            where_clauses.append("p.service = ?")
            params.append(service)

        if counterparty:
            where_clauses.append("(p.counterparty_normalized LIKE ? OR p.counterparty_raw LIKE ?)")
            params.append(f"%{counterparty.upper()}%")
            params.append(f"%{counterparty}%")

        if direction:
            where_clauses.append("p.direction = ?")
            params.append(direction)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            SELECT p.id, p.tx_id, p.service, p.counterparty_raw, p.counterparty_normalized,
                   p.direction, p.confidence, p.detection_method, p.created_at,
                   t.posted_at, t.amount, t.description_norm
            FROM p2p_transaction p
            JOIN [transaction] t ON t.id = p.tx_id
            WHERE {where_sql}
            ORDER BY t.posted_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()

        return [
            {
                "id": row[0],
                "tx_id": row[1],
                "service": row[2],
                "counterparty_raw": row[3],
                "counterparty_normalized": row[4],
                "direction": row[5],
                "confidence": row[6],
                "detection_method": row[7],
                "created_at": row[8],
                "posted_at": row[9],
                "amount": row[10],
                "description": row[11],
            }
            for row in rows
        ]

    def get_counterparties(
        self,
        recurring_only: bool = False,
        min_transactions: int = 1,
        limit: int = 50,
    ) -> List[CounterpartyInfo]:
        """Get counterparties with optional filters.

        Args:
            recurring_only: Only return counterparties marked as recurring
            min_transactions: Minimum transaction count
            limit: Max results

        Returns:
            List of CounterpartyInfo
        """
        conn = get_conn()

        where_clauses = ["transaction_count >= ?"]
        params = [min_transactions]

        if recurring_only:
            where_clauses.append("is_recurring = 1")

        where_sql = " AND ".join(where_clauses)

        rows = conn.execute(
            f"""
            SELECT id, name_normalized, aliases, total_sent, total_received,
                   transaction_count, first_seen, last_seen, is_recurring, counterparty_type
            FROM counterparty
            WHERE {where_sql}
            ORDER BY transaction_count DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()

        return [
            CounterpartyInfo(
                id=row[0],
                name_normalized=row[1],
                aliases=json.loads(row[2]) if row[2] else [],
                total_sent=row[3] or 0,
                total_received=row[4] or 0,
                transaction_count=row[5] or 0,
                first_seen=row[6],
                last_seen=row[7],
                is_recurring=bool(row[8]),
                counterparty_type=row[9] or "unknown",
            )
            for row in rows
        ]

    def get_counterparty_transactions(self, counterparty_id: str) -> List[Dict[str, Any]]:
        """Get all transactions with a specific counterparty.

        Args:
            counterparty_id: Counterparty ID

        Returns:
            List of transaction records
        """
        conn = get_conn()

        # Get counterparty name
        cp = conn.execute("SELECT name_normalized FROM counterparty WHERE id = ?", [counterparty_id]).fetchone()
        if not cp:
            return []

        return self.get_p2p_transactions(counterparty=cp[0], limit=1000)

    def get_stats(self) -> Dict[str, Any]:
        """Get P2P detection statistics.

        Returns:
            Dictionary with statistics by service, direction, top counterparties
        """
        conn = get_conn()

        # Total P2P transactions
        total = conn.execute("SELECT COUNT(*) FROM p2p_transaction").fetchone()[0]

        # By service
        by_service_rows = conn.execute(
            """
            SELECT service, COUNT(*), SUM(ABS(t.amount))
            FROM p2p_transaction p
            JOIN [transaction] t ON t.id = p.tx_id
            GROUP BY service
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()

        by_service = {
            row[0]: {"count": row[1], "total_amount": row[2] or 0}
            for row in by_service_rows
        }

        # By direction
        by_direction_rows = conn.execute(
            """
            SELECT direction, COUNT(*), SUM(ABS(t.amount))
            FROM p2p_transaction p
            JOIN [transaction] t ON t.id = p.tx_id
            GROUP BY direction
            """
        ).fetchall()

        by_direction = {
            row[0]: {"count": row[1], "total_amount": row[2] or 0}
            for row in by_direction_rows
        }

        # Top counterparties
        top_counterparties = conn.execute(
            """
            SELECT name_normalized, transaction_count, total_sent, total_received
            FROM counterparty
            ORDER BY transaction_count DESC
            LIMIT 10
            """
        ).fetchall()

        return {
            "total_p2p_transactions": total,
            "by_service": by_service,
            "by_direction": by_direction,
            "top_counterparties": [
                {
                    "name": row[0],
                    "transaction_count": row[1],
                    "total_sent": row[2] or 0,
                    "total_received": row[3] or 0,
                }
                for row in top_counterparties
            ],
        }

    async def detect_all_transactions(
        self,
        use_ai: bool = False,
        limit: int = 10000,
        skip_existing: bool = True,
    ) -> Dict[str, Any]:
        """Run P2P detection on all transactions.

        Args:
            use_ai: Use AI for ambiguous transactions
            limit: Maximum transactions to process
            skip_existing: Skip transactions already in p2p_transaction

        Returns:
            Detection results summary
        """
        conn = get_conn()

        # Get transactions to process
        if skip_existing:
            query = """
                SELECT t.id, t.description_norm, t.amount
                FROM [transaction] t
                LEFT JOIN p2p_transaction p ON p.tx_id = t.id
                WHERE p.id IS NULL
                LIMIT ?
            """
        else:
            query = """
                SELECT id, description_norm, amount
                FROM [transaction]
                LIMIT ?
            """

        rows = conn.execute(query, [limit]).fetchall()

        detected = 0
        ai_detected = 0
        processed = 0

        for row in rows:
            tx_id, desc, amount = row[0], row[1], row[2]
            tx = {"description_norm": desc, "amount": amount}

            result = self.detect_p2p_transaction(tx)
            if result:
                self.save_p2p_transaction(tx_id, result)
                detected += 1
            elif use_ai:
                result = await self.analyze_with_ai(tx)
                if result:
                    self.save_p2p_transaction(tx_id, result)
                    ai_detected += 1

            processed += 1

        return {
            "processed": processed,
            "detected_heuristic": detected,
            "detected_ai": ai_detected,
            "total_detected": detected + ai_detected,
        }

    def merge_counterparties(self, source_id: str, target_id: str) -> bool:
        """Merge two counterparties (user-corrected matching).

        Args:
            source_id: Counterparty to merge from (will be deleted)
            target_id: Counterparty to merge into

        Returns:
            True if successful
        """
        conn = get_conn()

        # Get both counterparties
        source = conn.execute("SELECT * FROM counterparty WHERE id = ?", [source_id]).fetchone()
        target = conn.execute("SELECT * FROM counterparty WHERE id = ?", [target_id]).fetchone()

        if not source or not target:
            return False

        # Merge aliases
        source_aliases = json.loads(source[2]) if source[2] else []
        target_aliases = json.loads(target[2]) if target[2] else []
        merged_aliases = list(set(target_aliases + source_aliases + [source[1]]))  # Include source name as alias

        # Merge amounts
        total_sent = (target[3] or 0) + (source[3] or 0)
        total_received = (target[4] or 0) + (source[4] or 0)
        transaction_count = (target[5] or 0) + (source[5] or 0)

        # Update target
        conn.execute(
            """
            UPDATE counterparty SET
                aliases = ?,
                total_sent = ?,
                total_received = ?,
                transaction_count = ?
            WHERE id = ?
            """,
            [json.dumps(merged_aliases), total_sent, total_received, transaction_count, target_id],
        )

        # Update p2p_transactions to point to target
        conn.execute(
            "UPDATE p2p_transaction SET counterparty_normalized = ? WHERE counterparty_normalized = ?",
            [target[1], source[1]],
        )

        # Delete source
        conn.execute("DELETE FROM counterparty WHERE id = ?", [source_id])

        return True

    # ========================================================================
    # AI ENRICHMENT PIPELINE
    # ========================================================================

    async def enrich_with_ai(self, p2p_id: str) -> Dict[str, Any]:
        """Enrich a single P2P transaction with AI classification.

        Args:
            p2p_id: P2P transaction ID

        Returns:
            Enrichment result with transaction_type, counterparty_type, etc.
        """
        conn = get_conn()
        ai_service = self._get_ai_service()

        if not ai_service:
            return {"status": "error", "message": "AI service not available"}

        # Get P2P transaction with underlying transaction data
        row = conn.execute(
            """
            SELECT p.id, p.service, p.counterparty_raw, p.counterparty_normalized,
                   p.direction, p.transaction_type, t.description_norm, t.amount, t.posted_at
            FROM p2p_transaction p
            JOIN [transaction] t ON t.id = p.tx_id
            WHERE p.id = ?
            """,
            [p2p_id],
        ).fetchone()

        if not row:
            return {"status": "error", "message": "P2P transaction not found"}

        service = row[1]
        counterparty_raw = row[2]
        counterparty_normalized = row[3]
        direction = row[4]
        current_type = row[5]
        description = row[6]
        amount = row[7]

        prompt = f"""Analyze this bank transaction that was detected as a {service} payment:

Description: {description}
Amount: ${abs(amount)}
Direction: {"Sent" if direction == "to" else "Received" if direction == "from" else "Unknown"}
Counterparty: {counterparty_raw or "Unknown"}

Classify this transaction:

1. Transaction Type:
   - "p2p_transfer" = True person-to-person money transfer (e.g., paying a friend back, sending money to family)
   - "subscription" = Recurring payment for a service (e.g., Netflix via PayPal, monthly Spotify)
   - "purchase" = One-time purchase of goods/services (e.g., buying something on eBay via PayPal)

2. Counterparty Type:
   - "person" = The counterparty is an individual person
   - "business" = The counterparty is a business/merchant/company

3. Merchant Category (if business):
   - entertainment, utilities, shopping, food_delivery, transportation, software, gaming, health, education, other

4. Is this likely a recurring payment? (true/false)

Respond ONLY with a JSON object:
{{"transaction_type": "p2p_transfer|subscription|purchase", "counterparty_type": "person|business", "merchant_category": "...", "is_recurring": true|false, "confidence": 0.0-1.0, "reasoning": "..."}}
"""

        try:
            result = await ai_service.analyze_with_prompt(prompt, max_tokens=300, task_type="p2p_enrichment")

            # Parse JSON from response
            json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
            if not json_match:
                logger.warning(f"Could not parse AI response for P2P enrichment: {result[:200]}")
                return {"status": "error", "message": "Could not parse AI response"}

            data = json.loads(json_match.group())

            # Update the P2P transaction
            conn.execute(
                """
                UPDATE p2p_transaction SET
                    transaction_type = ?,
                    counterparty_type = ?,
                    merchant_category = ?,
                    is_recurring = ?,
                    ai_confidence = ?,
                    ai_enriched_at = ?
                WHERE id = ?
                """,
                [
                    data.get("transaction_type", "unknown"),
                    data.get("counterparty_type", "unknown"),
                    data.get("merchant_category"),
                    1 if data.get("is_recurring") else 0,
                    data.get("confidence", 0.8),
                    datetime.now(timezone.utc).isoformat(),
                    p2p_id,
                ],
            )

            # Also update counterparty type if we have one
            if counterparty_normalized and data.get("counterparty_type"):
                conn.execute(
                    "UPDATE counterparty SET counterparty_type = ? WHERE name_normalized = ?",
                    [data.get("counterparty_type"), counterparty_normalized],
                )

            # Note: Recurring series creation is handled by the regular recurring pipeline
            # P2P detection just identifies the counterparty and transaction type

            return {
                "status": "success",
                "p2p_id": p2p_id,
                "enrichment": data,
            }

        except Exception as e:
            logger.error(f"AI enrichment failed for {p2p_id}: {e}")
            return {"status": "error", "message": str(e)}

    async def enrich_all_p2p(
        self,
        service_filter: Optional[str] = None,
        only_unclassified: bool = True,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Enrich all P2P transactions with AI classification.

        Args:
            service_filter: Only enrich transactions from this service (e.g., "paypal")
            only_unclassified: Only enrich transactions without transaction_type
            limit: Maximum transactions to enrich

        Returns:
            Summary of enrichment results
        """
        conn = get_conn()

        where_clauses = []
        params = []

        if only_unclassified:
            where_clauses.append("(p.transaction_type IS NULL OR p.transaction_type = 'unknown')")

        if service_filter:
            where_clauses.append("p.service = ?")
            params.append(service_filter)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        rows = conn.execute(
            f"""
            SELECT p.id FROM p2p_transaction p
            WHERE {where_sql}
            ORDER BY p.created_at DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()

        enriched = 0
        errors = 0

        for row in rows:
            p2p_id = row[0]
            result = await self.enrich_with_ai(p2p_id)
            if result.get("status") == "success":
                enriched += 1
            else:
                errors += 1

        return {
            "processed": len(rows),
            "enriched": enriched,
            "errors": errors,
        }

    def get_enrichment_stats(self) -> Dict[str, Any]:
        """Get statistics on P2P enrichment status.

        Returns:
            Breakdown by transaction_type, counterparty_type, and enrichment status
        """
        conn = get_conn()

        # Total and enriched counts
        total = conn.execute("SELECT COUNT(*) FROM p2p_transaction").fetchone()[0]
        enriched = conn.execute(
            "SELECT COUNT(*) FROM p2p_transaction WHERE ai_enriched_at IS NOT NULL"
        ).fetchone()[0]
        classified = conn.execute(
            "SELECT COUNT(*) FROM p2p_transaction WHERE transaction_type IS NOT NULL AND transaction_type != 'unknown'"
        ).fetchone()[0]

        # By transaction type
        by_type = conn.execute(
            """
            SELECT COALESCE(transaction_type, 'unknown') as tx_type, COUNT(*), SUM(ABS(t.amount))
            FROM p2p_transaction p
            JOIN [transaction] t ON t.id = p.tx_id
            GROUP BY tx_type
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()

        # By counterparty type
        by_cp_type = conn.execute(
            """
            SELECT COALESCE(counterparty_type, 'unknown') as cp_type, COUNT(*)
            FROM p2p_transaction
            GROUP BY cp_type
            """
        ).fetchall()

        # By service and type
        by_service_and_type = conn.execute(
            """
            SELECT service, COALESCE(transaction_type, 'unknown') as tx_type, COUNT(*)
            FROM p2p_transaction
            GROUP BY service, tx_type
            ORDER BY service, COUNT(*) DESC
            """
        ).fetchall()

        return {
            "total": total,
            "enriched": enriched,
            "classified": classified,
            "unclassified": total - classified,
            "by_transaction_type": {
                row[0]: {"count": row[1], "total_amount": row[2] or 0}
                for row in by_type
            },
            "by_counterparty_type": {
                row[0]: row[1]
                for row in by_cp_type
            },
            "by_service_and_type": [
                {"service": row[0], "transaction_type": row[1], "count": row[2]}
                for row in by_service_and_type
            ],
        }

    def link_to_recurring(self, p2p_id: str, recurring_series_id: str) -> bool:
        """Link a P2P transaction to a recurring series.

        This allows coordination between P2P detection and recurring workflow.

        Args:
            p2p_id: P2P transaction ID
            recurring_series_id: Recurring series ID

        Returns:
            True if successful
        """
        conn = get_conn()
        try:
            conn.execute(
                """
                UPDATE p2p_transaction SET
                    recurring_series_id = ?,
                    is_recurring = 1
                WHERE id = ?
                """,
                [recurring_series_id, p2p_id],
            )
            return True
        except Exception as e:
            logger.error(f"Failed to link P2P to recurring: {e}")
            return False

    def get_unlinked_recurring_p2p(self) -> List[Dict[str, Any]]:
        """Get P2P transactions that appear recurring but aren't linked to a recurring series.

        This helps identify transactions that should be in the recurring workflow.

        Returns:
            List of potentially recurring P2P transactions
        """
        conn = get_conn()

        # Find counterparties with 3+ transactions that aren't linked to recurring
        rows = conn.execute(
            """
            SELECT p.counterparty_normalized, p.service, COUNT(*) as tx_count,
                   AVG(ABS(t.amount)) as avg_amount,
                   MIN(t.posted_at) as first_date,
                   MAX(t.posted_at) as last_date
            FROM p2p_transaction p
            JOIN [transaction] t ON t.id = p.tx_id
            WHERE p.recurring_series_id IS NULL
              AND p.counterparty_normalized IS NOT NULL
            GROUP BY p.counterparty_normalized, p.service
            HAVING tx_count >= 3
            ORDER BY tx_count DESC
            """
        ).fetchall()

        return [
            {
                "counterparty": row[0],
                "service": row[1],
                "transaction_count": row[2],
                "avg_amount": row[3],
                "first_date": row[4],
                "last_date": row[5],
            }
            for row in rows
        ]


# Singleton instance
_p2p_service: Optional[P2PDetectionService] = None


def get_p2p_service() -> P2PDetectionService:
    """Get the singleton P2P detection service."""
    global _p2p_service
    if _p2p_service is None:
        _p2p_service = P2PDetectionService()
    return _p2p_service


def run_p2p_detection(limit: int = 10000) -> Dict[str, Any]:
    """Run P2P detection on all unprocessed transactions.

    This is a synchronous wrapper for the async detect_all_transactions method.
    Detects all P2P platforms: Zelle, Venmo, CashApp, PayPal, Western Union, Wire.

    Args:
        limit: Maximum number of transactions to process

    Returns:
        Dict with 'detected' count and 'by_service' breakdown
    """
    import asyncio
    from .db import get_conn

    service = get_p2p_service()
    conn = get_conn()

    # Get transactions without P2P detection
    rows = conn.execute("""
        SELECT t.id, t.description_norm, t.amount, t.posted_at
        FROM [transaction] t
        LEFT JOIN p2p_transaction p ON p.tx_id = t.id
        WHERE p.id IS NULL
        LIMIT ?
    """, [limit]).fetchall()

    if not rows:
        return {"detected": 0, "by_service": {}}

    detected = 0
    by_service: Dict[str, int] = {}

    for row in rows:
        tx = {
            "id": row[0],
            "description": row[1] or "",
            "amount": float(row[2] or 0),
            "posted_at": row[3],
        }

        result = service.detect_p2p_transaction(tx)
        if result:
            detected += 1
            svc = result.service or "unknown"
            by_service[svc] = by_service.get(svc, 0) + 1

            # Insert into p2p_transaction table
            import uuid
            from datetime import datetime, UTC
            try:
                conn.execute("""
                    INSERT INTO p2p_transaction (id, tx_id, service, counterparty_raw, counterparty_normalized, direction, confidence, detection_method, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (tx_id) DO NOTHING
                """, [
                    str(uuid.uuid4()),
                    tx["id"],
                    result.service,
                    result.counterparty_raw,
                    result.counterparty_normalized,
                    result.direction,
                    result.confidence,
                    result.detection_method,
                    datetime.now(UTC).isoformat(),
                ])
            except Exception:
                pass

    return {"detected": detected, "by_service": by_service}
