"""P&L chart restricted to active typologies.

Public and Threshold Charger produce structurally zero V2G, so they
are omitted from the P&L visual; their zero-V2G finding is reported
separately as a structural note.

Active typologies: Daily Charger, BEV 2nd Vehicle.
"""

from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt

from src.plot_style import apply_style, PALETTE
apply_style()
import numpy as np

from src.aggregator_stub import (
    CHARGER_CAPEX_BIDIR_2024_NIS,
    CHARGER_CAPEX_BIDIR_2024_UK_NIS,
    CHARGER_CAPEX_SMART_NIS,
)
from src.aging_table_lit import WONG_V2G_KWH_PER_YEAR, WONG_V2G_EFFECT, v2g_delta_pp_10yr
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
MAX_AGING_DELTA_PCT = 20.0
BATTERY_KWH = 67.0   # Israeli fleet weighted-average (see vehicle_catalog)
ISRAEL_RETAIL_PEAK_NIS = 1.6895
UK_POWER_PACK_GBP      = 0.12
# Sciurus 2021 figures are TOTAL, not additive.  Either/or:
UK_SCIURUS_TOTAL_GBP   = 725.0   # Model B: aggregator + DC ancillary, includes arbitrage

OBSERVED = {
    # Per-opted-in-EV annual V2G volumes (model output).
    "Daily Charger":   4820,
    "BEV 2nd Vehicle": 6220,
}
ACTIVE = list(OBSERVED.keys())


def annual_revenue(country: str, typology: str,
                   uk_model: str = "B_sciurus") -> float:
    """NET annual V2G revenue: gross peak revenue minus off-peak
    recharge cost to refill what was dispatched. RTE = 0.9025.

    Israel off-peak = 0.528 NIS/kWh, RTE = 0.9025.
      net = kWh * (peak - off/RTE) = kWh * (1.6895 - 0.585) = kWh * 1.105
    UK Power Pack: purely export income, no explicit recharge subtraction
      because Powerloop is designed as an export tariff; residential still
      pays retail import elsewhere.
    UK Sciurus Model B: 725 GBP flat is already net per Cenex 2021.
    """
    ISRAEL_OFFPEAK = 0.528
    RTE = 0.9025
    kwh = OBSERVED[typology]
    if country == "Israel":
        gross = kwh * ISRAEL_RETAIL_PEAK_NIS
        recharge = kwh / RTE * ISRAEL_OFFPEAK
        return gross - recharge
    if uk_model == "A_powerpack":
        return kwh * UK_POWER_PACK_GBP
    return UK_SCIURUS_TOTAL_GBP if kwh > 0 else 0.0


def annual_battery_cost(typology: str, chem: str, currency: str) -> float:
    chem_key = "NMC_B1" if chem == "NMC" else "LFP"
    # Beta-based delta from Wong 2026 Appendix E regressions.
    delta_pp = v2g_delta_pp_10yr(typology, chem_key, OBSERVED[typology])
    pct = max(0.0, -delta_pp)   # cost only for losses; improvement -> 0
    lost_kwh = (pct / 100.0) * BATTERY_KWH
    cost_per = (BATTERY_REPLACEMENT_COST_NIS_PER_KWH_NMC if chem == "NMC"
                else BATTERY_REPLACEMENT_COST_NIS_PER_KWH_LFP)
    cost10y = lost_kwh * cost_per
    annual = cost10y / 10.0
    return annual if currency == "NIS" else annual / GBP_TO_NIS


def draw(country: str, currency: str, premium: float) -> Path:
    typs = ACTIVE
    chems = ("NMC", "LFP")
    n_typ = len(typs)

    rows = []
    for typ in typs:
        for chem in chems:
            rev = annual_revenue(country, typ)
            bat = annual_battery_cost(typ, chem, currency)
            op = rev - bat
            pay = (premium / op) if op > 0 else float("inf")
            rows.append({"typ": typ, "chem": chem,
                         "rev": rev, "bat": bat,
                         "op": op, "pay": pay})

    fig, axes = plt.subplots(1, 2, figsize=(14, 6.0))

    # LEFT: operating P&L
    ax = axes[0]
    x = np.arange(n_typ); bw = 0.30
    rev_nmc = [r["rev"] for r in rows if r["chem"] == "NMC"]
    bat_nmc = [r["bat"] for r in rows if r["chem"] == "NMC"]
    op_nmc  = [r["op"]  for r in rows if r["chem"] == "NMC"]
    rev_lfp = [r["rev"] for r in rows if r["chem"] == "LFP"]
    bat_lfp = [r["bat"] for r in rows if r["chem"] == "LFP"]
    op_lfp  = [r["op"]  for r in rows if r["chem"] == "LFP"]

    ax.bar(x - bw/2, rev_nmc, bw, color="#10b981",
           edgecolor="white", label="Annual V2G revenue (NMC)")
    ax.bar(x + bw/2, rev_lfp, bw, color="#34d399",
           edgecolor="white", label="Annual V2G revenue (LFP)")
    ax.bar(x - bw/2, [-c for c in bat_nmc], bw, color="#b91c1c",
           edgecolor="white", label="Annual battery cost (NMC)")
    ax.bar(x + bw/2, [-c for c in bat_lfp], bw, color="#9a3412",
           edgecolor="white", label="Annual battery cost (LFP)")

    # In-bar revenue and battery labels
    for i in range(n_typ):
        # Revenue labels mid-bar
        ax.text(x[i] - bw/2, rev_nmc[i]/2, f"Rev\n{rev_nmc[i]:,.0f}",
                ha="center", va="center", fontsize=9, color="white",
                fontweight="bold")
        ax.text(x[i] + bw/2, rev_lfp[i]/2, f"Rev\n{rev_lfp[i]:,.0f}",
                ha="center", va="center", fontsize=9, color="#0b3d22",
                fontweight="bold")
        # Battery cost labels placed just ABOVE the zero line so they
        # don't overlap with x-tick labels or get clipped by tight y_min.
        ax.text(x[i] - bw/2, max(rev_nmc)*0.01,
                f"-{bat_nmc[i]:,.0f}", ha="center", va="bottom",
                fontsize=9, color="#b91c1c", fontweight="bold")
        ax.text(x[i] + bw/2, max(rev_lfp)*0.01,
                f"-{bat_lfp[i]:,.0f}", ha="center", va="bottom",
                fontsize=9, color="#9a3412", fontweight="bold")
        # Net operating P&L ABOVE the revenue bar (slightly higher for LFP
        # so the two labels don't merge into each other)
        ax.text(x[i] - bw/2, rev_nmc[i] + max(rev_nmc)*0.08,
                f"NMC net\n{op_nmc[i]:+,.0f}", ha="center", fontsize=9,
                fontweight="bold",
                color=("#0f766e" if op_nmc[i] > 0 else "#b91c1c"))
        ax.text(x[i] + bw/2, rev_lfp[i] + max(rev_lfp)*0.08,
                f"LFP net\n{op_lfp[i]:+,.0f}", ha="center", fontsize=9,
                fontweight="bold",
                color=("#0f766e" if op_lfp[i] > 0 else "#b91c1c"))

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x); ax.set_xticklabels(typs, fontsize=12)
    ax.set_ylabel(f"Annual operating P&L ({currency}/yr)", fontsize=11)
    # y_min sits just below the deepest battery bar (15 % margin so
    # labels stay readable).  Both panels use the same rule; the zero
    # line naturally sits low because revenue >> battery cost.
    max_bat = max(bat_nmc + bat_lfp)
    max_rev = max(rev_nmc + rev_lfp)
    ax.set_ylim(-max_bat * 1.15, max_rev * 1.30)
    ax.set_title(f"{country}  -  Annual operating P&L (active typologies)\n"
                 "V2G revenue minus battery degradation cost.",
                 fontsize=11, fontweight="bold")
    # Legend BELOW the plot so it does not overlap the bars
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncol=4, fontsize=8.5, framealpha=0.95)
    ax.grid(True, axis="y", alpha=0.3)

    # RIGHT: payback
    ax = axes[1]
    pb_nmc = [r["pay"] for r in rows if r["chem"] == "NMC"]
    pb_lfp = [r["pay"] for r in rows if r["chem"] == "LFP"]
    pb_nmc_d = [min(p, 999) for p in pb_nmc]
    pb_lfp_d = [min(p, 999) for p in pb_lfp]

    ax.bar(x - bw/2, pb_nmc_d, bw, color="#1d4ed8",
           edgecolor="white", label="NMC")
    ax.bar(x + bw/2, pb_lfp_d, bw, color="#155e75",
           edgecolor="white", label="LFP")

    for i in range(n_typ):
        ln = f"{pb_nmc[i]:.0f} y" if pb_nmc[i] < 999 else "never"
        ll = f"{pb_lfp[i]:.0f} y" if pb_lfp[i] < 999 else "never"
        cn = ("#0f766e" if pb_nmc[i] <= 10 else "#d97706" if pb_nmc[i] <= 20 else "#b91c1c")
        cl = ("#0f766e" if pb_lfp[i] <= 10 else "#d97706" if pb_lfp[i] <= 20 else "#b91c1c")
        ax.text(x[i] - bw/2, pb_nmc_d[i] + 0.5, ln,
                ha="center", fontsize=12, fontweight="bold", color=cn)
        ax.text(x[i] + bw/2, pb_lfp_d[i] + 0.5, ll,
                ha="center", fontsize=12, fontweight="bold", color=cl)

    ax.axhline(10, color="#0f766e", linestyle="--", linewidth=1,
               label="10-year battery life mark")
    ax.set_xticks(x); ax.set_xticklabels(typs, fontsize=12)
    ax.set_ylabel("Years to recoup V2G premium", fontsize=11)
    sub = (f"V2G premium = bidirectional minus smart unidirectional "
           f"= {premium:,.0f} {currency}.")
    if country == "UK":
        sub += f"  Sciurus aggregator model: {UK_SCIURUS_TOTAL_GBP:.0f} GBP/V2G EV/yr (total)."
    ax.set_title(f"{country}  -  V2G PREMIUM payback (years)\n{sub}",
                 fontsize=11, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10, framealpha=0.95)
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(0, max(20, max(pb_nmc_d + pb_lfp_d) * 1.20))

    fig.suptitle(f"{country}: V2G driver economics  -  active typologies only "
                 "(Public + Threshold dropped, structural zero V2G)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    out = OUTDIR / f"w11c_pnl_active_{country.lower()}.png"
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    return out


def main() -> None:
    print(f"Saved {draw('Israel', 'NIS', V2G_PREMIUM_NIS)}")
    print(f"Saved {draw('UK', 'GBP', V2G_PREMIUM_GBP)}")


if __name__ == "__main__":
    main()
