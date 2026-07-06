"""Per-country 10-year driver P&L.

Two charts: one for Israel, one for UK.  Each shows, per typology:
  + V2G revenue (10 years)             - GREEN gain bar
  - Battery degradation NIS/GBP cost   - RED loss bar
  - V2G premium charger CAPEX (one-off) - ORANGE loss bar
  = Net 10-year driver P&L              - black bar with label

V2G revenue source: simulated annual revenue from the smoke_w10d_twocountry
end-to-end run, x 10 years.

Battery cost: Wong V2G qualitative effect category translated into a
chemistry-specific 10-year capacity loss delta:
  IMPROVE  -> -2 pp  (negative cost = saving)
  NEUTRAL  ->  0 pp
  SLIGHT   ->  1.5 pp
  DECREASE ->  3 pp
  LARGE    ->  6 pp
times battery pack size (60 kWh) times BloombergNEF 2025 chemistry price.
Reported separately for NMC and LFP (different replacement costs).

V2G premium CAPEX: bidirectional installed cost minus the smart
unidirectional baseline (constants from aggregator_stub).

Run:  python -m src.plot_w10o_10yr_pnl
"""

from __future__ import annotations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.aggregator_stub import CHARGER_CAPEX_BIDIR_2024_NIS, CHARGER_CAPEX_SMART_NIS
from src.aging_table_lit import (
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
V2G_PREMIUM_GBP = V2G_PREMIUM_NIS / GBP_TO_NIS

# Wong V2G effect category -> percentage point delta on the V0 baseline
# 10-year capacity loss.  Visual reads from Wong 2026 Figure 6.
V2G_DELTA_PCT = {
    "IMPROVE":   -2.0,
    "NEUTRAL":    0.0,
    "SLIGHT":    +1.5,
    "DECREASE":  +3.0,
    "LARGE":     +6.0,
}

BATTERY_KWH = 67.0   # Israeli fleet weighted-average (see vehicle_catalog)

# Per-typology annual V2G revenue (from the smoke_w10d_twocountry retail run,
# with Wong-anchored caps - 1259/111/576/204 kWh/yr).
# Israel: retail TAOZ peak (1.69 NIS/kWh).
# UK: Power Pack 12 p export (0.12 GBP/kWh).
# Revenue = annual_v2g_kwh * average export price.
ISRAEL_RETAIL_PEAK_NIS = 1.6895
UK_POWER_PACK_GBP      = 0.12


def annual_revenue(country: str, typology: str) -> float:
    """V2G revenue / year for one typology under the country's V2G product."""
    kwh = WONG_V2G_KWH_PER_YEAR[typology]["mean"]
    if country == "Israel":
        return kwh * ISRAEL_RETAIL_PEAK_NIS
    if country == "UK":
        return kwh * UK_POWER_PACK_GBP
    raise ValueError(country)


def battery_cost_10yr(typology: str, chemistry: str, currency: str) -> float:
    """Battery degradation cost over 10 years in driver's local currency.

    chemistry: 'NMC' or 'LFP'
    currency:  'NIS' or 'GBP'
    """
    # Translate Wong qualitative effect into a percentage-point V2G delta.
    # Wong reports per (typology, chemistry) - we use NMC_B1 here as the
    # representative NMC for simplicity (B2 is mixed; LFP is cycle-dominated).
    chem_key = "NMC_B1" if chemistry == "NMC" else "LFP"
    pct_delta = V2G_DELTA_PCT[WONG_V2G_EFFECT[typology][chem_key]]

    # Capacity lost in kWh terms (fraction of full pack).
    lost_kwh = (pct_delta / 100.0) * BATTERY_KWH

    # Per-kWh replacement cost from BNEF 2025 survey, NIS.
    if chemistry == "NMC":
        cost_nis_per_kwh = BATTERY_REPLACEMENT_COST_NIS_PER_KWH_NMC
    else:
        cost_nis_per_kwh = BATTERY_REPLACEMENT_COST_NIS_PER_KWH_LFP

    cost_nis = lost_kwh * cost_nis_per_kwh
    if currency == "NIS":
        return cost_nis
    return cost_nis / GBP_TO_NIS


def draw_one_country(country: str, ax, currency: str, premium: float) -> None:
    """Draw the 10-year P&L stacked bars for one country into ax."""
    typologies = list(WONG_V2G_KWH_PER_YEAR.keys())
    n = len(typologies)
    x = np.arange(n)
    bar_w = 0.32

    revenues_10y = [annual_revenue(country, t) * 10 for t in typologies]
    # We report two chemistries: NMC and LFP, side by side per typology.
    nmc_cost = [battery_cost_10yr(t, "NMC", currency) for t in typologies]
    lfp_cost = [battery_cost_10yr(t, "LFP", currency) for t in typologies]

    # Bars
    b_rev_nmc = ax.bar(x - bar_w/2, revenues_10y, bar_w, color="#10b981",
                       label="V2G revenue (10 y)", edgecolor="white")
    b_rev_lfp = ax.bar(x + bar_w/2, revenues_10y, bar_w, color="#10b981",
                       edgecolor="white")

    # Costs below zero
    b_bat_nmc = ax.bar(x - bar_w/2, [-c for c in nmc_cost], bar_w,
                       color="#dc2626", edgecolor="white",
                       label="Battery degradation (NMC, 10 y)")
    b_bat_lfp = ax.bar(x + bar_w/2, [-c for c in lfp_cost], bar_w,
                       color="#9a3412", edgecolor="white",
                       label="Battery degradation (LFP, 10 y)")

    # Charger CAPEX premium (one-off) - small bar on top of cost
    cap_nmc = [-premium for _ in typologies]
    cap_lfp = [-premium for _ in typologies]
    b_cap_nmc = ax.bar(x - bar_w/2, cap_nmc, bar_w,
                       bottom=[-c for c in nmc_cost],
                       color="#f59e0b", edgecolor="white",
                       label="V2G premium CAPEX (one-off)")
    b_cap_lfp = ax.bar(x + bar_w/2, cap_lfp, bar_w,
                       bottom=[-c for c in lfp_cost],
                       color="#f59e0b", edgecolor="white")

    # Net annotations
    for i, t in enumerate(typologies):
        net_nmc = revenues_10y[i] - nmc_cost[i] - premium
        net_lfp = revenues_10y[i] - lfp_cost[i] - premium
        ax.text(x[i] - bar_w/2, -premium - max(nmc_cost) - 1500,
                f"NMC\n{net_nmc:,.0f}",
                ha="center", fontsize=8, fontweight="bold",
                color=("#15803d" if net_nmc >= 0 else "#dc2626"))
        ax.text(x[i] + bar_w/2, -premium - max(lfp_cost) - 1500,
                f"LFP\n{net_lfp:,.0f}",
                ha="center", fontsize=8, fontweight="bold",
                color=("#15803d" if net_lfp >= 0 else "#dc2626"))

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=10)
    ax.set_ylabel(f"10-year driver P&L ({currency})", fontsize=11)
    ax.grid(True, axis="y", alpha=0.3)


def main() -> None:
    # --- ISRAEL chart ---
    fig, ax = plt.subplots(figsize=(11, 6.5))
    draw_one_country("Israel", ax, "NIS", V2G_PREMIUM_NIS)
    ax.set_title(
        "Israel  -  10-year driver P&L per typology (NMC and LFP)\n"
        f"V2G revenue at retail peak (1.69 NIS/kWh).  V2G premium "
        f"{V2G_PREMIUM_NIS:,.0f} NIS (Wallbox Quasar 2 midpoint).  "
        f"Battery cost at BloombergNEF 2025: NMC 600, LFP 380 NIS/kWh.",
        fontsize=11, fontweight="bold",
    )
    ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
    fig.tight_layout()
    out = OUTDIR / "w10o_pnl_israel.png"
    fig.savefig(out, dpi=150, facecolor="white"); print(f"Saved {out}")
    plt.close(fig)

    # --- UK chart ---
    fig, ax = plt.subplots(figsize=(11, 6.5))
    draw_one_country("UK", ax, "GBP", V2G_PREMIUM_GBP)
    ax.set_title(
        "UK  -  10-year driver P&L per typology (NMC and LFP)\n"
        f"V2G revenue at Octopus Power Pack 12 p/kWh export.  V2G premium "
        f"GBP {V2G_PREMIUM_GBP:,.0f} (Wallbox Quasar 2 midpoint).  "
        "Battery cost at BloombergNEF 2025 chemistry rates.",
        fontsize=11, fontweight="bold",
    )
    ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
    fig.tight_layout()
    out = OUTDIR / "w10o_pnl_uk.png"
    fig.savefig(out, dpi=150, facecolor="white"); print(f"Saved {out}")
    plt.close(fig)


if __name__ == "__main__":
    main()
