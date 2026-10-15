import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import ledger_cli


def run_cli(tmp, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = ledger_cli.main(["--data-dir", tmp] + list(args))
    return code, buf.getvalue()


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_treasury_flow(self):
        code, out = run_cli(self.tmp, "treasury", "revenue",
                            "--source", "income-tax", "--amount", "50000")
        self.assertEqual(code, 0)
        self.assertIn("recorded revenue", out)
        code, out = run_cli(self.tmp, "treasury", "expense",
                            "--recipient", "Clinic", "--amount", "12000",
                            "--purpose", "health")
        self.assertIn("recorded expenditure", out)
        code, out = run_cli(self.tmp, "treasury", "balance")
        self.assertIn("38,000.00", out)
        code, out = run_cli(self.tmp, "treasury", "audit")
        self.assertIn("audit clean", out)

    def test_tax_flow(self):
        code, out = run_cli(self.tmp, "tax", "compute", "--income", "50000")
        self.assertEqual(code, 0)
        self.assertIn("4,800.00", out)
        code, out = run_cli(self.tmp, "tax", "file", "--filer", "CIT-1",
                            "--income", "50000", "--year", "2026")
        self.assertIn("filed CIT-1", out)
        code, out = run_cli(self.tmp, "tax", "collected", "--year", "2026")
        self.assertIn("4,800.00", out)

    def test_spending_feed(self):
        run_cli(self.tmp, "treasury", "revenue", "--source", "t",
                "--amount", "20000")
        run_cli(self.tmp, "treasury", "expense", "--recipient", "Library",
                "--amount", "5000", "--purpose", "books")
        code, out = run_cli(self.tmp, "spending", "feed")
        self.assertEqual(code, 0)
        self.assertIn("Library", out)
        self.assertIn("5,000.00", out)

    def test_mint_flow(self):
        run_cli(self.tmp, "mint", "record", "--supply", "1000",
                "--price-index", "100", "--date", "2025-01-01")
        run_cli(self.tmp, "mint", "record", "--supply", "1030",
                "--price-index", "102", "--date", "2026-01-01")
        code, out = run_cli(self.tmp, "mint", "stability")
        self.assertEqual(code, 0)
        self.assertIn("STABLE", out)


if __name__ == "__main__":
    unittest.main()
