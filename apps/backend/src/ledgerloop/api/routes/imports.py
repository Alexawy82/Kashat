from __future__ import annotations

import uuid
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from typing import Optional
from pydantic import BaseModel

from ...db import get_conn
from ...ingest_csv import import_csv_upload
from ...ingest_pdf import import_pdf_upload
from ...ai_import import get_ai_import_processor
from ...ai_workflow import get_workflow_engine, WorkflowConfig
from ...detect.income import mark_income
from ...detect.adjustments import mark_adjustments
from ...detect.zelle import parse_zelle_descriptor


router = APIRouter(prefix="/import", tags=["import"])


def _ensure_account(account_id: Optional[str]) -> str:
    conn = get_conn()
    if account_id:
        row = conn.execute("SELECT id FROM account WHERE id = ?", [account_id]).fetchone()
        if row:
            return account_id
    # create default account
    new_id = account_id or str(uuid.uuid4())
    conn.execute(
        "INSERT OR IGNORE INTO account (id, name, type, currency) VALUES (?, ?, ?, ?)",
        [new_id, "Imported Account", "checking", "USD"],
    )
    return new_id


@router.get("/runs")
def list_import_runs(limit: int = 20):
    """List recent import runs with info, file counts, tx count and covered period."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT ir.id, ir.started_at, COUNT(DISTINCT f.id) AS files,
               MIN(t.posted_at) AS period_start,
               MAX(t.posted_at) AS period_end,
               COUNT(DISTINCT ti.tx_id) AS tx_count
        FROM import_run ir
        LEFT JOIN import_file f ON f.run_id = ir.id
        LEFT JOIN transaction_ingest ti ON ti.run_id = ir.id
        LEFT JOIN transaction t ON t.id = ti.tx_id
        GROUP BY ir.id, ir.started_at
        ORDER BY ir.started_at DESC
        LIMIT ?
        """,
        [limit],
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
        LEFT JOIN transaction t ON t.id = ti.tx_id
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
        SELECT date_trunc('month', t.posted_at) AS month,
               SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spend,
               SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS income,
               SUM(t.amount) AS net,
               COUNT(*) AS count
        FROM transaction t
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
        _delete_in("transaction", "id", tx_ids)
        _delete_in("transaction_ingest", "tx_id", tx_ids)
    # delete raw_records of files
    file_ids = [r[0] for r in conn.execute("SELECT id FROM import_file WHERE run_id = ?", [run_id]).fetchall()]
    if file_ids:
        placeholders = ",".join(["?"] * len(file_ids))
        conn.execute(f"DELETE FROM raw_record WHERE file_id IN ({placeholders})", file_ids)
        conn.execute(f"DELETE FROM import_file WHERE id IN ({placeholders})", file_ids)
    # delete run
    conn.execute("DELETE FROM import_run WHERE id = ?", [run_id])
    return {"deleted": {"transactions": len(tx_ids), "files": len(file_ids), "run": run_id}}


@router.post("/runs/{run_id}/reprocess")
def reprocess_run(run_id: str, background_tasks: BackgroundTasks, account_id: Optional[str] = None, enable_workflow: bool = True):
    conn = get_conn()
    # Try to infer account from one transaction
    row = conn.execute(
        "SELECT t.account_id FROM transaction t JOIN transaction_ingest ti ON ti.tx_id = t.id WHERE ti.run_id = ? LIMIT 1",
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
async def import_bulk(
    files: list[UploadFile] = File(...),
    account_id: Optional[str] = Form(None),
    enable_ai: bool = Form(True),
    enable_workflow: bool = Form(True),
    background_tasks: BackgroundTasks = None,
):
    acc_id = _ensure_account(account_id)
    # Create a run and process each file under it
    import uuid as _uuid
    from datetime import datetime as _dt
    conn = get_conn()
    run_id = str(_uuid.uuid4())
    conn.execute(
        "INSERT INTO import_run (id, started_at, source, user_note) VALUES (?, ?, ?, ?)",
        [run_id, _dt.utcnow(), "upload:bulk", f"{len(files)} files"],
    )
    summary = []
    total_inserted = 0
    total_deduped = 0
    total_raw = 0
    for uf in files:
        data = await uf.read()
        file_id = str(_uuid.uuid4())
        name = uf.filename or "upload"
        if name.lower().endswith(".csv"):
            res = import_csv_upload(data, name, acc_id, run_id=run_id, file_id=file_id)
        elif name.lower().endswith(".pdf"):
            res = import_pdf_upload(data, name, acc_id, run_id=run_id, file_id=file_id)
        else:
            res = {"error": "unsupported file type", "file": name}
        summary.append({"file": name, **{k:v for k,v in res.items() if k != 'file_id'}})
        total_inserted += int(res.get("inserted", 0) or 0)
        total_deduped += int(res.get("deduped", 0) or 0)
        total_raw += int(res.get("raw", 0) or 0)
    # Queue AI processing if enabled and any records were inserted
    if enable_ai and total_inserted > 0 and background_tasks:
        if enable_workflow:
            background_tasks.add_task(_process_import_with_workflow, run_id, acc_id)
        else:
            background_tasks.add_task(_process_import_with_ai, run_id, acc_id)
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
async def import_csv(
    file: UploadFile = File(...),
    account_id: Optional[str] = Form(None),
    enable_ai: bool = Form(True),
    enable_workflow: bool = Form(True),
    background_tasks: BackgroundTasks = None,
):
    acc_id = _ensure_account(account_id)
    data = await file.read()
    result = import_csv_upload(data, file.filename, acc_id)
    
    # Add AI processing if enabled and import was successful
    if enable_ai and result.get('inserted', 0) > 0:
        run_id = result.get('run_id')
        if run_id and background_tasks:
            if enable_workflow:
                # Use full workflow
                background_tasks.add_task(_process_import_with_workflow, run_id, acc_id)
            else:
                # Use basic AI processing
                background_tasks.add_task(_process_import_with_ai, run_id, acc_id)
    
    return {"account_id": acc_id, "ai_processing": enable_ai, "workflow_enabled": enable_workflow, **result}


@router.post("/pdf")
async def import_pdf(
    file: UploadFile = File(...),
    account_id: Optional[str] = Form(None),
    enable_ai: bool = Form(True),
    enable_workflow: bool = Form(True),
    background_tasks: BackgroundTasks = None,
):
    acc_id = _ensure_account(account_id)
    data = await file.read()
    result = import_pdf_upload(data, file.filename, acc_id)
    
    # Add AI processing if enabled and import was successful
    if enable_ai and result.get('inserted', 0) > 0:
        run_id = result.get('run_id')
        if run_id and background_tasks:
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
            FROM transaction t
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
    """Mark Zelle/income/adjustments post-import for cleaner analytics."""
    try:
        conn = get_conn()
        # Zelle: scan and tag this account's transactions
        rows = conn.execute("SELECT id, description_norm FROM transaction WHERE account_id = ?", [account_id]).fetchall()
        tagged = 0
        for tx_id, desc in rows:
            info = parse_zelle_descriptor(desc or "")
            if not info:
                continue
            conn.execute("INSERT OR IGNORE INTO transaction_tag (tx_id, tag) VALUES (?, ?)", [tx_id, "zelle"])
            if info.get("direction"):
                conn.execute("UPDATE transaction SET zelle_direction = ? WHERE id = ?", [info["direction"], tx_id])
            if info.get("counterparty"):
                conn.execute("UPDATE transaction SET zelle_counterparty = ? WHERE id = ?", [info["counterparty"], tx_id])
            tagged += 1
        # Income
        rows = conn.execute("SELECT id, posted_at, amount, description_norm FROM transaction WHERE account_id = ?", [account_id]).fetchall()
        records = [{"id": r[0], "posted_at": r[1], "amount": r[2], "description_norm": r[3]} for r in rows]
        for tx_id in mark_income(records):
            conn.execute("UPDATE transaction SET is_income = TRUE WHERE id = ?", [tx_id])
        # Adjustments
        for tx_id in mark_adjustments(records):
            conn.execute("UPDATE transaction SET is_adjustment = TRUE WHERE id = ?", [tx_id])
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
        FROM transaction t
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
        FROM transaction t
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
            suggested_rules.append({
                'priority': 100,
                'predicate': {
                    'op': 'contains',
                    'field': 'description',
                    'value': merchant.lower()
                },
                'action': {
                    'type': 'set_category',
                    'category_id': category_id
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
