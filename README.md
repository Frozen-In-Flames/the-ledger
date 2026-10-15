# the-ledger

Treasury core for a new nation. Step 1 of the Nation Kit's 17-to-1
reverse-SDG build sequence.

## The idea

Every federal agency is one class with one job. This build centralizes the
four money classes:

- `Treasury` — one job: the books balance. Double-entry public ledger;
  every public dollar in and out is recorded and auditable.
- `TaxCollector` — one job: revenue comes in. Tax calculator and filer on
  the nation's default bracket schedule.
- `SpendingPublisher` — one job: anyone can see where the money went.
  Public spending feed from the Treasury ledger, plus a live USAspending.gov
  reference feed.
- `Mint` — one job: the currency holds its value. Money-supply and
  price-index tracker with a plain stability readout.

## SDGs unlocked

This build unlocks **SDG 16 (Peace, Justice and Strong Institutions)** and
**SDG 17 (Partnerships for the Goals)**. Strong institutions need honest
books: a government that cannot show where the money went cannot be
trusted, and a coordination layer for partnerships starts with a ledger
everyone can read.

It is step 1 of the 17-to-1 sequence because everything else in the Nation
Kit spends money. You cannot run a registry, a shield, a sword, commons, or
a safety net without first knowing the books balance.

## Usage

```bash
# Treasury
python3 ledger_cli.py treasury revenue --source income-tax --amount 50000
python3 ledger_cli.py treasury expense --recipient Clinic --amount 12000 --purpose health
python3 ledger_cli.py treasury balance
python3 ledger_cli.py treasury audit

# Tax
python3 ledger_cli.py tax compute --income 50000
python3 ledger_cli.py tax file --filer CIT-001 --income 50000 --year 2026
python3 ledger_cli.py tax collected --year 2026

# Spending
python3 ledger_cli.py spending feed
python3 ledger_cli.py spending federal --fiscal-year 2025 --limit 10
python3 ledger_cli.py spending recipient --name "Lockheed Martin"

# Mint
python3 ledger_cli.py mint record --supply 1000 --price-index 100 --date 2025-01-01
python3 ledger_cli.py mint record --supply 1030 --price-index 102 --date 2026-01-01
python3 ledger_cli.py mint stability
```

Data lives in `data/` (JSON). `--data-dir` overrides the location.

## Data sources and labels

- Treasury ledger, tax returns, mint observations: recorded locally by this
  tool, labeled with entry date and record time.
- US federal feed: USAspending.gov
  `/api/v2/search/spending_by_category/recipient/`, pulled live at runtime,
  free and keyless. Recipient totals are matched by recipient-name tokens.
  Federal obligations only; excludes state and local spending.
- Cache (`data/spending_cache.json`) is fallback only, always labeled with
  its pull date. `--refresh` forces a fresh live pull.

Every figure carries its source and date. Estimates are never presented
as exacts.

## Honest limits

- The tax schedule is the nation's default (0%/10%/20%/30% at
  12k/40k/100k), fully configurable; it is a starting point, not tax law.
- The Mint's stability readout is descriptive, not monetary policy; it
  reports what happened, it does not prescribe rates.
- USAspending recipient matching is by name tokens; near-name collisions
  are possible and the match method is recorded per query.
- Treasury enforces no-spend-beyond-cash at the tool level; real
  appropriation authority is a legal layer above this code.
- Tests run with no network access; live behavior is demonstrated, not
  unit-tested.

## TRL

TRL 8: system complete and qualified. 26/26 tests green, CLI demonstrated
end to end on live data, v0.1.0 released. The gap to 9 is operational use:
a real treasury running real books on it.

## License

Apache-2.0. Not financial or tax advice.
