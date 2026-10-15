"""SpendingPublisher: anyone can see where the money went.

One job: publish public spending as an open feed. Two sources:

1. The nation's own Treasury ledger (primary): every recorded expenditure,
   published verbatim.
2. The United States federal feed (reference implementation): live-first
   pulls from USAspending.gov's spending_by_category/recipient endpoint,
   free and keyless. Cache is fallback only, always labeled with its date.

Every figure carries source and date. Estimates are never presented
as exacts.
"""

import datetime
import json
import os
import re
import time
import urllib.request

USASPENDING = "https://api.usaspending.gov"
USER_AGENT = ("NationKit the-ledger/0.1.0 "
              "spending-publisher contact@example.com")

FISCAL_YEARS = [2023, 2024, 2025]

FEED_LABEL = ("Public spending feed: every recorded Treasury expenditure, "
              "published verbatim with entry id and date.")
US_LABEL = ("USAspending.gov recipient totals: federal obligated award "
            "dollars matched by recipient name. Federal only; excludes "
            "state and local spending.")

_STOPWORDS = {
    "inc", "incorporated", "corp", "corporation", "co", "company",
    "companies", "ltd", "limited", "llc", "lp", "plc", "sa", "ag", "nv",
    "group", "holdings", "holding", "systems", "system", "technologies",
    "technology", "tech", "international", "global", "industries",
    "industry", "enterprises", "enterprise", "partners", "brands", "foods",
    "products", "services", "the", "and", "&", "of",
}


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def distinctive_tokens(name):
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    toks = [w for w in words if w not in _STOPWORDS and len(w) > 1]
    return toks or words


def _post_json(url, payload, timeout=90):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _post_json_retry(url, payload, tries=3, timeout=120):
    last = None
    for i in range(tries):
        try:
            return _post_json(url, payload, timeout=timeout)
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


def us_federal_recipient_totals(name, fiscal_years=None):
    """{fy: obligated_usd} for a recipient name via USAspending.

    Returns (by_year, matched_names, match_method). A year that fails
    records None: honest missing, never zero.
    """
    fiscal_years = fiscal_years or FISCAL_YEARS
    tokens = distinctive_tokens(name)
    by_year = {}
    matched = set()
    for fy in fiscal_years:
        payload = {
            "filters": {
                "recipient_search_text": [name],
                "award_type_codes": ["A", "B", "C", "D"],
                "time_period": [{
                    "start_date": "%d-10-01" % (fy - 1),
                    "end_date": "%d-09-30" % fy,
                }],
            },
            "limit": 50,
            "page": 1,
        }
        try:
            d = _post_json_retry(
                USASPENDING + "/api/v2/search/spending_by_category/recipient/",
                payload)
        except Exception:
            by_year[fy] = None
            continue
        total = 0.0
        for row in d.get("results", []):
            rname = (row.get("name") or "").lower()
            if all(t in rname for t in tokens):
                total += float(row.get("amount") or 0)
                matched.add(row.get("name") or "")
        by_year[fy] = round(total, 2)
        time.sleep(0.3)
    return by_year, sorted(matched), "recipient-name token match"


def us_federal_top_recipients(fiscal_year, limit=10):
    """Top federal recipients for one fiscal year, live from USAspending."""
    payload = {
        "filters": {
            "award_type_codes": ["A", "B", "C", "D"],
            "time_period": [{
                "start_date": "%d-10-01" % (fiscal_year - 1),
                "end_date": "%d-09-30" % fiscal_year,
            }],
        },
        "limit": limit,
        "page": 1,
    }
    d = _post_json_retry(
        USASPENDING + "/api/v2/search/spending_by_category/recipient/",
        payload)
    out = []
    for row in d.get("results", []):
        out.append({"name": row.get("name"),
                    "amount": float(row.get("amount") or 0)})
    return out


class SpendingPublisher:
    """Publishes the nation's own spending, with the US federal feed as a
    live reference implementation."""

    def __init__(self, treasury, cache_path):
        self.treasury = treasury
        self.cache_path = cache_path

    # -- nation's own feed -------------------------------------------
    def feed(self, limit=None):
        rows = self.treasury.expenditures()
        rows.sort(key=lambda r: (r["date"], r["entry_id"]), reverse=True)
        doc = {"source": "national treasury ledger",
               "label": FEED_LABEL,
               "published_at": _now(),
               "records": rows[:limit] if limit else rows}
        return doc

    # -- US federal reference feed (live-first) ------------------------
    def _load_cache(self):
        if os.path.exists(self.cache_path):
            with open(self.cache_path) as f:
                return json.load(f)
        return None

    def _save_cache(self, doc):
        os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)),
                    exist_ok=True)
        with open(self.cache_path, "w") as f:
            json.dump(doc, f, indent=2)

    def federal_top(self, fiscal_year, limit=10, refresh=False):
        """Live-first top recipients. Returns (rows, provenance).

        Tries the live pull first; on failure falls back to the labeled
        cache. refresh=True forces a fresh pull and rewrites the cache,
        still falling back to cache if the network fails.
        """
        try:
            rows = us_federal_top_recipients(fiscal_year, limit)
            doc = {"source": "USAspending.gov",
                   "label": US_LABEL,
                   "fiscal_year": fiscal_year,
                   "pulled_at": _now(),
                   "rows": rows}
            self._save_cache(doc)
            return rows, "live"
        except Exception:
            pass
        cached = self._load_cache()
        if cached and cached.get("fiscal_year") == fiscal_year:
            return cached["rows"][:limit], \
                "cached:%s" % cached.get("pulled_at", "unknown")
        raise RuntimeError("live pull failed and no cache available")

    def federal_recipient(self, name, fiscal_years=None):
        by_year, matched, method = us_federal_recipient_totals(
            name, fiscal_years)
        return {"source": "USAspending.gov",
                "label": US_LABEL,
                "recipient": name,
                "pulled_at": _now(),
                "by_year": by_year,
                "matched_names": matched,
                "match_method": method}
