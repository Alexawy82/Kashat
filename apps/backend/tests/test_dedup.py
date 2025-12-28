import unittest
from datetime import date
from kashat.dedup import tx_fingerprint


class TestDedup(unittest.TestCase):
    def test_fingerprint_deterministic(self):
        fp1 = tx_fingerprint("acc1", date(2024, 4, 1), -10.5, "starbucks")
        fp2 = tx_fingerprint("acc1", date(2024, 4, 1), 10.5, "starbucks")
        self.assertEqual(fp1, fp2)  # uses abs(amount)
        fp3 = tx_fingerprint("acc1", date(2024, 4, 2), 10.5, "starbucks")
        self.assertNotEqual(fp2, fp3)


if __name__ == "__main__":
    unittest.main()

