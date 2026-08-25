"""The representative vehicle as the scaling unit (Figure 5.4).

Left panel:  what one simulated participating vehicle does in a year,
             by typology (fleet means from the 240-agent run).
Right panel: the multiplication chain from that vehicle to the national
             estimates of Figure 5.3(b).

Run:  python -m src.plot_w15d_representative_vehicle
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from src.plot_style import apply_style, PALETTE
from src.fleet_assumptions import N_FLEET_ISRAEL

apply_style()

OUT = Path(__file__).resolve().parent.parent / "outputs" / "w15d_representative_vehicle.png"

TYPS = ["Daily\nCharger", "BEV 2nd\nVehicle", "Public\nCharger", "Threshold\nCharger"]
KWH = [4820, 6220, 0, 0]
NET = [5323, 6870, 0, 0]


def main() -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.6), width_ratios=[1, 1.15])

    x = np.arange(4); bw = 0.55
    colors = [PALETTE["israel"], PALETTE["uk"], "#94a3b8", "#94a3b8"]
    ax1.bar(x, KWH, bw, color=colors)
    for i in range(4):
        if KWH[i] > 0:
            ax1.text(x[i], KWH[i] + 640, f"{KWH[i]:,} kWh", ha="center",
                     fontsize=12, fontweight="bold", color=colors[i])
            ax1.text(x[i], KWH[i] + 170, f"nets {NET[i]:,} NIS", ha="center",
                     fontsize=10.5, fontweight="bold", color=colors[i])
        else:
            ax1.text(x[i], 180, "structural\nzero", ha="center", fontsize=10.5,
                     color="#64748b", style="italic")
    ax1.set_xticks(x); ax1.set_xticklabels(TYPS, fontsize=11.5)
    ax1.set_ylabel("Annual V2G dispatch per participating vehicle (kWh)")
    ax1.set_title("(a) One simulated vehicle, by typology\n(fleet means, 240-agent run, Israel)",
                  fontsize=12.5, loc="center")
    ax1.set_ylim(0, 7600)

    # right: multiplication chain
    ax2.set_xlim(0, 10); ax2.set_ylim(0, 10); ax2.axis("off")

    def box(y, label, sub, color, h=1.7):
        ax2.add_patch(FancyBboxPatch((1.2, y), 7.6, h,
                                     boxstyle="round,pad=0.05,rounding_size=0.1",
                                     facecolor=color, edgecolor="none"))
        ax2.text(5.0, y + h*0.62, label, ha="center", va="center",
                 fontsize=12.5, fontweight="bold", color="white")
        ax2.text(5.0, y + h*0.25, sub, ha="center", va="center",
                 fontsize=10.5, color="white", alpha=0.95)

    def arrow(y0, y1, label):
        ax2.add_patch(FancyArrowPatch((5.0, y0), (5.0, y1), arrowstyle="-|>",
                                      mutation_scale=22, lw=2.4, color=PALETTE["neutral"]))
        ax2.text(5.35, (y0+y1)/2, label, ha="left", va="center",
                 fontsize=11, fontweight="bold", color=PALETTE["neutral"])

    box(8.1, "The representative vehicle", "~6,100 NIS net pool per participant-year (typology mean)",
        PALETTE["israel"])
    arrow(8.0, 6.75, "x participating fleet")
    box(5.0, "Participating fleet", "alpha x beta*gamma x 3.5M cars  (funnel-passing vehicles)",
        PALETTE["uk"], h=1.7)
    arrow(4.9, 3.65, "= national pool")
    box(1.9, "National NET V2G pool", "alpha 0.30 x bg 0.2  ->  ~1.3 bn NIS / yr  (Fig. 5.3b)",
        "#0a4f49", h=1.7)
    ax2.text(5.0, 0.85, "valid while the feeder constraint of Fig. 5.3(a) is slack;\n"
             "beyond it, a learned surrogate must replace the linear scale-up",
             ha="center", fontsize=10, style="italic", color=PALETTE["neutral"])
    ax2.set_title("(b) From one vehicle to the national estimate", fontsize=12.5, loc="center")

    fig.tight_layout()
    fig.savefig(OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
