import os
import tempfile
import unittest

from mint import Mint


class TestMint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.m = Mint(os.path.join(self.tmp, "mint.json"))

    def test_insufficient_data(self):
        self.assertEqual(self.m.stability()["verdict"],
                         "insufficient data")
        self.m.record(1000.0, 100.0, date="2026-01-01")
        self.assertEqual(self.m.stability()["verdict"],
                         "insufficient data")

    def test_stable_band(self):
        self.m.record(1000.0, 100.0, date="2025-01-01")
        self.m.record(1030.0, 102.0, date="2026-01-01")
        s = self.m.stability()
        self.assertEqual(s["verdict"], "stable")
        self.assertAlmostEqual(s["annualized_inflation"], 0.02, places=2)

    def test_unstable_band(self):
        self.m.record(1000.0, 100.0, date="2025-01-01")
        self.m.record(1500.0, 110.0, date="2026-01-01")
        s = self.m.stability()
        self.assertEqual(s["verdict"], "unstable")
        self.assertAlmostEqual(s["annualized_money_supply_growth"], 0.50,
                               places=2)

    def test_very_stable_band(self):
        self.m.record(1000.0, 100.0, date="2025-01-01")
        self.m.record(1005.0, 100.5, date="2026-01-01")
        self.assertEqual(self.m.stability()["verdict"], "very stable")

    def test_negative_values_rejected(self):
        with self.assertRaises(ValueError):
            self.m.record(-1.0, 100.0)
        with self.assertRaises(ValueError):
            self.m.record(1000.0, 0.0)

    def test_persistence(self):
        self.m.record(1000.0, 100.0, date="2026-01-01", source="census")
        m2 = Mint(os.path.join(self.tmp, "mint.json"))
        self.assertEqual(len(m2.observations), 1)
        self.assertEqual(m2.observations[0]["source"], "census")


if __name__ == "__main__":
    unittest.main()
