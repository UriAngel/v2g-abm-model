"""Fleet capability composition: Israel vs UK, three layers.

Shares of each country's BEV car fleet that are (i) V2L (power socket
only), (ii) V2G potential (hardware built in, awaiting manufacturer
activation), and (iii) V2G capable (vehicle already permits discharge).
The V2G-potential basket is the SAME in both countries (Leaf, Renault 5,
Ioniq 5/6, EV6, EV9, GV60) so the comparison is like-for-like.

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
L_V2L = "V2L\n(power socket only,\nno grid export)"
L_POT = "V2G potential\n(hardware built in, awaiting\nmanufacturer activation)"
L_CAP = "V2G capable\n(vehicle already\npermits discharge)"
DATA = {
    #        Israel                   UK
    L_V2L: (58347 / 235933 * 100, 195000 / 1656000 * 100),
    L_POT: (9899 / 235933 * 100,  101000 / 1656000 * 100),
    L_CAP: (259 / 235933 * 100,   750 / 1656000 * 100),
}
COUNTS = {
    L_V2L: ("58,347", "~195k"),
    L_POT: ("9,899", "~101k"),
    L_CAP: ("~259", "~500-1,000"),
}
FLOOR = {L_V2L}


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
    ax.set_title("V2G capability layers in the Israeli and UK EV fleets, "
                 "mid-2026")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 0.99))

    ax.annotate("potential vs capable:\n~38× gap (IL), ~135× gap (UK)",
                xy=(2.0, 1.2), xytext=(2.0, 9.5),
                ha="center", fontsize=9, color=PALETTE["cost"],
                arrowprops=dict(arrowstyle="->", color=PALETTE["cost"],
                                linewidth=1.0))

    fig.text(0.5, 0.015,
             "Israel: registry query (data.gov.il, Jul 2026), exact counts; V2L floor (realistic ~35-40%).\n"
             "UK: constructed from DfT licensing statistics, SMMT tables, OEM cumulative sales; V2L floor (plausible 14-18%).\n"
             "V2G-potential basket: Leaf, Renault 5, Ioniq 5/6, EV6, EV9, GV60 (IL registry; UK constructed).  V2G capable: IL = Leaf + R5;\n"
             "UK = vehicles in live paid programmes (Powerloop + Sciurus + Power Pack tail, order-of-magnitude).\n"
             "Israel: grid export is not yet authorised, so even these vehicles cannot yet be paid.",
             ha="center", fontsize=7.8, color=PALETTE["neutral"])

    fig.tight_layout(rect=(0, 0.11, 1, 1))
    fig.savefig(OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
