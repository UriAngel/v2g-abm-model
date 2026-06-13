"""W8 SEM funnel plot.

For each typology, simulate a large sample of agents and show what
percentage pass each downstream gate on the way to actually doing V2G.

Gates (in order, every gate must be passed for the next):
  Gate 1: V2G-capable (has a home charger)
  Gate 2: Positive Attitude towards V2G (Attitude > 0)
  Gate 3: Positive Intention to use V2G (Intention > 0)  =  opted in
  Gate 4: On the aggregator's contracted retailer (IEC by default)
  Gate 5: Actually discharges during the simulated week (kWh sold > 0)

Output: w8_sem_funnel.png  -- one panel per typology, each showing the
five gates as horizontal bars with percentages.
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
    COUNTERFACTUAL_V2G,
)
from src.aggregator_stub import AGGREGATOR_CONTRACTED_RETAILER
from src.pricing import price_at_hour


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

SAMPLES_PER_TYPOLOGY = 200
HOURS_IN_WEEK = 168

GATE_COLORS = [
    "#9ca3af",   # total (grey)
    "#3b82f6",   # V2G-capable (blue)
    "#10b981",   # positive Attitude (green)
    "#16a34a",   # positive Intention (darker green)
    "#f59e0b",   # passes retailer gate (amber)
    "#dc2626",   # actually discharges (red)
]
GATE_LABELS = [
    "Total agents sampled",
    "Gate 1: V2G-capable (home charger)",
    "Gate 2: Attitude > 0",
    "Gate 3: Intention > 0 (opted in)",
    f"Gate 4: Retailer = {AGGREGATOR_CONTRACTED_RETAILER}",
    "Gate 5: Actually discharges (>0 kWh)",
]


def sample_and_simulate(typology: str, n: int) -> list[dict]:
    """Build n agents of the given typology, simulate each for one week."""
    ev_agent_module.SEM_ENABLED = True
    t_idx = list(ALL_TYPOLOGIES).index(typology)
    recs = []
    for car_idx in range(n):
        # Use a wide-spaced agent_id so seeds are diverse across the sample.
        agent_id = t_idx * 1_000_000 + car_idx
        a = EVAgent(agent_id=agent_id, typology=typology, counterfactual=COUNTERFACTUAL_V2G)
        # Simulate one week to find out if the agent actually discharges.
        for hour in range(HOURS_IN_WEEK):
            hour_of_day = hour % 24
            day_of_week = (hour // 24) % 7
            price = price_at_hour(hour_of_day, day_of_week)
            a.step(current_hour=hour, current_price_per_kwh=price)
        kwh_sold = sum(-r["energy_kwh"] for r in a.hourly_log if r["action"] == "DISCHARGE")
        recs.append({
            "v2g_capable":     a.state.v2g_capable,
            "attitude_pos":    a.state.attitude_towards_v2g > 0,
            "intention_pos":   a.state.intention_to_use_v2g > 0,
            "on_iec_retailer": a.state.retailer == AGGREGATOR_CONTRACTED_RETAILER,
            "discharges":      kwh_sold > 0,
        })
    return recs


def funnel_counts(recs: list[dict]) -> list[int]:
    """Return the count of agents passing each cumulative gate."""
    n = len(recs)
    counts = [n]
    # gate 1: v2g_capable
    survivors = [r for r in recs if r["v2g_capable"]]
    counts.append(len(survivors))
    # gate 2: positive Attitude (cumulative)
    survivors = [r for r in survivors if r["attitude_pos"]]
    counts.append(len(survivors))
    # gate 3: positive Intention (cumulative)
    survivors = [r for r in survivors if r["intention_pos"]]
    counts.append(len(survivors))
    # gate 4: on IEC
    survivors = [r for r in survivors if r["on_iec_retailer"]]
    counts.append(len(survivors))
    # gate 5: actually discharges
    survivors = [r for r in survivors if r["discharges"]]
    counts.append(len(survivors))
    return counts


def draw_funnel(ax, typology: str, counts: list[int]) -> None:
    y = np.arange(len(counts))[::-1]
    total = counts[0]
    percentages = [100.0 * c / total for c in counts]
    ax.barh(y, percentages, color=GATE_COLORS, edgecolor="white", linewidth=0.5)
    for yi, (label, pct, cnt) in enumerate(zip(GATE_LABELS, percentages, counts)):
        y_pos = len(counts) - 1 - yi
        ax.text(pct + 1.5, y_pos, f"{pct:.0f}%   ({cnt}/{total})",
                fontsize=9, va="center")
    ax.set_yticks(y)
    ax.set_yticklabels(GATE_LABELS, fontsize=9)
    ax.set_xlim(0, 115)
    ax.set_xlabel("Share of sample (%)")
    ax.set_title(typology, fontsize=12, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def main() -> None:
    print(f"Sampling {SAMPLES_PER_TYPOLOGY} agents per typology and simulating each for one week...")
    all_counts = {}
    for typology in ALL_TYPOLOGIES:
        recs = sample_and_simulate(typology, SAMPLES_PER_TYPOLOGY)
        all_counts[typology] = funnel_counts(recs)
        print(f"  {typology:<20}  done")

    fig, axes = plt.subplots(2, 2, figsize=(18, 11))
    for ax, typology in zip(axes.flat, ALL_TYPOLOGIES):
        draw_funnel(ax, typology, all_counts[typology])

    fig.suptitle(
        f"V2G participation funnel per typology  (n = {SAMPLES_PER_TYPOLOGY} per typology, retailer gate ON)",
        fontsize=14, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    out = OUTPUTS_DIR / "w8_sem_funnel.png"
    fig.savefig(out, dpi=150, facecolor="white")
    print(f"Saved {out}")

    # Print numeric summary
    print()
    print(f"{'Typology':>20} | " + " | ".join(f"{g:>15}" for g in
        ["total", "V2G-capable", "Attitude>0", "Intention>0", "on IEC", "discharges"]))
    print("-" * 120)
    for typology in ALL_TYPOLOGIES:
        c = all_counts[typology]
        print(f"{typology:>20} | " + " | ".join(f"{x:>15}" for x in c))


if __name__ == "__main__":
    main()
