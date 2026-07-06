"""UK retail vs wholesale V2G revenue scenario.

Both revenue routes are encoded:

  RETAIL  : Octopus Power Pack pays the driver a flat 12 p/kWh
            inside the 16:00-19:00 discharge window.  Plus the
            Sciurus 2021 Dynamic Containment grid-services layer
            (725 GBP / V2G EV / yr) that an aggregator on top of
            the retailer can earn.

  WHOLESALE: GB day-ahead market peak (17:00-20:00 evening peak,
            mean ~14.4 p/kWh) MINUS the wholesale off-peak the EV
            charged on (mean overnight ~6.5 p) = ~7.9 p/kWh net
            arbitrage spread that the aggregator captures.  No
            Sciurus DC layer in this scenario - that revenue stream
            is a separate ancillary services market, not embedded
            in the day-ahead.  The driver's V2G rate is whatever
            the aggregator chooses to share; we apply the same
            75/25 driver/aggregator split as Israel for like-for-like.

Run:  python -m src.plot_w11b_uk_retail_vs_wholesale
"""

from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from src.pricing_uk import (
    POWERLOOP_EXPORT_GBP,
    UK_WHOLESALE_24H_GBP,
    POWERLOOP_DISCHARGE_START_HOUR,
    POWERLOOP_DISCHARGE_END_HOUR,
)


OUTDIR = Path(__file__).resolve().parent.parent / "outputs"

# Active typologies (only ones that actually V2G)
ACTIVE_TYPOLOGIES = {
    "Daily Charger":   2402,
    "BEV 2nd Vehicle": 3130,
}

# Sciurus £725 is TOTAL annual earnings, not an additive layer.
UK_SCIURUS_TOTAL_GBP = 725.0   # Total under aggregator + DC ancillary
UK_SCIURUS_FFR_GBP   = 513.0   # Total under aggregator + FFR
UK_SCIURUS_BASE_GBP  = 340.0   # Total under V2G smart charging only

# Wholesale peak window mean (16-19, same window as Power Pack)
WHOLESALE_PEAK_MEAN = float(np.mean(
    UK_WHOLESALE_24H_GBP[POWERLOOP_DISCHARGE_START_HOUR
                         :POWERLOOP_DISCHARGE_END_HOUR]
))
# Overnight off-peak mean (00-06, charge window)
WHOLESALE_OFFPEAK_MEAN = float(np.mean(UK_WHOLESALE_24H_GBP[0:6]))
WHOLESALE_SPREAD = WHOLESALE_PEAK_MEAN - WHOLESALE_OFFPEAK_MEAN


def main() -> None:
    fig, ax = plt.subplots(figsize=(12, 6))

    typologies = list(ACTIVE_TYPOLOGIES.keys())
    n = len(typologies)
    x = np.arange(n)
    w = 0.27

    # Model A: retail Power Pack arbitrage only
    retail_arb = [ACTIVE_TYPOLOGIES[t] * POWERLOOP_EXPORT_GBP
                  for t in typologies]
    # Model B: Sciurus aggregator total earnings (NOT additive on top of A)
    sciurus_total = [UK_SCIURUS_TOTAL_GBP if ACTIVE_TYPOLOGIES[t] > 0 else 0
                     for t in typologies]
    # Model C: wholesale arbitrage from real BMRS curve
    wholesale_arb = [ACTIVE_TYPOLOGIES[t] * WHOLESALE_SPREAD
                     for t in typologies]

    b1 = ax.bar(x - w, retail_arb, w, color="#02808F",
                edgecolor="white",
                label=f"Model A: Retail (Power Pack {POWERLOOP_EXPORT_GBP*100:.0f} p/kWh)")
    b2 = ax.bar(x, sciurus_total, w, color="#15803d",
                edgecolor="white",
                label=f"Model B: Sciurus total ({UK_SCIURUS_TOTAL_GBP:.0f} GBP/EV/yr)")
    b3 = ax.bar(x + w, wholesale_arb, w, color="#0891b2",
                edgecolor="white",
                label=f"Model C: Wholesale ({WHOLESALE_SPREAD*100:.1f} p/kWh BMRS spread)")

    for bars, vals in [(b1, retail_arb), (b2, sciurus_total), (b3, wholesale_arb)]:
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width()/2, v + 25,
                    f"GBP {v:,.0f}",
                    ha="center", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(typologies, fontsize=11)
    ax.set_ylabel("Annual UK V2G revenue per V2G-active EV (GBP)",
                  fontsize=11)
    ax.set_ylim(0, max(sciurus_total) * 1.45)
    ax.set_title(
        "UK V2G revenue: retail (Power Pack) vs wholesale (day-ahead) "
        "scenarios\n"
        f"Retail rate 12 p/kWh fixed.  Wholesale peak mean "
        f"{WHOLESALE_PEAK_MEAN*100:.1f} p, off-peak "
        f"{WHOLESALE_OFFPEAK_MEAN*100:.1f} p, spread "
        f"{WHOLESALE_SPREAD*100:.1f} p/kWh.",
        fontsize=11, fontweight="bold",
    )
    # Legend BELOW the chart to avoid the bars
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncol=3, fontsize=9, framealpha=0.95)
    ax.grid(True, axis="y", alpha=0.3)

    # Sources go below the figure, not inside the axes
    fig.text(0.5, 0.005,
             "Sources: Octopus Power Pack public terms 2026; "
             "GB day-ahead curve from energy-stats.uk / Elexon BMRS, "
             "12-month average to June 2026; Sciurus Trial Insights 2021.",
             ha="center", fontsize=8, style="italic", color="#666")

    fig.tight_layout(rect=(0, 0.10, 1, 1))
    out = OUTDIR / "w11b_uk_retail_vs_wholesale.png"
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")
    print(f"  Wholesale peak mean   = {WHOLESALE_PEAK_MEAN:.4f} GBP/kWh")
    print(f"  Wholesale off-peak    = {WHOLESALE_OFFPEAK_MEAN:.4f} GBP/kWh")
    print(f"  Wholesale spread      = {WHOLESALE_SPREAD:.4f} GBP/kWh")
    print(f"  Retail Power Pack     = {POWERLOOP_EXPORT_GBP:.4f} GBP/kWh")


if __name__ == "__main__":
    main()
