import unittest
from kashat.normalization import normalize_description, parse_amount, parse_date, currency_or_default


class TestNormalization(unittest.TestCase):
    def test_normalize_description(self):
        self.assertEqual(normalize_description("  Starbucks  #1234  "), "starbucks #1234")
        self.assertEqual(normalize_description("-- ACME, INC. --"), "acme, inc")

    def test_parse_amount(self):
        self.assertEqual(parse_amount("10.00", None, None), 10.0)
        self.assertEqual(parse_amount(None, "10.00", None), 10.0)
        self.assertEqual(parse_amount(None, None, "10.00"), -10.0)
        self.assertEqual(parse_amount(None, "100", "30"), 70.0)

    def test_parse_date(self):
        self.assertEqual(str(parse_date("2024-04-01")), "2024-04-01")
        self.assertEqual(str(parse_date("04/01/2024")), "2024-04-01")

    def test_currency(self):
        self.assertEqual(currency_or_default("usd"), "USD")
        self.assertEqual(currency_or_default(None), "USD")


if __name__ == "__main__":
    unittest.main()

