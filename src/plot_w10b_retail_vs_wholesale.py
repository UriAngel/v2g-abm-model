"""Retail vs wholesale V2G revenue per typology.

Visualises the smoke_w10b_scenarios.py finding: at wholesale prices,
no typology participates in V2G because the wholesale peak (0.46
NIS/kWh) is below every SEM-derived OSP.

Two grouped bars per typology: retail revenue (teal), wholesale
revenue (gray).  Annotated.

Run:  python -m src.plot_w10b_retail_vs_wholesale
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
from src.pricing import price_at_hour, wholesale_price_at_hour


HOURS = 168       # one calendar week
N_AGENTS = 60

OUT = (Path(__file__).resolve().parent.parent
       / "outputs" / "w10b_retail_vs_wholesale.png")


def run_one(typology: str, scenario: str) -> dict:
    ev_agent_module.SEM_ENABLED = True
    v2g_kwh, revenue = [], []
    base = abs(hash((typology, scenario))) % 100_000
    for i in range(N_AGENTS):
        a = EVAgent(agent_id=base * 1000 + i, typology=typology,
                    counterfactual=COUNTERFACTUAL_V2G)
        for hour in range(HOURS):
            hod = hour % 24
            dow = (hour // 24) % 7
            p_retail = price_at_hour(hod, dow)
            p_export = (p_retail if scenario == "retail"
                        else wholesale_price_at_hour(hod, dow))
            a.step(current_hour=hour, current_price_per_kwh=p_retail,
                   discharge_revenue_per_kwh=p_export)
        revenue.append(-sum(r["cost_currency"] for r in a.hourly_log
                            if r["cost_currency"] < 0))
        v2g_kwh.append(a.state.cumulative_v2g_discharge_kwh)
    return {
        "v2g_kwh_wk": float(np.mean(v2g_kwh)),
        "revenue_wk": float(np.mean(revenue)),
    }


def main() -> None:
    typologies = list(ALL_TYPOLOGIES)
    retail = [run_one(t, "retail") for t in typologies]
    wholesale = [run_one(t, "wholesale") for t in typologies]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2),
                             gridspec_kw={"width_ratios": [1.0, 1.0]})

    # ---- left panel: weekly revenue in NIS ----
    ax = axes[0]
    x = np.arange(len(typologies))
    w = 0.36
    retail_rev = [r["revenue_wk"] for r in retail]
    whsale_rev = [r["revenue_wk"] for r in wholesale]
    b1 = ax.bar(x - w/2, retail_rev, w, color="#02808F", label="Retail scenario")
    b2 = ax.bar(x + w/2, whsale_rev, w, color="#9CA3AF", label="Wholesale scenario")
    for b, v in zip(b1, retail_rev):
        ax.text(b.get_x() + b.get_width()/2, v + 1.5, f"{v:.0f}",
                ha="center", fontsize=10, fontweight="bold")
    for b, v in zip(b2, whsale_rev):
        ax.text(b.get_x() + b.get_width()/2, v + 1.5, f"{v:.0f}",
                ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=10)
    ax.set_ylabel("Driver V2G revenue, NIS/week", fontsize=11)
    ax.set_title("Weekly V2G revenue per typology", fontsize=12, fontweight="bold")
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, axis="y", alpha=0.3)

    # ---- right panel: V2G discharge kWh ----
    ax = axes[1]
    retail_kwh = [r["v2g_kwh_wk"] for r in retail]
    whsale_kwh = [r["v2g_kwh_wk"] for r in wholesale]
    b1 = ax.bar(x - w/2, retail_kwh, w, color="#02808F", label="Retail scenario")
    b2 = ax.bar(x + w/2, whsale_kwh, w, color="#9CA3AF", label="Wholesale scenario")
    for b, v in zip(b1, retail_kwh):
        ax.text(b.get_x() + b.get_width()/2, v + 1.5, f"{v:.0f}",
                ha="center", fontsize=10, fontweight="bold")
    for b, v in zip(b2, whsale_kwh):
        ax.text(b.get_x() + b.get_width()/2, v + 1.5, f"{v:.1f}",
                ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=10)
    ax.set_ylabel("V2G discharge, kWh/week", fontsize=11)
    ax.set_title("Weekly V2G discharge per typology", fontsize=12, fontweight="bold")
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, axis="y", alpha=0.3)

    # Headline finding annotation
    fig.suptitle(
        "Retail vs wholesale pricing scenarios (Israel, 1 week, 60 agents)\n"
        "At wholesale prices, NO typology participates - wholesale peak "
        "(0.46 NIS/kWh) is below every SEM-derived OSP (~1.0-1.5).",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(OUT, dpi=150, facecolor="white")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
