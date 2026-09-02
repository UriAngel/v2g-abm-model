"""Simple 24-hour UK pricing visualisation for the deck.

Shows V0 (Ofgem cap, flat), V1G (Octopus Go), V2G (Octopus Go import
with Powerloop export overlay) across a single day.
"""

from pathlib import Path
import matplotlib.pyplot as plt
from src.plot_style import apply_style
apply_style()
import numpy as np
from src.pricing_uk import (
    OFGEM_CAP_RATE_GBP, OCTOPUS_GO_OFFPEAK_GBP, OCTOPUS_GO_PEAK_GBP,
    OCTOPUS_GO_OFFPEAK_START_HOUR, OCTOPUS_GO_OFFPEAK_END_HOUR,
    POWERLOOP_EXPORT_GBP, POWERLOOP_DISCHARGE_START_HOUR, POWERLOOP_DISCHARGE_END_HOUR,
    ofgem_cap_rate_at_hour, octopus_go_rate_at_hour, octopus_powerloop_export_at_hour,
)


OUT = Path(__file__).resolve().parent.parent / "outputs" / "uk_pricing_24h.png"


def main() -> None:
    hours = np.arange(24)
    ofgem = np.array([ofgem_cap_rate_at_hour(h) for h in hours]) * 100   # to p/kWh
    octgo = np.array([octopus_go_rate_at_hour(h) for h in hours]) * 100
    export = np.array([octopus_powerloop_export_at_hour(h) for h in hours]) * 100

    fig, ax = plt.subplots(figsize=(14, 6.8))

    # V0 - flat Ofgem
    ax.plot(hours, ofgem, color="#9ca3af", linewidth=3,
            label=f"V0: Ofgem default cap ({OFGEM_CAP_RATE_GBP*100:.1f} p/kWh, flat)",
            drawstyle="steps-post")

    # V1G - Octopus Go
    ax.plot(hours, octgo, color="#1f77b4", linewidth=3,
            label=f"V1G: Octopus Go ({OCTOPUS_GO_OFFPEAK_GBP*100:.1f}p off-peak  /  {OCTOPUS_GO_PEAK_GBP*100:.1f}p peak)",
            drawstyle="steps-post")

    # V2G export overlay
    export_mask = export > 0
    ax.fill_between(np.arange(25)[:24], 0, export, where=export_mask, step="post",
                    color="#10b981", alpha=0.35,
                    label=f"V2G: Powerloop export ({POWERLOOP_EXPORT_GBP*100:.1f} p/kWh paid TO driver, 16:00 to 19:00)")
    ax.plot(hours, export, color="#10b981", linewidth=2.5,
            drawstyle="steps-post")

    # Annotations
    ax.axvspan(OCTOPUS_GO_OFFPEAK_START_HOUR, OCTOPUS_GO_OFFPEAK_END_HOUR,
               color="#dbeafe", alpha=0.4, zorder=0)
    ax.text(2.5, 33, "Octopus Go\noff-peak window",
            ha="center", fontsize=11.5, color="#1f3864", style="italic")
    ax.text(17.5, 25, "Powerloop\nexport window",
            ha="center", fontsize=11.5, color="#065f46", style="italic")

    ax.set_xlabel("Hour of day", fontsize=12)
    ax.set_ylabel("Rate (pence per kWh)", fontsize=12)
    ax.set_xlim(0, 23)
    ax.set_ylim(0, 35)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)])
    ax.set_title("UK three-tariff structure for the V2G model  (24-hour view)",
                 fontsize=14, fontweight="bold")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=11.5, framealpha=0.95)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT, dpi=200, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
