"""SoH milestones: year-1, year-5, year-10 health projection.

Battery aging is reported as a physical consequence of operation
rather than as a price folded into the OSP.  This script runs each
typology x counterfactual for one calendar week and projects SoH to
year-1, 5 and 10 milestones.

Run:  python -m src.smoke_w10f_soh_milestones
"""

from __future__ import annotations

import numpy as np

import src.agents.ev_agent as ev_agent_module
from src.agents.ev_agent import (
    EVAgent,
    ALL_TYPOLOGIES,
    COUNTERFACTUAL_V0,
    COUNTERFACTUAL_V1G,
    COUNTERFACTUAL_V2G,
)
from src.battery_aging import project_soh_milestones, EOL_SOH
from src.pricing import price_at_hour


HOURS_IN_WEEK = 168
N_AGENTS_PER_CELL = 40

COUNTERFACTUALS = (COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G)


def measure_one_week(typology: str, counterfactual: str) -> tuple[float, float]:
    """Run N_AGENTS_PER_CELL of (typology, counterfactual) and return mean
    weekly calendar and cycle SoH loss."""
    ev_agent_module.SEM_ENABLED = True
    cal_arr, cyc_arr = [], []
    base = abs(hash((typology, counterfactual))) % 100_000
    for i in range(N_AGENTS_PER_CELL):
        a = EVAgent(agent_id=base * 1000 + i, typology=typology,
                    counterfactual=counterfactual)
        for hour in range(HOURS_IN_WEEK):
            hod = hour % 24
            dow = (hour // 24) % 7
            p_retail = price_at_hour(hod, dow)
            a.step(current_hour=hour, current_price_per_kwh=p_retail,
                   discharge_revenue_per_kwh=p_retail)
        cal_arr.append(a.state.cumulative_calendar_aging)
        cyc_arr.append(a.state.cumulative_cycle_aging)
    return float(np.mean(cal_arr)), float(np.mean(cyc_arr))


def main() -> None:
    print()
    print(f"SoH milestones (one-week sim x {N_AGENTS_PER_CELL} agents, "
          f"projected linearly)")
    print(f"EoL threshold = {EOL_SOH * 100:.0f}% SoH; "
          f"* marks runs that fall below EoL by year 10.")
    print()

    hdr = (f"{'Typology':>20} | {'CF':>4} | "
           f"{'1y SoH':>7} | {'5y SoH':>7} | {'10y SoH':>8} | "
           f"{'10y cal':>8} | {'10y cyc':>8}")
    print(hdr); print("-" * len(hdr))

    for typology in ALL_TYPOLOGIES:
        for cf in COUNTERFACTUALS:
            cal_w, cyc_w = measure_one_week(typology, cf)
            ms = project_soh_milestones(cal_w, cyc_w, hours_observed=HOURS_IN_WEEK)
            star10 = " " if ms[10]["above_eol"] else "*"
            print(f"{typology:>20} | {cf:>4} | "
                  f"{ms[1]['soh_pct']:>6.2f}% | "
                  f"{ms[5]['soh_pct']:>6.2f}% | "
                  f"{ms[10]['soh_pct']:>6.2f}%{star10}| "
                  f"{ms[10]['cal_loss_pct']:>6.2f}% | "
                  f"{ms[10]['cyc_loss_pct']:>6.2f}%")
        print()


if __name__ == "__main__":
    main()
