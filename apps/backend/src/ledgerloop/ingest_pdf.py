from __future__ import annotations

import io
import re
import uuid
from datetime import datetime
from typing import Dict, Any

from .normalization import normalize_description, parse_date, currency_or_default
from .dedup import tx_fingerprint
from .parse.banks.boa_v2025 import parse_boa_pdf


def import_pdf_upload(file_bytes: bytes, filename: str, account_id: str, run_id: str | None = None, file_id: str | None = None) -> Dict[str, Any]:
    """Parse a scoped PDF bank statement format (SimpleBankV1).

    SimpleBankV1 line format (after text extraction):
      YYYY-MM-DD <DESCRIPTION> <AMOUNT> [CURRENCY]

    This function requires `pdfplumber`. If unavailable, raises ImportError.
    """
    try:
        import pdfplumber  # type: ignore
    except Exception as e:
        raise ImportError("pdfplumber is required for PDF ingestion") from e

    from .db import get_conn

    conn = get_conn()
    now = datetime.utcnow()
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
    conn.execute(
        "INSERT OR IGNORE INTO import_file (id, run_id, path, hash, type) VALUES (?, ?, ?, ?, ?)",
        [file_id, run_id, filename, None, "pdf"],
    )

    inserted = 0
    deduped = 0
    raw_count = 0

    # Try BoA parser first
    try:
        result = parse_boa_pdf(file_bytes)
        rows = result.rows
        raw_count = len(rows)
        for r in rows:
            posted_at = r["posted_at"]
            desc_norm = r.get("description_norm") or normalize_description(r.get("description", ""))
            amount = float(r.get("amount", 0))
            curr = "USD"
            fp = tx_fingerprint(account_id, posted_at, amount, desc_norm)
            tx_id = str(uuid.uuid4())
            try:
                conn.execute(
                    """
                    INSERT INTO transaction (
                        id, account_id, posted_at, amount, currency, description_norm,
                        external_id, fingerprint, source_raw_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [tx_id, account_id, posted_at, amount, curr, desc_norm, None, fp, None, now],
                )
                inserted += 1
            except Exception as e:
                if e.__class__.__name__ != 'ConstraintException':
                    raise
                deduped += 1
            else:
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO transaction_ingest (tx_id, run_id, file_id) VALUES (?, ?, ?)",
                        [tx_id, run_id, file_id],
                    )
                except Exception:
                    pass
        return {"run_id": run_id, "file_id": file_id, "inserted": inserted, "deduped": deduped, "raw": raw_count, "parser": "boa_v2025"}
    except Exception:
        pass

    # Fallback: SimpleBankV1 text lines
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    line_re = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(.+?)\s+(-?\d+(?:\.\d{2})?)\s*(\w+)?$")
    for idx, line in enumerate(text.splitlines(), start=1):
        m = line_re.match(line.strip())
        if not m:
            continue
        raw_count += 1
        d, desc, amt_str, curr_str = m.groups()
        posted_at = parse_date(d)
        desc_norm = normalize_description(desc)
        amount = float(amt_str)
        curr = currency_or_default(curr_str)
        fp = tx_fingerprint(account_id, posted_at, amount, desc_norm)
        tx_id = str(uuid.uuid4())
        try:
            conn.execute(
                """
                INSERT INTO transaction (
                    id, account_id, posted_at, amount, currency, description_norm,
                    external_id, fingerprint, source_raw_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [tx_id, account_id, posted_at, amount, curr, desc_norm, None, fp, None, now],
            )
            inserted += 1
        except Exception as e:
            if e.__class__.__name__ != 'ConstraintException':
                raise
            deduped += 1
        else:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO transaction_ingest (tx_id, run_id, file_id) VALUES (?, ?, ?)",
                    [tx_id, run_id, file_id],
                )
            except Exception:
                pass

    return {"run_id": run_id, "file_id": file_id, "inserted": inserted, "deduped": deduped, "raw": raw_count, "parser": "fallback"}
