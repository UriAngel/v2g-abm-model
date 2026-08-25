"""Two introductory diagrams for Chapter 1.

  1. w15a_v2g_basic.png   - what V2G is: grid, home, EV, two directions of flow
  2. w15b_actors.png      - the residential V2G value chain: actors, electricity
                            and money flows

Run:  python -m src.plot_w15_intro_diagrams
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from src.plot_style import apply_style, PALETTE

apply_style()

OUT = Path(__file__).resolve().parent.parent / "outputs"


def _box(ax, x, y, w, h, label, sub, color, text_color="white", fs=15, sub_fs=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.06,rounding_size=0.12",
                                facecolor=color, edgecolor="none"))
    ax.text(x + w / 2, y + h * 0.62, label, ha="center", va="center",
            fontsize=fs, fontweight="bold", color=text_color)
    if sub:
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center",
                fontsize=sub_fs, color=text_color, alpha=0.92)


def _arrow(ax, x0, y0, x1, y1, color, label=None, ly=0.32, style="-", lw=3.2,
           fs=12, label_color=None, rad=0.0):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1),
                                 arrowstyle="-|>", mutation_scale=26,
                                 linewidth=lw, linestyle=style, color=color,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + ly, label, ha="center",
                fontsize=fs, fontweight="bold",
                color=label_color or color)


def fig_basic() -> None:
    fig, ax = plt.subplots(figsize=(12, 5.2))
    ax.set_xlim(0, 12); ax.set_ylim(0, 6); ax.axis("off")

    _box(ax, 0.4, 2.2, 2.9, 1.9, "Grid", "power stations,\nsolar at midday",
         PALETTE["neutral"])
    _box(ax, 4.55, 2.2, 2.9, 1.9, "Home", "meter and\nbidirectional charger",
         PALETTE["israel"])
    _box(ax, 8.7, 2.2, 2.9, 1.9, "EV battery", "a store on wheels,\nparked 90% of the time",
         PALETTE["uk"])

    # top arrows: off-peak, left to right (charging)
    _arrow(ax, 3.5, 4.35, 4.4, 4.35, PALETTE["israel"], None)
    _arrow(ax, 7.6, 4.35, 8.5, 4.35, PALETTE["israel"], None)
    ax.text(6.0, 5.35, "Off-peak (night and midday): cheap energy charges the car",
            ha="center", fontsize=13, fontweight="bold", color=PALETTE["israel"])
    ax.plot([1.85, 1.85], [4.15, 4.55], color="white", lw=0)  # spacing anchor

    # bottom arrows: peak, right to left (discharging)
    _arrow(ax, 8.5, 1.75, 7.6, 1.75, PALETTE["cost"], None)
    _arrow(ax, 4.4, 1.75, 3.5, 1.75, PALETTE["cost"], None)
    ax.text(6.0, 0.62, "Evening peak: the car powers the home and exports to the grid",
            ha="center", fontsize=13, fontweight="bold", color=PALETTE["cost"])

    ax.set_title("Vehicle-to-Grid in one picture", fontsize=15)
    fig.tight_layout()
    out = OUT / "w15a_v2g_basic.png"
    fig.savefig(out)
    print(f"Saved {out}")


def fig_actors() -> None:
    fig, ax = plt.subplots(figsize=(12, 6.8))
    ax.set_xlim(0, 12); ax.set_ylim(0, 8); ax.axis("off")

    _box(ax, 0.4, 5.6, 3.2, 1.8, "EV owner", "provides the battery,\nplugs in at home",
         PALETTE["uk"])
    _box(ax, 8.4, 5.6, 3.2, 1.8, "Aggregator", "recruits and contracts owners,\ncontrols dispatch",
         PALETTE["israel"])
    _box(ax, 8.4, 0.6, 3.2, 1.8, "Electricity supplier", "billing, tariffs,\nmarket access",
         PALETTE["neutral"])
    _box(ax, 0.4, 0.6, 3.2, 1.8, "Grid / system operator", "network, balancing,\navoided peak cost",
         PALETTE["cost"])

    # contracts and control (dashed, money): both flow aggregator -> owner
    _arrow(ax, 8.3, 6.7, 3.7, 6.7, PALETTE["amber"], "revenue share",
           ly=0.3, style="--", lw=2.4, fs=12.5)
    _arrow(ax, 8.3, 6.05, 3.7, 6.05, PALETTE["israel"], "dispatch commands",
           ly=-0.55, lw=2.4, fs=12.5)
    _arrow(ax, 10.0, 5.5, 10.0, 2.55, PALETTE["amber"], None,
           style="--", lw=2.4)
    ax.text(9.8, 4.0, "flexibility sold,\nsettlement", ha="right",
            fontsize=12.5, fontweight="bold", color=PALETTE["amber"])
    _arrow(ax, 8.3, 1.5, 3.7, 1.5, PALETTE["amber"], "payment for\navoided system cost",
           ly=0.55, style="--", lw=2.4, fs=12.5)

    # electricity (solid)
    _arrow(ax, 2.0, 5.5, 2.0, 2.55, PALETTE["uk"], None, lw=3.2)
    ax.text(2.25, 4.0, "discharge at peak,\ncharge off-peak", ha="left",
            fontsize=12.5, fontweight="bold", color=PALETTE["uk"])

    ax.text(6.0, 3.1, "Electricity flows once, money flows in a circle:\n"
                      "the consumer's bill funds every payment in the chain",
            ha="center", fontsize=12.5, style="italic", color=PALETTE["neutral"])

    ax.set_title("The residential V2G value chain", fontsize=15)
    fig.text(0.5, 0.02, "Solid arrows carry electricity and control; dashed arrows carry money.",
             ha="center", fontsize=11.5, style="italic", color=PALETTE["neutral"])
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out = OUT / "w15b_actors.png"
    fig.savefig(out)
    print(f"Saved {out}")


def main() -> None:
    fig_basic()
    fig_actors()


if __name__ == "__main__":
    main()
