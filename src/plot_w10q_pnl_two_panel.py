"""Two-panel P&L per country.

Each country gets two panels:

  LEFT  - Annual operating P&L (V2G revenue minus battery degradation).
          NO charger CAPEX included.  Shows the "is the operation itself
          profitable" question.

  RIGHT - Years to break even on the V2G premium charger CAPEX,
          computed as premium / annual_operating_P&L.

Two output files: w10q_pnl_israel.png, w10q_pnl_uk.png.

Run:  python -m src.plot_w10q_pnl_two_panel
"""

from __future__ import annotations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.aggregator_stub import (
    CHARGER_CAPEX_BIDIR_2024_NIS,
    CHARGER_CAPEX_BIDIR_2024_UK_NIS,
    CHARGER_CAPEX_SMART_NIS,
)
from src.aging_table_lit import (
    v2g_delta_pp_10yr,
    WONG_V2G_KWH_PER_YEAR,
    WONG_V2G_EFFECT,
)
from src.battery_aging import (
    BATTERY_REPLACEMENT_COST_NIS_PER_KWH_NMC,
    BATTERY_REPLACEMENT_COST_NIS_PER_KWH_LFP,
)
from src.pricing_uk import GBP_TO_NIS


OUTDIR = Path(__file__).resolve().parent.parent / "outputs"

V2G_PREMIUM_NIS = CHARGER_CAPEX_BIDIR_2024_NIS - CHARGER_CAPEX_SMART_NIS
V2G_PREMIUM_GBP = (CHARGER_CAPEX_BIDIR_2024_UK_NIS - CHARGER_CAPEX_SMART_NIS) / GBP_TO_NIS

V2G_DELTA_PCT_AT_WONG_VOL = {
    "IMPROVE":   -2.0,
    "NEUTRAL":    0.0,
    "SLIGHT":    +1.5,
    "DECREASE":  +3.0,
    "LARGE":     +6.0,
}
MAX_AGING_DELTA_PCT = 20.0   # cap at +/- 20 pp

BATTERY_KWH = 67.0   # Israeli fleet weighted-average (see vehicle_catalog)
ISRAEL_RETAIL_PEAK_NIS = 1.6895
UK_POWER_PACK_GBP      = 0.12

# Observed V2G volumes from the uncapped model (Public Charger is
# structurally 0 - no home charger per Wong).
OBSERVED_V2G_KWH_PER_YEAR = {
    # PER-OPTED-IN-EV values from the 240-agent Israel V2G ABM.
    # These are per participating driver, not fleet-averaged.
    "Daily Charger":     4820,
    "Public Charger":       0,
    "BEV 2nd Vehicle":   6220,
    "Threshold Charger":    0,
}

# UK grid-services revenue layer (Sciurus 2021, Dynamic Containment)
UK_GRID_SERVICES_REVENUE_GBP = 725.0


def annual_revenue(country: str, typology: str) -> float:
    kwh = OBSERVED_V2G_KWH_PER_YEAR[typology]
    if country == "Israel":
        return kwh * ISRAEL_RETAIL_PEAK_NIS
    rev = kwh * UK_POWER_PACK_GBP
    # Add grid-services layer only for agents that actually V2G
    if kwh > 0:
        rev += UK_GRID_SERVICES_REVENUE_GBP
    return rev


def annual_battery_cost(typology: str, chemistry: str, currency: str) -> float:
    """Annualised battery degradation cost, scaled by observed/Wong volume."""
    chem_key = "NMC_B1" if chemistry == "NMC" else "LFP"
    # Beta-based delta from Wong 2026 Appendix E regressions.
    delta_pp = v2g_delta_pp_10yr(typology, chem_key, OBSERVED_V2G_KWH_PER_YEAR[typology])
    pct_delta = max(0.0, -delta_pp)
    lost_kwh = (pct_delta / 100.0) * BATTERY_KWH
    if chemistry == "NMC":
        cost_nis_per_kwh = BATTERY_REPLACEMENT_COST_NIS_PER_KWH_NMC
    else:
        cost_nis_per_kwh = BATTERY_REPLACEMENT_COST_NIS_PER_KWH_LFP
    cost_10y_nis = lost_kwh * cost_nis_per_kwh
    cost_annual_nis = cost_10y_nis / 10.0
    if currency == "NIS":
        return cost_annual_nis
    return cost_annual_nis / GBP_TO_NIS


def draw_country(country: str, currency: str, premium: float) -> Path:
    typologies = list(WONG_V2G_KWH_PER_YEAR.keys())
    chems = ("NMC", "LFP")
    n_typ = len(typologies)

    # Compute the numbers
    rows = []
    for typ in typologies:
        for chem in chems:
            rev = annual_revenue(country, typ)
            bat = annual_battery_cost(typ, chem, currency)
            op_pnl = rev - bat
            payback = (premium / op_pnl) if op_pnl > 0 else float("inf")
            rows.append({"typ": typ, "chem": chem,
                         "rev": rev, "bat": bat,
                         "op_pnl": op_pnl, "payback": payback})

    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))

    # ---- LEFT panel: annual operating P&L = revenue minus battery ----
    ax = axes[0]
    x = np.arange(n_typ)
    bar_w = 0.36

    rev_nmc = [r["rev"] for r in rows if r["chem"] == "NMC"]
    bat_nmc = [r["bat"] for r in rows if r["chem"] == "NMC"]
    op_nmc  = [r["op_pnl"] for r in rows if r["chem"] == "NMC"]
    rev_lfp = [r["rev"] for r in rows if r["chem"] == "LFP"]
    bat_lfp = [r["bat"] for r in rows if r["chem"] == "LFP"]
    op_lfp  = [r["op_pnl"] for r in rows if r["chem"] == "LFP"]

    # revenue green up
    ax.bar(x - bar_w/2, rev_nmc, bar_w, color="#10b981",
           edgecolor="white", label="V2G revenue (NMC)")
    ax.bar(x + bar_w/2, rev_lfp, bar_w, color="#34d399",
           edgecolor="white", label="V2G revenue (LFP)")
    # battery cost red down
    ax.bar(x - bar_w/2, [-c for c in bat_nmc], bar_w, color="#dc2626",
           edgecolor="white", label="Battery degradation (NMC)")
    ax.bar(x + bar_w/2, [-c for c in bat_lfp], bar_w, color="#9a3412",
           edgecolor="white", label="Battery degradation (LFP)")
    # net annotations
    for i in range(n_typ):
        ax.text(x[i] - bar_w/2, rev_nmc[i] + max(rev_nmc) * 0.04,
                f"{op_nmc[i]:+,.0f}",
                ha="center", fontsize=8, fontweight="bold",
                color=("#15803d" if op_nmc[i] > 0 else "#dc2626"))
        ax.text(x[i] + bar_w/2, rev_lfp[i] + max(rev_lfp) * 0.04,
                f"{op_lfp[i]:+,.0f}",
                ha="center", fontsize=8, fontweight="bold",
                color=("#15803d" if op_lfp[i] > 0 else "#dc2626"))

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=10)
    ax.set_ylabel(f"Annual operating P&L ({currency}/yr)", fontsize=11)
    ax.set_title(
        f"{country}  -  Annual operating P&L\n"
        "V2G revenue minus battery degradation.  No charger CAPEX.",
        fontsize=11, fontweight="bold",
    )
    ax.legend(loc="upper right", fontsize=8, framealpha=0.95)
    ax.grid(True, axis="y", alpha=0.3)

    # ---- RIGHT panel: charger payback in years ----
    ax = axes[1]
    pb_nmc = [r["payback"] for r in rows if r["chem"] == "NMC"]
    pb_lfp = [r["payback"] for r in rows if r["chem"] == "LFP"]
    # cap infinite at a visible 999 for display
    pb_nmc_disp = [min(p, 999) for p in pb_nmc]
    pb_lfp_disp = [min(p, 999) for p in pb_lfp]

    bars_nmc = ax.bar(x - bar_w/2, pb_nmc_disp, bar_w, color="#0891b2",
                      edgecolor="white", label="NMC battery")
    bars_lfp = ax.bar(x + bar_w/2, pb_lfp_disp, bar_w, color="#155e75",
                      edgecolor="white", label="LFP battery")

    # Annotate; show "never" for inf
    for i in range(n_typ):
        label_n = f"{pb_nmc[i]:.0f} y" if pb_nmc[i] < 999 else "never"
        label_l = f"{pb_lfp[i]:.0f} y" if pb_lfp[i] < 999 else "never"
        col_n = ("#15803d" if pb_nmc[i] <= 10
                 else "#f59e0b" if pb_nmc[i] <= 20
                 else "#dc2626")
        col_l = ("#15803d" if pb_lfp[i] <= 10
                 else "#f59e0b" if pb_lfp[i] <= 20
                 else "#dc2626")
        ax.text(x[i] - bar_w/2, pb_nmc_disp[i] + 3, label_n,
                ha="center", fontsize=9, fontweight="bold", color=col_n)
        ax.text(x[i] + bar_w/2, pb_lfp_disp[i] + 3, label_l,
                ha="center", fontsize=9, fontweight="bold", color=col_l)

    ax.axhline(10, color="#15803d", linestyle="--", linewidth=1,
               label="10-year battery life mark")
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=10)
    ax.set_ylabel("Years to recoup V2G premium charger", fontsize=11)
    if country == "UK":
        sub = (f"Premium {premium:,.0f} {currency}.  Includes Sciurus 2021 "
               f"Dynamic Containment revenue {UK_GRID_SERVICES_REVENUE_GBP:.0f} "
               "GBP/yr per V2G EV.")
    else:
        sub = f"Premium {premium:,.0f} {currency}.  V2G revenue at retail peak."
    ax.set_title(
        f"{country}  -  Charger payback time\n{sub}",
        fontsize=11, fontweight="bold",
    )
    ax.legend(loc="upper left", fontsize=9, framealpha=0.95)
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(0, max(50, max(pb_nmc_disp + pb_lfp_disp) * 1.15))

    fig.suptitle(
        f"{country}: V2G driver economics under Wong-realistic volumes",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = OUTDIR / f"w10q_pnl_{country.lower()}.png"
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    return out


def main() -> None:
    out_il = draw_country("Israel", "NIS", V2G_PREMIUM_NIS)
    print(f"Saved {out_il}")
    out_uk = draw_country("UK", "GBP", V2G_PREMIUM_GBP)
    print(f"Saved {out_uk}")


if __name__ == "__main__":
    main()
