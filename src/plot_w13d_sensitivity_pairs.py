"""Sensitivity figures restructured as matched two-panel pairs (draft-1 review).

Produces:
  w13d_feeder_envelope.png   Fig 4.8  - feeder worst-case envelope (single)
  w13d_pair_paybacks.png     Fig 4.9a - CAPEX + UK export rate (Y: years)
  w13d_pair_revenue.png      Fig 4.9b - TAOZ spread + SoC floor (Y: NET NIS/yr)
  w13d_pair_behaviour.png    Fig 4.9c - plug-in + return hour (Y: kWh/yr)
  w13d_pair_dd_gamma.png     Fig 4.9d - drive-days (kWh) + gamma (aggregator NIS)

TAOZ panel converted to NET (same basis as all headline figures):
kWh = 4,820 / 6,220 constant across the ratio sweep (dispatch is
window/headroom-limited); peak = 0.528 x ratio; NET = kWh x (peak -
0.528/0.9025).  SoC floor panel: sweep_w13b_soc_floor.py, 3-seed avg.
Gamma panel: aggregator 25 % share of the NET pool per capable EV
(previously the right panel of the aggregator unit-economics figure).

Run:  python -m src.plot_w13d_sensitivity_pairs
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.plot_style import apply_style, PALETTE
apply_style()

from src.plot_w12t_sensitivity_split import (
    panel_capex, panel_uk_rate, panel_plugin, panel_return_home,
    panel_drive_days, panel_grid,
)

OUT = Path(__file__).resolve().parent.parent / "outputs"

TEAL, BLUE, RED, GREY = (PALETTE["israel"], PALETTE["uk"],
                         PALETTE["cost"], PALETTE["neutral"])

NET_M = 1.6895 - 0.528 / 0.9025   # NIS per dispatched kWh at current TAOZ


def panel_taoz_net(ax):
    # kWh constant across the ratio sweep (window/headroom-limited);
    # peak = 0.528 * ratio, off-peak fixed; NET = kwh * (peak - 0.528/RTE).
    ratios = np.array([2.0, 3.2, 4.5, 6.0])
    peaks = 0.528 * ratios
    dc = 4820 * (peaks - 0.528 / 0.9025)
    bev = 6220 * (peaks - 0.528 / 0.9025)
    x = np.arange(len(ratios)); w = 0.35
    ax.bar(x - w/2, dc, w, color=TEAL, label="Daily Charger", edgecolor="white")
    ax.bar(x + w/2, bev, w, color=BLUE, label="BEV 2nd Vehicle", edgecolor="white")
    for i in range(len(ratios)):
        ax.text(i - w/2, dc[i] + 250, f"{dc[i]:,.0f}", ha="center", fontsize=8, fontweight="bold")
        ax.text(i + w/2, bev[i] + 250, f"{bev[i]:,.0f}", ha="center", fontsize=8, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r:.1f}x" + ("\n(current)" if r == 3.2 else "")
                        for r in ratios], fontsize=9)
    ax.set_xlabel("TAOZ peak / off-peak ratio", fontsize=10)
    ax.set_ylabel("Annual NET V2G revenue (NIS / opted-in EV)", fontsize=10)
    ax.set_title("(3) Israel TAOZ spread (NET basis)",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, axis="y", alpha=0.3)


def panel_floor(ax):
    # sweep_w13b_soc_floor.py, 3-seed averages, 90 % cap, per-opted-in.
    floors = np.array([40, 45, 50, 55, 60])
    dc_kwh = np.array([6409, 5686, 4919, 4145, 3345])
    bev_kwh = np.array([7840, 7029, 6259, 5431, 4651])
    dc, bev = dc_kwh * NET_M, bev_kwh * NET_M
    ax.plot(floors, dc, "-o", color=TEAL, linewidth=2, markersize=7,
            label="Daily Charger")
    ax.plot(floors, bev, "-s", color=BLUE, linewidth=2, markersize=7,
            label="BEV 2nd Vehicle")
    for f, v in zip(floors, dc):
        ax.text(f, v - 450, f"{v:,.0f}", ha="center", fontsize=8,
                fontweight="bold", color=TEAL)
    for f, v in zip(floors, bev):
        ax.text(f, v + 280, f"{v:,.0f}", ha="center", fontsize=8,
                fontweight="bold", color=BLUE)
    ax.axvline(50, color=RED, linestyle=":", linewidth=1,
               label="contractual floor 50 %")
    ax.set_xlabel("V2G SoC floor (%)", fontsize=10)
    ax.set_ylabel("Annual NET V2G revenue (NIS / opted-in EV)", fontsize=10)
    ax.set_title("(4) SoC floor sweep (3-seed avg, 90 % cap)",
                 fontsize=11, fontweight="bold")
    ax.set_xticks(floors)
    ax.set_ylim(2900, 9400)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.3)


def panel_gamma_aggregator(ax):
    """(8) Percentage change of aggregator total revenue when the SEM
    behavioural inputs or the opt-in share move.

    Opt-in share = Phi(w * shift / 0.64) with the Mehdizadeh path weights
    (Trust: 0.388 direct + 0.174*0.205 via Attitude = 0.424; Vehicle
    Battery Concern: 0.174*(-0.177) = -0.031).  Aggregator revenue scales
    linearly with the opted-in count because per-participant dispatch is
    independent of Intention (the OSP never binds at baseline tariffs).
    gamma is drawn on the same axis, mapped linearly 0.30..0.70.
    """
    from math import erf, sqrt
    def phi(z):
        return 0.5 * (1.0 + erf(z / sqrt(2.0)))
    x = np.linspace(-1, 1, 81)
    sd_int = 0.64
    w_trust = 0.388 + 0.174 * 0.205
    w_vbc = 0.174 * (-0.177)
    rev_trust = (np.array([phi(w_trust * s / sd_int) for s in x]) / 0.5 - 1) * 100
    rev_vbc = (np.array([phi(w_vbc * s / sd_int) for s in x]) / 0.5 - 1) * 100
    rev_gamma = ((0.5 + 0.2 * x) / 0.5 - 1) * 100
    ax.plot(x, rev_trust, color=TEAL, linewidth=2.2,
            label="Trust mean shift (SEM factor)")
    ax.plot(x, rev_vbc, color="#b45309", linewidth=2.2,
            label="Battery-concern mean shift (SEM factor)")
    ax.plot(x, rev_gamma, color=BLUE, linewidth=2.2, linestyle="--",
            label="gamma-2 directly (0.30 to 0.70)")
    ax.axhline(0, color="#94a3b8", linewidth=0.8)
    ax.set_xlabel("shift in standard deviations (gamma-2 mapped 0.30-0.70)",
                  fontsize=10)
    ax.set_ylabel("Change in aggregator total revenue (%)", fontsize=10)
    ax.set_title("(8) Aggregator revenue vs behavioural inputs and gamma-2",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)


def pair(fname, left, right, figsize=(14, 5.6)):
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    left(axes[0]); right(axes[1])
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=150, facecolor="white")
    plt.close(fig)
    print("Saved", OUT / fname)


def single(fname, panel, figsize=(9.5, 6.4)):
    fig, ax = plt.subplots(figsize=figsize)
    panel(ax)
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=150, facecolor="white")
    plt.close(fig)
    print("Saved", OUT / fname)


if __name__ == "__main__":
    single("w13d_feeder_envelope.png", panel_grid)
    pair("w13d_pair_paybacks.png", panel_capex, panel_uk_rate)
    pair("w13d_pair_revenue.png", panel_taoz_net, panel_floor)
    pair("w13d_pair_behaviour.png", panel_plugin, panel_return_home)
    pair("w13d_pair_dd_gamma.png", panel_drive_days, panel_gamma_aggregator)
