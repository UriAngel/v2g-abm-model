"""Figure 4.7: per-vehicle NET pool under the 75/25 split (single panel).

Run:  python -m src.plot_w11b_single
"""

import matplotlib.pyplot as plt
import numpy as np

from src.plot_style import apply_style, PALETTE

apply_style()

KWH = {"Daily Charger": 4820, "BEV 2nd Vehicle": 6220}
PEAK, OFF, RTE = 1.6895, 0.528, 0.9025
IL_NET = sum(k * PEAK - k / RTE * OFF for k in KWH.values()) / 2
UK_NET_GBP = 725
GBP_TO_NIS = 4.70
VALS = {"Israel": IL_NET, "UK (Sciurus)": UK_NET_GBP * GBP_TO_NIS}
DR, AG = 0.75, 0.25


def main() -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    x = np.arange(2); bw = 0.5
    drv = [VALS[c] * DR for c in VALS]
    agg = [VALS[c] * AG for c in VALS]
    ax.bar(x, drv, bw, color=PALETTE["israel"], label="Driver share (75%)")
    ax.bar(x, agg, bw, bottom=drv, color=PALETTE["uk"], label="Aggregator share (25%)")
    for i, c in enumerate(VALS):
        ax.text(x[i], drv[i] / 2, f"{drv[i]:,.0f}", ha="center", va="center",
                fontsize=13, fontweight="bold", color="white")
        ax.text(x[i], drv[i] + agg[i] / 2, f"{agg[i]:,.0f}", ha="center", va="center",
                fontsize=13, fontweight="bold", color="white")
        ax.text(x[i], drv[i] + agg[i] + 150, f"pool {VALS[c]:,.0f} NIS-eq", ha="center",
                fontsize=12, fontweight="bold", color=PALETTE["neutral"])
    ax.set_xticks(x); ax.set_xticklabels(list(VALS), fontsize=13)
    ax.set_ylabel("NET pool per V2G-active EV (NIS-eq / yr)", fontsize=12)
    ax.set_title("Aggregator unit economics", fontsize=17.5, fontweight="bold", loc="center")
    ax.legend(fontsize=11.5, loc="upper right")
    ax.set_ylim(0, max(VALS.values()) * 1.22)
    fig.text(0.5, 0.02, "Israel: TAOZ arbitrage net of recharge (model output).  "
             "UK: Cenex (2021) Sciurus total earnings at 4.70 NIS/GBP.",
             ha="center", fontsize=9.5, color=PALETTE["neutral"], style="italic")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig("outputs/w11b_aggregator_per_ev_single.png")
    print("Saved outputs/w11b_aggregator_per_ev_single.png")


if __name__ == "__main__":
    main()
