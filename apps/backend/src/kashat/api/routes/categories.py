from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ...db import get_conn
from ...ai_smart_categorization import process_ai_category_suggestion


router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None


@router.get("")
def list_categories():
    conn = get_conn()
    rows = conn.execute("SELECT id, name, parent_id FROM category ORDER BY name").fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.post("")
def create_category(body: CategoryCreate):
    conn = get_conn()
    # First, avoid duplicates: try to find existing by case-insensitive name
    row = conn.execute(
        "SELECT id, name, parent_id FROM category WHERE LOWER(name) = ?",
        [body.name.strip().lower()],
    ).fetchone()
    if row:
        # Return existing record to prevent duplication
        return {"id": row[0], "name": row[1], "parent_id": row[2]}

    # As a smarter fallback, try AI-aware dedup/mapping (synonyms, fuzzy)
    try:
        result = process_ai_category_suggestion(body.name, confidence=0.9, auto_create=False)
        if result and result.category_id:
            return {"id": result.category_id, "name": result.category_name, "parent_id": result.parent_id}
    except Exception:
        # If AI helper not available, continue to create
        pass

    cid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO category (id, name, parent_id) VALUES (?, ?, ?)",
        [cid, body.name, body.parent_id],
    )
    return {"id": cid, "name": body.name, "parent_id": body.parent_id}


@router.get("/{category_id}/usage")
def category_usage(category_id: str):
    conn = get_conn()
    # Children count
    child = conn.execute("SELECT COUNT(1) FROM category WHERE parent_id = ?", [category_id]).fetchone()[0]
    # Transaction references
    tx = conn.execute("SELECT COUNT(1) FROM transaction_category WHERE category_id = ?", [category_id]).fetchone()[0]
    return {"children": int(child or 0), "tx_refs": int(tx or 0)}


@router.delete("/{category_id}")
def delete_category(category_id: str):
    conn = get_conn()
    # Check exists
    row = conn.execute("SELECT id, parent_id FROM category WHERE id = ?", [category_id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Category not found")
    # Block if children
    child = conn.execute("SELECT 1 FROM category WHERE parent_id = ? LIMIT 1", [category_id]).fetchone()
    if child:
        raise HTTPException(status_code=400, detail="Cannot delete category with children.")
    # Block if referenced
    ref = conn.execute("SELECT 1 FROM transaction_category WHERE category_id = ? LIMIT 1", [category_id]).fetchone()
    if ref:
        raise HTTPException(status_code=400, detail="Category in use; use merge.")
    conn.execute("DELETE FROM category WHERE id = ?", [category_id])
    # Audit log
    try:
        import uuid as _uuid
        import json as _json
        from datetime import datetime as _dt, UTC as _UTC
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(_uuid.uuid4()), "category", category_id, "delete", _json.dumps({}), _dt.now(_UTC), "user"],
        )
    except Exception:
        pass
    return {"deleted": True}


@router.patch("/{category_id}")
def update_category(category_id: str, body: CategoryUpdate):
    conn = get_conn()
    row = conn.execute("SELECT id, name, parent_id FROM category WHERE id = ?", [category_id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Category not found")

    current_name, current_parent_id = row[1], row[2]

    fields_set = getattr(body, "model_fields_set", None)
    if fields_set is None:
        fields_set = getattr(body, "__fields_set__", set())

    new_name = current_name
    if "name" in fields_set and body.name is not None:
        candidate = body.name.strip()
        if not candidate:
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        dupe = conn.execute(
            "SELECT 1 FROM category WHERE LOWER(name) = ? AND id != ? LIMIT 1",
            [candidate.lower(), category_id],
        ).fetchone()
        if dupe:
            raise HTTPException(status_code=400, detail="Category name already exists")
        new_name = candidate

    new_parent_id = current_parent_id
    if "parent_id" in fields_set:
        new_parent_id = body.parent_id

    if new_parent_id == category_id:
        raise HTTPException(status_code=400, detail="Category cannot be its own parent")

    if new_parent_id:
        parent = conn.execute("SELECT id, parent_id FROM category WHERE id = ?", [new_parent_id]).fetchone()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")
        # Prevent cycles: traverse up from proposed parent; category_id must not appear.
        cur = parent
        visited: List[str] = []
        while cur and cur[1]:
            visited.append(cur[1])
            if cur[1] == category_id:
                raise HTTPException(status_code=400, detail="Invalid parent: would create cycle")
            cur = conn.execute("SELECT id, parent_id FROM category WHERE id = ?", [cur[1]]).fetchone()

    conn.execute(
        "UPDATE category SET name = ?, parent_id = ? WHERE id = ?",
        [new_name, new_parent_id, category_id],
    )
    try:
        import uuid as _uuid
        import json as _json
        from datetime import datetime as _dt, UTC as _UTC

        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                str(_uuid.uuid4()),
                "category",
                category_id,
                "update",
                _json.dumps({"name": new_name, "parent_id": new_parent_id}),
                _dt.now(_UTC),
                "user",
            ],
        )
    except Exception:
        pass

    return {"id": category_id, "name": new_name, "parent_id": new_parent_id}


class MergeBody(BaseModel):
    from_id: str
    to_id: str


@router.post("/merge")
def merge_categories(body: MergeBody):
    if body.from_id == body.to_id:
        raise HTTPException(status_code=400, detail="from_id and to_id must differ")
    conn = get_conn()
    # Ensure both exist
    f = conn.execute("SELECT id, parent_id FROM category WHERE id = ?", [body.from_id]).fetchone()
    t = conn.execute("SELECT id, parent_id FROM category WHERE id = ?", [body.to_id]).fetchone()
    if not f or not t:
        raise HTTPException(status_code=404, detail="Category not found")
    # Disallow merging parent into child (to_id is descendant of from_id)
    cur = t
    visited: List[str] = []
    while cur and cur[1]:
        visited.append(cur[1])
        if cur[1] == body.from_id:
            raise HTTPException(status_code=400, detail="Cannot merge parent into child")
        cur = conn.execute("SELECT id, parent_id FROM category WHERE id = ?", [cur[1]]).fetchone()

    # Move transaction_category references
    # Avoid duplicates by deleting existing to_id refs first, then updating
    conn.execute("DELETE FROM transaction_category WHERE category_id = ? AND tx_id IN (SELECT tx_id FROM transaction_category WHERE category_id = ?)", [body.to_id, body.from_id])
    conn.execute("UPDATE transaction_category SET category_id = ? WHERE category_id = ?", [body.to_id, body.from_id])
    # Update AI category mappings to preserve links (respect FK)
    try:
        conn.execute("UPDATE ai_category_mapping SET category_id = ? WHERE category_id = ?", [body.to_id, body.from_id])
    except Exception:
        pass
    # Update predictive analytics tables that reference categories (FKs)
    for table in (
        "seasonal_patterns",
        "predictions",
        "smart_insights",
        "financial_goals",
        "spending_patterns",
    ):
        try:
            conn.execute(f"UPDATE {table} SET category_id = ? WHERE category_id = ?", [body.to_id, body.from_id])
        except Exception:
            # Table may not exist or column may be NULL-able; best-effort
            pass
    # Delete the from category
    conn.execute("DELETE FROM category WHERE id = ?", [body.from_id])
    # Audit log
    try:
        import uuid as _uuid
        import json as _json
        from datetime import datetime as _dt, UTC as _UTC
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(_uuid.uuid4()), "category", body.from_id, "merge", _json.dumps({"to_id": body.to_id}), _dt.now(_UTC), "user"],
        )
    except Exception:
        pass
    return {"merged": True, "from_id": body.from_id, "to_id": body.to_id}
