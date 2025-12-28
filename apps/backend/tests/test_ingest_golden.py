import unittest
from kashat.ingest_csv import normalize_row


class TestIngestGolden(unittest.TestCase):
    def test_sample_bank_row(self):
        row = {"date": "2024-04-01", "description": "STARBUCKS #1234", "amount": "-4.50", "currency": "usd"}
        posted_at, desc_norm, amount, curr = normalize_row(row)
        self.assertEqual(str(posted_at), "2024-04-01")
        self.assertEqual(desc_norm, "starbucks #1234")
        self.assertAlmostEqual(amount, -4.50, places=2)
        self.assertEqual(curr, "USD")

    def test_sample_bank2_row_credit_debit(self):
        row = {"Date": "04/02/2024", "Description": "Transfer From Checking", "credit": "200.00", "debit": "", "Currency": "USD"}
        posted_at, desc_norm, amount, curr = normalize_row(row)
        self.assertEqual(str(posted_at), "2024-04-02")
        self.assertEqual(desc_norm, "transfer from checking")
        self.assertAlmostEqual(amount, 200.00, places=2)
        self.assertEqual(curr, "USD")

    def test_sample_bank3_mixed_columns(self):
        row = {"date": "2024-04-10", "description": "GROCERY MART", "credit": "", "debit": "45.10", "currency": "usd"}
        posted_at, desc_norm, amount, curr = normalize_row(row)
        self.assertEqual(str(posted_at), "2024-04-10")
        self.assertEqual(desc_norm, "grocery mart")
        self.assertAlmostEqual(amount, -45.10, places=2)
        self.assertEqual(curr, "USD")


if __name__ == "__main__":
    unittest.main()
