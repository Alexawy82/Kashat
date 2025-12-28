from __future__ import annotations

import json
from datetime import datetime, UTC
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Query

from ...db import get_conn


router = APIRouter(prefix="/workflows", tags=["workflows"])


def _load_state(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:
        return {}


@router.get("")
def list_workflows(prefix: Optional[str] = Query(None)):
    conn = get_conn()
    if prefix is not None and not isinstance(prefix, str):
        prefix = None
    if prefix:
        rows = conn.execute(
            "SELECT id FROM workflow_state WHERE id LIKE ? ORDER BY updated_ts DESC",
            [f"{prefix}%"],
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id FROM workflow_state ORDER BY updated_ts DESC"
        ).fetchall()
    return {"keys": [r[0] for r in rows]}


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT state_json FROM workflow_state WHERE id = ?",
        [workflow_id],
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="workflow not found")
    payload = _load_state(row[0])
    if isinstance(payload, dict) and not payload.get("id"):
        payload["id"] = workflow_id
    return payload


@router.put("/{workflow_id}")
def upsert_workflow(workflow_id: str, payload: dict = Body(...)):
    conn = get_conn()
    now = datetime.now(UTC)
    if isinstance(payload, dict) and not payload.get("id"):
        payload["id"] = workflow_id
    wf_type = payload.get("type") if isinstance(payload, dict) else None
    status = payload.get("status") if isinstance(payload, dict) else None
    state_json = json.dumps(payload)
    conn.execute(
        """
        INSERT INTO workflow_state (id, type, status, state_json, created_ts, updated_ts)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            type = EXCLUDED.type,
            status = EXCLUDED.status,
            state_json = EXCLUDED.state_json,
            updated_ts = EXCLUDED.updated_ts
        """,
        [workflow_id, wf_type, status, state_json, now, now],
    )
    return payload


@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM workflow_state WHERE id = ?", [workflow_id])
    return {"ok": True, "id": workflow_id}


@router.delete("")
def clear_workflows():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM workflow_state").fetchone()[0]
    conn.execute("DELETE FROM workflow_state")
    return {"ok": True, "cleared": int(count)}
