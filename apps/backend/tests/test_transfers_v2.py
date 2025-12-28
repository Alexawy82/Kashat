import unittest
from datetime import date
from kashat.transfers import _parse_ob


class TestTransfersV2(unittest.TestCase):
    def test_parse_ob(self):
        self.assertEqual(_parse_ob('Online Banking transfer from SAV 3454')['direction'], 'from')
        self.assertEqual(_parse_ob('ONLINE BANKING TRANSFER TO CHK 1234')['last4'], '1234')
        self.assertIsNone(_parse_ob('Starbucks coffee'))


if __name__ == '__main__':
    unittest.main()

