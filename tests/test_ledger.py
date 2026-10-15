import json
import os
import tempfile
import unittest

from ledger import Treasury


class TestTreasury(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.t = Treasury(os.path.join(self.tmp, "ledger.json"))

    def test_revenue_and_expenditure_balance(self):
        self.t.record_revenue("income-tax", 100000.0, date="2026-01-15")
        self.t.record_expenditure("Road Authority", 40000.0, "roads",
                                  date="2026-02-01")
        t = self.t.totals()
        self.assertEqual(t["revenue"], 100000.0)
        self.assertEqual(t["expenditure"], 40000.0)
        self.assertEqual(t["cash"], 60000.0)
        self.assertEqual(self.t.cash_balance(), 60000.0)

    def test_expenditure_beyond_cash_rejected(self):
        self.t.record_revenue("income-tax", 1000.0)
        with self.assertRaises(ValueError):
            self.t.record_expenditure("Someone", 2000.0, "things")

    def test_negative_amounts_rejected(self):
        with self.assertRaises(ValueError):
            self.t.record_revenue("x", -5.0)
        self.t.record_revenue("x", 100.0)
        with self.assertRaises(ValueError):
            self.t.record_expenditure("y", 0.0, "z")

    def test_audit_clean(self):
        self.t.record_revenue("income-tax", 50000.0, date="2026-01-01")
        self.t.record_expenditure("Clinic", 20000.0, "health",
                                  date="2026-03-01")
        self.assertEqual(self.t.audit(), [])

    def test_audit_catches_tampering(self):
        self.t.record_revenue("income-tax", 50000.0)
        self.t.entries[0]["lines"][0]["debit"] = 1.0
        findings = self.t.audit()
        self.assertTrue(any("does not balance" in f for f in findings))

    def test_expenditures_feed(self):
        self.t.record_revenue("income-tax", 9000.0)
        self.t.record_expenditure("Library", 3000.0, "books")
        feed = self.t.expenditures()
        self.assertEqual(len(feed), 1)
        self.assertEqual(feed[0]["recipient"], "Library")
        self.assertEqual(feed[0]["purpose"], "books")
        self.assertEqual(feed[0]["amount"], 3000.0)

    def test_persistence(self):
        self.t.record_revenue("income-tax", 7000.0, date="2026-05-05")
        t2 = Treasury(os.path.join(self.tmp, "ledger.json"))
        self.assertEqual(t2.totals()["revenue"], 7000.0)
        self.assertEqual(len(t2.entries), 1)


if __name__ == "__main__":
    unittest.main()
