"""Apples-to-apples: Israel retail (TAOZ) vs UK retail (Power Pack).

Same layer of the market on both sides.  UK aggregator/ancillary is shown
separately on a supplementary panel to make the like-for-like nature of
the headline explicit.
"""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt

from src.plot_style import apply_style, PALETTE
apply_style()
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "outputs" / "w12m_retail_vs_retail.png"

# Per-opted-in-EV annual V2G volumes (model output)
ACTIVE = {"Daily Charger": 4820, "BEV 2nd Vehicle": 6220}
IL_RETAIL_PEAK = 1.6895   # NIS/kWh
UK_POWER_PACK  = 0.12     # GBP/kWh
UK_SCIURUS_TOT = 725.0    # GBP/yr, total (arbitrage + DC)
GBP_TO_NIS     = 4.7

# V2G premiums (Sigenergy installed minus smart unidirectional baseline)
IL_PREMIUM_NIS = 22_650 - 3_300      # ~19,350 NIS
UK_PREMIUM_GBP = (20_700 - 3_300) / GBP_TO_NIS   # ~3,702 GBP


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    typs = list(ACTIVE.keys())
    x = np.arange(len(typs))
    w = 0.35

    # ----- LEFT: apples-to-apples retail comparison in NIS-equivalent
    # NET revenue after off-peak recharge (subtract kWh/RTE * off-peak).
    ax = axes[0]
    IL_OFFPEAK = 0.528
    RTE = 0.9025
    il_rev = [ACTIVE[t] * IL_RETAIL_PEAK - ACTIVE[t] / RTE * IL_OFFPEAK for t in typs]
    UK_GO_OFFPEAK = 0.070
    uk_rev_gbp = [ACTIVE[t] * UK_POWER_PACK - ACTIVE[t] / RTE * UK_GO_OFFPEAK
                  for t in typs]   # NET, same basis as Israel
    uk_rev_nis = [r * GBP_TO_NIS for r in uk_rev_gbp]

    b1 = ax.bar(x - w/2, il_rev, w, color="#0f766e",
                label="Israel retail (TAOZ 1.6895 NIS/kWh)",
                edgecolor="white")
    b2 = ax.bar(x + w/2, uk_rev_nis, w, color="#1d4ed8",
                label="UK retail NET (12 p export less 7 p Go recharge)",
                edgecolor="white")

    for b, v_il, v_uk_gbp in zip(range(len(typs)), il_rev, uk_rev_gbp):
        ax.text(x[b] - w/2, il_rev[b] + 200,
                f"{il_rev[b]:,.0f} NIS", ha="center",
                fontsize=11.5, fontweight="bold")
        ax.text(x[b] + w/2, uk_rev_nis[b] + 200,
                f"{uk_rev_nis[b]:,.0f} NIS\n({v_uk_gbp:,.0f} GBP)",
                ha="center", fontsize=11.5, fontweight="bold")

    ax.set_xticks(x); ax.set_xticklabels(typs, fontsize=11)
    ax.set_ylabel("Annual NET V2G revenue per opted-in EV (NIS-equivalent)",
                  fontsize=11)
    ax.set_title("Retail vs retail, NET basis",
                 fontsize=14.0, fontweight="bold")
    ax.legend(loc="upper left", fontsize=13.0, framealpha=0.95)
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(0, max(il_rev) * 1.30)

    # ----- RIGHT: supplementary UK-with-ancillary and IL-gap
    ax = axes[1]
    scenarios = ["UK retail\n(Power Pack)",
                 "UK retail +\nDC ancillary\n(Sciurus)",
                 "Israel retail\n(TAOZ)",
                 "Israel retail +\nancillary\n(no market yet)"]
    vals_gbp = [
        ACTIVE["Daily Charger"] * (UK_POWER_PACK - 0.070 / 0.9025),   # UK retail NET
        UK_SCIURUS_TOT,                            # UK retail + DC
        ACTIVE["Daily Charger"] * IL_RETAIL_PEAK / GBP_TO_NIS,  # IL retail
        0.0,                                       # IL retail + ancillary unknown
    ]
    colors = ["#1d4ed8", "#0f766e", "#0f766e", "#475569"]
    hatches = ["", "", "", "//"]
    bars = ax.bar(scenarios, vals_gbp, color=colors, edgecolor="white",
                  hatch=hatches)
    for b, v in zip(bars, vals_gbp):
        if v > 0:
            ax.text(b.get_x() + b.get_width()/2, v + 30,
                    f"GBP {v:,.0f}", ha="center",
                    fontsize=11.5, fontweight="bold")
        else:
            ax.text(b.get_x() + b.get_width()/2, 100,
                    "no data", ha="center", fontsize=11.5,
                    fontweight="bold", color="#475569",
                    style="italic")

    ax.set_ylabel("Annual V2G revenue per active EV (GBP)", fontsize=11)
    ax.set_title("Full market picture (Daily Charger)",
                 fontsize=14.0, fontweight="bold")
    ax.set_ylim(0, max(vals_gbp) * 1.30)
    ax.grid(True, axis="y", alpha=0.3)
    ax.tick_params(axis="x", labelsize=9)

    pass
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
