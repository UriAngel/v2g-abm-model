"""Figure 4.1 - SoC-over-a-week trace for all four typologies.

Runs a 1-week Israel V2G simulation for one representative agent of each
typology and plots hour-by-hour SoC.  Produced for Chapter 4, Figure 4.1.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from src.plot_style import apply_style, PALETTE
apply_style()
from pathlib import Path

from src.agents.ev_agent import (
    DAILY_CHARGER, PUBLIC_CHARGER, BEV_2ND_VEHICLE, THRESHOLD_CHARGER,
    COUNTERFACTUAL_V2G, EVAgent,
)
from src.pricing import price_at_hour
from src.calendar_helper import hour_to_calendar


OUT = Path(__file__).resolve().parent.parent / "outputs" / "w12ae_soc_week.png"
HOURS_IN_WEEK = 24 * 7


def run_agent(typology, hours=HOURS_IN_WEEK):
    agent = EVAgent(agent_id=1, typology=typology,
                    counterfactual=COUNTERFACTUAL_V2G, country="Israel")
    agent.state.v2g_opted_in = True
    soc_trace = []
    for h in range(hours):
        hod, dow, month = hour_to_calendar(h)
        p = price_at_hour(hod, dow, month)
        agent.step(current_hour=h, current_price_per_kwh=p,
                   month=month, discharge_revenue_per_kwh=None)
        soc_trace.append(agent.state.soc * 100)
    return soc_trace


def main() -> None:
    typologies = [
        (DAILY_CHARGER,     "Daily Charger",     "#0f766e"),
        (BEV_2ND_VEHICLE,   "BEV 2nd Vehicle",   "#1d4ed8"),
        (PUBLIC_CHARGER,    "Public Charger",    "#8B5CF6"),
        (THRESHOLD_CHARGER, "Threshold Charger", "#C26B12"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(15, 8), sharex=True, sharey=True)
    axes = axes.flatten()

    for ax, (typology, label, color) in zip(axes, typologies):
        trace = run_agent(typology)
        hours = list(range(len(trace)))
        ax.plot(hours, trace, color=color, linewidth=2, label=label)
        ax.axhline(50, color="#b91c1c", linestyle="--", linewidth=1,
                   label="V2G floor 50%")
        ax.axhline(30, color="#d97706", linestyle=":", linewidth=1,
                   label="Range-anxiety floor 30%")
        # Day boundaries
        for d in range(1, 7):
            ax.axvline(d * 24, color="#cccccc", linestyle="-", linewidth=0.5,
                       alpha=0.5)
        # Weekday labels
        day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        ax.set_xticks([d * 24 + 12 for d in range(7)])
        ax.set_xticklabels(day_names, fontsize=9)
        ax.set_xlim(0, 168)
        ax.set_ylim(0, 105)
        ax.set_ylabel("State of Charge (%)", fontsize=10)
        ax.set_title(f"{label}",
                     fontsize=12, fontweight="bold", color=color)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc="lower right")

    fig.suptitle("Figure 4.1  -  Battery SoC over one representative week, "
                 "by typology (Israel V2G, July)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT, dpi=150, facecolor="white")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
