"""Treasury: the books balance.

One job: every public dollar in and out is recorded, and the books always
balance. Double-entry journal persisted as JSON, fully auditable.

Conventions:
- Amounts are positive floats rounded to 2 decimals, in the nation's
  currency units (default label "NCU", configurable per Treasury).
- Every journal entry balances: sum(debits) == sum(credits).
- record_revenue: debit cash, credit revenue:<source>.
- record_expenditure: debit expense:<purpose>, credit cash.
"""

import datetime
import json
import os


def _today():
    return datetime.date.today().isoformat()


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Treasury:
    def __init__(self, path, currency="NCU"):
        self.path = path
        self.currency = currency
        self.entries = []
        self._next_id = 1
        self._load()

    # -- persistence -------------------------------------------------
    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                doc = json.load(f)
            self.entries = doc.get("entries", [])
            self._next_id = doc.get("next_id", len(self.entries) + 1)

    def _save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)),
                    exist_ok=True)
        with open(self.path, "w") as f:
            json.dump({"currency": self.currency,
                       "next_id": self._next_id,
                       "entries": self.entries}, f, indent=2)

    # -- journal ------------------------------------------------------
    def _post(self, date, memo, lines):
        """lines: list of (account, debit, credit). Must balance."""
        debit = round(sum(l[1] for l in lines), 2)
        credit = round(sum(l[2] for l in lines), 2)
        if debit != credit:
            raise ValueError(
                "entry does not balance: debits %s != credits %s"
                % (debit, credit))
        if debit <= 0:
            raise ValueError("entry amount must be positive")
        entry = {
            "id": self._next_id,
            "date": date or _today(),
            "memo": memo,
            "lines": [{"account": a, "debit": round(d, 2),
                       "credit": round(c, 2)} for a, d, c in lines],
            "recorded_at": _now(),
        }
        self._next_id += 1
        self.entries.append(entry)
        self._save()
        return entry

    def record_revenue(self, source, amount, date=None, note=""):
        amount = round(float(amount), 2)
        if amount <= 0:
            raise ValueError("revenue amount must be positive")
        return self._post(date, note or ("revenue: %s" % source), [
            ("cash", amount, 0.0),
            ("revenue:%s" % source, 0.0, amount),
        ])

    def record_expenditure(self, recipient, amount, purpose, date=None,
                           note=""):
        amount = round(float(amount), 2)
        if amount <= 0:
            raise ValueError("expenditure amount must be positive")
        if self.cash_balance() < amount:
            raise ValueError(
                "insufficient cash: balance %s, attempted %s"
                % (self.cash_balance(), amount))
        return self._post_with_recipient(date, recipient, purpose, amount,
                                         note)

    def _post_with_recipient(self, date, recipient, purpose, amount, note):
        entry = self._post(date, note or ("paid %s: %s" % (recipient,
                                                          purpose)), [
            ("expense:%s" % purpose, amount, 0.0),
            ("cash", 0.0, amount),
        ])
        entry["recipient"] = recipient
        self._save()
        return entry

    # -- reads ---------------------------------------------------------
    def account_balance(self, account):
        bal = 0.0
        for e in self.entries:
            for l in e["lines"]:
                if l["account"] == account:
                    bal += l["debit"] - l["credit"]
        return round(bal, 2)

    def cash_balance(self):
        return self.account_balance("cash")

    def totals(self):
        revenue = expenditure = 0.0
        for e in self.entries:
            for l in e["lines"]:
                if l["account"].startswith("revenue:"):
                    revenue += l["credit"]
                elif l["account"].startswith("expense:"):
                    expenditure += l["debit"]
        return {"revenue": round(revenue, 2),
                "expenditure": round(expenditure, 2),
                "cash": round(revenue - expenditure, 2)}

    def expenditures(self):
        """Public spending records, for the SpendingPublisher feed."""
        out = []
        for e in self.entries:
            if "recipient" in e:
                amount = sum(l["debit"] for l in e["lines"])
                purpose = next(
                    (l["account"].split(":", 1)[1] for l in e["lines"]
                     if l["account"].startswith("expense:")), "")
                out.append({"date": e["date"], "recipient": e["recipient"],
                            "purpose": purpose, "amount": amount,
                            "entry_id": e["id"]})
        return out

    # -- audit ----------------------------------------------------------
    def audit(self):
        """Verify the books. Returns a list of findings; empty is clean."""
        findings = []
        seen_ids = set()
        for e in self.entries:
            if e["id"] in seen_ids:
                findings.append("duplicate entry id %s" % e["id"])
            seen_ids.add(e["id"])
            debit = round(sum(l["debit"] for l in e["lines"]), 2)
            credit = round(sum(l["credit"] for l in e["lines"]), 2)
            if debit != credit:
                findings.append("entry %s does not balance (%s vs %s)"
                                % (e["id"], debit, credit))
            if debit <= 0:
                findings.append("entry %s has non-positive amount" % e["id"])
        totals = self.totals()
        if totals["cash"] != self.cash_balance():
            findings.append("cash account disagrees with revenue minus "
                            "expenditure")
        if totals["cash"] < 0:
            findings.append("negative cash balance: %s" % totals["cash"])
        return findings
