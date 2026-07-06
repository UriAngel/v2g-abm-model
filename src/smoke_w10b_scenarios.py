"""Smoke test: V2G economics under retail vs wholesale revenue.

With no aggregator-retailer coupling, the model exposes two clean
scenarios for V2G revenue per kWh:

  - retail    : driver receives the retail TAOZ tariff (peak/off-peak)
  - wholesale : driver receives the wholesale system-marginal-cost rate

Driver keeps 100% of revenue in both scenarios.  There is no
aggregator dispatch window; the agent discharges any hour where the
offered price exceeds its SEM-derived OSP.

Run:  python -m src.smoke_w10b_scenarios
"""

from __future__ import annotations

import src.agents.ev_agent as ev_agent_module
from src.agents.ev_agent import (
    EVAgent,
    ALL_TYPOLOGIES,
    COUNTERFACTUAL_V2G,
)
from src.pricing import price_at_hour, wholesale_price_at_hour
from src.run_demo import CARS_PER_TYPOLOGY


HOURS = 168       # one calendar week
N_AGENTS = 60     # oversample so SEM opt-in randomness averages out


def run_one(typology: str, scenario: str) -> dict:
    """Mean weekly economics for one typology under one scenario."""
    v2g_kwh_arr, revenue_arr, import_arr, opted_arr = [], [], [], []
    base = abs(hash((typology, scenario))) % 100_000
    for i in range(N_AGENTS):
        a = EVAgent(agent_id=base * 1000 + i, typology=typology,
                    counterfactual=COUNTERFACTUAL_V2G)
        for hour in range(HOURS):
            hod = hour % 24
            dow = (hour // 24) % 7
            p_retail = price_at_hour(hod, dow)
            if scenario == "retail":
                p_export = p_retail
            elif scenario == "wholesale":
                p_export = wholesale_price_at_hour(hod, dow)
            else:
                raise ValueError(scenario)
            a.step(
                current_hour=hour,
                current_price_per_kwh=p_retail,
                discharge_revenue_per_kwh=p_export,
            )
        revenue = -sum(r["cost_currency"] for r in a.hourly_log if r["cost_currency"] < 0)
        cost    =  sum(r["cost_currency"] for r in a.hourly_log if r["cost_currency"] > 0)
        v2g_kwh_arr.append(a.state.cumulative_v2g_discharge_kwh)
        revenue_arr.append(revenue)
        import_arr.append(cost)
        opted_arr.append(a.state.v2g_opted_in)
    n = len(v2g_kwh_arr)
    return {
        "v2g_kwh":     sum(v2g_kwh_arr) / n,
        "revenue":     sum(revenue_arr) / n,
        "import":      sum(import_arr) / n,
        "net":         (sum(revenue_arr) - sum(import_arr)) / n,
        "opt_in_rate": sum(opted_arr) / n,
    }


def main() -> None:
    ev_agent_module.SEM_ENABLED = True

    print(f"Smoke test - retail vs wholesale V2G revenue")
    print(f"({N_AGENTS} agents per cell, one calendar week, NIS)")
    print()
    hdr = (f"{'Typology':>20} | {'Scenario':>9} | {'OptIn':>6} | "
           f"{'V2G kWh':>9} | {'Revenue':>9} | {'Import':>9} | {'Net':>9}")
    print(hdr)
    print("-" * len(hdr))
    for typology in ALL_TYPOLOGIES:
        for scen in ("retail", "wholesale"):
            r = run_one(typology, scen)
            print(f"{typology:>20} | {scen:>9} | {r['opt_in_rate']*100:>5.0f}% | "
                  f"{r['v2g_kwh']:>9.1f} | {r['revenue']:>9.2f} | "
                  f"{r['import']:>9.2f} | {r['net']:>9.2f}")
        print()


if __name__ == "__main__":
    main()
