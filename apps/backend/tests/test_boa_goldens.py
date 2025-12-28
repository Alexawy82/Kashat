import glob
import os
import unittest
import csv
from difflib import unified_diff


def _has_pdfplumber():
    try:
        import pdfplumber  # noqa: F401
        return True
    except Exception:
        return False


@unittest.skipUnless(_has_pdfplumber(), "pdfplumber not installed; skipping BoA goldens")
class TestBOAGoldens(unittest.TestCase):
    def test_boa_pdfs_to_goldens(self):
        from kashat.parse.banks.boa_v2025 import parse_boa_pdf
        pdfs = sorted(glob.glob('bank/*.pdf'))
        self.assertGreaterEqual(len(pdfs), 1, 'No PDFs found in bank/*.pdf')
        total_rows = 0
        total_matched = 0
        for pdf in pdfs:
            with open(pdf, 'rb') as fh:
                data = fh.read()
            res = parse_boa_pdf(data)
            total_rows += len(res.rows)
            golden_path = os.path.join('data/fixtures/boa_goldens', f"{os.path.splitext(os.path.basename(pdf))[0]}.csv")
            if not os.path.exists(golden_path):
                self.skipTest(f"Missing golden: {golden_path}")
            with open(golden_path, 'r') as f:
                rdr = csv.DictReader(f)
                golden_rows = list(rdr)
            # Compare approx row counts (>=99%)
            if len(golden_rows) == 0:
                continue
            ratio = len(res.rows) / len(golden_rows)
            self.assertGreaterEqual(ratio, 0.99, f"Row capture below 99% for {pdf}: got {len(res.rows)} vs {len(golden_rows)}")
            # Human-readable diffs for mismatches
            # Create lightweight normalized lists: date|desc|amount
            def shape(rows):
                def _row(r):
                    return [str(r.get('posted_at') or r.get('date')), (r.get('description') or r.get('description_norm') or '').strip().lower(), f"{float(r.get('amount') or 0):.2f}"]
                return ["|".join(_row(r)) for r in rows]
            parser_list = shape(res.rows)
            golden_list = shape(golden_rows)
            # Only compare up to min length for diff preview
            if len(parser_list) != len(golden_list):
                diff = "\n".join(unified_diff(golden_list[:50], parser_list[:50], fromfile='golden', tofile='parser', lineterm=''))
                print(diff)
            total_matched += min(len(res.rows), len(golden_rows))
            # Header/meta checks
            self.assertIn('opening_balance', res.meta)
            self.assertIn('closing_balance', res.meta)
            self.assertIn('account_last4', res.meta)
            self.assertIn('period_start', res.meta)
            self.assertIn('period_end', res.meta)
            if 'closing_balance_calc' in res.meta:
                self.assertAlmostEqual(res.meta['closing_balance'], res.meta['closing_balance_calc'], places=2)
        # Sanity on totals if any goldens present
        if total_rows > 0:
            self.assertGreater(total_matched, 0)


if __name__ == '__main__':
    unittest.main()
