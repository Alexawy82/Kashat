import unittest
import json
from kashat.rules import RulePredicate, predicate_to_sql, validate_rule, RuleAction, parse_rule, apply_all_rules


class TestRules(unittest.TestCase):
    def test_predicate_to_sql(self):
        pred = RulePredicate(description_regex="starbucks|peet's", amount_min=-20, amount_max=0, sign="debit", account_ids=["a1", "a2"])
        where, params = predicate_to_sql(pred)
        self.assertIn("account_id IN (?,?)", where)
        self.assertIn("amount >= ?", where)
        self.assertIn("amount <= ?", where)
        self.assertIn("amount < 0", where)
        self.assertIn("regexp_matches(description_norm, ?)", where)
        self.assertEqual(params[0:2], ["a1", "a2"])

    def test_validate_rule(self):
        pred = RulePredicate(description_regex="(")
        act = RuleAction(assign_category_id=None)
        err = validate_rule(pred, act)
        self.assertIsNotNone(err)
        pred2 = RulePredicate(sign="invalid")
        err2 = validate_rule(pred2, RuleAction(assign_category_id="cat1"))
        self.assertIsNotNone(err2)


def test_parse_rule():
    pred_json = json.dumps({"description_regex": "coffee", "amount_min": -10})
    act_json = json.dumps({"assign_category_id": "cat1", "set_business": True})
    pred, act = parse_rule(pred_json, act_json)
    assert pred.description_regex == "coffee"
    assert pred.amount_min == -10
    assert act.assign_category_id == "cat1"
    assert act.set_business is True


def test_apply_all_rules_assigns_category(db_conn, seed_transactions, sample_transactions):
    seed_transactions(sample_transactions)
    db_conn.execute("INSERT OR IGNORE INTO category (id, name) VALUES ('cat1', 'Food')")
    db_conn.execute(
        "INSERT INTO rule (id, priority, predicate_json, action_json, enabled) VALUES (?, ?, ?, ?, ?)",
        [
            "r1",
            1,
            json.dumps({"description_regex": "coffee", "amount_min": -20, "amount_max": 0}),
            json.dumps({"assign_category_id": "cat1", "set_business": True}),
            True,
        ],
    )

    result = apply_all_rules()
    assert result["rules_applied"] == 1
    assert result["transactions_updated"] == 1

    row = db_conn.execute(
        "SELECT category_id FROM transaction_category WHERE tx_id = 't1'"
    ).fetchone()
    assert row is not None
    assert row[0] == "cat1"

    is_business = db_conn.execute(
        "SELECT is_business FROM transaction WHERE id = 't1'"
    ).fetchone()[0]
    assert bool(is_business) is True


if __name__ == "__main__":
    unittest.main()
