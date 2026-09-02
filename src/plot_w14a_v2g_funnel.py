"""The V2G Funnel: the general stages between a national vehicle fleet
and actual V2G participation.  No country numbers: the frame itself.

Run:  python -m src.plot_w14a_v2g_funnel
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from src.plot_style import apply_style, PALETTE

apply_style()

OUT = (Path(__file__).resolve().parent.parent
       / "outputs" / "w14a_v2g_funnel.png")

STAGES = [
    ("All registered vehicles", ""),
    ("\u03b1   electric", "electrification of the fleet"),
    ("\u03b21  V2L socket", "import mix: models carrying a household socket"),
    ("\u03b22  V2G potential", "discharge hardware built in at the factory"),
    ("\u03b23  V2G capable", "manufacturer switches it on: BMS software + warranty"),
    ("\u03b31  access", "home charger and a peak plug-in pattern (typology)"),
    ("\u03b32  willing", "the owner opts in (SEM willingness)"),
]

SHRINK = 0.82
H = 1.0
GAP = 0.22


def main() -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6.6))
    ax.set_xlim(0, 10)
    n = len(STAGES)
    ax.set_ylim(-(n * (H + GAP)) - 0.2, 0.55)
    ax.axis("off")

    xc, hw0 = 3.4, 2.6
    y = 0.0
    for i, (name, filt) in enumerate(STAGES):
        w_top = hw0 * (SHRINK ** i)
        w_bot = hw0 * (SHRINK ** (i + 1))
        poly = Polygon([(xc - w_top, y), (xc + w_top, y),
                        (xc + w_bot, y - H), (xc - w_bot, y - H)],
                       closed=True, facecolor=PALETTE["israel"],
                       edgecolor="white", linewidth=1.6, alpha=0.94)
        ax.add_patch(poly)
        ax.text(xc, y - H / 2, name, ha="center", va="center",
                fontsize=11.5 if i < 5 else 10.5, fontweight="bold",
                color="white")
        if filt:
            ax.annotate(filt, xy=(xc + w_top + 0.15, y - H / 2),
                        xytext=(7.0, y - H / 2), ha="left", va="center",
                        fontsize=11, color="#1e293b",
                        arrowprops=dict(arrowstyle="-", color="#94a3b8",
                                        linewidth=0.9))
        y -= (H + GAP)

    ax.set_title("The V2G Funnel: what stands between a vehicle fleet "
                 "and V2G participation", fontsize=15.0, fontweight="bold",
                 pad=12)

    fig.text(0.5, 0.015,
             "Each stage is measurable: \u03b1 and \u03b21-\u03b23 from a national vehicle registry, "
             "\u03b31 from driving typologies, \u03b32 from behavioural survey data.",
             ha="center", fontsize=11.5, color=PALETTE["neutral"])

    fig.tight_layout(rect=(0, 0.045, 1, 1))
    fig.savefig(OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
