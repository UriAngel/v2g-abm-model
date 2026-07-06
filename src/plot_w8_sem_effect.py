"""SEM effect plot.

Runs the 20-car fleet twice for the V2G counterfactual:
  Scenario A: SEM disabled.  Everyone opts in.  OSP is a flat 1.00 NIS/kWh.
  Scenario B: SEM enabled.   Per-agent Intention drives opt-in and OSP.

Produces a single PNG `w8_sem_effect.png` with three panels:
  (a) Annual V2G earnings per typology, side-by-side bars (with / without SEM)
  (b) Number of opted-in V2G-capable agents per typology
  (c) Fleet-level annual V2G earnings summary

The retailer gate is held at whatever value is currently configured in
aggregator_stub.py, so only the SEM is toggled between the two runs.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import src.agents.ev_agent as ev_agent_module
from src.agents.ev_agent import (
    EVAgent,
    ALL_TYPOLOGIES,
    COUNTERFACTUAL_V2G,
)
from src.aggregator_stub import (
    AGGREGATOR_CONTRACTED_RETAILER,
    RETAILER_GATE_ENABLED,
)
from src.pricing import price_at_hour
from src.run_demo import CARS_PER_TYPOLOGY, HOURS_IN_WEEK


COLORS = {
    "without SEM": "#a0a0a0",   # neutral grey for the baseline
    "with SEM":    "#028090",   # forest+teal palette accent for the SEM run
}
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


def run_v2g_fleet() -> list[dict]:
    """Simulate every V2G-capable agent under current ev_agent flags."""
    recs = []
    for t_idx, typology in enumerate(ALL_TYPOLOGIES):
        n_cars = CARS_PER_TYPOLOGY[typology]
        for car_idx in range(n_cars):
            agent_id = t_idx * 1000 + car_idx + 1
            a = EVAgent(agent_id=agent_id, typology=typology, counterfactual=COUNTERFACTUAL_V2G)
            for hour in range(HOURS_IN_WEEK):
                hour_of_day = hour % 24
                day_of_week = (hour // 24) % 7
                price = price_at_hour(hour_of_day, day_of_week)
                a.step(current_hour=hour, current_price_per_kwh=price)
            net_week = sum(r["cost_currency"] for r in a.hourly_log)
            recs.append({
                "agent_id": a.id,
                "typology": typology,
                "opted_in": a.state.v2g_opted_in,
                "kwh_sold": sum(-r["energy_kwh"] for r in a.hourly_log if r["action"] == "DISCHARGE"),
                "net_annual": net_week * 52.0,
            })
    return recs


def summarise(recs):
    annual = {t: sum(r["net_annual"] for r in recs if r["typology"] == t) for t in ALL_TYPOLOGIES}
    annual["FLEET TOTAL"] = sum(annual.values())
    opted = {t: sum(1 for r in recs if r["typology"] == t and r["opted_in"]) for t in ALL_TYPOLOGIES}
    return annual, opted


def main() -> None:
    # Scenario A: SEM disabled
    print("Running V2G fleet WITHOUT SEM (everyone opts in, OSP = 1.00)...")
    ev_agent_module.SEM_ENABLED = False
    recs_no_sem = run_v2g_fleet()
    annual_no, opted_no = summarise(recs_no_sem)

    # Scenario B: SEM enabled
    print("Running V2G fleet WITH SEM (Mehdizadeh-style 5-factor)...")
    ev_agent_module.SEM_ENABLED = True
    recs_sem = run_v2g_fleet()
    annual_sem, opted_sem = summarise(recs_sem)

    # ------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    # Panel (a): annual earnings per typology, side by side
    ax = axes[0]
    typologies = list(ALL_TYPOLOGIES)
    x = np.arange(len(typologies))
    width = 0.36
    vals_no = [annual_no[t] for t in typologies]
    vals_sem = [annual_sem[t] for t in typologies]
    ax.bar(x - width/2, vals_no, width, label="without SEM", color=COLORS["without SEM"])
    ax.bar(x + width/2, vals_sem, width, label="with SEM",    color=COLORS["with SEM"])
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=9)
    ax.set_ylabel("Annual V2G cost (NIS)  -- negative = earned")
    ax.set_title("(a) Annual V2G earnings per typology")
    ax.legend()

    # Panel (b): opt-in count
    ax = axes[1]
    ax.bar(x - width/2, [opted_no[t]  for t in typologies], width, label="without SEM", color=COLORS["without SEM"])
    ax.bar(x + width/2, [opted_sem[t] for t in typologies], width, label="with SEM",    color=COLORS["with SEM"])
    for i, t in enumerate(typologies):
        ax.text(i, opted_no[t]  + 0.1, str(opted_no[t]),  ha="center", fontsize=9)
        ax.text(i, opted_sem[t] + 0.1, str(opted_sem[t]), ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=9)
    ax.set_ylabel("Number of agents opted into V2G")
    ax.set_title("(b) Opt-in count by typology")
    ax.legend()
    # Cap fleet count for headroom
    ax.set_ylim(0, max(max(opted_no.values()), max(opted_sem.values())) + 1.5)

    # Panel (c): fleet total
    ax = axes[2]
    labels = ["without SEM", "with SEM"]
    fleet_totals = [annual_no["FLEET TOTAL"], annual_sem["FLEET TOTAL"]]
    colors = [COLORS["without SEM"], COLORS["with SEM"]]
    bars = ax.bar(labels, fleet_totals, color=colors)
    for bar, val in zip(bars, fleet_totals):
        ax.text(bar.get_x() + bar.get_width() / 2,
                val + (200 if val >= 0 else -400),
                f"{val:,.0f}",
                ha="center", fontsize=11, fontweight="bold")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_ylabel("Annual fleet-level V2G cost (NIS)  -- negative = earned")
    ax.set_title("(c) Fleet-total annual V2G earnings")

    gate_str = f"retailer gate {'ON' if RETAILER_GATE_ENABLED else 'OFF'} ({AGGREGATOR_CONTRACTED_RETAILER})"
    fig.suptitle(
        f"Effect of the Mehdizadeh-style SEM on V2G outcomes ({gate_str})",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    out = OUTPUTS_DIR / "w8_sem_effect.png"
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")

    # Print summary
    print()
    print(f"{'Typology':>20} | {'without SEM (NIS/yr)':>22} | {'with SEM (NIS/yr)':>20} | {'change':>10}")
    print("-" * 82)
    for t in typologies + ["FLEET TOTAL"]:
        diff = annual_sem[t] - annual_no[t]
        print(f"{t:>20} | {annual_no[t]:>22,.0f} | {annual_sem[t]:>20,.0f} | {diff:>+10,.0f}")


if __name__ == "__main__":
    main()
