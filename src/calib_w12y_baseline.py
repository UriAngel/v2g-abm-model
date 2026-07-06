"""240-agent ABM baseline with Monte Carlo variance across seeds.

run_seed propagates into every agent RNG via run_year(..., run_seed=i),
so each seed draws a genuinely different realisation while remaining
fully reproducible.  run_seed=0 reproduces the published
single-realisation baseline exactly (DC 4,820 / BEV 6,220 kWh per
opted-in EV).

Reports mean V2G kWh per typology, both fleet-wide (all agents including
non-opted-in) and per-opted-in, with cross-seed mean, std, and 95 % CI.
"""

from __future__ import annotations

import math
import sys

from src.agents.ev_agent import (
    DAILY_CHARGER, PUBLIC_CHARGER, BEV_2ND_VEHICLE, THRESHOLD_CHARGER,
    COUNTERFACTUAL_V2G,
)
from src.run_w9_fleet import run_year, DEFAULT_FLEET_SHARES


def one_run(run_seed: int) -> dict:
    out = run_year(country="Israel", counterfactual=COUNTERFACTUAL_V2G,
                   shares=DEFAULT_FLEET_SHARES, verbose=False,
                   run_seed=run_seed)
    result = {}
    for typ in (DAILY_CHARGER, BEV_2ND_VEHICLE):
        agents = [a for a in out["agents"] if a.typology == typ]
        v2g = [a.state.cumulative_v2g_discharge_kwh for a in agents]
        opt = [a.state.cumulative_v2g_discharge_kwh for a in agents if a.state.v2g_opted_in]
        result[typ] = {
            "all_mean":   sum(v2g)/len(v2g) if v2g else 0,
            "optin_mean": sum(opt)/len(opt) if opt else 0,
            "n_optin":    len(opt),
            "n_all":      len(agents),
        }
    return result


def _mean_std(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / (n - 1) if n > 1 else 0.0
    return m, math.sqrt(var)


def main() -> None:
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    per_seed = []
    for i in range(n_seeds):
        r = one_run(i)
        per_seed.append(r)
        print(f"Seed {i:>2}: DC all={r[DAILY_CHARGER]['all_mean']:>5,.0f} "
              f"opt={r[DAILY_CHARGER]['optin_mean']:>5,.0f} "
              f"(n_optin={r[DAILY_CHARGER]['n_optin']}), "
              f"BEV all={r[BEV_2ND_VEHICLE]['all_mean']:>5,.0f} "
              f"opt={r[BEV_2ND_VEHICLE]['optin_mean']:>5,.0f} "
              f"(n_optin={r[BEV_2ND_VEHICLE]['n_optin']})")

    print()
    print(f"{'Typology':<20} {'metric':<11} {'mean':>8} {'std':>7} {'95% CI':>19} {'CV%':>6}")
    print("-" * 75)
    for typ in (DAILY_CHARGER, BEV_2ND_VEHICLE):
        for key, label in (("all_mean", "fleet-mean"), ("optin_mean", "opt-in")):
            xs = [r[typ][key] for r in per_seed]
            m, sd = _mean_std(xs)
            half = 1.96 * sd / math.sqrt(len(xs))
            cv = 100 * sd / m if m else 0.0
            print(f"{typ:<20} {label:<11} {m:>8,.0f} {sd:>7,.0f} "
                  f"[{m-half:>7,.0f} -{m+half:>8,.0f}] {cv:>5.1f}%")


if __name__ == "__main__":
    main()
