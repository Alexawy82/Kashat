from __future__ import annotations

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Query, Body

from ...db import get_conn


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def logs(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
):
    conn = get_conn()
    where = []
    params = []
    if entity_type:
        where.append("entity_type = ?")
        params.append(entity_type)
    if entity_id:
        where.append("entity_id = ?")
        params.append(entity_id)
    if action:
        where.append("action = ?")
        params.append(action)
    if start:
        where.append("ts >= ?")
        params.append(start)
    if end:
        where.append("ts <= ?")
        params.append(end)
    wh = " WHERE " + " AND ".join(where) if where else ""
    rows = conn.execute(
        f"SELECT id, entity_type, entity_id, action, payload_json, ts, actor FROM event_log {wh} ORDER BY ts DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.post("/client")
def client_event(event: str = Body(...), payload: dict | None = Body(None), actor: str = Body("client")):
    """Record a lightweight client-side telemetry event in the audit log.

    The payload is stored as JSON for debugging/analytics. Avoid PII.
    """
    import uuid, json
    from datetime import datetime, UTC
    conn = get_conn()
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), "client", "telemetry", event, json.dumps(payload or {}), datetime.now(UTC), actor],
    )
    return {"ok": True}
