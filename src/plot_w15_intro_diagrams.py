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
    fig, ax = plt.subplots(figsize=(12, 7.0))
    ax.set_xlim(0, 12); ax.set_ylim(0, 8.4); ax.axis("off")

    # layout: supplier left, owner centre, aggregator right, grid bottom-centre
    _box(ax, 0.3, 5.3, 3.0, 1.9, "Electricity\nsupplier", "tariff, billing,\nmarket access", PALETTE["neutral"])
    _box(ax, 4.5, 5.3, 3.0, 1.9, "EV owner", "provides the battery,\nplugs in at home", PALETTE["uk"])
    _box(ax, 8.7, 5.3, 3.0, 1.9, "Aggregator", "recruits owners,\ncontrols dispatch", PALETTE["israel"])
    _box(ax, 4.5, 0.6, 3.0, 1.9, "Grid", "carries the energy;\navoided peak cost\nfunds the chain", PALETTE["cost"])

    # supplier <-> owner (billing relationship)
    _arr(ax, (4.4, 6.75), (3.4, 6.75), PALETTE["amber"], style="--")
    ax.text(3.9, 7.0, "pays the bill", ha="center", fontsize=11, fontweight="bold", color=PALETTE["amber"])
    _arr(ax, (3.4, 5.75), (4.4, 5.75), PALETTE["amber"], style="--")
    ax.text(3.9, 5.28, "bills import,\nsettles export", ha="center", fontsize=11,
            fontweight="bold", color=PALETTE["amber"], va="top")

    # aggregator <-> owner
    _arr(ax, (8.6, 6.75), (7.6, 6.75), PALETTE["amber"], style="--")
    ax.text(8.1, 7.0, "revenue share", ha="center", fontsize=11, fontweight="bold", color=PALETTE["amber"])
    _arr(ax, (8.6, 5.75), (7.6, 5.75), PALETTE["israel"])
    ax.text(8.1, 5.28, "dispatch\ncommands", ha="center", fontsize=11,
            fontweight="bold", color=PALETTE["israel"], va="top")

    # owner <-> grid (electricity, both directions)
    _arr(ax, (5.6, 5.2), (5.6, 2.6), PALETTE["uk"], lw=3.2)
    ax.text(5.38, 3.9, "discharge\nat peak", ha="right", fontsize=11, fontweight="bold", color=PALETTE["uk"])
    _arr(ax, (6.4, 2.6), (6.4, 5.2), PALETTE["israel"], lw=3.2)
    ax.text(6.62, 3.9, "charge\noff-peak", ha="left", fontsize=11, fontweight="bold", color=PALETTE["israel"])

    # aggregator sells pooled flexibility to the supplier (arc over the top)
    _arr(ax, (10.2, 7.35), (1.8, 7.35), PALETTE["amber"], style="--", rad=0.16)
    ax.text(6.0, 8.33, "sells the pooled flexibility of many vehicles",
            ha="center", fontsize=11.5, fontweight="bold", color=PALETTE["amber"])

    fig.text(0.5, 0.03, "Solid arrows carry electricity and control; dashed arrows carry money.  "
             "Every payment in the chain is funded from the consumer's bill.",
             ha="center", fontsize=11, style="italic", color=PALETTE["neutral"])
    ax.set_title("The residential V2G value chain", fontsize=15)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUT / "w15b_actors.png")
    print("Saved", OUT / "w15b_actors.png")


def main() -> None:
    fig_basic()
    fig_actors()


if __name__ == "__main__":
    main()
