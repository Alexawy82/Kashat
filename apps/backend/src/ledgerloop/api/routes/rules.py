from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from datetime import datetime, UTC
from ...db import get_conn
from ...rules import RulePredicate, RuleAction, predicate_to_sql, validate_rule, apply_all_rules


router = APIRouter(prefix="/rules", tags=["rules"])


class RuleCreate(BaseModel):
    priority: int
    predicate: Dict[str, Any]
    action: Dict[str, Any]
    enabled: bool = True


class RuleUpdate(BaseModel):
    priority: Optional[int] = None
    predicate: Optional[Dict[str, Any]] = None
    action: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class RulesImportBody(BaseModel):
    rules: List[RuleCreate]


@router.get("")
def list_rules():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, priority, predicate_json, action_json, enabled FROM rule ORDER BY priority ASC"
    ).fetchall()
    cols = [c[0] for c in conn.description]
    items = [dict(zip(cols, r)) for r in rows]
    for it in items:
        it["predicate"] = json.loads(it.pop("predicate_json"))
        it["action"] = json.loads(it.pop("action_json"))
    return items


@router.post("")
def create_rule(body: RuleCreate):
    pred = RulePredicate.from_json(body.predicate)
    act = RuleAction.from_json(body.action)
    err = validate_rule(pred, act)
    if err:
        raise HTTPException(status_code=400, detail=err)
    conn = get_conn()
    rid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO rule (id, priority, predicate_json, action_json, enabled) VALUES (?, ?, ?, ?, ?)",
        [rid, body.priority, json.dumps(body.predicate), json.dumps(body.action), body.enabled],
    )
    return {"id": rid, **body.dict()}


@router.patch("/{rule_id}")
def update_rule(rule_id: str, body: RuleUpdate):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, priority, predicate_json, action_json, enabled FROM rule WHERE id = ?",
        [rule_id],
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="rule not found")

    _, cur_priority, cur_pred_json, cur_act_json, cur_enabled = row
    cur_pred = json.loads(cur_pred_json)
    cur_act = json.loads(cur_act_json)

    fields_set = getattr(body, "model_fields_set", None)
    if fields_set is None:
        fields_set = getattr(body, "__fields_set__", set())

    next_priority = cur_priority
    if "priority" in fields_set:
        if body.priority is None:
            raise HTTPException(status_code=400, detail="priority is required")
        next_priority = int(body.priority)

    next_pred = cur_pred
    if "predicate" in fields_set:
        if body.predicate is None:
            raise HTTPException(status_code=400, detail="predicate is required")
        next_pred = body.predicate

    next_act = cur_act
    if "action" in fields_set:
        if body.action is None:
            raise HTTPException(status_code=400, detail="action is required")
        next_act = body.action

    next_enabled = bool(cur_enabled)
    if "enabled" in fields_set:
        if body.enabled is None:
            raise HTTPException(status_code=400, detail="enabled is required")
        next_enabled = bool(body.enabled)

    pred = RulePredicate.from_json(next_pred)
    act = RuleAction.from_json(next_act)
    err = validate_rule(pred, act)
    if err:
        raise HTTPException(status_code=400, detail=err)

    conn.execute(
        "UPDATE rule SET priority = ?, predicate_json = ?, action_json = ?, enabled = ? WHERE id = ?",
        [next_priority, json.dumps(next_pred), json.dumps(next_act), next_enabled, rule_id],
    )
    try:
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                str(uuid.uuid4()),
                "rule",
                rule_id,
                "update",
                json.dumps(
                    {
                        "priority": next_priority,
                        "predicate": next_pred,
                        "action": next_act,
                        "enabled": next_enabled,
                    }
                ),
                datetime.now(UTC),
                "user",
            ],
        )
    except Exception:
        pass
    return {
        "id": rule_id,
        "priority": next_priority,
        "predicate": next_pred,
        "action": next_act,
        "enabled": next_enabled,
    }


@router.delete("/{rule_id}")
def delete_rule(rule_id: str):
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM rule WHERE id = ?", [rule_id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="rule not found")
    conn.execute("DELETE FROM rule WHERE id = ?", [rule_id])
    try:
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), "rule", rule_id, "delete", json.dumps({}), datetime.now(UTC), "user"],
        )
    except Exception:
        pass
    return {"deleted": True}


@router.get("/export")
def export_rules():
    conn = get_conn()
    rows = conn.execute("SELECT priority, predicate_json, action_json, enabled FROM rule ORDER BY priority").fetchall()
    return {
        "rules": [
            {
                "priority": r[0],
                "predicate": json.loads(r[1]),
                "action": json.loads(r[2]),
                "enabled": bool(r[3])
            }
            for r in rows
        ]
    }


@router.post("/import")
def import_rules(body: RulesImportBody | None = None):
    conn = get_conn()
    data = None
    if body and body.rules:
        data = body.dict()
    else:
        # load seed
        import json as _json
        from pathlib import Path
        seed = Path("data/seed/seed_rules.json")
        if not seed.exists():
            return {"imported": 0, "error": "no rules provided and seed not found"}
        data = _json.loads(seed.read_text())
    count = 0
    for r in data.get("rules", []):
        pred = RulePredicate.from_json(r["predicate"]) if isinstance(r["predicate"], dict) else RulePredicate.from_json(r["predicate"])
        act = RuleAction.from_json(r["action"]) if isinstance(r["action"], dict) else RuleAction.from_json(r["action"])
        err = validate_rule(pred, act)
        if err:
            continue
        rid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO rule (id, priority, predicate_json, action_json, enabled) VALUES (?, ?, ?, ?, ?)",
            [rid, r["priority"], json.dumps(r["predicate"]), json.dumps(r["action"]), r.get("enabled", True)],
        )
        count += 1
    return {"imported": count}


class RulePreview(BaseModel):
    predicate: Dict[str, Any]
    limit: int = 20


@router.post("/preview")
def preview_rule(body: RulePreview):
    pred = RulePredicate.from_json(body.predicate)
    conn = get_conn()
    where, params = predicate_to_sql(pred)
    rows = conn.execute(
        f"SELECT id, account_id, posted_at, amount, currency, description_norm FROM [transaction] WHERE {where} ORDER BY posted_at DESC LIMIT ?",
        params + [body.limit],
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.post("/{rule_id}/apply")
def apply_rule(rule_id: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, predicate_json, action_json, enabled FROM rule WHERE id = ?",
        [rule_id],
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="rule not found")
    _, predicate_json, action_json, enabled = row
    if not enabled:
        return {"applied": 0, "skipped": True}
    pred = RulePredicate.from_json(json.loads(predicate_json))
    act = RuleAction.from_json(json.loads(action_json))

    where, params = predicate_to_sql(pred)
    # Find matching transaction IDs
    tx_ids = [r[0] for r in conn.execute(
        f"SELECT id FROM [transaction] WHERE {where}", params
    ).fetchall()]

    applied = 0
    now = datetime.now(UTC)
    for tx_id in tx_ids:
        # category assignment
        if act.assign_category_id is not None:
            conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [tx_id])
            conn.execute(
                "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
                [tx_id, act.assign_category_id, f"rule:{rule_id}"],
            )
        # set business flag if requested
        if act.set_business is not None:
            conn.execute("UPDATE [transaction] SET is_business = ? WHERE id = ?", [bool(act.set_business), tx_id])
        # set payee alias if provided
        try:
            if getattr(act, "payee_alias", None):
                conn.execute("UPDATE [transaction] SET payee_alias = ? WHERE id = ?", [act.payee_alias, tx_id])
        except Exception:
            pass
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), [transaction], tx_id, "rule_apply", json.dumps({"rule_id": rule_id, "category_id": act.assign_category_id}), now, "system"],
        )
        applied += 1

    return {"applied": applied}


@router.get("/suggestions")
def suggest_rules(limit: int = 20):
    """Suggest simple regex-based rules for frequent uncategorized merchants.

    Returns entries like:
      { payee: str, count: int, debit_ratio: float, recommended_predicate: {...}, example: str }
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT COALESCE(t.payee_alias, t.description_norm) AS payee,
               COUNT(*) AS cnt,
               SUM(CASE WHEN t.amount < 0 THEN 1 ELSE 0 END) AS debits,
               SUM(CASE WHEN t.amount > 0 THEN 1 ELSE 0 END) AS credits,
               MIN(t.description_norm) as example
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        WHERE tc.tx_id IS NULL
        GROUP BY 1
        ORDER BY cnt DESC
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    cols = [c[0] for c in conn.description]
    items = [dict(zip(cols, r)) for r in rows]
    out = []
    import re
    for it in items:
        payee = (it.get("payee") or "").strip()
        # build a light regex from first words without numbers
        words = [w for w in re.split(r"\W+", payee.lower()) if w and not re.search(r"\d", w)]
        regex = "|".join(words[:3]) if words else payee.lower()
        debit_ratio = 0.0
        total = float((it.get("debits") or 0) + (it.get("credits") or 0))
        if total:
            debit_ratio = float((it.get("debits") or 0)) / total
        pred = {"description_regex": regex}
        # if mostly debits, constrain to debits
        if debit_ratio >= 0.6:
            pred["amount_max"] = 0
        out.append({
            "payee": payee,
            "count": int(it.get("cnt") or 0),
            "debit_ratio": debit_ratio,
            "recommended_predicate": pred,
            "example": it.get("example") or payee,
        })
    return out


@router.post("/apply-all")
def apply_all():
    """Apply all enabled rules to uncategorized transactions.

    Returns a summary of how many rules matched and how many transactions were updated.
    """
    return apply_all_rules()
