"""Fleet capability composition: Israel vs UK - the beta decomposition.

Three beta layers, defined SYMMETRICALLY in both countries:
  beta1 V2L           - household power socket only, no grid export.
  beta2 V2G potential - built with discharge hardware (Leaf, Renault 5,
        Ioniq 5/6, EV6, EV9, GV60); activation is a manufacturer decision.
  beta3 V2G capable   - vehicle side already permits discharge
        (CHAdeMO Leaf + AC-bidirectional Renault 5, both countries).
In Israel even beta3 cannot yet export (not authorised).

Data provenance:
  Israel: data/il_registry_ev_counts_2026-07.csv - full national vehicle
          registry query (data.gov.il CKAN, 2026-07-07).  Exact counts.
  UK:     data/uk_fleet_capability_2026-07.csv - constructed from DfT
          licensing statistics, SMMT annual tables and manufacturer
          cumulative-sales releases (2026-07-08).  Estimates; V2L is a
          floor; see CSV notes for per-model weak links.

Run:  python -m src.plot_w12z_capability_ilvuk
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.plot_style import apply_style, PALETTE

apply_style()

OUT = (Path(__file__).resolve().parent.parent
       / "outputs" / "w12z_capability_ilvuk.png")

# Shares of the national BEV car fleet (percent).
# Israel denominators: 235,933 EVs (registry).  UK: ~1,656,000 BEV cars (DfT).
L_B1 = "\u03b21  V2L\n(power socket only,\nno grid export)"
L_B2 = "\u03b22  V2G potential\n(hardware built in, awaiting\nmanufacturer activation)"
L_B3 = "\u03b23  V2G capable\n(vehicle already\npermits discharge)"
DATA = {
    #        Israel                   UK
    L_B1: (58347 / 235933 * 100, 195000 / 1656000 * 100),
    L_B2: (9899 / 235933 * 100,  101000 / 1656000 * 100),
    L_B3: (259 / 235933 * 100,   59000 / 1656000 * 100),
}
COUNTS = {
    L_B1: ("58,347", "~195k"),
    L_B2: ("9,899", "~101k"),
    L_B3: ("~259", "~59k"),
}
FLOOR = {L_B1}


def main() -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.8))

    labels = list(DATA.keys())
    x = np.arange(len(labels)) * 1.0
    w = 0.32

    il_vals = [DATA[k][0] for k in labels]
    uk_vals = [DATA[k][1] for k in labels]

    b_il = ax.bar(x - w / 2, il_vals, width=w, color=PALETTE["israel"],
                  label="Israel (registry, exact)")
    b_uk = ax.bar(x + w / 2, uk_vals, width=w, color=PALETTE["uk"],
                  label="UK (constructed estimate)")

    for xi, v, k, side in [(x[i] - w / 2, il_vals[i], labels[i], 0)
                           for i in range(len(labels))] + \
                          [(x[i] + w / 2, uk_vals[i], labels[i], 1)
                           for i in range(len(labels))]:
        cnt = COUNTS[k][side]
        prefix = "≥" if k in FLOOR and side == 0 else ""
        pct = f"{v:.2f}%" if v < 0.5 else f"{v:.1f}%"
        ax.text(xi, v + 0.45, f"{prefix}{pct}", ha="center",
                fontsize=10.5, fontweight="bold", color="#1e293b")
        ax.text(xi, v + 2.0, f"({cnt})", ha="center",
                fontsize=8, color=PALETTE["neutral"])

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("Share of national BEV car fleet (%)")
    ax.set_ylim(0, 30)
    ax.set_title("The three beta layers of the Israeli and UK EV fleets, "
                 "mid-2026")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 0.99))

    ax.annotate("\u03b22\u2192\u03b23 in Israel: ~38\u00d7 gap, closed by a\nBMS software switch + OEM approval",
                xy=(2.0 - 0.16, 1.0), xytext=(1.55, 10.5),
                ha="center", fontsize=9, color=PALETTE["cost"],
                arrowprops=dict(arrowstyle="->", color=PALETTE["cost"],
                                linewidth=1.0))

    fig.text(0.5, 0.015,
             "Israel: exact registry counts (data.gov.il, Jul 2026); V2L is a counted floor.  UK: constructed from DfT, SMMT and manufacturer data.\n"
             "β3 basket in both countries: CHAdeMO Nissan Leaf + AC-bidirectional Renault 5.  In Israel even β3 cannot yet export: not authorised.",
             ha="center", fontsize=7.8, color=PALETTE["neutral"])

    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
