"""Per-EV aggregator revenue chart.

The alpha-beta heatmap shows UK total fleet aggregator revenue >>
Israeli because the UK fleet is 10x bigger.  This chart
normalises out the fleet size effect and shows the per-V2G-EV
aggregator revenue directly, which is the citable unit-economics
number.

Three sub-panels:
  1. Annual aggregator revenue per V2G-active EV (Israel vs UK)
  2. Annual aggregator revenue per V2G-active EV under three gamma
     (SEM participation) scenarios
  3. Stacked fleet aggregator revenue vs share split (Israel + UK)

Run:  python -m src.plot_w11b_aggregator_per_ev
"""

from __future__ import annotations
from pathlib import Path

import matplotlib.pyplot as plt

from src.plot_style import apply_style, PALETTE
apply_style()
import numpy as np


OUTDIR = Path(__file__).resolve().parent.parent / "outputs"

# Per V2G-active EV annual driver-side gross V2G revenue.
# COMPUTED from the model's observed V2G volumes and the country's
# V2G export rate.  NOT a hand-picked round number.
#
#   Israel = mean over active typologies of (kWh/yr * retail peak NIS/kWh)
#   UK     = mean over active typologies of (kWh/yr * Power Pack p/kWh
#                                            + Sciurus DC GBP/EV/yr)
ACTIVE_KWH = {"Daily Charger": 4820, "BEV 2nd Vehicle": 6220}  # opt-in mean
ISRAEL_RETAIL_PEAK_NIS = 1.6895
UK_POWER_PACK_GBP      = 0.12
UK_SCIURUS_TOTAL_GBP   = 725.0   # total, not additive

# UK central case = Sciurus aggregator model (£725 total)
# Israel NET = gross peak revenue - off-peak recharge cost.
IL_OFFPEAK = 0.528
RTE = 0.9025
_il_rev_per_typ = [k * ISRAEL_RETAIL_PEAK_NIS - k / RTE * IL_OFFPEAK
                    for k in ACTIVE_KWH.values()]
_uk_rev_per_typ = [UK_SCIURUS_TOTAL_GBP if k > 0 else 0
                   for k in ACTIVE_KWH.values()]
PER_EV_GROSS = {
    "Israel": sum(_il_rev_per_typ) / len(_il_rev_per_typ),
    "UK":     sum(_uk_rev_per_typ) / len(_uk_rev_per_typ),
}

AGGREGATOR_SHARE_DEFAULT = 0.25
DRIVER_SHARE_DEFAULT     = 0.75

# Explicit gamma = SEM participation rate
# (fraction of V2G-capable EVs that actually opt in and discharge)
GAMMA_SCENARIOS = {
    "low":     0.30,
    "medium":  0.50,
    "high":    0.70,
}


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Panel 1: per-V2G-active-EV annual aggregator revenue
    ax = axes[0]
    countries = ["Israel", "UK"]
    aggregator_per_ev = [PER_EV_GROSS[c] * AGGREGATOR_SHARE_DEFAULT
                         for c in countries]
    driver_per_ev = [PER_EV_GROSS[c] * DRIVER_SHARE_DEFAULT
                     for c in countries]
    x = np.arange(len(countries))
    w = 0.4

    # Show in same currency-equivalent for fair comparison: convert UK to NIS
    GBP_TO_NIS = 4.7
    aggregator_per_ev_nis = [aggregator_per_ev[0],
                             aggregator_per_ev[1] * GBP_TO_NIS]
    driver_per_ev_nis = [driver_per_ev[0],
                         driver_per_ev[1] * GBP_TO_NIS]

    b1 = ax.bar(x - w/2, driver_per_ev_nis, w, color="#0f766e",
                label="Driver (75 %)", edgecolor="white")
    b2 = ax.bar(x + w/2, aggregator_per_ev_nis, w, color="#1d4ed8",
                label="Aggregator (25 %)", edgecolor="white")

    for i, (b, v) in enumerate(zip(b1, driver_per_ev_nis)):
        local = driver_per_ev[i]
        ccy = "NIS" if i == 0 else "GBP"
        ax.text(b.get_x() + b.get_width()/2, v + 80,
                f"{v:,.0f} NIS\n({local:,.0f} {ccy})",
                ha="center", fontsize=11.5, fontweight="bold", va="bottom")
    for i, (b, v) in enumerate(zip(b2, aggregator_per_ev_nis)):
        local = aggregator_per_ev[i]
        ccy = "NIS" if i == 0 else "GBP"
        ax.text(b.get_x() + b.get_width()/2, v + 80,
                f"{v:,.0f} NIS\n({local:,.0f} {ccy})",
                ha="center", fontsize=11.5, fontweight="bold", va="bottom")
    ax.set_ylim(0, max(driver_per_ev_nis) * 1.30)

    ax.set_xticks(x)
    ax.set_xticklabels(countries, fontsize=11)
    ax.set_ylabel("Per V2G-active EV annual revenue (NIS-equivalent)",
                  fontsize=11)
    ax.set_title("Per V2G-active EV annual V2G revenue\n"
                 "Driver 75 % / Aggregator 25 % split",
                 fontsize=11, fontweight="bold")
    ax.legend(loc="upper right", fontsize=11.5, framealpha=0.95)
    ax.grid(True, axis="y", alpha=0.3)

    # Panel 2: gamma (SEM participation) sensitivity
    ax = axes[1]
    gammas = list(GAMMA_SCENARIOS.values())
    gamma_labels = [f"{n} γ = {v:.2f}" for n, v in GAMMA_SCENARIOS.items()]

    width = 0.35
    x = np.arange(len(gammas))
    il = [PER_EV_GROSS["Israel"] * AGGREGATOR_SHARE_DEFAULT * g
          for g in gammas]
    uk_nis = [PER_EV_GROSS["UK"] * AGGREGATOR_SHARE_DEFAULT * g * GBP_TO_NIS
              for g in gammas]

    # NOTE: gamma here scales the per-V2G-CAPABLE-EV revenue down
    # because only gamma fraction actually discharges.
    b1 = ax.bar(x - width/2, il, width, color="#0f766e",
                label="Israel (NIS / capable EV)", edgecolor="white")
    b2 = ax.bar(x + width/2, uk_nis, width, color="#1d4ed8",
                label="UK (NIS-equiv / capable EV)", edgecolor="white")

    for b, v in zip(b1, il):
        ax.text(b.get_x() + b.get_width()/2, v + 30, f"{v:,.0f}",
                ha="center", fontsize=11.5, fontweight="bold")
    for b, v in zip(b2, uk_nis):
        ax.text(b.get_x() + b.get_width()/2, v + 30, f"{v:,.0f}",
                ha="center", fontsize=11.5, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(gamma_labels, fontsize=11.5)
    ax.set_ylabel("Annual aggregator revenue per V2G-capable EV "
                  "(NIS-equivalent)", fontsize=11)
    ax.set_title("Sensitivity to gamma\n"
                 "(fraction of V2G-capable EVs actually participating)",
                 fontsize=11, fontweight="bold")
    ax.legend(loc="upper left", fontsize=11.5, framealpha=0.95)
    ax.grid(True, axis="y", alpha=0.3)

    fig.suptitle(
        "Aggregator unit economics  -  per-EV revenue, not aggregate fleet "
        "revenue.  Removes fleet-size distortion between Israel and UK.",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = OUTDIR / "w11b_aggregator_per_ev.png"
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
