"""TaxCollector: revenue comes in.

One job: compute what is owed and file the return. The bracket schedule is
the new nation's default and is fully configurable; every figure it produces
is labeled with the schedule used.

Default schedule (annual income in national currency units):
  0%   on the first 12,000
  10%  on 12,001 - 40,000
  20%  on 40,001 - 100,000
  30%  above 100,000
"""

import datetime
import json
import os

DEFAULT_BRACKETS = [
    (12000.0, 0.00),
    (40000.0, 0.10),
    (100000.0, 0.20),
    (float("inf"), 0.30),
]

SCHEDULE_LABEL = ("default national schedule v1: 0%/10%/20%/30% at "
                  "12k/40k/100k")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def compute_liability(income, brackets=None):
    """Return (total_due, breakdown). breakdown is a list of
    (bracket_top, rate, taxable_in_bracket, due_in_bracket)."""
    income = float(income)
    if income < 0:
        raise ValueError("income cannot be negative")
    brackets = brackets or DEFAULT_BRACKETS
    total = 0.0
    breakdown = []
    lower = 0.0
    for top, rate in brackets:
        if income <= lower:
            break
        taxable = min(income, top) - lower
        due = round(taxable * rate, 2)
        total += due
        breakdown.append({"bracket_top": None if top == float("inf") else top,
                          "rate": rate,
                          "taxable": round(taxable, 2),
                          "due": due})
        lower = top
    return round(total, 2), breakdown


class TaxCollector:
    def __init__(self, path, brackets=None, schedule_label=None):
        self.path = path
        self.brackets = brackets or DEFAULT_BRACKETS
        self.schedule_label = schedule_label or SCHEDULE_LABEL
        self.returns = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                self.returns = json.load(f).get("returns", [])

    def _save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)),
                    exist_ok=True)
        with open(self.path, "w") as f:
            json.dump({"schedule": self.schedule_label,
                       "returns": self.returns}, f, indent=2)

    def compute(self, income):
        return compute_liability(income, self.brackets)

    def file_return(self, filer_id, income, year):
        due, breakdown = self.compute(income)
        record = {
            "filer_id": filer_id,
            "income": round(float(income), 2),
            "year": int(year),
            "liability": due,
            "breakdown": breakdown,
            "schedule": self.schedule_label,
            "filed_at": _now(),
        }
        self.returns.append(record)
        self._save()
        return record

    def total_collected(self, year=None):
        total = 0.0
        for r in self.returns:
            if year is None or r["year"] == int(year):
                total += r["liability"]
        return round(total, 2)
