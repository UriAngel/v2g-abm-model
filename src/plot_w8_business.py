"""Business model plot.

Runs the V2G fleet and computes:
  - Driver annual net benefit: V2G earnings (75% share) + V1G savings vs V0
  - Driver payback period for the charger CAPEX (~28,000 NIS)
  - Aggregator revenue per car per year (25% share)
  - Aggregator total revenue from the modelled fleet

Four panels:
  (a) Driver annual net benefit per typology  (V2G + V1G savings)
  (b) Driver charger CAPEX payback period per typology (years)
  (c) Aggregator annual revenue per car per typology
  (d) Aggregator annual revenue scaled to fleet sizes (10, 100, 1000 cars)
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import src.agents.ev_agent as ev_agent_module
from src.agents.ev_agent import (
    EVAgent,
    ALL_TYPOLOGIES,
    DAILY_CHARGER,
    PUBLIC_CHARGER,
    BEV_2ND_VEHICLE,
    THRESHOLD_CHARGER,
    COUNTERFACTUAL_V0,
    COUNTERFACTUAL_V1G,
    COUNTERFACTUAL_V2G,
)
from src.aggregator_stub import (
    CHARGER_CAPEX_NIS,
    CHARGER_CAPEX_BIDIR_2024_NIS,
    CHARGER_CAPEX_BIDIR_2028_NIS,
    CHARGER_CAPEX_SMART_NIS,
    V2G_PREMIUM_2024_NIS,
    V2G_PREMIUM_2028_NIS,
    AGGREGATOR_REVENUE_SHARE,
    DRIVER_REVENUE_SHARE,
)
from src.pricing import price_at_hour
from src.calendar_helper import hour_to_calendar, HOURS_IN_YEAR
from src.run_demo import CARS_PER_TYPOLOGY


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

COLORS = {
    DAILY_CHARGER:     "#1f77b4",
    PUBLIC_CHARGER:    "#ff7f0e",
    BEV_2ND_VEHICLE:   "#2ca02c",
    THRESHOLD_CHARGER: "#d62728",
}


def run_fleet(country: str = "Israel") -> dict:
    """Simulate V0, V1G, V2G for every car over a full calendar year.

    Runs the annual 8,760-hour horizon with seasonal TAOZ dispatch.
    Hourly indices are mapped to (hour_of_day, day_of_week, month)
    via calendar_helper.hour_to_calendar so the pricing module sees
    the correct season and weekday rule on each step.  Keys named
    ``V0_week`` etc hold full-year net costs despite the name;
    downstream panels do not multiply by 52.
    """
    ev_agent_module.SEM_ENABLED = True
    results = {t: {"V0_week": [], "V1G_week": [], "V2G_week": [], "gross_kwh_sold": []} for t in ALL_TYPOLOGIES}

    for t_idx, typology in enumerate(ALL_TYPOLOGIES):
        n_cars = CARS_PER_TYPOLOGY[typology]
        for car_idx in range(n_cars):
            agent_id = t_idx * 1000 + car_idx + 1
            year = {}
            kwh_sold_gross = 0.0
            for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G):
                a = EVAgent(agent_id=agent_id, typology=typology, counterfactual=cf, country=country)
                for hour in range(HOURS_IN_YEAR):
                    hour_of_day, day_of_week, month = hour_to_calendar(hour)
                    price = price_at_hour(hour_of_day, day_of_week, month)
                    a.step(current_hour=hour, current_price_per_kwh=price, month=month)
                net_year = sum(r["cost_currency"] for r in a.hourly_log)
                year[cf] = net_year
                if cf == COUNTERFACTUAL_V2G:
                    kwh_sold_gross = sum(-r["energy_kwh"] for r in a.hourly_log if r["action"] == "DISCHARGE")

            results[typology]["V0_week"].append(year[COUNTERFACTUAL_V0])
            results[typology]["V1G_week"].append(year[COUNTERFACTUAL_V1G])
            results[typology]["V2G_week"].append(year[COUNTERFACTUAL_V2G])
            results[typology]["gross_kwh_sold"].append(kwh_sold_gross)
    return results


def panel_driver_benefit(ax, summary):
    """Driver annual net benefit per typology, vs the V0 baseline."""
    typologies = list(ALL_TYPOLOGIES)
    x = np.arange(len(typologies))
    width = 0.35

    v1g_savings = []
    v2g_total = []
    for t in typologies:
        v0_yr = np.mean(summary[t]["V0_week"])
        v1g_yr = np.mean(summary[t]["V1G_week"])
        v2g_yr = np.mean(summary[t]["V2G_week"])
        v1g_savings.append(v0_yr - v1g_yr)        # how much V1G saves vs V0
        v2g_total.append(v0_yr - v2g_yr)          # how much V2G saves vs V0 (incl. V1G savings + V2G)

    ax.bar(x - width/2, v1g_savings, width, label="V1G savings (vs V0)", color="#9ca3af")
    ax.bar(x + width/2, v2g_total,    width, label="V2G total benefit (vs V0)", color="#10b981")
    for i, t in enumerate(typologies):
        ax.text(i - width/2, v1g_savings[i] + 100, f"{v1g_savings[i]:,.0f}", ha="center", fontsize=9)
        ax.text(i + width/2, v2g_total[i] + 100,   f"{v2g_total[i]:,.0f}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=9)
    ax.set_ylabel("Annual driver benefit (NIS/yr)")
    ax.set_title("(a) Driver annual benefit per typology")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.legend(fontsize=8)


def panel_payback(ax, summary):
    """Driver payback periods per typology, two CAPEX layers shown side-by-side.

    V0->V1G payback uses the smart charger CAPEX (CHARGER_CAPEX_SMART_NIS,
    ~3,300 NIS) divided by the V1G annual savings vs. V0.  This is the
    relevant number for "should I upgrade my dumb installation to a smart
    unidirectional charger so I can shift my charging to off-peak?".

    V1G->V2G payback uses the V2G premium (V2G_PREMIUM_2024_NIS, the cost
    of going bidirectional ABOVE the smart unidirectional baseline)
    divided by the marginal V2G benefit over V1G.  This is the relevant
    number for "should I upgrade my smart charger to a bidirectional
    V2G unit?".

    A dashed line marks the typical 10-year charger lifetime.
    """
    typologies = list(ALL_TYPOLOGIES)
    x = np.arange(len(typologies))
    width = 0.35

    payback_v0_v1g = []
    payback_v1g_v2g = []
    for t in typologies:
        v0_yr  = np.mean(summary[t]["V0_week"])
        v1g_yr = np.mean(summary[t]["V1G_week"])
        v2g_yr = np.mean(summary[t]["V2G_week"])

        v1g_savings = v0_yr - v1g_yr     # V1G saves vs V0 (positive = better)
        marginal    = v1g_yr - v2g_yr    # V2G marginal benefit over V1G

        if v1g_savings <= 0:
            payback_v0_v1g.append(float("inf"))
        else:
            payback_v0_v1g.append(CHARGER_CAPEX_SMART_NIS / v1g_savings)

        if marginal <= 0:
            payback_v1g_v2g.append(float("inf"))
        else:
            payback_v1g_v2g.append(V2G_PREMIUM_2024_NIS / marginal)

    capped_v0v1g  = [min(p, 30) for p in payback_v0_v1g]
    capped_v1gv2g = [min(p, 30) for p in payback_v1g_v2g]
    ax.bar(x - width/2, capped_v0v1g,  width,
           label=f"V0→V1G (smart charger {CHARGER_CAPEX_SMART_NIS:,.0f} NIS)",
           color="#9ca3af")
    ax.bar(x + width/2, capped_v1gv2g, width,
           label=f"V1G→V2G (V2G premium {V2G_PREMIUM_2024_NIS:,.0f} NIS)",
           color="#10b981")
    for i in range(len(typologies)):
        l1 = "no payback" if payback_v0_v1g[i]  == float("inf") else f"{payback_v0_v1g[i]:.1f} yr"
        l2 = "no payback" if payback_v1g_v2g[i] == float("inf") else f"{payback_v1g_v2g[i]:.1f} yr"
        ax.text(i - width/2, min(capped_v0v1g[i]  + 0.5, 27), l1,
                ha="center", fontsize=8.5, fontweight="bold")
        ax.text(i + width/2, min(capped_v1gv2g[i] + 0.5, 27), l2,
                ha="center", fontsize=8.5, fontweight="bold")
    ax.axhline(10, color="black", linestyle="--", linewidth=1,
               label="Charger lifetime (~10 yr)")
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=9)
    ax.set_ylabel("Years to repay charger CAPEX")
    ax.set_title("(b) Driver payback   V0→V1G smart charger vs V1G→V2G premium")
    ax.legend(fontsize=8, loc="upper left")
    ax.set_ylim(0, 30)


def panel_aggregator_per_car(ax, summary):
    """Aggregator revenue per car per year by typology."""
    typologies = list(ALL_TYPOLOGIES)
    x = np.arange(len(typologies))
    agg_revenue = []
    for t in typologies:
        # Aggregator revenue = AGGREGATOR_REVENUE_SHARE × gross V2G revenue per car per year
        # Gross V2G revenue per kWh ≈ peak price 1.69 (since discharge only at peak)
        # gross_kwh_sold is per week; × 52 for annual
        gross_kwh_yr = np.mean(summary[t]["gross_kwh_sold"])
        gross_revenue_yr = gross_kwh_yr * 1.69  # peak rate
        agg_yr = gross_revenue_yr * AGGREGATOR_REVENUE_SHARE
        agg_revenue.append(agg_yr)

    colors = [COLORS[t] for t in typologies]
    ax.bar(x, agg_revenue, color=colors)
    for i, v in enumerate(agg_revenue):
        ax.text(i, v + 20, f"{v:,.0f}", ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=9)
    ax.set_ylabel("Aggregator revenue (NIS / car / year)")
    ax.set_title(f"(c) Aggregator revenue per car  ({AGGREGATOR_REVENUE_SHARE*100:.0f}% share)")


def panel_aggregator_fleet(ax, summary):
    """Aggregator annual revenue at fleet scales."""
    typologies = list(ALL_TYPOLOGIES)
    fleet_sizes = [100, 1_000, 10_000, 50_000]
    # Use a typology-weighted average per-car revenue (California shares)
    weights = {DAILY_CHARGER: 0.26, PUBLIC_CHARGER: 0.19, BEV_2ND_VEHICLE: 0.17, THRESHOLD_CHARGER: 0.38}
    avg_rev_per_car = 0.0
    for t in typologies:
        gross_kwh_yr = np.mean(summary[t]["gross_kwh_sold"])
        gross_revenue_yr = gross_kwh_yr * 1.69
        agg_yr = gross_revenue_yr * AGGREGATOR_REVENUE_SHARE
        avg_rev_per_car += weights[t] * agg_yr

    revs = [avg_rev_per_car * n for n in fleet_sizes]
    x = np.arange(len(fleet_sizes))
    ax.bar(x, revs, color="#1f3864")
    for i, (n, v) in enumerate(zip(fleet_sizes, revs)):
        if v >= 1_000_000:
            label = f"{v/1_000_000:.1f} M NIS"
        else:
            label = f"{v/1000:.0f}k NIS"
        ax.text(i, v + max(revs)*0.02, label, ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{n:,} cars" for n in fleet_sizes], fontsize=9)
    ax.set_ylabel("Aggregator annual revenue (NIS)")
    ax.set_title(f"(d) Aggregator revenue at fleet scale  (avg {avg_rev_per_car:,.0f} NIS/car/yr)")


def main() -> None:
    print("Running V0 + V1G + V2G fleet simulation for business-model analysis...")
    summary = run_fleet()

    fig, axes = plt.subplots(2, 2, figsize=(18, 11))
    panel_driver_benefit(axes[0][0], summary)
    panel_payback(axes[0][1], summary)
    panel_aggregator_per_car(axes[1][0], summary)
    panel_aggregator_fleet(axes[1][1], summary)

    fig.suptitle(
        f"V2G business model  -  bidirectional charger {CHARGER_CAPEX_BIDIR_2024_NIS:,.0f} NIS today "
        f"(smart baseline {CHARGER_CAPEX_SMART_NIS:,.0f} NIS), 75/25 driver/aggregator split",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    out = OUTPUTS_DIR / "w8_business.png"
    fig.savefig(out, dpi=150, facecolor="white")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
