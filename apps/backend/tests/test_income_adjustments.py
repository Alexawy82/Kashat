import unittest
from datetime import date, timedelta
from kashat.detect.income import mark_income
from kashat.detect.adjustments import mark_adjustments


class TestIncomeAdjustments(unittest.TestCase):
    def test_income_biweekly_or_keywords(self):
        base = date(2024, 1, 1)
        txs = [
            {"id": "t1", "posted_at": base, "amount": 1000.0, "description_norm": "employer payroll"},
            {"id": "t2", "posted_at": base + timedelta(days=14), "amount": 1000.0, "description_norm": "employer payroll"},
            {"id": "t3", "posted_at": base + timedelta(days=28), "amount": 1000.0, "description_norm": "employer payroll"},
            {"id": "t4", "posted_at": base + timedelta(days=1), "amount": -10.0, "description_norm": "coffee"},
        ]
        ids = mark_income(txs)
        self.assertIn("t1", ids)
        self.assertIn("t2", ids)
        self.assertIn("t3", ids)

    def test_adjustments(self):
        txs = [
            {"id": "a1", "posted_at": date(2024, 4, 1), "amount": 5.0, "description_norm": "cashback credit"},
            {"id": "a2", "posted_at": date(2024, 4, 2), "amount": -3.0, "description_norm": "fee"},
        ]
        ids = mark_adjustments(txs)
        self.assertIn("a1", ids)


if __name__ == "__main__":
    unittest.main()

