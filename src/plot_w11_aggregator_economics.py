"""Aggregator economics charts.

Two figures, per country: how much does the aggregator make per year
and how does it depend on (i) fleet size and V2G adoption
(alpha, beta), and (ii) the driver share of the V2G margin.

Charts:
  1. w11_aggregator_alpha_beta.png  -  alpha x beta heatmap per country
  2. w11_aggregator_share_curve.png -  driver-share sweep at 2030 target

Run:  python -m src.plot_w11_aggregator_economics
"""

from __future__ import annotations
from pathlib import Path

import matplotlib.pyplot as plt

from src.plot_style import apply_style, PALETTE
apply_style()
import numpy as np

from src.fleet_assumptions import N_FLEET_ISRAEL


OUTDIR = Path(__file__).resolve().parent.parent / "outputs"

# Per-V2G-active EV revenue from the full-year model.
#   Israel = mean over active typologies of kWh x TAOZ peak rate (retail)
#   UK     = Sciurus 2021 total earnings (Model B), which INCLUDES arbitrage
_ACTIVE_KWH = {"Daily Charger": 4820, "BEV 2nd Vehicle": 6220}  # opt-in mean
_ISRAEL_RETAIL_PEAK_NIS = 1.6895
_IL_OFFPEAK = 0.528
_RTE = 0.9025
# NET per-EV revenue = gross - off-peak recharge cost.
PER_EV_REVENUE = {
    "Israel": sum(k * _ISRAEL_RETAIL_PEAK_NIS - k / _RTE * _IL_OFFPEAK
                   for k in _ACTIVE_KWH.values()) / len(_ACTIVE_KWH),
    "UK":     725,    # GBP (Sciurus Model B total, already net per Cenex 2021)
}

# Default driver/aggregator split
DRIVER_SHARE_DEFAULT     = 0.75
AGGREGATOR_SHARE_DEFAULT = 0.25

# UK fleet, for the UK chart.  Source: UK SMMT vehicle parc data.
N_FLEET_UK = 33_000_000   # ~33 M passenger cars in GB


# Wider alpha and combined (beta*gamma) axis to match the deck layout.
ALPHA_GRID  = [0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 1.00]
BGAMMA_GRID = [0.05, 0.10, 0.20, 0.40, 0.60, 0.80]


def aggregator_revenue_m_currency(country: str, alpha: float, bgamma: float,
                                  aggregator_share: float = AGGREGATOR_SHARE_DEFAULT) -> float:
    """Aggregator annual revenue in million NIS (Israel) or M GBP (UK).

    bgamma = beta * gamma = share of EVs BOTH V2G-capable AND
    participating.  The participation fraction is part of the axis,
    not a hidden constant.
    """
    n_fleet = N_FLEET_ISRAEL if country == "Israel" else N_FLEET_UK
    rev_per_ev = PER_EV_REVENUE[country]
    active_evs = alpha * bgamma * n_fleet
    total_gross = active_evs * rev_per_ev
    aggregator = total_gross * aggregator_share
    return aggregator / 1_000_000


def fig1_alpha_beta_heatmap() -> Path:
    """alpha x (beta*gamma) heatmap, matching the deck layout."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5))
    for ax, country in zip(axes, ("Israel", "UK")):
        grid = np.zeros((len(BGAMMA_GRID), len(ALPHA_GRID)))
        for i, bg in enumerate(BGAMMA_GRID):
            for j, alpha in enumerate(ALPHA_GRID):
                grid[i, j] = aggregator_revenue_m_currency(country, alpha, bg)

        im = ax.imshow(grid, origin="lower", cmap="YlGn", aspect="auto")
        ax.set_xticks(range(len(ALPHA_GRID)))
        ax.set_xticklabels([f"{a:.2f}" for a in ALPHA_GRID])
        ax.set_yticks(range(len(BGAMMA_GRID)))
        ax.set_yticklabels([f"{b:.2f}" for b in BGAMMA_GRID])
        ax.set_xlabel(r"$\alpha$  -  EV share of total fleet", fontsize=11)
        ax.set_ylabel(r"$\beta \cdot \gamma$  -  capable AND participating share of EVs",
                      fontsize=11)
        currency = "NIS" if country == "Israel" else "GBP"
        ax.set_title(f"{country}  -  aggregator annual revenue (M {currency})",
                     fontsize=12, fontweight="bold")

        vmax = grid.max() if grid.max() > 0 else 1.0
        for i in range(len(BGAMMA_GRID)):
            for j in range(len(ALPHA_GRID)):
                c = "white" if grid[i, j] > vmax * 0.55 else "#14201d"
                ax.text(j, i, f"{grid[i, j]:.0f}",
                        ha="center", va="center",
                        color=c, fontsize=10, fontweight="bold")

        plt.colorbar(im, ax=ax, fraction=0.045, pad=0.04,
                     label=f"M {currency} per year")

    fig.suptitle(
        "Aggregator annual revenue under alpha x (beta*gamma) sensitivity   "
        f"-   aggregator share {AGGREGATOR_SHARE_DEFAULT*100:.0f}% of V2G margin",
        fontsize=12, fontweight="bold",
    )
    fig.text(0.5, 0.02,
             "alpha = EV share of total fleet  ·  beta*gamma = share of EVs "
             "BOTH V2G-capable AND participating (Wong-weighted).",
             ha="center", fontsize=9, style="italic", color="#555")
    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    out = OUTDIR / "w11_aggregator_alpha_beta.png"
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    return out


def fig2_share_sensitivity() -> Path:
    """At fixed 2030 target fleet, sweep the driver/aggregator split."""
    # 2030 target: Israel alpha=0.30, beta=0.25; UK assumed alpha=0.40, beta=0.25
    scenarios = {
        "Israel": (0.30, 0.25),
        "UK":     (0.40, 0.25),
    }
    aggregator_shares = np.linspace(0.05, 0.50, 19)   # 5 % to 50 %

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))

    for ax, country in zip(axes, ("Israel", "UK")):
        alpha, beta = scenarios[country]
        currency = "NIS" if country == "Israel" else "GBP"
        rev_agg = np.array([
            aggregator_revenue_m_currency(country, alpha, beta, s)
            for s in aggregator_shares
        ])
        n_fleet = N_FLEET_ISRAEL if country == "Israel" else N_FLEET_UK
        v2g_active = alpha * beta * n_fleet   # here beta means beta*gamma
        total_pool = v2g_active * PER_EV_REVENUE[country] / 1_000_000  # M

        rev_driver = total_pool * (1 - aggregator_shares)

        driver_shares_pct = (1 - aggregator_shares) * 100

        ax.plot(aggregator_shares * 100, rev_agg, color="#1d4ed8",
                linewidth=2.5, marker="o", markersize=4,
                label=f"Aggregator revenue ({currency})")
        ax.plot(aggregator_shares * 100, rev_driver, color="#0f766e",
                linewidth=2.5, marker="s", markersize=4,
                label=f"Aggregate driver revenue ({currency})")

        # Mark default 25 %
        default_idx = int(np.argmin(np.abs(aggregator_shares - 0.25)))
        ax.axvline(25, color="#b91c1c", linestyle="--", linewidth=1, alpha=0.7)
        ax.text(26, rev_agg.max() * 0.95, "default 25 %",
                color="#b91c1c", fontsize=9, fontweight="bold")

        ax.set_xlabel("Aggregator share of V2G margin (%)", fontsize=11)
        ax.set_ylabel(f"Annual revenue (M {currency})", fontsize=11)
        ax.set_title(
            f"{country}  -  2030 target fleet "
            f"(alpha={alpha:.2f}, beta={beta:.2f})",
            fontsize=12, fontweight="bold",
        )
        ax.legend(loc="center right", fontsize=10, framealpha=0.95)
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        "Driver vs aggregator split  -  fixed 2030 target fleet, "
        "Wong-weighted per-EV V2G revenue",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = OUTDIR / "w11_aggregator_share_curve.png"
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    return out


def main() -> None:
    out1 = fig1_alpha_beta_heatmap()
    print(f"Saved {out1}")
    out2 = fig2_share_sensitivity()
    print(f"Saved {out2}")


if __name__ == "__main__":
    main()
