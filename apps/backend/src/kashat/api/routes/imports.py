import uuid
import os
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Depends, Request
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from fastapi import HTTPException

from .. import limiter
from ...db import get_conn
from ...ingest_csv import import_csv_upload
from ...ingest_pdf import import_pdf_upload
from ...parse.banks.boa_v2025 import parse_boa_pdf
from ...ai_import import get_ai_import_processor
from ...ai_workflow import get_workflow_engine, WorkflowConfig
from ...detect.income import mark_income
from ...detect.adjustments import mark_adjustments
from ...detect.zelle import parse_zelle_descriptor
from ...recurring import auto_link_transactions_to_series
from ..auth import require_admin


router = APIRouter(prefix="/imports", tags=["imports"])


class ParseFileInfo(BaseModel):
    name: str
    type: Optional[str] = None
    size: Optional[int] = None
    hash: Optional[str] = None


class ParseRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    account_id: Optional[str] = None
    run_id: Optional[str] = None
    source: Optional[str] = None
    user_note: Optional[str] = None
    file_info: Optional[ParseFileInfo] = Field(default=None, alias="fileInfo")

def _max_upload_bytes() -> int | None:
    """Maximum allowed upload size in bytes per file (None = unlimited)."""
    raw = (os.getenv("KASHAT_MAX_UPLOAD_MB") or "").strip()
    if raw == "":
        return 50 * 1024 * 1024
    try:
        mb = int(raw)
    except Exception:
        return 50 * 1024 * 1024
    if mb <= 0:
        return None
    return mb * 1024 * 1024


def _allow_background_ai_tasks() -> bool:
    """Disable background AI tasks during pytest to keep tests fast and deterministic."""
    return os.getenv("PYTEST_CURRENT_TEST") is None


async def _read_upload_limited(upload: UploadFile) -> bytes:
    limit = _max_upload_bytes()
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if limit is not None and total > limit:
            raise HTTPException(status_code=413, detail="Upload too large")
        chunks.append(chunk)
    return b"".join(chunks)


def _ensure_account(account_id: Optional[str]) -> str:
    conn = get_conn()
    if account_id:
        row = conn.execute("SELECT id FROM account WHERE id = ?", [account_id]).fetchone()
        if row:
            return account_id
    # create default account
    new_id = account_id or str(uuid.uuid4())
    conn.execute(
        "INSERT INTO account (id, name, type, currency) VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING",
        [new_id, "Imported Account", "checking", "USD"],
    )
    return new_id


def _find_or_create_account_by_last4(last4: str, default_name: str = None) -> str:
    """Find an account by last4; create if not found.

    Returns the account id.
    """
    conn = get_conn()
    row = conn.execute("SELECT id FROM account WHERE last4 = ? LIMIT 1", [last4]).fetchone()
    if row:
        return row[0]
    new_id = str(uuid.uuid4())
    name = default_name or f"Bank Account ••••{last4}"
    conn.execute(
        "INSERT INTO account (id, name, type, currency, last4) VALUES (?, ?, ?, ?, ?)",
        [new_id, name, "checking", "USD", last4],
    )
    return new_id


@router.post("/parse")
def parse_import(payload: ParseRequest):
    """Create or resume an import run for workflow-based parsing."""
    from datetime import datetime as _dt, UTC as _UTC
    conn = get_conn()
    run_id = payload.run_id or str(uuid.uuid4())
    row = conn.execute("SELECT id FROM import_run WHERE id = ?", [run_id]).fetchone()
    created = False
    if not row:
        conn.execute(
            "INSERT INTO import_run (id, started_at, source, user_note) VALUES (?, ?, ?, ?)",
            [run_id, _dt.now(_UTC), payload.source or "workflow:parse", payload.user_note],
        )
        created = True

    acc_id = _ensure_account(payload.account_id) if payload.account_id else None
    file_id = None
    file_info = payload.file_info
    if file_info:
        file_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO import_file (id, run_id, path, hash, type) VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
            [file_id, run_id, file_info.name, file_info.hash, file_info.type],
        )

    return {
        "run_id": run_id,
        "file_id": file_id,
        "account_id": acc_id,
        "status": "created" if created else "existing",
        "file": file_info.model_dump() if file_info else None,
    }


@router.get("/runs")
def list_import_runs(limit: int = 20):
    """List recent import runs with info, file counts, tx count and covered period."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT ir.id, ir.started_at, COUNT(DISTINCT f.id) AS files,
               MIN(t.posted_at) AS period_start,
               MAX(t.posted_at) AS period_end,
               COUNT(DISTINCT ti.tx_id) AS tx_count,
               MAX(COALESCE(ir.ai_analysis_complete, FALSE)) AS ai_done
        FROM import_run ir
        LEFT JOIN import_file f ON f.run_id = ir.id
        LEFT JOIN transaction_ingest ti ON ti.run_id = ir.id
        LEFT JOIN [transaction] t ON t.id = ti.tx_id
        GROUP BY ir.id, ir.started_at
        ORDER BY ir.started_at DESC
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    cols = [c[0] for c in conn.description]
    out = []
    for raw in rows:
        d = dict(zip(cols, raw))
        txc = int(d.get("tx_count") or 0)
        ai_done = bool(d.get("ai_done"))
        d["status"] = "completed" if ai_done else ("ready" if txc > 0 else "empty")
        d["file_count"] = int(d.get("files") or 0)
        d["summary_available"] = txc > 0
        out.append(d)
    return out


@router.get("/files")
def list_import_files(limit: int = 100):
    """List all imported files with their details."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT f.id, f.run_id, f.path, f.type, f.hash,
               COUNT(ti.tx_id) AS tx_count,
               MIN(t.posted_at) AS period_start,
               MAX(t.posted_at) AS period_end
        FROM import_file f
        LEFT JOIN transaction_ingest ti ON ti.file_id = f.id
        LEFT JOIN [transaction] t ON t.id = ti.tx_id
        GROUP BY f.id, f.run_id, f.path, f.type, f.hash
        ORDER BY period_end DESC NULLS LAST
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/periods")
def list_import_periods():
    """List available import periods (months with imported transactions)."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            strftime('%Y-%m-01', t.posted_at) AS period,
            COUNT(DISTINCT t.id) AS tx_count,
            COUNT(DISTINCT ti.run_id) AS run_count,
            MIN(t.posted_at) AS first_tx,
            MAX(t.posted_at) AS last_tx,
            SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS total_spend,
            SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS total_income
        FROM [transaction] t
        JOIN transaction_ingest ti ON ti.tx_id = t.id
        WHERE t.posted_at IS NOT NULL
        GROUP BY 1
        ORDER BY 1 DESC
        """
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/runs/{run_id}/files")
def list_run_files(run_id: str):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT f.id as file_id, f.path, f.type,
               COUNT(ti.tx_id) AS tx_count,
               MIN(t.posted_at) AS period_start,
               MAX(t.posted_at) AS period_end
        FROM import_file f
        LEFT JOIN transaction_ingest ti ON ti.file_id = f.id
        LEFT JOIN [transaction] t ON t.id = ti.tx_id
        WHERE f.run_id = ?
        GROUP BY f.id, f.path, f.type
        ORDER BY f.path
        """,
        [run_id],
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/runs/{run_id}/summary")
def run_monthly_summary(run_id: str):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m-01', t.posted_at) AS month,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS income,
               SUM(t.amount) AS net,
               COUNT(*) AS count
        FROM [transaction] t
        JOIN transaction_ingest ti ON ti.tx_id = t.id AND ti.run_id = ?
        GROUP BY 1 ORDER BY 1
        """,
        [run_id],
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.delete("/runs/{run_id}")
def delete_run(run_id: str):
    """Delete an import run and all transactions linked to it (safe via transaction_ingest)."""
    conn = get_conn()
    # Mark as deleted up-front so UI immediately hides it even if cleanup encounters FK edge cases
    try:
        conn.execute("ALTER TABLE import_run ADD COLUMN deleted BOOLEAN DEFAULT FALSE")
    except Exception:
        pass
    try:
        conn.execute("UPDATE import_run SET deleted = TRUE WHERE id = ?", [run_id])
    except Exception:
        pass
    # Ensure FK constraints don't block batched deletes when background tasks might still be scanning
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
    except Exception:
        pass
    tx_ids = [r[0] for r in conn.execute("SELECT tx_id FROM transaction_ingest WHERE run_id = ?", [run_id]).fetchall()]
    # delete dependent rows
    def _delete_in(table: str, col: str, ids: list[str], or_second: tuple[str,str] | None = None):
        if not ids:
            return
        placeholders = ",".join(["?"] * len(ids))
        if or_second is None:
            conn.execute(f"DELETE FROM {table} WHERE {col} IN ({placeholders})", ids)
        else:
            a, b = or_second
            conn.execute(f"DELETE FROM {table} WHERE {a} IN ({placeholders}) OR {b} IN ({placeholders})", ids + ids)

    if tx_ids:
        _delete_in("transaction_category", "tx_id", tx_ids)
        _delete_in("match_transfer", "left_tx_id", tx_ids, or_second=("left_tx_id","right_tx_id"))
        _delete_in("recurring_tx", "tx_id", tx_ids)
        _delete_in("transaction_tag", "tx_id", tx_ids)
        _delete_in('"transaction"', "id", tx_ids)
        _delete_in("transaction_ingest", "tx_id", tx_ids)
    # delete raw_records and files by run id to avoid FK mismatch
    try:
        file_ids = [r[0] for r in conn.execute("SELECT id FROM import_file WHERE run_id = ?", [run_id]).fetchall()]
        for fid in file_ids:
            try:
                conn.execute("DELETE FROM raw_record WHERE file_id = ?", [fid])
            except Exception:
                pass
    except Exception:
        pass
    try:
        conn.execute("DELETE FROM import_file WHERE run_id = ?", [run_id])
    except Exception:
        pass
    # delete run
    try:
        conn.execute("DELETE FROM import_run WHERE id = ?", [run_id])
    except Exception:
        # As a last resort, mark deleted to avoid FK issues in limited DBs
        try:
            conn.execute("ALTER TABLE import_run ADD COLUMN deleted BOOLEAN DEFAULT FALSE")
        except Exception:
            pass
        conn.execute("UPDATE import_run SET deleted = TRUE WHERE id = ?", [run_id])
    out = {"deleted": {"transactions": len(tx_ids), "files": None, "run": run_id}}
    try:
        conn.execute("PRAGMA foreign_keys = ON")
    except Exception:
        pass
    return out


@router.post("/runs/{run_id}/reprocess")
def reprocess_run(run_id: str, background_tasks: BackgroundTasks, account_id: Optional[str] = None, enable_workflow: bool = True):
    conn = get_conn()
    # Try to infer account from one transaction
    row = conn.execute(
        "SELECT t.account_id FROM [transaction] t JOIN transaction_ingest ti ON ti.tx_id = t.id WHERE ti.run_id = ? LIMIT 1",
        [run_id],
    ).fetchone()
    acc = account_id or (row[0] if row else None)
    if not acc:
        return {"status": "no-op", "reason": "no transactions for run"}
    if enable_workflow:
        background_tasks.add_task(_process_import_with_workflow, run_id, acc)
    else:
        background_tasks.add_task(_process_import_with_ai, run_id, acc)
    return {"status": "queued"}


@router.post("/bulk")
@limiter.limit("10/minute")
async def import_bulk(
    files: List[UploadFile] = File(...),
    account_id: Optional[str] = Form(None),
    enable_ai: bool = Form(True),
    enable_workflow: bool = Form(True),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    # Allow query params to override form fields (client uses query string)
    if request is not None:
        qp = request.query_params
        account_id = account_id or qp.get("account_id")
        if qp.get("enable_ai") is not None:
            enable_ai = qp.get("enable_ai", "true").lower() in ("1", "true", "yes")
        if qp.get("enable_workflow") is not None:
            enable_workflow = qp.get("enable_workflow", "true").lower() in ("1", "true", "yes")
    # Determine target account: prefer provided; otherwise attempt auto-detect for PDFs by last4
    acc_id: Optional[str] = None
    if account_id:
        acc_id = _ensure_account(account_id)
    else:
        # Peek at first file for PDF last4
        try:
            first = files[0] if files else None
            if first and (first.filename or '').lower().endswith('.pdf'):
                data0 = await _read_upload_limited(first)
                # rewind for normal loop consumption later
                first.file.seek(0)
                try:
                    result = parse_boa_pdf(data0)
                    last4 = (result.meta or {}).get('account_last4')
                    if last4:
                        acc_id = _find_or_create_account_by_last4(last4, default_name=f"Bank of America ••••{last4}")
                except Exception:
                    acc_id = None
        except Exception:
            acc_id = None
        if not acc_id:
            acc_id = _ensure_account(None)
    # Create a run and process each file under it
    import uuid as _uuid
    from datetime import datetime as _dt, UTC as _UTC
    conn = get_conn()
    run_id = str(_uuid.uuid4())
    conn.execute(
        "INSERT INTO import_run (id, started_at, source, user_note) VALUES (?, ?, ?, ?)",
        [run_id, _dt.now(_UTC), "upload:bulk", f"{len(files)} files"],
    )
    summary = []
    total_inserted = 0
    total_deduped = 0
    total_raw = 0
    for uf in files:
        data = await _read_upload_limited(uf)
        file_id = str(_uuid.uuid4())
        name = uf.filename or "upload"
        # Compute file hash for duplicate detection
        import hashlib as _hashlib
        digest = _hashlib.sha256(data).hexdigest()
        # Duplicate file detection scoped to account: same content already imported for account
        try:
            exists = conn.execute(
                """
                SELECT 1 FROM import_file f
                JOIN transaction_ingest ti ON ti.file_id = f.id
                JOIN [transaction] t ON t.id = ti.tx_id
                WHERE f.hash = ? AND t.account_id = ? LIMIT 1
                """,
                [digest, acc_id],
            ).fetchone()
        except Exception:
            exists = None
        if exists:
            res = {"file": name, "skipped": True, "reason": "duplicate_file", "hash": digest}
            summary.append(res)
            continue
        if name.lower().endswith(".csv"):
            res = import_csv_upload(data, name, acc_id, run_id=run_id, file_id=file_id)
        elif name.lower().endswith(".pdf"):
            res = import_pdf_upload(data, name, acc_id, run_id=run_id, file_id=file_id)
        else:
            res = {"error": "unsupported file type", "file": name, "hash": digest}
        # After ingest, compute logical hash and detect logical duplicates in same account
        try:
            logical = _ensure_import_file_logical_hash(file_id)
        except Exception:
            logical = None
        detail = {"file": name, **{k:v for k,v in res.items() if k != 'file_id'}}
        if logical:
            try:
                dupe = conn.execute(
                    """
                    SELECT f.id, f.run_id FROM import_file f
                    JOIN transaction_ingest ti ON ti.file_id = f.id
                    JOIN [transaction] t ON t.id = ti.tx_id
                    WHERE f.logical_hash = ? AND f.id != ? AND t.account_id = ?
                    LIMIT 1
                    """,
                    [logical, file_id, acc_id],
                ).fetchone()
                if dupe:
                    detail["logical_duplicate_of_file_id"] = dupe[0]
                    detail["logical_duplicate_of_run_id"] = dupe[1]
            except Exception:
                pass
        summary.append(detail)
        total_inserted += int(res.get("inserted", 0) or 0)
        total_deduped += int(res.get("deduped", 0) or 0)
        total_raw += int(res.get("raw", 0) or 0)
    # Queue AI processing if enabled and any records were inserted
    # Also respect global AI processing settings
    from ...settings import load_settings
    ai_settings = load_settings()
    should_run_ai = (
        enable_ai
        and total_inserted > 0
        and background_tasks
        and _allow_background_ai_tasks()
        and ai_settings.get("ai_auto_start_on_import", True)
        and not ai_settings.get("ai_processing_paused", False)
    )
    if should_run_ai:
        if enable_workflow:
            background_tasks.add_task(_process_import_with_workflow, run_id, acc_id)
        else:
            background_tasks.add_task(_process_import_with_ai, run_id, acc_id)

    # Auto-link new transactions to existing recurring series
    if background_tasks and total_inserted > 0:
        background_tasks.add_task(auto_link_transactions_to_series)

    return {
        "run_id": run_id,
        "account_id": acc_id,
        "files": len(files),
        "inserted": total_inserted,
        "deduped": total_deduped,
        "raw": total_raw,
        "ai_processing": enable_ai,
        "workflow_enabled": enable_workflow,
        "details": summary,
    }


@router.post("/csv")
@limiter.limit("10/minute")
async def import_csv(
    file: UploadFile = File(...),
    account_id: Optional[str] = Form(None),
    run_id: Optional[str] = Form(None),
    enable_ai: bool = Form(True),
    enable_workflow: bool = Form(True),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    # Allow query params to override form fields (client uses query string)
    if request is not None:
        qp = request.query_params
        account_id = account_id or qp.get("account_id")
        run_id = run_id or qp.get("run_id")
        if qp.get("enable_ai") is not None:
            enable_ai = qp.get("enable_ai", "true").lower() in ("1", "true", "yes")
        if qp.get("enable_workflow") is not None:
            enable_workflow = qp.get("enable_workflow", "true").lower() in ("1", "true", "yes")
    acc_id = _ensure_account(account_id)
    data = await _read_upload_limited(file)
    result = import_csv_upload(data, file.filename, acc_id, run_id=run_id)
    # Compute logical hash for this file
    try:
        if result.get('file_id'):
            _ensure_import_file_logical_hash(result['file_id'])
    except Exception:
        pass
    
    # Add AI processing if enabled and import was successful
    # Also respect global AI processing settings
    from ...settings import load_settings
    ai_settings = load_settings()
    should_run_ai = (
        enable_ai
        and result.get('inserted', 0) > 0
        and background_tasks
        and _allow_background_ai_tasks()
        and ai_settings.get("ai_auto_start_on_import", True)
        and not ai_settings.get("ai_processing_paused", False)
    )
    if should_run_ai:
        run_id = result.get('run_id')
        if run_id:
            if enable_workflow:
                # Use full workflow
                background_tasks.add_task(_process_import_with_workflow, run_id, acc_id)
            else:
                # Use basic AI processing
                background_tasks.add_task(_process_import_with_ai, run_id, acc_id)

    return {"account_id": acc_id, "ai_processing": enable_ai, "workflow_enabled": enable_workflow, **result}


@router.post("/pdf")
@limiter.limit("10/minute")
async def import_pdf(
    file: UploadFile = File(...),
    account_id: Optional[str] = Form(None),
    run_id: Optional[str] = Form(None),
    enable_ai: bool = Form(True),
    enable_workflow: bool = Form(True),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    # Allow query params to override form fields (client uses query string)
    if request is not None:
        qp = request.query_params
        account_id = account_id or qp.get("account_id")
        run_id = run_id or qp.get("run_id")
        if qp.get("enable_ai") is not None:
            enable_ai = qp.get("enable_ai", "true").lower() in ("1", "true", "yes")
        if qp.get("enable_workflow") is not None:
            enable_workflow = qp.get("enable_workflow", "true").lower() in ("1", "true", "yes")
    data = await _read_upload_limited(file)

    # Compute file hash for duplicate detection
    import hashlib as _hashlib
    digest = _hashlib.sha256(data).hexdigest()
    conn = get_conn()

    # Check for file-level duplicate (same hash already imported)
    existing_file = conn.execute(
        "SELECT f.id, f.run_id FROM import_file f WHERE f.hash = ? LIMIT 1",
        [digest],
    ).fetchone()
    if existing_file:
        return {
            "account_id": None,
            "ai_processing": False,
            "workflow_enabled": False,
            "run_id": existing_file[1],
            "file_id": existing_file[0],
            "inserted": 0,
            "deduped": 0,
            "raw": 0,
            "parser": "skipped",
            "hash": digest,
            "skipped": True,
            "reason": "duplicate_file_hash",
        }

    # Determine account: prefer provided; otherwise auto-detect by last4 from PDF
    acc_id: Optional[str] = None
    if account_id:
        acc_id = _ensure_account(account_id)
    else:
        # Try to extract last4 from BoA PDF for account matching
        try:
            result = parse_boa_pdf(data)
            last4 = (result.meta or {}).get('account_last4')
            if last4:
                acc_id = _find_or_create_account_by_last4(last4, default_name=f"Bank of America ••••{last4}")
        except Exception:
            pass
        if not acc_id:
            acc_id = _ensure_account(None)

    result = import_pdf_upload(data, file.filename, acc_id, run_id=run_id)
    # Compute logical hash for this file
    try:
        if result.get('file_id'):
            _ensure_import_file_logical_hash(result['file_id'])
    except Exception:
        pass
    
    # Add AI processing if enabled and import was successful
    # Also respect global AI processing settings
    from ...settings import load_settings
    ai_settings = load_settings()
    should_run_ai = (
        enable_ai
        and result.get('inserted', 0) > 0
        and background_tasks
        and _allow_background_ai_tasks()
        and ai_settings.get("ai_auto_start_on_import", True)
        and not ai_settings.get("ai_processing_paused", False)
    )
    if should_run_ai:
        run_id = result.get('run_id')
        if run_id:
            if enable_workflow:
                # Use full workflow
                background_tasks.add_task(_process_import_with_workflow, run_id, acc_id)
            else:
                # Use basic AI processing
                background_tasks.add_task(_process_import_with_ai, run_id, acc_id)

    return {"account_id": acc_id, "ai_processing": enable_ai, "workflow_enabled": enable_workflow, **result}


@router.get("/report/{run_id}")
def download_report(run_id: str):
    from ...config import tmp_dir
    from fastapi.responses import StreamingResponse
    try:
        UUID(run_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run_id")
    path = tmp_dir() / f"import-{run_id}.ndjson"
    if not path.exists():
        return {"error": "report not found"}
    def _iter():
        with path.open('rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk
    return StreamingResponse(_iter(), media_type="application/x-ndjson", headers={"Content-Disposition": f"attachment; filename=import-{run_id}.ndjson"})


async def _process_import_with_ai(run_id: str, account_id: str):
    """Background task to process imported transactions with AI"""
    conn = get_conn()
    
    try:
        # Get transactions from this import run
        transactions = conn.execute("""
            SELECT t.id, t.description_norm, t.amount, t.posted_at
            FROM [transaction] t
            JOIN import_run ir ON ir.id = ?
            WHERE t.account_id = ?
            AND t.created_at >= ir.started_at
            ORDER BY t.posted_at DESC
        """, [run_id, account_id]).fetchall()
        
        if not transactions:
            return
        
        # Convert to dict format
        tx_dicts = []
        for tx in transactions:
            tx_dicts.append({
                'id': tx[0],
                'description': tx[1],
                'amount': tx[2],
                'posted_at': tx[3]
            })
        
        # Process with AI
        ai_processor = get_ai_import_processor()
        analysis = await ai_processor.process_import_batch(tx_dicts, account_id, run_id)
        
        # Store analysis results
        conn.execute("""
            UPDATE import_run 
            SET ai_analysis_complete = TRUE, ai_suggested_rules_count = ?
            WHERE id = ?
        """, [len(analysis.suggested_rules), run_id])
        # Run built-in detectors after AI analysis
        await _run_builtin_detectors(account_id)
        
    except Exception as e:
        # Log error in production
        print(f"AI import processing error: {e}")


async def _process_import_with_workflow(run_id: str, account_id: str):
    """Background task to process imported transactions with full AI workflow"""
    try:
        workflow_engine = get_workflow_engine()
        
        # Configure workflow for automated processing
        config = WorkflowConfig(
            enable_ai_enhancement=True,
            enable_auto_categorization=True,
            enable_duplicate_detection=True,
            enable_auto_merge_duplicates=False,  # Conservative: don't auto-merge
            ai_confidence_threshold=0.7,
            duplicate_confidence_threshold=0.9,
            auto_rule_creation=True,
            quality_threshold=0.6
        )
        
        # Run the full workflow
        progress = await workflow_engine.process_import_workflow(
            import_run_id=run_id,
            account_id=account_id,
            config=config
        )
        
        # Update import run with workflow results
        conn = get_conn()
        conn.execute("""
            UPDATE import_run 
            SET ai_workflow_id = ?, ai_analysis_complete = TRUE
            WHERE id = ?
        """, [progress.workflow_id, run_id])
        # Run built-in detectors after workflow completes
        await _run_builtin_detectors(account_id)
        
    except Exception as e:
        print(f"AI workflow processing error: {e}")


async def _run_builtin_detectors(account_id: str):
    """Run all detection pipelines in correct order post-import.

    Order: Zelle → Income → Adjustments → Transfers → P2P → Recurring
    Transfer and P2P MUST run before Recurring to exclude them from recurring patterns.
    """
    try:
        conn = get_conn()

        # 1. Zelle: scan and tag this account's transactions
        rows = conn.execute("SELECT id, description_norm FROM [transaction] WHERE account_id = ?", [account_id]).fetchall()
        tagged = 0
        for tx_id, desc in rows:
            info = parse_zelle_descriptor(desc or "")
            if not info:
                continue
            conn.execute("INSERT INTO transaction_tag (tx_id, tag) VALUES (?, ?) ON CONFLICT DO NOTHING", [tx_id, "zelle"])
            if info.get("direction"):
                conn.execute("UPDATE [transaction] SET zelle_direction = ? WHERE id = ?", [info["direction"], tx_id])
            if info.get("counterparty"):
                conn.execute("UPDATE [transaction] SET zelle_counterparty = ? WHERE id = ?", [info["counterparty"], tx_id])
            tagged += 1

        # 2. Income detection
        rows = conn.execute("SELECT id, posted_at, amount, description_norm FROM [transaction] WHERE account_id = ?", [account_id]).fetchall()
        records = [{"id": r[0], "posted_at": r[1], "amount": r[2], "description_norm": r[3]} for r in rows]
        for tx_id in mark_income(records):
            conn.execute("UPDATE [transaction] SET is_income = TRUE WHERE id = ?", [tx_id])

        # 3. Adjustments detection
        for tx_id in mark_adjustments(records):
            conn.execute("UPDATE [transaction] SET is_adjustment = TRUE WHERE id = ?", [tx_id])

        # 4. Transfer detection - BEFORE recurring to exclude from patterns
        try:
            from ...transfers import suggest_transfers_v2
            transfer_result = suggest_transfers_v2()
            print(f"Transfer detection: {transfer_result.get('created', 0)} pairs found")
        except Exception as transfer_err:
            print(f"Transfer detection error (non-fatal): {transfer_err}")

        # 5. Full P2P detection - BEFORE recurring to exclude from patterns
        try:
            from ...p2p_detection import run_p2p_detection
            p2p_result = run_p2p_detection(limit=10000)
            print(f"P2P detection: {p2p_result.get('detected', 0)} transactions detected")
        except Exception as p2p_err:
            print(f"P2P detection error (non-fatal): {p2p_err}")

        # 6. Recurring detection - AFTER transfers/P2P are marked
        try:
            from ...recurring import suggest_recurring
            suggest_result = suggest_recurring(min_occurrences=3)
            if suggest_result.get("candidates"):
                print(f"Recurring detection: found {len(suggest_result['candidates'])} candidates")
        except Exception as rec_err:
            print(f"Recurring detection error (non-fatal): {rec_err}")
    except Exception as e:
        print(f"Post-import detectors error: {e}")


@router.get("/{run_id}/ai-analysis")
async def get_import_ai_analysis(run_id: str):
    """Get AI analysis results for an import run"""
    conn = get_conn()
    
    # Get basic import run info
    run_info = conn.execute("""
        SELECT id, ai_enhanced_count, ai_avg_quality_score, ai_anomalies_detected, 
               ai_analysis_complete, ai_suggested_rules_count
        FROM import_run 
        WHERE id = ?
    """, [run_id]).fetchone()
    
    if not run_info:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Import run not found")
    
    # Get AI-enhanced transactions
    ai_transactions = conn.execute("""
        SELECT t.id, t.description_norm, t.ai_merchant_name, t.ai_confidence_score
        FROM [transaction] t
        JOIN import_run ir ON ir.id = ?
        WHERE t.ai_merchant_name IS NOT NULL
        AND t.created_at >= ir.started_at
        ORDER BY t.ai_confidence_score DESC
        LIMIT 20
    """, [run_id]).fetchall()
    
    return {
        "run_id": run_id,
        "ai_enhanced_count": run_info[1] or 0,
        "avg_quality_score": run_info[2] or 0.0,
        "anomalies_detected": run_info[3] or 0,
        "analysis_complete": bool(run_info[4]),
        "suggested_rules_count": run_info[5] or 0,
        "sample_ai_transactions": [
            {
                "id": tx[0],
                "original_description": tx[1],
                "ai_merchant_name": tx[2],
                "confidence": tx[3]
            }
            for tx in ai_transactions
        ]
    }


class RuleSuggestionRequest(BaseModel):
    run_id: str
    min_confidence: float = 0.7
    min_transaction_count: int = 3


@router.post("/suggest-rules")
async def suggest_rules_from_import(request: RuleSuggestionRequest):
    """Generate rule suggestions based on import AI analysis"""
    conn = get_conn()
    
    # Get AI-enhanced transactions from the run
    transactions = conn.execute("""
        SELECT t.description_norm, t.ai_merchant_name, tc.category_id, c.name as category_name
        FROM [transaction] t
        JOIN import_run ir ON ir.id = ?
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        WHERE t.ai_merchant_name IS NOT NULL
        AND t.ai_confidence_score >= ?
        AND t.created_at >= ir.started_at
    """, [request.run_id, request.min_confidence]).fetchall()
    
    # Analyze patterns
    merchant_patterns = {}
    for tx in transactions:
        merchant = tx[1]  # ai_merchant_name
        category_id = tx[2]
        category_name = tx[3]
        
        if merchant and category_id:
            if merchant not in merchant_patterns:
                merchant_patterns[merchant] = {}
            
            if category_id not in merchant_patterns[merchant]:
                merchant_patterns[merchant][category_id] = {
                    'category_name': category_name,
                    'count': 0
                }
            
            merchant_patterns[merchant][category_id]['count'] += 1
    
    # Generate rule suggestions
    suggested_rules = []
    for merchant, categories in merchant_patterns.items():
        # Find dominant category
        best_category = max(categories.items(), key=lambda x: x[1]['count'])
        category_id, category_info = best_category
        
        if category_info['count'] >= request.min_transaction_count:
            # Rules engine expects RulePredicate/RuleAction JSON:
            #  predicate: { description_regex, ... }
            #  action: { assign_category_id, ... }
            import re as _re
            words = [w for w in _re.split(r"\W+", (merchant or "").lower()) if w and not _re.search(r"\d", w)]
            pattern = "|".join(_re.escape(w) for w in words[:3]) if words else _re.escape((merchant or "").lower())
            suggested_rules.append({
                'priority': 100,
                'predicate': {
                    'description_regex': pattern
                },
                'action': {
                    'assign_category_id': category_id
                },
                'reasoning': f"Based on {category_info['count']} transactions from '{merchant}' categorized as '{category_info['category_name']}'",
                'transaction_count': category_info['count'],
                'merchant': merchant,
                'category_name': category_info['category_name']
            })
    
    # Sort by transaction count
    suggested_rules.sort(key=lambda r: r['transaction_count'], reverse=True)
    
    return {
        "run_id": request.run_id,
        "suggested_rules": suggested_rules[:10],  # Top 10
        "total_patterns": len(merchant_patterns)
    }
def _ensure_import_file_logical_hash(file_id: str) -> str | None:
    """Compute and persist a logical hash for an import_file based on its linked transactions.

    This provides stable duplicate detection even when original file bytes are unavailable.
    """
    from ...db import get_conn
    import hashlib
    conn = get_conn()
    # Ensure column exists
    try:
        conn.execute("ALTER TABLE import_file ADD COLUMN logical_hash TEXT")
    except Exception:
        pass
    rows = conn.execute(
        """
        SELECT t.posted_at, t.amount, COALESCE(t.description_norm, '')
        FROM [transaction] t
        JOIN transaction_ingest ti ON ti.tx_id = t.id
        WHERE ti.file_id = ?
        ORDER BY t.posted_at, t.amount, t.description_norm
        """,
        [file_id],
    ).fetchall()
    if not rows:
        try:
            # Still update to NULL
            conn.execute("UPDATE import_file SET logical_hash = NULL WHERE id = ?", [file_id])
        except Exception:
            pass
        return None
    h = hashlib.sha256()
    for d, amt, desc in rows:
        # Normalize values for stable hashing
        s = f"{str(d)[:10]}|{float(amt):.2f}|{desc}\n"
        h.update(s.encode('utf-8', errors='ignore'))
    digest = h.hexdigest()
    conn.execute("UPDATE import_file SET logical_hash = ? WHERE id = ?", [digest, file_id])
    return digest
@router.post("/backfill-hashes", dependencies=[Depends(require_admin)])
def backfill_import_file_hashes() -> dict:
    """Backfill logical hashes for existing import files that lack them.

    Also attempts to populate file hash where missing for CSV (using stored digest) and leaves others untouched.
    """
    from ...db import get_conn
    conn = get_conn()
    # Ensure column exists
    try:
        conn.execute("ALTER TABLE import_file ADD COLUMN logical_hash TEXT")
    except Exception:
        pass
    files = conn.execute("SELECT id FROM import_file").fetchall()
    updated = 0
    for (fid,) in files:
        try:
            d = _ensure_import_file_logical_hash(fid)
            if d:
                updated += 1
        except Exception:
            continue
    return {"updated_logical_hash": updated}
