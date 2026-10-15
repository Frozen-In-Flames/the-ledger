"""Mint: the currency holds its value.

One job: track the money supply and the price level, and say plainly
whether the currency is stable. Observations are recorded over time
(money supply, price index, date, source); the stability readout compares
the first and latest observations.

Stability bands (annualized price-index change):
  within +/-1%      : very stable
  1% to 3%         : stable (target band)
  3% to 6%         : watch (elevated)
  -1% to -3%       : watch (deflation risk)
  beyond           : unstable
With fewer than two observations the readout reports insufficient data,
never a verdict.
"""

import datetime
import json
import os

STABILITY_LABEL = ("Currency stability readout from recorded money-supply "
                   "and price-index observations. Bands: +/-1% very stable, "
                   "1-3% stable, 3-6% watch, beyond unstable. Fewer than "
                   "two observations: insufficient data.")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Mint:
    def __init__(self, path):
        self.path = path
        self.observations = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                self.observations = json.load(f).get("observations", [])

    def _save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)),
                    exist_ok=True)
        with open(self.path, "w") as f:
            json.dump({"label": STABILITY_LABEL,
                       "observations": self.observations}, f, indent=2)

    def record(self, money_supply, price_index, date=None, source=""):
        money_supply = float(money_supply)
        price_index = float(price_index)
        if money_supply <= 0 or price_index <= 0:
            raise ValueError("supply and price index must be positive")
        obs = {
            "date": date or datetime.date.today().isoformat(),
            "money_supply": money_supply,
            "price_index": round(price_index, 4),
            "source": source,
            "recorded_at": _now(),
        }
        self.observations.append(obs)
        self.observations.sort(key=lambda o: o["date"])
        self._save()
        return obs

    def stability(self):
        obs = self.observations
        if len(obs) < 2:
            return {"verdict": "insufficient data",
                    "label": STABILITY_LABEL,
                    "observations": len(obs)}
        first, last = obs[0], obs[-1]
        d0 = datetime.date.fromisoformat(first["date"])
        d1 = datetime.date.fromisoformat(last["date"])
        years = (d1 - d0).days / 365.25
        if years <= 0:
            return {"verdict": "insufficient data",
                    "label": STABILITY_LABEL,
                    "observations": len(obs)}
        price_change = last["price_index"] / first["price_index"] - 1
        supply_change = last["money_supply"] / first["money_supply"] - 1
        annual_inflation = (1 + price_change) ** (1 / years) - 1
        annual_supply = (1 + supply_change) ** (1 / years) - 1
        a = abs(annual_inflation)
        if a <= 0.01:
            verdict = "very stable"
        elif a <= 0.03:
            verdict = "stable"
        elif a <= 0.06:
            verdict = "watch"
        else:
            verdict = "unstable"
        return {
            "verdict": verdict,
            "label": STABILITY_LABEL,
            "period": {"from": first["date"], "to": last["date"],
                       "years": round(years, 2)},
            "annualized_inflation": round(annual_inflation, 4),
            "annualized_money_supply_growth": round(annual_supply, 4),
            "observations": len(obs),
        }
