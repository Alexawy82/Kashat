from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from datetime import datetime, UTC
from typing import Dict, Any, List, Tuple
from datetime import date


# Avoid importing DB on module load to keep pure helpers testable without duckdb
from .normalization import normalize_description, parse_amount, parse_date, currency_or_default
from .dedup import tx_fingerprint


def _sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def normalize_row(row: Dict[str, Any]) -> Tuple[date, str, float, str]:
    date_str = row.get("date") or row.get("Date") or row.get("DATE") or ""
    desc = row.get("description") or row.get("Description") or row.get("DESC") or ""
    amount = parse_amount(row.get("amount"), row.get("credit"), row.get("debit"))
    curr = currency_or_default(row.get("currency") or row.get("Currency"))
    posted_at = parse_date(date_str)
    desc_norm = normalize_description(desc)
    return posted_at, desc_norm, amount, curr


def import_csv_upload(file_bytes: bytes, filename: str, account_id: str, run_id: str | None = None, file_id: str | None = None) -> Dict[str, Any]:
    from .db import get_conn
    """Import CSV content for a given account.

    Expected headers include at least: date, description, and either amount or credit/debit columns.
    Optional: currency
    """
    conn = get_conn()
    now = datetime.now(UTC)
    created_run = False
    if not run_id:
        run_id = str(uuid.uuid4())
        created_run = True
    if not file_id:
        file_id = str(uuid.uuid4())
    digest = _sha256(file_bytes)

    # Ensure account exists to satisfy FK
    conn.execute(
        "INSERT OR IGNORE INTO account (id, name, type, currency) VALUES (?, ?, ?, ?)",
        [account_id, "Imported Account", "checking", "USD"],
    )

    if created_run:
        conn.execute(
            "INSERT INTO import_run (id, started_at, source, user_note) VALUES (?, ?, ?, ?)",
            [run_id, now, "upload:csv", filename],
        )
    conn.execute(
        "INSERT OR IGNORE INTO import_file (id, run_id, path, hash, type) VALUES (?, ?, ?, ?, ?)",
        [file_id, run_id, filename, digest, "csv"],
    )

    # Parse CSV
    buf = io.StringIO(file_bytes.decode("utf-8", errors="ignore"))
    reader = csv.DictReader(buf)

    inserted = 0
    deduped = 0
    raw_count = 0
    # local import to avoid requiring duckdb for pure helper tests
    import duckdb  # type: ignore

    # Prepare NDJSON error report
    from .config import tmp_dir
    report_path = tmp_dir() / f"import-{run_id}.ndjson"
    report_f = report_path.open("w", encoding="utf-8")
    errors = 0

    for idx, row in enumerate(reader, start=1):
        raw_count += 1
        # store raw
        conn.execute(
            "INSERT INTO raw_record (id, file_id, row_no, raw_json, parsed_at) VALUES (?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), file_id, idx, json.dumps(row), now],
        )

        try:
            posted_at, desc_norm, amount, curr = normalize_row(row)
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
                    [
                        tx_id,
                        account_id,
                        posted_at,
                        amount,
                        curr,
                        desc_norm,
                        None,
                        fp,
                        None,
                        now,
                    ],
                )
                inserted += 1
                # Link transaction to ingest run/file for management
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO transaction_ingest (tx_id, run_id, file_id) VALUES (?, ?, ?)",
                        [tx_id, run_id, file_id],
                    )
                except Exception:
                    pass
            except Exception as e:
                if e.__class__.__name__ != 'ConstraintException':
                    raise
                deduped += 1
                continue
        except Exception as e:
            errors += 1
            report_f.write(json.dumps({"row_no": idx, "error": str(e), "row": row}, ensure_ascii=False) + "\n")
            continue

    report_f.close()
    return {
        "run_id": run_id,
        "file_id": file_id,
        "inserted": inserted,
        "deduped": deduped,
        "raw": raw_count,
        "hash": digest,
        "errors": errors,
        "report": str(report_path) if errors else None,
    }
