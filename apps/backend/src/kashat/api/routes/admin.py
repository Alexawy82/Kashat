from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from fastapi import UploadFile, File
from pydantic import BaseModel
from typing import Optional
from datetime import date
import shutil
import uuid
import re
import os
from pathlib import Path

from ...db import get_conn
from ...config import db_path, tmp_dir


from ..auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

_BACKUP_NAME_RE = re.compile(r"^(backup|backup-before-factory)-[0-9a-fA-F-]{36}\.(duckdb|sqlite)$")


def _safe_tmp_download_path(name: str) -> Path:
    if not name or name != Path(name).name:
        raise HTTPException(status_code=400, detail="Invalid file name")
    if not _BACKUP_NAME_RE.fullmatch(name):
        raise HTTPException(status_code=400, detail="Invalid backup name")
    base = tmp_dir().resolve()
    candidate = (tmp_dir() / name).resolve()
    if not candidate.is_relative_to(base):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return candidate


@router.get("/data/stats")
def get_data_stats() -> dict:
    conn = get_conn()
    stats = {}
    stats["transactions"] = conn.execute("SELECT COUNT(*) FROM [transaction]").fetchone()[0]
    stats["categories"] = conn.execute("SELECT COUNT(*) FROM category").fetchone()[0]
    stats["rules"] = conn.execute("SELECT COUNT(*) FROM rule").fetchone()[0]
    stats["import_runs"] = conn.execute("SELECT COUNT(*) FROM import_run").fetchone()[0]
    stats["import_files"] = conn.execute("SELECT COUNT(*) FROM import_file").fetchone()[0]
    stats["raw_records"] = conn.execute("SELECT COUNT(*) FROM raw_record").fetchone()[0]
    stats["events"] = conn.execute("SELECT COUNT(*) FROM event_log").fetchone()[0]
    stats["ai_jobs"] = conn.execute("SELECT COUNT(*) FROM ai_bulk_job").fetchone()[0]
    # DB size
    try:
        size = db_path().stat().st_size
    except Exception:
        size = 0
    stats["db_size_bytes"] = size
    return {"stats": stats}


@router.post("/data/optimize")
def optimize_database() -> dict:
    conn = get_conn()
    optimized = False
    vacuumed = False
    try:
        conn.execute("PRAGMA optimize")
        optimized = True
    except Exception:
        pass
    try:
        conn.execute("VACUUM")
        vacuumed = True
    except Exception:
        pass
    return {"optimized": optimized, "vacuumed": vacuumed}


class DeleteTransactionsBody(BaseModel):
    account_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category_id: Optional[str] = None
    only_uncategorized: bool = False


@router.post("/data/delete-transactions")
def delete_transactions(body: DeleteTransactionsBody) -> dict:
    conn = get_conn()
    where = []
    params = []
    if body.account_id:
        where.append("t.account_id = ?")
        params.append(body.account_id)
    if body.start_date:
        where.append("t.posted_at >= ?")
        params.append(body.start_date)
    if body.end_date:
        where.append("t.posted_at <= ?")
        params.append(body.end_date)
    if body.category_id:
        where.append("tc.category_id = ?")
        params.append(body.category_id)
    if body.only_uncategorized:
        where.append("tc.tx_id IS NULL")
    wh = (" WHERE " + " AND ".join(where)) if where else ""

    # Select IDs to delete first
    rows = conn.execute(
        f"""
        SELECT t.id FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        {wh}
        """,
        params,
    ).fetchall()
    ids = [r[0] for r in rows]
    if not ids:
        return {"deleted": 0}

    # Delete from child tables then transactions
    qmarks = ",".join(["?"] * len(ids))
    conn.execute(f"DELETE FROM transaction_category WHERE tx_id IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM match_transfer WHERE left_tx_id IN ({qmarks}) OR right_tx_id IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM transaction_tag WHERE tx_id IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM [transaction] WHERE id IN ({qmarks})", ids)
    return {"deleted": len(ids)}


@router.post("/data/reset-ai")
def reset_ai_fields() -> dict:
    conn = get_conn()
    conn.execute(
        """
        UPDATE [transaction] SET 
            ai_merchant_name = NULL,
            ai_category_suggestions = NULL,
            ai_confidence_score = NULL,
            ai_processed_at = NULL,
            ai_provider = NULL,
            ai_model = NULL,
            ai_latency_ms = NULL
        """
    )
    # Keep jobs history; comment out next line if purging jobs is desired
    # conn.execute("DELETE FROM ai_bulk_job")
    return {"reset": True}


class DeleteAllBody(BaseModel):
    confirm: str
    include_categories: bool = False


@router.post("/data/delete-all")
def delete_all_data(body: DeleteAllBody) -> dict:
    if body.confirm != "DELETE ALL":
        raise HTTPException(status_code=400, detail="Confirmation phrase mismatch. Type 'DELETE ALL'.")
    conn = get_conn()
    # Delete in dependency order
    tables = [
        "transaction_category",
        "match_transfer",
        "transaction_tag",
        "raw_record",
        "import_file",
        "import_run",
        "recurring_tx",
        "recurring_series",
        "event_log",
        "transaction",
        "rule",
        "ai_bulk_job",
        "ai_workflow_run",
    ]
    if body.include_categories:
        tables.append("category")
    for table in tables:
        try:
            conn.execute(f"DELETE FROM {table}")
        except Exception:
            pass
    return {"deleted": True}


@router.post("/data/backup")
def create_backup() -> dict:
    # Copy the SQLite file to a tmp backup
    src = db_path()
    if not src.exists():
        raise HTTPException(status_code=404, detail="Database file not found")
    backup_name = f"backup-{uuid.uuid4()}.sqlite"
    dest = tmp_dir() / backup_name
    shutil.copy2(src, dest)
    return {"backup_file": backup_name, "path": str(dest)}


@router.get("/data/backup/{name}")
def download_backup(name: str):
    from fastapi.responses import StreamingResponse
    path = _safe_tmp_download_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    def _iter():
        with path.open('rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk
    return StreamingResponse(_iter(), media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={name}"})


@router.post("/data/restore")
def restore_database(file: UploadFile = File(...)) -> dict:
    """Restore database from uploaded SQLite file. This will temporarily close the DB connection."""
    raw = (os.getenv("KASHAT_MAX_UPLOAD_MB") or "").strip()
    try:
        max_mb = int(raw) if raw != "" else 50
    except Exception:
        max_mb = 50
    max_bytes = None if max_mb <= 0 else max_mb * 1024 * 1024

    # Save upload to tmp
    dest = tmp_dir() / f"restore-{uuid.uuid4()}.sqlite"
    total = 0
    try:
        with dest.open("wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if max_bytes is not None and total > max_bytes:
                    raise HTTPException(status_code=413, detail="Upload too large")
                out.write(chunk)
    except HTTPException:
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
        raise
    # Close DB and replace
    from ...db import close, connect
    try:
        close()
    except Exception:
        pass
    shutil.copy2(dest, db_path())
    connect()
    return {"restored": True, "from": file.filename}


# AI Category Mapping Management
class AIMappingBody(BaseModel):
    provider: str | None = None  # null for global
    source_label: str
    category_id: str


@router.get("/ai-mapping")
def list_ai_mapping() -> dict:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT m.provider, m.source_label, m.category_id, c.name
        FROM ai_category_mapping m
        LEFT JOIN category c ON c.id = m.category_id
        ORDER BY COALESCE(m.provider, ''), m.source_label
        """
    ).fetchall()
    return {
        "mappings": [
            {
                "provider": r[0],
                "source_label": r[1],
                "category_id": r[2],
                "category_name": r[3],
            }
            for r in rows
        ]
    }


@router.post("/ai-mapping")
def add_ai_mapping(body: AIMappingBody) -> dict:
    conn = get_conn()
    # Ensure category exists
    exists = conn.execute("SELECT 1 FROM category WHERE id = ?", [body.category_id]).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Category not found")
    conn.execute(
        "INSERT INTO ai_category_mapping (provider, source_label, category_id) VALUES (?, ?, ?) ON CONFLICT (provider, source_label) DO UPDATE SET category_id = EXCLUDED.category_id",
        [body.provider, body.source_label, body.category_id],
    )
    return {"created": True}


@router.delete("/ai-mapping")
def delete_ai_mapping(provider: str | None = None, source_label: str | None = None) -> dict:
    if not source_label:
        raise HTTPException(status_code=400, detail="source_label required")
    conn = get_conn()
    if provider is None:
        conn.execute(
            "DELETE FROM ai_category_mapping WHERE provider IS NULL AND source_label = ?",
            [source_label],
        )
    else:
        conn.execute(
            "DELETE FROM ai_category_mapping WHERE provider = ? AND source_label = ?",
            [provider, source_label],
        )
    return {"deleted": True}


# Factory reset: backup current DB, fully delete it, and create a fresh empty database.
class FactoryResetBody(BaseModel):
    confirm: str


@router.post("/data/factory-reset")
def factory_reset(body: FactoryResetBody) -> dict:
    """Fully wipe the database file and recreate an empty schema.

    This performs a best‑effort backup to tmp before deleting the DB file.
    Confirmation phrase must be exactly 'FACTORY RESET'.
    """
    if body.confirm != "FACTORY RESET":
        raise HTTPException(status_code=400, detail="Confirmation phrase mismatch. Type 'FACTORY RESET'.")

    # Backup if present
    src = db_path()
    backup_file = None
    if src.exists():
        backup_file = f"backup-before-factory-{uuid.uuid4()}.sqlite"
        dest = tmp_dir() / backup_file
        try:
            from ...db import close
            close()
        except Exception:
            pass
        shutil.copy2(src, dest)

    # Delete DB file
    try:
        if src.exists():
            src.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete DB: {e}")

    # Recreate empty schema directly to avoid schema-init race guards
    try:
        import sqlite3
        from ... import db as dbmod
        conn = sqlite3.connect(str(src))
        # Register custom functions for SQLite
        conn.create_function("regexp", 2, dbmod._sqlite_regexp)
        conn.create_function("regexp_matches", 2, dbmod._sqlite_regexp_matches)
        conn.executescript(dbmod.SCHEMA_SQL)
        # Best-effort upgrades (safe to run on empty DB)
        try:
            dbmod._upgrade_schema(conn)  # type: ignore[attr-defined]
        except Exception:
            pass
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize new DB: {e}")

    # Reconnect application connection
    try:
        from ...db import connect
        connect()
    except Exception:
        pass

    return {"reset": True, "backup_file": backup_file}


# Wipe all data in-place without deleting the DB file (safer on networked or locked filesystems)
class WipeAllBody(BaseModel):
    confirm: str


@router.post("/data/backfill-confidence")
def backfill_confidence_scores() -> dict:
    """Backfill ai_confidence_score for categorized transactions that have NULL scores.

    Runs pattern matching to get actual confidence, or defaults to 0.85 (high).
    """
    from ...ai_enhanced_categorization import categorize_transaction_enhanced

    conn = get_conn()

    # Find categorized transactions without confidence scores
    rows = conn.execute("""
        SELECT t.id, t.description_norm, t.amount
        FROM [transaction] t
        JOIN transaction_category tc ON tc.tx_id = t.id
        WHERE t.ai_confidence_score IS NULL
    """).fetchall()

    updated = 0
    for row in rows:
        tx_id, desc, amount = row

        # Try to get actual confidence from pattern matching
        suggestions = categorize_transaction_enhanced(desc, amount)
        if suggestions and suggestions[0].confidence > 0:
            confidence = suggestions[0].confidence
        else:
            # Default to high confidence since they were pattern-matched
            confidence = 0.85

        conn.execute(
            "UPDATE [transaction] SET ai_confidence_score = ? WHERE id = ?",
            [confidence, tx_id]
        )
        updated += 1

    return {"updated": updated, "message": f"Backfilled confidence scores for {updated} transactions"}


@router.post("/data/backfill-merchant-names")
def backfill_merchant_names() -> dict:
    """Backfill ai_merchant_name for all transactions.

    Runs pattern matching to extract clean merchant names for display.
    """
    from ...ai_enhanced_categorization import get_enhanced_categorization_service

    conn = get_conn()
    service = get_enhanced_categorization_service()

    # Get all transactions (we'll update merchant names for all)
    rows = conn.execute("""
        SELECT t.id, t.description_norm, t.amount
        FROM [transaction] t
        WHERE t.ai_merchant_name IS NULL
    """).fetchall()

    updated = 0
    for row in rows:
        tx_id, desc, amount = row

        # Run categorization to get merchant name
        suggestions = service.categorize_transaction(desc, amount)
        merchant_name = None

        # Get merchant name from first suggestion that has one
        for suggestion in suggestions:
            if suggestion.merchant_name:
                merchant_name = suggestion.merchant_name
                break

        if merchant_name:
            conn.execute(
                "UPDATE [transaction] SET ai_merchant_name = ? WHERE id = ?",
                [merchant_name, tx_id]
            )
            updated += 1

    return {"updated": updated, "total_processed": len(rows), "message": f"Backfilled merchant names for {updated} transactions"}


@router.post("/data/wipe-all")
def wipe_all_data(body: WipeAllBody) -> dict:
    """Delete all rows from all application tables in a safe order.

    Confirmation phrase must be exactly 'WIPE ALL'. This keeps the schema intact and avoids filesystem locks.
    """
    if body.confirm != "WIPE ALL":
        raise HTTPException(status_code=400, detail="Confirmation phrase mismatch. Type 'WIPE ALL'.")

    conn = get_conn()
    counts: dict[str,int] = {}
    # Helper to count and delete
    def del_all(table: str):
        try:
            c = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            c = 0
        try:
            conn.execute(f"DELETE FROM {table}")
        except Exception:
            pass
        counts[table] = int(c or 0)

    # Child tables first
    for t in (
        "transaction_category",
        "match_transfer",
        "recurring_tx",
        "transaction_tag",
        "transaction_ingest",
        "raw_record",
    ):
        del_all(t)
    # Core tables
    for t in (
        "transaction",
        "import_file",
        "import_run",
        "recurring_series",
        "event_log",
        "ai_bulk_job",
        "ai_workflow_run",
        "ai_category_mapping",
    ):
        del_all(t)
    return {"wiped": True, "counts": counts}
