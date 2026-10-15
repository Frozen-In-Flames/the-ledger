import os
import tempfile
import unittest

from tax import TaxCollector, compute_liability


class TestTaxCollector(unittest.TestCase):
    def test_bracket_math(self):
        due, _ = compute_liability(0)
        self.assertEqual(due, 0.0)
        due, _ = compute_liability(12000)
        self.assertEqual(due, 0.0)
        due, breakdown = compute_liability(50000)
        # 28,000 @10% = 2,800; 10,000 @20% = 2,000
        self.assertEqual(due, 4800.0)
        self.assertEqual(len(breakdown), 3)
        due, _ = compute_liability(150000)
        # 2,800 + 12,000 + 15,000
        self.assertEqual(due, 29800.0)

    def test_negative_income_rejected(self):
        with self.assertRaises(ValueError):
            compute_liability(-100)

    def test_file_and_total_collected(self):
        tmp = tempfile.mkdtemp()
        tc = TaxCollector(os.path.join(tmp, "returns.json"))
        r = tc.file_return("CIT-001", 50000, 2026)
        self.assertEqual(r["liability"], 4800.0)
        self.assertEqual(r["year"], 2026)
        tc.file_return("CIT-002", 150000, 2026)
        tc.file_return("CIT-003", 50000, 2025)
        self.assertEqual(tc.total_collected(2026), 4800.0 + 29800.0)
        self.assertEqual(tc.total_collected(),
                         4800.0 + 29800.0 + 4800.0)

    def test_persistence(self):
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "returns.json")
        TaxCollector(p).file_return("A", 20000, 2026)
        tc2 = TaxCollector(p)
        self.assertEqual(len(tc2.returns), 1)
        self.assertEqual(tc2.total_collected(2026), 800.0)  # 8k @10%


if __name__ == "__main__":
    unittest.main()
