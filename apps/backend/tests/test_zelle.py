import unittest
from kashat.detect.zelle import parse_zelle_descriptor


class TestZelle(unittest.TestCase):
    def test_directions(self):
        self.assertEqual(parse_zelle_descriptor("Zelle payment from John Doe")['direction'], 'from')
        self.assertEqual(parse_zelle_descriptor("ZELLE TO Jane Roe")['direction'], 'to')
        self.assertIsNone(parse_zelle_descriptor("STARBUCKS"))


if __name__ == "__main__":
    unittest.main()

