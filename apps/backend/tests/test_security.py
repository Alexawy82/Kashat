import unittest
from kashat.security import redact


class TestSecurity(unittest.TestCase):
    def test_redact(self):
        s = "Account number: 1234 5678 9012 3456; token 999999999999"
        out = redact(s)
        self.assertNotIn("9012 3456", out)
        self.assertIn("***REDACTED***", out)


if __name__ == '__main__':
    unittest.main()

