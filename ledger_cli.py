#!/usr/bin/env python3
"""the-ledger CLI: Treasury core for a new nation.

Subcommands:
  treasury revenue --source S --amount A [--date D] [--note N]
  treasury expense --recipient R --amount A --purpose P [--date D] [--note N]
  treasury balance
  treasury audit
  tax compute --income N
  tax file --filer ID --income N --year Y
  tax collected [--year Y]
  spending feed [--limit N]
  spending federal --fiscal-year FY [--limit N] [--refresh]
  spending recipient --name NAME
  mint record --supply N --price-index N [--date D] [--source S]
  mint stability

Global: --data-dir DIR (default: data/)
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ledger import Treasury
from tax import TaxCollector, SCHEDULE_LABEL
from spending import SpendingPublisher
from mint import Mint


def _usd(v, suffix=" NCU"):
    return "$%s%s" % (f"{v:,.2f}", suffix) if isinstance(v, (int, float)) \
        else "n/a"


def _pct(v):
    return "%s%%" % round(v * 100, 2) if isinstance(v, (int, float)) else "n/a"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ledger",
                                 description="the-ledger: Treasury core")
    ap.add_argument("--data-dir", default="data",
                    help="directory for ledger data files")
    sub = ap.add_subparsers(dest="group", required=True)

    # treasury ---------------------------------------------------------
    tr = sub.add_parser("treasury")
    trsub = tr.add_subparsers(dest="cmd", required=True)
    p = trsub.add_parser("revenue")
    p.add_argument("--source", required=True)
    p.add_argument("--amount", required=True, type=float)
    p.add_argument("--date")
    p.add_argument("--note", default="")
    p = trsub.add_parser("expense")
    p.add_argument("--recipient", required=True)
    p.add_argument("--amount", required=True, type=float)
    p.add_argument("--purpose", required=True)
    p.add_argument("--date")
    p.add_argument("--note", default="")
    trsub.add_parser("balance")
    trsub.add_parser("audit")

    # tax ---------------------------------------------------------------
    tx = sub.add_parser("tax")
    txsub = tx.add_subparsers(dest="cmd", required=True)
    p = txsub.add_parser("compute")
    p.add_argument("--income", required=True, type=float)
    p = txsub.add_parser("file")
    p.add_argument("--filer", required=True)
    p.add_argument("--income", required=True, type=float)
    p.add_argument("--year", required=True, type=int)
    p = txsub.add_parser("collected")
    p.add_argument("--year", type=int)

    # spending ------------------------------------------------------------
    sp = sub.add_parser("spending")
    spsub = sp.add_subparsers(dest="cmd", required=True)
    p = spsub.add_parser("feed")
    p.add_argument("--limit", type=int)
    p = spsub.add_parser("federal")
    p.add_argument("--fiscal-year", required=True, type=int)
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--refresh", action="store_true")
    p = spsub.add_parser("recipient")
    p.add_argument("--name", required=True)

    # mint ------------------------------------------------------------------
    mn = sub.add_parser("mint")
    mnsub = mn.add_subparsers(dest="cmd", required=True)
    p = mnsub.add_parser("record")
    p.add_argument("--supply", required=True, type=float)
    p.add_argument("--price-index", required=True, type=float)
    p.add_argument("--date")
    p.add_argument("--source", default="")
    mnsub.add_parser("stability")

    args = ap.parse_args(argv)
    dd = args.data_dir
    treasury = Treasury(os.path.join(dd, "ledger.json"))
    taxman = TaxCollector(os.path.join(dd, "returns.json"))
    publisher = SpendingPublisher(treasury,
                                  os.path.join(dd, "spending_cache.json"))
    mint = Mint(os.path.join(dd, "mint.json"))

    if args.group == "treasury":
        if args.cmd == "revenue":
            e = treasury.record_revenue(args.source, args.amount,
                                        args.date, args.note)
            print("recorded revenue entry %d: %s from %s"
                  % (e["id"], _usd(args.amount), args.source))
        elif args.cmd == "expense":
            e = treasury.record_expenditure(args.recipient, args.amount,
                                            args.purpose, args.date,
                                            args.note)
            print("recorded expenditure entry %d: %s to %s (%s)"
                  % (e["id"], _usd(args.amount), args.recipient,
                     args.purpose))
        elif args.cmd == "balance":
            t = treasury.totals()
            print("revenue:     %s" % _usd(t["revenue"]))
            print("expenditure: %s" % _usd(t["expenditure"]))
            print("cash:        %s" % _usd(t["cash"]))
        elif args.cmd == "audit":
            findings = treasury.audit()
            if not findings:
                print("audit clean: %d entries, all balanced"
                      % len(treasury.entries))
            else:
                print("audit found %d issue(s):" % len(findings))
                for f in findings:
                    print("  - %s" % f)

    elif args.group == "tax":
        if args.cmd == "compute":
            due, breakdown = taxman.compute(args.income)
            print("schedule: %s" % SCHEDULE_LABEL)
            for b in breakdown:
                top = "up" if b["bracket_top"] is None \
                    else "to %s" % f"{b['bracket_top']:,.0f}"
                print("  %d%% %s: taxable %s -> due %s"
                      % (int(b["rate"] * 100), top,
                         _usd(b["taxable"]), _usd(b["due"])))
            print("total liability on %s: %s"
                  % (_usd(args.income), _usd(due)))
        elif args.cmd == "file":
            r = taxman.file_return(args.filer, args.income, args.year)
            print("filed %s year %d: income %s, liability %s"
                  % (r["filer_id"], r["year"], _usd(r["income"]),
                     _usd(r["liability"])))
        elif args.cmd == "collected":
            total = taxman.total_collected(args.year)
            scope = "year %d" % args.year if args.year else "all years"
            print("total collected (%s): %s" % (scope, _usd(total)))

    elif args.group == "spending":
        if args.cmd == "feed":
            doc = publisher.feed(args.limit)
            print("Public spending feed | %s" % doc["label"][:80])
            print("published at %s | %d records"
                  % (doc["published_at"], len(doc["records"])))
            for r in doc["records"]:
                print("  %s | %s | %s | %s"
                      % (r["date"], r["recipient"][:28],
                         r["purpose"][:24], _usd(r["amount"])))
        elif args.cmd == "federal":
            try:
                rows, prov = publisher.federal_top(
                    args.fiscal_year, args.limit, args.refresh)
            except RuntimeError as e:
                print("federal feed unavailable: %s" % e)
                return 1
            tag = "LIVE (USAspending.gov)" if prov == "live" \
                else "CACHED as of %s" % prov.split(":", 1)[1]
            print("US federal top recipients FY%d | %s"
                  % (args.fiscal_year, tag))
            for i, r in enumerate(rows, 1):
                print("  %2d. %-40s %s"
                      % (i, (r["name"] or "")[:40], _usd(r["amount"], "")))
        elif args.cmd == "recipient":
            doc = publisher.federal_recipient(args.name)
            print("USAspending.gov | %s | pulled %s"
                  % (args.name, doc["pulled_at"][:10]))
            print("match method: %s" % doc["match_method"])
            for fy in sorted(doc["by_year"]):
                v = doc["by_year"][fy]
                print("  FY%d: %s" % (fy, _usd(v, "") if v is not None
                                      else "unavailable"))

    elif args.group == "mint":
        if args.cmd == "record":
            o = mint.record(args.supply, args.price_index, args.date,
                            args.source)
            print("recorded observation %s: supply %s, price index %s"
                  % (o["date"], f"{o['money_supply']:,.0f}",
                     o["price_index"]))
        elif args.cmd == "stability":
            s = mint.stability()
            print("verdict: %s" % s["verdict"].upper())
            if s["verdict"] != "insufficient data":
                print("period: %s to %s (%s years)"
                      % (s["period"]["from"], s["period"]["to"],
                         s["period"]["years"]))
                print("annualized inflation: %s"
                      % _pct(s["annualized_inflation"]))
                print("annualized money-supply growth: %s"
                      % _pct(s["annualized_money_supply_growth"]))
            print("note: %s" % s["label"][:100])
    return 0


if __name__ == "__main__":
    sys.exit(main())
