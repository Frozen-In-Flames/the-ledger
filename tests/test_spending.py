import json
import os
import tempfile
import unittest

import spending
from spending import SpendingPublisher
from ledger import Treasury


class TestSpendingPublisher(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.t = Treasury(os.path.join(self.tmp, "ledger.json"))
        self.t.record_revenue("income-tax", 100000.0, date="2026-01-01")
        self.t.record_expenditure("Road Authority", 25000.0, "roads",
                                  date="2026-02-01")
        self.pub = SpendingPublisher(
            self.t, os.path.join(self.tmp, "spending_cache.json"))

    def test_feed_publishes_ledger_expenditures(self):
        doc = self.pub.feed()
        self.assertIn("label", doc)
        self.assertEqual(len(doc["records"]), 1)
        r = doc["records"][0]
        self.assertEqual(r["recipient"], "Road Authority")
        self.assertEqual(r["amount"], 25000.0)

    def test_federal_top_falls_back_to_labeled_cache(self):
        cache = {"source": "USAspending.gov", "fiscal_year": 2025,
                 "pulled_at": "2026-01-01T00:00:00+00:00",
                 "rows": [{"name": "Acme Corp", "amount": 123.0}]}
        with open(os.path.join(self.tmp, "spending_cache.json"), "w") as f:
            json.dump(cache, f)
        orig = spending.us_federal_top_recipients
        spending.us_federal_top_recipients = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("network down"))
        try:
            rows, prov = self.pub.federal_top(2025, limit=5)
        finally:
            spending.us_federal_top_recipients = orig
        self.assertEqual(rows, cache["rows"])
        self.assertTrue(prov.startswith("cached:2026-01-01"))

    def test_federal_top_raises_when_no_cache(self):
        orig = spending.us_federal_top_recipients
        spending.us_federal_top_recipients = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("network down"))
        try:
            with self.assertRaises(RuntimeError):
                self.pub.federal_top(2025)
        finally:
            spending.us_federal_top_recipients = orig

    def test_recipient_totals_honest_missing_on_failure(self):
        orig = spending._post_json_retry
        spending._post_json_retry = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("network down"))
        try:
            by_year, matched, method = spending.us_federal_recipient_totals(
                "Nobody Corp", fiscal_years=[2025])
        finally:
            spending._post_json_retry = orig
        self.assertEqual(by_year, {2025: None})
        self.assertEqual(matched, [])

    def test_distinctive_tokens(self):
        toks = spending.distinctive_tokens("Lockheed Martin Corporation")
        self.assertEqual(toks, ["lockheed", "martin"])


if __name__ == "__main__":
    unittest.main()
