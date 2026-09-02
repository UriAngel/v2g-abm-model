"""Two introductory diagrams for Chapter 1 (v2 after supervisor round).

  1. w15a_v2g_basic.png   - car + pylon illustration: off-peak flow one way,
                            evening-peak flow the other way
  2. w15b_actors.png      - the V2G value chain with the supplier-owner
                            billing relationship included

Run:  python -m src.plot_w15_intro_diagrams
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Polygon

from src.plot_style import apply_style, PALETTE

apply_style()

OUT = Path(__file__).resolve().parent.parent / "outputs"


def draw_car(ax, cx, cy, scale=1.0, color="#1d4ed8"):
    """Simple side-view EV silhouette centred at (cx, cy)."""
    s = scale
    body = [(cx-2.2*s, cy), (cx+2.2*s, cy), (cx+2.05*s, cy+0.55*s),
            (cx+1.1*s, cy+0.72*s), (cx+0.75*s, cy+1.25*s),
            (cx-1.05*s, cy+1.25*s), (cx-1.75*s, cy+0.68*s), (cx-2.2*s, cy+0.55*s)]
    ax.add_patch(Polygon(body, closed=True, facecolor=color, edgecolor="none"))
    for wx in (cx-1.25*s, cx+1.25*s):
        ax.add_patch(Circle((wx, cy), 0.42*s, facecolor="#0f172a", edgecolor="white", lw=2*s, zorder=5))
        ax.add_patch(Circle((wx, cy), 0.17*s, facecolor="#94a3b8", edgecolor="none", zorder=6))
    # window
    win = [(cx-0.85*s, cy+0.72*s), (cx+0.55*s, cy+0.72*s), (cx+0.35*s, cy+1.1*s), (cx-0.75*s, cy+1.1*s)]
    ax.add_patch(Polygon(win, closed=True, facecolor="#dbeafe", edgecolor="none"))
    # charge port flash
    ax.text(cx+1.9*s, cy+0.95*s, "⚡", fontsize=20*s, ha="center", va="center", color=PALETTE["amber"])


def draw_pylon(ax, cx, base_y, h=3.2, color="#475569"):
    w0, w1 = 1.15, 0.34
    ax.plot([cx-w0, cx-w1], [base_y, base_y+h], color=color, lw=3)
    ax.plot([cx+w0, cx+w1], [base_y, base_y+h], color=color, lw=3)
    n = 5
    for i in range(n+1):
        f0, f1 = i/n, (i+1)/n
        y0, y1 = base_y+h*f0, base_y+h*f1
        xl0 = cx - (w0 + (w1-w0)*f0); xr0 = cx + (w0 + (w1-w0)*f0)
        xl1 = cx - (w0 + (w1-w0)*f1); xr1 = cx + (w0 + (w1-w0)*f1)
        ax.plot([xl0, xr0], [y0, y0], color=color, lw=1.6)
        if i < n:
            ax.plot([xl0, xr1], [y0, y1], color=color, lw=1.1)
            ax.plot([xr0, xl1], [y0, y1], color=color, lw=1.1)
    # cross-arms
    for dy, arm in ((h*0.98, 0.95), (h*0.80, 0.75)):
        y = base_y+dy
        ax.plot([cx-arm, cx+arm], [y, y], color=color, lw=3)
        for ex in (-arm, arm):
            ax.plot([ex+cx, ex+cx], [y, y-0.16], color=color, lw=1.6)
            ax.add_patch(Circle((ex+cx, y-0.2), 0.045, facecolor=color))


def fig_basic() -> None:
    fig, ax = plt.subplots(figsize=(12, 5.4))
    ax.set_xlim(0, 12); ax.set_ylim(0, 6.2); ax.axis("off")

    draw_pylon(ax, 2.1, 1.15, h=3.4)
    ax.text(2.1, 0.62, "the grid", ha="center", fontsize=13, fontweight="bold", color=PALETTE["neutral"])
    draw_car(ax, 9.3, 1.35, scale=1.05, color=PALETTE["uk"])
    ax.text(9.3, 0.62, "the EV", ha="center", fontsize=13, fontweight="bold", color=PALETTE["uk"])

    # top: off-peak, grid -> car
    ax.add_patch(FancyArrowPatch((3.6, 4.15), (7.6, 4.15), arrowstyle="-|>",
                                 mutation_scale=34, lw=4, color=PALETTE["israel"]))
    ax.text(5.6, 4.55, "off-peak (night and midday)", ha="center",
            fontsize=13.5, fontweight="bold", color=PALETTE["israel"])
    ax.text(5.6, 3.72, "cheap electricity charges the car", ha="center",
            fontsize=11.5, color=PALETTE["israel"])

    # bottom: evening peak, car -> grid
    ax.add_patch(FancyArrowPatch((7.6, 2.35), (3.6, 2.35), arrowstyle="-|>",
                                 mutation_scale=34, lw=4, color=PALETTE["cost"]))
    ax.text(5.6, 2.72, "evening peak (17:00-22:00)", ha="center",
            fontsize=13.5, fontweight="bold", color=PALETTE["cost"])
    ax.text(5.6, 1.92, "the car sends electricity back", ha="center",
            fontsize=11.5, color=PALETTE["cost"])

    ax.set_title("Vehicle-to-Grid: one battery, two directions", fontsize=15)
    fig.tight_layout()
    fig.savefig(OUT / "w15a_v2g_basic.png")
    print("Saved", OUT / "w15a_v2g_basic.png")


def _box(ax, x, y, w, h, label, sub, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.06,rounding_size=0.12",
                                facecolor=color, edgecolor="none"))
    ax.text(x+w/2, y+h*0.63, label, ha="center", va="center",
            fontsize=14.5, fontweight="bold", color="white")
    if sub:
        ax.text(x+w/2, y+h*0.27, sub, ha="center", va="center",
                fontsize=10.5, color="white", alpha=0.92)


def _arr(ax, p0, p1, color, style="-", lw=2.6, rad=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=24,
                                 linewidth=lw, linestyle=style, color=color,
                                 connectionstyle=f"arc3,rad={rad}"))


def fig_actors() -> None:
    """Three-tier layout: owner / market layer (supplier + aggregator) / grid."""
    fig, ax = plt.subplots(figsize=(11.5, 8.4))
    ax.set_xlim(0, 12); ax.set_ylim(0, 10.3); ax.axis("off")

    def vbox(x, y, w, h, label, sub, color, fs=14):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
                                    facecolor=color, edgecolor="none", zorder=3))
        ax.text(x+w/2, y+h*0.63, label, ha="center", va="center", fontsize=fs,
                fontweight="bold", color="white", zorder=4)
        if sub:
            ax.text(x+w/2, y+h*0.26, sub, ha="center", va="center", fontsize=10,
                    color="white", alpha=0.93, zorder=4)

    def varr(p0, p1, color, style="-", lw=2.6, z=2, ms=24):
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                                     linewidth=lw, linestyle=style, color=color, zorder=z))

    vbox(3.6, 8.2, 4.8, 1.75, "EV owner", "provides the battery,\nplugs in at home", PALETTE["uk"])
    ax.add_patch(FancyBboxPatch((0.75, 3.7), 10.5, 3.1, boxstyle="round,pad=0.08,rounding_size=0.18",
                                facecolor="#f1f5f9", edgecolor="#94a3b8", linewidth=1.6, zorder=1))
    vbox(1.25, 4.75, 3.8, 1.75, "Electricity supplier", "tariff, billing,\nsettlement of export", PALETTE["neutral"], fs=13)
    vbox(6.95, 4.75, 3.8, 1.75, "Aggregator", "EMS services: pooling,\ndispatch, grid products", PALETTE["israel"], fs=13)
    ax.text(6.0, 4.12, "the market layer: one company, or a supplier contracting an aggregator",
            ha="center", fontsize=11, style="italic", color="#475569", zorder=4)
    vbox(3.6, 0.5, 4.8, 1.75, "Grid and system\noperator", "wires, balancing,\navoided peak cost", PALETTE["cost"])

    # aggregator -> supplier: EMS services; supplier -> aggregator: fees
    varr((6.85, 5.62), (5.15, 5.62), "#475569", style="--", lw=1.8, z=1, ms=16)
    ax.text(6.0, 5.8, "EMS services", ha="center", fontsize=9.5, color="#475569", zorder=1)
    varr((5.15, 5.05), (6.85, 5.05), "#475569", style="--", lw=1.8, z=1, ms=16)
    ax.text(6.0, 4.82, "fees", ha="center", fontsize=9.5, color="#475569", zorder=1)

    varr((4.15, 8.1), (4.15, 6.9), PALETTE["amber"], style="--")
    varr((4.75, 6.9), (4.75, 8.1), PALETTE["amber"], style="--")
    ax.text(3.95, 7.62, "pays the bill", ha="right", fontsize=10.5, fontweight="bold", color=PALETTE["amber"])
    ax.text(3.95, 7.08, "export credit,\nrevenue share", ha="right", fontsize=10.5,
            fontweight="bold", color=PALETTE["amber"])

    varr((7.9, 6.9), (7.9, 8.1), PALETTE["israel"])
    ax.text(8.1, 7.5, "dispatch commands", ha="left", fontsize=11, fontweight="bold", color=PALETTE["israel"])

    varr((4.4, 3.6), (4.4, 2.35), PALETTE["amber"], style="--")
    ax.text(4.2, 3.0, "network charges,\nwholesale purchases", ha="right", fontsize=10.5,
            fontweight="bold", color=PALETTE["amber"])
    varr((7.6, 2.35), (7.6, 3.6), PALETTE["amber"], style="--")
    ax.text(7.8, 3.0, "payment for flexibility\nand balancing services", ha="left", fontsize=10.5,
            fontweight="bold", color=PALETTE["amber"])

    varr((5.62, 8.1), (5.62, 2.4), PALETTE["uk"], lw=3.4, z=2)
    varr((6.38, 2.4), (6.38, 8.1), "#0a8f66", lw=3.4, z=2)
    ax.text(5.36, 7.75, "discharge\nat peak", ha="right", fontsize=10.5, fontweight="bold", color=PALETTE["uk"])
    ax.text(6.56, 7.75, "charge\noff-peak", ha="left", fontsize=10.5, fontweight="bold", color="#0a8f66")

    fig.text(0.5, 0.02, "Dashed arrows carry money, solid arrows carry electricity and control.  "
             "No money passes between the owner and the grid directly.",
             ha="center", fontsize=10.5, style="italic", color="#475569")
    ax.set_title("The residential V2G value chain", fontsize=15)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(OUT / "w15b_actors.png")
    print("Saved", OUT / "w15b_actors.png")


def main() -> None:
    fig_basic()
    fig_actors()


if __name__ == "__main__":
    main()
