"""Sensitivity heatmap for the (alpha, beta) fleet sweep.

Two-panel heatmap: GWh/year on the left, M NIS/year on the right.
Annotates the (today, beta_low) and (2030 target, beta_mid) cells so
the chart is usable as a single-figure dissertation result.

Run:  python -m src.plot_w10c_alphabeta_heatmap
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

from src.fleet_assumptions import ALPHA_TODAY, ALPHA_2030, BETA_LOW, BETA_MID
from src.sweep_w10c_alphabeta import (
    ALPHA_GRID, BETA_GRID,
    per_typology_weekly_v2g_economics,
    fleet_level_annual,
)


OUT = Path(__file__).resolve().parent.parent / "outputs" / "w10_alpha_beta_heatmap.png"


def build_grids() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    per_typ = per_typology_weekly_v2g_economics()
    n_alpha = len(ALPHA_GRID)
    n_beta  = len(BETA_GRID)
    gwh   = np.zeros((n_beta, n_alpha))    # rows = beta, cols = alpha
    mnis  = np.zeros((n_beta, n_alpha))
    n_evs = np.zeros((n_beta, n_alpha), dtype=int)
    for j, alpha in enumerate(ALPHA_GRID):
        for i, beta in enumerate(BETA_GRID):
            r = fleet_level_annual(alpha, beta, per_typ)
            gwh[i, j] = r["fleet_gwh_yr"]
            mnis[i, j] = r["fleet_revenue_mnis_yr"]
            n_evs[i, j] = r["n_v2g_evs"]
    return gwh, mnis, n_evs


def draw_heatmap(ax, data: np.ndarray, n_evs: np.ndarray, title: str,
                 cbar_label: str, value_fmt: str = "{:.0f}"):
    im = ax.imshow(data, origin="lower", cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(ALPHA_GRID)))
    ax.set_xticklabels([f"{a:.2f}" for a in ALPHA_GRID])
    ax.set_yticks(range(len(BETA_GRID)))
    ax.set_yticklabels([f"{b:.2f}" for b in BETA_GRID])
    ax.set_xlabel(r"$\alpha$  -  EV share of total fleet", fontsize=11)
    ax.set_ylabel(r"$\beta$  -  V2G share of EV fleet", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)

    # cell annotations: primary value + V2G EV count below
    n_beta, n_alpha = data.shape
    vmax = data.max()
    for i in range(n_beta):
        for j in range(n_alpha):
            txt_color = "white" if data[i, j] > vmax * 0.55 else "#14201d"
            ax.text(j, i + 0.08, value_fmt.format(data[i, j]),
                    ha="center", va="center",
                    color=txt_color, fontsize=10, fontweight="bold")
            ax.text(j, i - 0.22, f"{n_evs[i, j]/1000:.0f}k EVs",
                    ha="center", va="center",
                    color=txt_color, fontsize=7)

    cbar = plt.colorbar(im, ax=ax, fraction=0.045, pad=0.04)
    cbar.set_label(cbar_label, fontsize=10)

    # Highlight reference scenarios
    def mark(alpha_val, beta_val, label):
        if alpha_val in ALPHA_GRID and beta_val in BETA_GRID:
            j = ALPHA_GRID.index(alpha_val)
            i = BETA_GRID.index(beta_val)
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                         fill=False, edgecolor="#dc2626", linewidth=2.5))
            ax.annotate(label, xy=(j, i + 0.45),
                        xytext=(j, i + 0.55), ha="center",
                        fontsize=8, color="#dc2626", fontweight="bold")

    # Do not mark "today".  Real V2G penetration in Israel is
    # below the smallest cell on this grid (< 5 % alpha and a few % beta),
    # so a "today" annotation would overstate where the market actually
    # is.  Mark only the 2030 policy-target POTENTIAL.
    a_2030 = min(ALPHA_GRID, key=lambda a: abs(a - ALPHA_2030))
    b_mid  = min(BETA_GRID, key=lambda b: abs(b - BETA_MID))
    mark(a_2030, b_mid, "2030 policy POTENTIAL")


def main() -> None:
    gwh, mnis, n_evs = build_grids()

    fig, axes = plt.subplots(1, 2, figsize=(15, 6.2))
    draw_heatmap(axes[0], gwh, n_evs,
                 "Annual V2G discharge  (GWh / yr)",
                 cbar_label="GWh per year",
                 value_fmt="{:.0f}")
    draw_heatmap(axes[1], mnis, n_evs,
                 "Annual driver V2G revenue  (M NIS / yr)",
                 cbar_label="Million NIS per year",
                 value_fmt="{:.0f}")

    fig.suptitle(
        "Israeli fleet V2G impact under (alpha, beta) sensitivity  -  "
        "retail price scenario, 3.5M-car fleet baseline",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    fig.savefig(OUT, dpi=150, facecolor="white")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
