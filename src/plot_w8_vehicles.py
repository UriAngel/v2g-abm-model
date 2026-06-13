"""W8 Batch E diagnostic: vehicle mix, chemistry split and aging cost.

Three panels:
  (a) Vehicle model market share per country, side by side.
  (b) Chemistry split (LFP vs NMC) per country.
  (c) Aging cost per kWh discharged by chemistry, plus net effect on OSP.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

from src.vehicle_catalog import (
    VEHICLE_CATALOG,
    MARKET_SHARES_ISRAEL,
    MARKET_SHARES_UK,
    chemistry_share_per_country,
)
from src.battery_aging import (
    aging_cost_per_kwh_discharged,
    cycle_aging_coefficient,
    battery_replacement_cost,
)


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


def panel_vehicle_mix(ax):
    countries = ["Israel", "United Kingdom"]
    vehicles = sorted(VEHICLE_CATALOG.keys())
    x = np.arange(len(countries))
    width = 0.7
    bottom = np.zeros(len(countries))
    cmap = plt.colormaps.get_cmap("tab20")
    for i, v in enumerate(vehicles):
        chemistry = VEHICLE_CATALOG[v]["chemistry"]
        # Colour: blue tones for NMC, green tones for LFP
        base = "#3b82f6" if chemistry == "NMC" else "#22c55e"
        shade_factor = 0.4 + 0.6 * (i / len(vehicles))
        color = cmap(i / len(vehicles))
        il = MARKET_SHARES_ISRAEL.get(v, 0) * 100
        uk = MARKET_SHARES_UK.get(v, 0) * 100
        heights = np.array([il, uk])
        ax.bar(x, heights, width, bottom=bottom, label=f"{v} ({chemistry})", color=color, edgecolor="white", linewidth=0.5)
        bottom = bottom + heights
    ax.set_xticks(x)
    ax.set_xticklabels(countries, fontsize=11)
    ax.set_ylabel("Market share (%)")
    ax.set_title("(a) Vehicle market shares 2024-25")
    ax.legend(fontsize=6, loc="center left", bbox_to_anchor=(1.0, 0.5), ncol=1)


def panel_chemistry_split(ax):
    countries = ["Israel", "United Kingdom"]
    mix = chemistry_share_per_country()
    x = np.arange(len(countries))
    width = 0.6
    lfp = np.array([mix[c]["LFP"] for c in countries]) * 100
    nmc = np.array([mix[c]["NMC"] for c in countries]) * 100
    ax.bar(x, lfp, width, label="LFP", color="#22c55e")
    ax.bar(x, nmc, width, bottom=lfp, label="NMC", color="#3b82f6")
    for i, c in enumerate(countries):
        ax.text(i, lfp[i] / 2, f"{lfp[i]:.0f}% LFP", ha="center", fontsize=11, fontweight="bold", color="white")
        ax.text(i, lfp[i] + nmc[i] / 2, f"{nmc[i]:.0f}% NMC", ha="center", fontsize=11, fontweight="bold", color="white")
    ax.set_xticks(x)
    ax.set_xticklabels(countries, fontsize=11)
    ax.set_ylabel("Chemistry share (%)")
    ax.set_title("(b) Battery chemistry split per country")
    ax.set_ylim(0, 110)
    ax.legend(fontsize=10)


def panel_aging_cost(ax):
    chemistries = ["NMC", "LFP"]
    cycle_coefs = [cycle_aging_coefficient(c) for c in chemistries]
    repl_costs  = [battery_replacement_cost(c) for c in chemistries]
    aging_costs = [aging_cost_per_kwh_discharged(c) for c in chemistries]

    # Side-by-side bars: cycle coefficient (left axis) and aging cost (right axis)
    x = np.arange(len(chemistries))
    width = 0.35

    # Left bars: cycle aging coefficient (per kWh, scaled by 1e6 for readability)
    ax.bar(x - width/2, np.array(cycle_coefs) * 1e6, width,
           label="Cycle aging coef × 1e6 (SoH loss / kWh)", color="#dc2626")
    # Right bars: aging cost
    ax2 = ax.twinx()
    ax2.bar(x + width/2, aging_costs, width, label="Aging cost (NIS/kWh)", color="#1f2937")

    for i, (c, cost) in enumerate(zip(chemistries, aging_costs)):
        ax.text(i - width/2, cycle_coefs[i] * 1e6 + 0.05, f"{cycle_coefs[i]*1e6:.2f}",
                ha="center", fontsize=10)
        ax2.text(i + width/2, cost + 0.00005, f"{cost:.4f}", ha="center", fontsize=10)

    ax.set_xticks(x)
    ax.set_xticklabels(chemistries, fontsize=11)
    ax.set_ylabel("Cycle coefficient (SoH/kWh, × 1e6)", color="#dc2626")
    ax2.set_ylabel("Aging cost (NIS/kWh)", color="#1f2937")
    ax.set_title("(c) Chemistry-dependent aging  (LFP: more wear, cheaper pack)")
    ax.tick_params(axis="y", labelcolor="#dc2626")
    ax2.tick_params(axis="y", labelcolor="#1f2937")
    # Combined legend
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")


def main() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(22, 7))
    panel_vehicle_mix(axes[0])
    panel_chemistry_split(axes[1])
    panel_aging_cost(axes[2])

    fig.suptitle(
        "Vehicle catalogue + chemistry split (Israel vs UK, 2024-25)",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    out = OUTPUTS_DIR / "w8_vehicles.png"
    fig.savefig(out, dpi=150, facecolor="white", bbox_inches="tight")
    print(f"Saved {out}")

    # Print summary
    print()
    mix = chemistry_share_per_country()
    print(f"Israel:         {mix['Israel']['LFP']*100:.0f}% LFP, {mix['Israel']['NMC']*100:.0f}% NMC")
    print(f"United Kingdom: {mix['United Kingdom']['LFP']*100:.0f}% LFP, {mix['United Kingdom']['NMC']*100:.0f}% NMC")
    print()
    print(f"Aging cost NMC: {aging_cost_per_kwh_discharged('NMC'):.4f} NIS/kWh")
    print(f"Aging cost LFP: {aging_cost_per_kwh_discharged('LFP'):.4f} NIS/kWh")


if __name__ == "__main__":
    main()
