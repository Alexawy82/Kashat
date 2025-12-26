"""
PDF Bank Statement Ingestion

Multi-layer parsing strategy:
1. Bank-specific parsers (boa_v2025, etc.) - Fast, accurate for known formats
2. AI Vision Parser - Flexible fallback for unknown formats (uses LMStudio/OpenAI)
3. SimpleBankV1 regex - Last resort text extraction

The AI parser provides additional enrichment:
- Merchant name normalization
- Category hints
- Higher accuracy for complex layouts
"""
from __future__ import annotations

import io
import logging
import os
import re
import uuid
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from .normalization import normalize_description, parse_date, currency_or_default
import hashlib

logger = logging.getLogger(__name__)


def _sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


from .dedup import tx_fingerprint
from .parse.banks.boa_v2025 import parse_boa_pdf


def _should_use_ai_fallback() -> bool:
    """Check if AI fallback parsing is enabled."""
    from .settings import load_settings
    s = load_settings()
    # Enabled by default, can be disabled via settings
    return s.get("ai_pdf_fallback_enabled", True)


def _is_ai_available() -> bool:
    """Check if AI service is available (OpenAI API key or LMStudio running)."""
    try:
        from .ai import AIConfig
        config = AIConfig.from_env()

        # OpenAI is preferred (native PDF support, no image conversion)
        if config.openai_api_key:
            return True

        # Check LMStudio as fallback
        try:
            import requests
            resp = requests.get(
                f"{config.lmstudio_base_url}/models",
                timeout=2
            )
            if resp.ok:
                return True
        except Exception:
            pass

        return False
    except Exception:
        return False


def _insert_transaction(
    conn,
    tx_id: str,
    account_id: str,
    posted_at,
    amount: float,
    curr: str,
    desc_norm: str,
    now: datetime,
    fp: str,
    run_id: str,
    file_id: str,
    ai_merchant_name: Optional[str] = None,
    ai_category_hint: Optional[str] = None,
    ai_confidence: Optional[float] = None,
) -> bool:
    """Insert a transaction, returning True if inserted, False if deduped."""
    try:
        # Build column list dynamically based on AI enrichment
        cols = [
            "id", "account_id", "posted_at", "amount", "currency", "description_norm",
            "external_id", "fingerprint", "source_raw_id", "created_at"
        ]
        vals = [tx_id, account_id, posted_at, amount, curr, desc_norm, None, fp, None, now]

        if ai_merchant_name:
            cols.append("ai_merchant_name")
            vals.append(ai_merchant_name)
        if ai_confidence is not None:
            cols.append("ai_confidence_score")
            vals.append(ai_confidence)

        placeholders = ", ".join(["?"] * len(vals))
        col_str = ", ".join(cols)

        conn.execute(
            f"INSERT INTO [transaction] ({col_str}) VALUES ({placeholders})",
            vals,
        )

        # Link to import run/file
        try:
            conn.execute(
                "INSERT INTO transaction_ingest (tx_id, run_id, file_id) VALUES (?, ?, ?) ON CONFLICT (tx_id) DO UPDATE SET run_id = EXCLUDED.run_id, file_id = EXCLUDED.file_id",
                [tx_id, run_id, file_id],
            )
        except Exception:
            pass

        return True
    except Exception as e:
        # Handle both DuckDB (ConstraintException) and SQLite (IntegrityError)
        if e.__class__.__name__ not in ('ConstraintException', 'IntegrityError'):
            raise
        return False


def _process_rows(
    rows: list,
    conn,
    account_id: str,
    run_id: str,
    file_id: str,
    now: datetime,
) -> tuple[int, int]:
    """Process parsed rows into transactions. Returns (inserted, deduped)."""
    inserted = 0
    deduped = 0

    for r in rows:
        posted_at = r.get("posted_at")
        if posted_at is None:
            continue

        desc_norm = r.get("description_norm") or normalize_description(r.get("description", ""))
        amount = float(r.get("amount", 0))
        curr = r.get("currency", "USD")
        fp = tx_fingerprint(account_id, posted_at, amount, desc_norm)
        tx_id = str(uuid.uuid4())

        if _insert_transaction(
            conn, tx_id, account_id, posted_at, amount, curr, desc_norm, now, fp,
            run_id, file_id,
            ai_merchant_name=r.get("ai_merchant_name"),
            ai_category_hint=r.get("ai_category_hint"),
            ai_confidence=r.get("ai_confidence"),
        ):
            inserted += 1
        else:
            deduped += 1

    return inserted, deduped


def import_pdf_upload(
    file_bytes: bytes,
    filename: str,
    account_id: str,
    run_id: str | None = None,
    file_id: str | None = None,
    enable_ai_fallback: bool = True,
) -> Dict[str, Any]:
    """Parse and import a PDF bank statement.

    Uses a multi-layer parsing strategy:
    1. Bank-specific parsers (boa_v2025) - Fast, reliable for known formats
    2. AI Vision Parser - Flexible, extracts from any format with enrichment
    3. SimpleBankV1 regex - Last resort for simple text-based statements

    Args:
        file_bytes: Raw PDF content
        filename: Original filename
        account_id: Target account ID
        run_id: Import run ID (created if None)
        file_id: Import file ID (created if None)
        enable_ai_fallback: Whether to try AI parser before text fallback

    Returns:
        Dict with run_id, file_id, inserted, deduped, raw, parser, hash
    """
    try:
        import pdfplumber  # type: ignore
    except Exception as e:
        raise ImportError("pdfplumber is required for PDF ingestion") from e

    from .db import get_conn

    conn = get_conn()
    now = datetime.now(UTC)
    created_run = False

    if not run_id:
        run_id = str(uuid.uuid4())
        created_run = True
    if not file_id:
        file_id = str(uuid.uuid4())

    if created_run:
        conn.execute(
            "INSERT INTO import_run (id, started_at, source, user_note) VALUES (?, ?, ?, ?)",
            [run_id, now, "upload:pdf", filename],
        )

    digest = _sha256(file_bytes)
    conn.execute(
        "INSERT INTO import_file (id, run_id, path, hash, type) VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
        [file_id, run_id, filename, digest, "pdf"],
    )

    # =========================================================================
    # Layer 1: Bank-specific parsers (fast, deterministic)
    # =========================================================================
    try:
        result = parse_boa_pdf(file_bytes)
        rows = result.rows
        raw_count = len(rows)

        if raw_count > 0:
            inserted, deduped = _process_rows(rows, conn, account_id, run_id, file_id, now)
            logger.info(f"boa_v2025 parser: {inserted} inserted, {deduped} deduped from {raw_count} rows")
            return {
                "run_id": run_id,
                "file_id": file_id,
                "inserted": inserted,
                "deduped": deduped,
                "raw": raw_count,
                "parser": "boa_v2025",
                "hash": digest,
                "meta": result.meta,
            }
    except Exception as e:
        logger.debug(f"boa_v2025 parser failed: {e}")

    # =========================================================================
    # Layer 2: AI Vision Parser (flexible, with enrichment)
    # =========================================================================
    if enable_ai_fallback and _should_use_ai_fallback():
        try:
            # Check if AI is available before attempting
            if _is_ai_available():
                logger.info("Attempting AI vision parser...")
                from .parse.ai_parser import parse_pdf_with_ai

                result = parse_pdf_with_ai(file_bytes)
                rows = result.rows
                raw_count = len(rows)

                if raw_count > 0:
                    inserted, deduped = _process_rows(rows, conn, account_id, run_id, file_id, now)
                    logger.info(f"AI parser: {inserted} inserted, {deduped} deduped from {raw_count} rows")
                    return {
                        "run_id": run_id,
                        "file_id": file_id,
                        "inserted": inserted,
                        "deduped": deduped,
                        "raw": raw_count,
                        "parser": "ai_vision",
                        "hash": digest,
                        "meta": result.meta,
                        "ai_confidence": result.meta.get("ai_confidence", 0.0),
                    }
                else:
                    logger.warning("AI parser returned no transactions")
            else:
                logger.debug("AI service not available, skipping AI fallback")
        except Exception as e:
            logger.warning(f"AI parser failed: {e}")

    # =========================================================================
    # Layer 3: SimpleBankV1 text fallback (last resort)
    # =========================================================================
    logger.info("Using SimpleBankV1 text fallback parser...")

    inserted = 0
    deduped = 0
    raw_count = 0

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    line_re = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(.+?)\s+(-?\d+(?:\.\d{2})?)\s*(\w+)?$")

    for idx, line in enumerate(text.splitlines(), start=1):
        m = line_re.match(line.strip())
        if not m:
            continue
        raw_count += 1
        d, desc, amt_str, curr_str = m.groups()

        try:
            posted_at = parse_date(d)
        except Exception:
            continue

        desc_norm = normalize_description(desc)
        amount = float(amt_str)
        curr = currency_or_default(curr_str)
        fp = tx_fingerprint(account_id, posted_at, amount, desc_norm)
        tx_id = str(uuid.uuid4())

        if _insert_transaction(
            conn, tx_id, account_id, posted_at, amount, curr, desc_norm, now, fp,
            run_id, file_id
        ):
            inserted += 1
        else:
            deduped += 1

    logger.info(f"Fallback parser: {inserted} inserted, {deduped} deduped from {raw_count} rows")

    return {
        "run_id": run_id,
        "file_id": file_id,
        "inserted": inserted,
        "deduped": deduped,
        "raw": raw_count,
        "parser": "fallback",
        "hash": digest,
    }
