"""Fleet sensitivity heatmap: alpha vs (beta x gamma).

Design choices:
  * The alpha axis extends to 100 %.
  * beta and gamma are combined into a single axis,
    "V2G capable AND participating share of EVs", so the two-way
    heatmap captures all three coefficients in one figure.

Effective V2G-active EV count on the fleet:
    N_v2g = N_fleet * alpha * (beta * gamma)

The x-axis is alpha (EV share of total fleet).
The y-axis is beta*gamma (of the EV subset, what fraction is BOTH
V2G-capable AND actually participating).

Two panels:
  1. Annual V2G discharge (GWh/yr)
  2. Annual driver V2G revenue (M NIS/yr)

Run:  python -m src.plot_w12d_fleet_alpha_bgamma
"""

from __future__ import annotations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.fleet_assumptions import ALPHA_TODAY, ALPHA_2030
from src.sweep_w10c_alphabeta import (
    per_typology_weekly_v2g_economics,
    WONG_SHARES,
    WEEKS_IN_YEAR,
    ALL_TYPOLOGIES,
)
from src.fleet_assumptions import N_FLEET_ISRAEL


OUT = (Path(__file__).resolve().parent.parent
       / "outputs" / "w12d_fleet_alpha_bgamma.png")


# Wide alpha and combined beta*gamma axis.
# Alpha grid stretches to 1.0 to answer "what if everyone drives an EV".
ALPHA_GRID = [0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 1.00]
# beta * gamma = "V2G-capable AND participating" share of the EV fleet.
BGAMMA_GRID = [0.05, 0.10, 0.20, 0.40, 0.60, 0.80]


def build_grids() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    per_typ = per_typology_weekly_v2g_economics()
    # Wong-weighted per-V2G-active-EV annual figures
    kwh_per_ev_yr = sum(WONG_SHARES[t] * per_typ[t]["v2g_kwh_per_yr"]
                        for t in ALL_TYPOLOGIES)
    rev_per_ev_yr = sum(WONG_SHARES[t] * per_typ[t]["revenue_nis_per_yr"]
                        for t in ALL_TYPOLOGIES)

    n_alpha = len(ALPHA_GRID)
    n_bg    = len(BGAMMA_GRID)
    gwh   = np.zeros((n_bg, n_alpha))
    mnis  = np.zeros((n_bg, n_alpha))
    n_evs = np.zeros((n_bg, n_alpha), dtype=int)

    for j, alpha in enumerate(ALPHA_GRID):
        for i, bg in enumerate(BGAMMA_GRID):
            n_v2g = int(round(alpha * bg * N_FLEET_ISRAEL))
            gwh[i, j] = n_v2g * kwh_per_ev_yr / 1e6
            mnis[i, j] = n_v2g * rev_per_ev_yr / 1e6
            n_evs[i, j] = n_v2g
    return gwh, mnis, n_evs


def draw_heatmap(ax, data: np.ndarray, n_evs: np.ndarray,
                 title: str, cbar_label: str,
                 value_fmt: str = "{:.0f}"):
    im = ax.imshow(data, origin="lower", cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(ALPHA_GRID)))
    ax.set_xticklabels([f"{a:.2f}" for a in ALPHA_GRID])
    ax.set_yticks(range(len(BGAMMA_GRID)))
    ax.set_yticklabels([f"{b:.2f}" for b in BGAMMA_GRID])
    ax.set_xlabel(r"$\alpha$  -  EV share of total fleet", fontsize=11)
    ax.set_ylabel(r"$\beta \cdot \gamma$  -  V2G capable AND participating "
                  "share of EVs", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)

    n_bg, n_alpha = data.shape
    vmax = data.max() if data.max() > 0 else 1.0
    for i in range(n_bg):
        for j in range(n_alpha):
            txt_color = "white" if data[i, j] > vmax * 0.55 else "#14201d"
            ax.text(j, i + 0.10, value_fmt.format(data[i, j]),
                    ha="center", va="center",
                    color=txt_color, fontsize=10, fontweight="bold")
            ax.text(j, i - 0.22, f"{n_evs[i, j]/1000:.0f}k EVs",
                    ha="center", va="center",
                    color=txt_color, fontsize=7)

    cbar = plt.colorbar(im, ax=ax, fraction=0.045, pad=0.04)
    cbar.set_label(cbar_label, fontsize=10)


def main() -> None:
    gwh, mnis, n_evs = build_grids()
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5))
    draw_heatmap(axes[0], gwh, n_evs,
                 "Annual V2G discharge  (GWh / yr)",
                 cbar_label="GWh per year")
    draw_heatmap(axes[1], mnis, n_evs,
                 "Annual driver V2G revenue  (M NIS / yr)",
                 cbar_label="Million NIS per year")

    fig.suptitle(
        f"Israeli fleet V2G impact under alpha x (beta*gamma) sensitivity  -  "
        f"3.5 M-car fleet, retail TAOZ price",
        fontsize=13, fontweight="bold",
    )
    fig.text(0.5, 0.02,
             "alpha = EV share of total fleet  ·  beta = V2G-capable share "
             "of EVs  ·  gamma = SEM participation among capable EVs.  "
             "Product beta*gamma = share of EVs both capable AND participating.",
             ha="center", fontsize=9, style="italic", color="#555")
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(OUT, dpi=150, facecolor="white")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
