from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class RulePredicate:
    description_regex: Optional[str] = None
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    account_ids: Optional[List[str]] = None
    sign: Optional[str] = None  # 'credit' | 'debit' | None

    @staticmethod
    def from_json(d: Dict[str, Any]) -> "RulePredicate":
        return RulePredicate(
            description_regex=d.get("description_regex"),
            amount_min=d.get("amount_min"),
            amount_max=d.get("amount_max"),
            account_ids=d.get("account_ids"),
            sign=d.get("sign"),
        )


@dataclass
class RuleAction:
    assign_category_id: Optional[str] = None
    payee_alias: Optional[str] = None
    set_business: Optional[bool] = None

    @staticmethod
    def from_json(d: Dict[str, Any]) -> "RuleAction":
        return RuleAction(
            assign_category_id=d.get("assign_category_id"),
            payee_alias=d.get("payee_alias"),
            set_business=d.get("set_business"),
        )


def predicate_to_sql(predicate: RulePredicate) -> Tuple[str, List[Any]]:
    where: List[str] = []
    params: List[Any] = []
    if predicate.account_ids:
        where.append("account_id IN (" + ",".join(["?"] * len(predicate.account_ids)) + ")")
        params.extend(predicate.account_ids)
    if predicate.amount_min is not None:
        where.append("amount >= ?")
        params.append(predicate.amount_min)
    if predicate.amount_max is not None:
        where.append("amount <= ?")
        params.append(predicate.amount_max)
    if predicate.sign == "credit":
        where.append("amount > 0")
    elif predicate.sign == "debit":
        where.append("amount < 0")
    if predicate.description_regex:
        # DuckDB regexp: regexp_matches(string, pattern)
        where.append("regexp_matches(description_norm, ?)")
        params.append(predicate.description_regex)
    return (" AND ".join(where) if where else "1=1", params)


def parse_rule(predicate_json: str, action_json: str) -> Tuple[RulePredicate, RuleAction]:
    pred = RulePredicate.from_json(json.loads(predicate_json))
    act = RuleAction.from_json(json.loads(action_json))
    return pred, act


def validate_rule(predicate: RulePredicate, action: RuleAction) -> Optional[str]:
    if action.assign_category_id is None and action.payee_alias is None and action.set_business is None:
        return "action must assign a category or set a payee_alias or set_business"
    if predicate.sign not in (None, "credit", "debit"):
        return "predicate.sign must be 'credit', 'debit', or omitted"
    # quick regex check
    if predicate.description_regex:
        try:
            re.compile(predicate.description_regex)
        except re.error as e:
            return f"invalid description_regex: {e}"
    return None


def apply_all_rules() -> Dict[str, Any]:
    """Apply all enabled rules to matching transactions.

    Returns a summary of how many transactions were updated by each rule.
    """
    from .db import get_conn
    import uuid
    from datetime import datetime, timezone

    conn = get_conn()

    # Get all enabled rules ordered by priority
    rows = conn.execute(
        "SELECT id, priority, predicate_json, action_json FROM rule WHERE enabled = true ORDER BY priority ASC"
    ).fetchall()

    results = {
        "rules_applied": 0,
        "transactions_updated": 0,
        "by_rule": []
    }

    now = datetime.now(timezone.utc)

    for rule_id, priority, predicate_json, action_json in rows:
        pred = RulePredicate.from_json(json.loads(predicate_json))
        act = RuleAction.from_json(json.loads(action_json))

        where, params = predicate_to_sql(pred)

        # Find matching transaction IDs that don't already have a category
        tx_ids = [r[0] for r in conn.execute(
            f"""SELECT t.id FROM [transaction] t
                LEFT JOIN transaction_category tc ON t.id = tc.tx_id
                WHERE tc.tx_id IS NULL AND {where}""",
            params
        ).fetchall()]

        applied = 0
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
            if act.payee_alias:
                conn.execute("UPDATE [transaction] SET payee_alias = ? WHERE id = ?", [act.payee_alias, tx_id])

            conn.execute(
                "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [str(uuid.uuid4()), [transaction], tx_id, "rule_apply", json.dumps({"rule_id": rule_id, "category_id": act.assign_category_id}), now, "system"],
            )
            applied += 1

        if applied > 0:
            results["rules_applied"] += 1
            results["transactions_updated"] += applied
            results["by_rule"].append({
                "rule_id": rule_id,
                "priority": priority,
                "transactions_updated": applied
            })

    return results
