import unittest
import os
import tempfile


def _has_duckdb():
    try:
        import duckdb  # noqa: F401
        return True
    except Exception:
        return False


def _has_pdfplumber():
    try:
        import pdfplumber  # noqa: F401
        return True
    except Exception:
        return False


@unittest.skipUnless(_has_duckdb() and _has_pdfplumber(), "requires duckdb and pdfplumber")
class TestAnalyticsReconcile(unittest.TestCase):
    def test_statement_totals_reconcile(self):
        import importlib
        import re
        from pathlib import Path
        from kashat.db import close as db_close, get_conn
        from kashat.parse.banks.boa_v2025 import parse_boa_pdf

        # Fresh DB
        tmp = tempfile.mkdtemp(prefix="ll_recon_")
        os.environ["LEDGERLOOP_DATA_DIR"] = tmp
        db_close()
        import kashat.db as dbmod
        importlib.reload(dbmod)

        # Parse statement and extract rows
        pdf_path = next((p for p in ["bank/eStmt_2025-01-10.pdf", "bank/eStmt_2025-02-07.pdf"] if Path(p).exists()), None)
        self.assertIsNotNone(pdf_path, "No bank PDF found for reconciliation test")
        res = parse_boa_pdf(Path(pdf_path).read_bytes())

        conn = get_conn()
        # Ensure account exists for FK
        conn.execute("INSERT OR IGNORE INTO account (id, name, type, currency) VALUES ('acc1','Test','checking','USD')")
        # Insert rows as transactions (include transfers for reconciliation)
        for r in res.rows:
            conn.execute(
                "INSERT INTO transaction (id, account_id, posted_at, amount, currency, description_norm, external_id, fingerprint, source_raw_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                [
                    os.urandom(16).hex(),
                    "acc1",
                    r["posted_at"],
                    float(r["amount"]),
                    "USD",
                    r.get("description_norm") or r.get("description") or "",
                    None,
                    os.urandom(8).hex(),
                    None,
                ],
            )

        # Compute sums from DB (include transfers/adjustments)
        income = conn.execute("SELECT COALESCE(SUM(CASE WHEN amount>0 THEN amount ELSE 0 END),0) FROM transaction").fetchone()[0]
        debits = conn.execute("SELECT COALESCE(SUM(CASE WHEN amount<0 THEN -amount ELSE 0 END),0) FROM transaction").fetchone()[0]

        # Parse summary totals from page 1
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            text = (pdf.pages[0].extract_text() or "")
        dep_m = re.search(r"Deposits and other additions\s+\$?([\d,]+\.\d{2})", text)
        wdr_m = re.search(r"Withdrawals and other subtractions\s+\-?\$?([\d,]+\.\d{2})", text)
        self.assertIsNotNone(dep_m, "Deposits total not found in statement header")
        self.assertIsNotNone(wdr_m, "Withdrawals total not found in statement header")
        dep_total = float(dep_m.group(1).replace(",", ""))
        wdr_total = float(wdr_m.group(1).replace(",", ""))

        self.assertAlmostEqual(income, dep_total, places=2)
        self.assertAlmostEqual(debits, wdr_total, places=2)


if __name__ == "__main__":
    unittest.main()
