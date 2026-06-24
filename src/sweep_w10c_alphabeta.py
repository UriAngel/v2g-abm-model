"""W10.C.2 sensitivity sweep over (alpha, beta).

David M6 ask: parameterise the Israeli V2G fleet capacity by two
multiplicative coefficients and play with them.

  alpha = EV share of total vehicle fleet
  beta  = V2G-capable share of the EV fleet

This script computes per-V2G-EV weekly economics from the W10.B smoke
test output (typology-weighted using Wong shares) and scales it to
fleet-level annual figures across a sweep of (alpha, beta) pairs.

The simulation is run under the *retail* scenario, because the
wholesale scenario produces zero V2G activity for the SEM-derived OSPs.

Run:  python -m src.sweep_w10c_alphabeta
"""

from __future__ import annotations

import numpy as np

import src.agents.ev_agent as ev_agent_module
from src.agents.ev_agent import (
    EVAgent,
    ALL_TYPOLOGIES,
    DAILY_CHARGER,
    PUBLIC_CHARGER,
    BEV_2ND_VEHICLE,
    THRESHOLD_CHARGER,
    COUNTERFACTUAL_V2G,
)
from src.pricing import price_at_hour
from src.fleet_assumptions import N_FLEET_ISRAEL


HOURS_IN_WEEK = 168
WEEKS_IN_YEAR = 52
N_AGENTS_PER_TYPOLOGY = 80     # oversample for stable means

# Wong shares (used to weight per-typology results into a "per V2G-capable
# EV" mean for fleet-level scaling).  These are the California shares from
# Hoke 2026 Appendix B; we use them as our best available proxy for the
# Israeli driver-type mix in the absence of local data.
WONG_SHARES = {
    DAILY_CHARGER:     0.25,
    PUBLIC_CHARGER:    0.20,   # contributes 0 V2G (no home charger)
    BEV_2ND_VEHICLE:   0.15,
    THRESHOLD_CHARGER: 0.40,   # contributes 0 V2G (floor + threshold rules)
}

# Sweep grids
ALPHA_GRID = [0.05, 0.10, 0.20, 0.30, 0.40]   # EV share of fleet
BETA_GRID  = [0.10, 0.25, 0.50, 0.75, 1.00]   # V2G share of EVs


def per_typology_weekly_v2g_economics() -> dict[str, dict]:
    """For each typology, mean weekly V2G discharge and revenue per agent
    (retail scenario)."""
    ev_agent_module.SEM_ENABLED = True
    out: dict[str, dict] = {}
    for typology in ALL_TYPOLOGIES:
        v2g_kwh_arr, revenue_arr = [], []
        base = abs(hash(typology)) % 100_000
        for i in range(N_AGENTS_PER_TYPOLOGY):
            a = EVAgent(agent_id=base * 1000 + i, typology=typology,
                        counterfactual=COUNTERFACTUAL_V2G)
            for hour in range(HOURS_IN_WEEK):
                hod = hour % 24
                dow = (hour // 24) % 7
                p_retail = price_at_hour(hod, dow)
                a.step(current_hour=hour, current_price_per_kwh=p_retail,
                       discharge_revenue_per_kwh=p_retail)
            v2g_kwh_arr.append(a.state.cumulative_v2g_discharge_kwh)
            rev = -sum(r["cost_currency"] for r in a.hourly_log
                       if r["cost_currency"] < 0)
            revenue_arr.append(rev)
        out[typology] = {
            "v2g_kwh_per_wk": float(np.mean(v2g_kwh_arr)),
            "revenue_nis_per_wk": float(np.mean(revenue_arr)),
        }
    return out


def fleet_level_annual(
    alpha: float,
    beta: float,
    per_typ: dict[str, dict],
    n_fleet: int = N_FLEET_ISRAEL,
) -> dict:
    """Aggregate fleet-level annual V2G stats under (alpha, beta).

    Wong shares apply within the V2G-capable population as a proxy for
    driver-type distribution: a Public Charger may still be classified
    as V2G-capable on hardware (his car can do it), but the rule cascade
    will produce zero V2G discharge for him.  We weight by Wong shares
    to get a realistic per-V2G-capable-EV mean across the population.
    """
    weighted_kwh_per_wk = sum(
        WONG_SHARES[t] * per_typ[t]["v2g_kwh_per_wk"] for t in ALL_TYPOLOGIES
    )
    weighted_revenue_per_wk = sum(
        WONG_SHARES[t] * per_typ[t]["revenue_nis_per_wk"] for t in ALL_TYPOLOGIES
    )
    n_v2g = int(round(alpha * beta * n_fleet))
    return {
        "alpha":         alpha,
        "beta":          beta,
        "n_v2g_evs":     n_v2g,
        "kwh_per_v2g_yr":     weighted_kwh_per_wk * WEEKS_IN_YEAR,
        "revenue_per_v2g_yr": weighted_revenue_per_wk * WEEKS_IN_YEAR,
        "fleet_gwh_yr":       n_v2g * weighted_kwh_per_wk * WEEKS_IN_YEAR / 1e6,
        "fleet_revenue_mnis_yr": n_v2g * weighted_revenue_per_wk * WEEKS_IN_YEAR / 1e6,
    }


def main() -> None:
    print("Step 1: per-typology weekly V2G economics (retail scenario)")
    per_typ = per_typology_weekly_v2g_economics()
    for t in ALL_TYPOLOGIES:
        r = per_typ[t]
        print(f"  {t:>20}  kWh/wk={r['v2g_kwh_per_wk']:>6.1f}  "
              f"NIS/wk={r['revenue_nis_per_wk']:>7.2f}")

    weighted_kwh = sum(WONG_SHARES[t] * per_typ[t]["v2g_kwh_per_wk"]
                       for t in ALL_TYPOLOGIES)
    weighted_nis = sum(WONG_SHARES[t] * per_typ[t]["revenue_nis_per_wk"]
                       for t in ALL_TYPOLOGIES)
    print(f"\n  Per-V2G-capable EV (Wong-weighted): "
          f"{weighted_kwh:.1f} kWh/wk, {weighted_nis:.2f} NIS/wk")
    print(f"  Annual per EV: {weighted_kwh*52:.0f} kWh, {weighted_nis*52:.0f} NIS")

    print()
    print(f"Step 2: fleet-level annual V2G impact, Israeli baseline "
          f"({N_FLEET_ISRAEL:,} cars)")
    print()
    hdr = (f"{'alpha':>5} | {'beta':>5} | {'V2G EVs':>9} | "
           f"{'GWh/yr':>8} | {'M NIS/yr':>9}")
    print(hdr); print("-" * len(hdr))
    for alpha in ALPHA_GRID:
        for beta in BETA_GRID:
            r = fleet_level_annual(alpha, beta, per_typ)
            print(f"{alpha:>5.2f} | {beta:>5.2f} | {r['n_v2g_evs']:>9,} | "
                  f"{r['fleet_gwh_yr']:>8.1f} | {r['fleet_revenue_mnis_yr']:>9.1f}")
        print()


if __name__ == "__main__":
    main()
