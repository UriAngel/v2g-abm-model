"""Two-country business model plot.

Renders side-by-side Israel and UK results from a single run of the
fleet engine.  Six panels (2 rows x 3 columns):

  (a) Israel driver annual benefit per typology  (V1G + V2G)
  (b) Israel driver payback periods               (V0->V1G, V1G->V2G)
  (c) Israel aggregator revenue per car
  (d) UK driver annual benefit per typology       (V1G + V2G)
  (e) UK driver payback periods                   (V0->V1G, V1G->V2G)
  (f) UK aggregator revenue per car

Units differ by country: Israel in NIS, UK in GBP.

Run:  python -m src.plot_w9_two_country
Output:  outputs/w9_two_country.png
"""

from __future__ import annotations
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import src.agents.ev_agent as ev_agent_module
from src.agents.ev_agent import (
    ALL_TYPOLOGIES,
    DAILY_CHARGER, PUBLIC_CHARGER, BEV_2ND_VEHICLE, THRESHOLD_CHARGER,
    COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G,
)
from src.aggregator_stub import (
    CHARGER_CAPEX_SMART_NIS,
    V2G_PREMIUM_2024_NIS,
    AGGREGATOR_REVENUE_SHARE,
)
from src.pricing_uk import GBP_TO_NIS
from src.run_w9_fleet import run_year


# Small fleet so the script fits in memory.  Wong shares preserved.
SHARES = {
    DAILY_CHARGER:     10,
    PUBLIC_CHARGER:     8,
    BEV_2ND_VEHICLE:    7,
    THRESHOLD_CHARGER: 15,
}   # 40 vehicles total

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

COLORS = {
    DAILY_CHARGER:     "#1f77b4",
    PUBLIC_CHARGER:    "#ff7f0e",
    BEV_2ND_VEHICLE:   "#2ca02c",
    THRESHOLD_CHARGER: "#d62728",
}


def collect(country: str) -> dict:
    """Run V0/V1G/V2G for one country and aggregate per-typology means."""
    out: dict = {}
    for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G):
        res = run_year(country=country, counterfactual=cf, shares=SHARES, verbose=False)
        by_typ_net = defaultdict(list)
        by_typ_kwh_sold = defaultdict(list)
        for a in res["agents"]:
            net = sum(r["cost_currency"] for r in a.hourly_log)
            by_typ_net[a.typology].append(net)
            if cf == COUNTERFACTUAL_V2G:
                kwh = sum(-r["energy_kwh"] for r in a.hourly_log if r["action"] == "DISCHARGE")
                by_typ_kwh_sold[a.typology].append(kwh)
        out[cf] = {t: float(np.mean(v)) for t, v in by_typ_net.items()}
        if cf == COUNTERFACTUAL_V2G:
            out["v2g_kwh_sold"] = {t: float(np.mean(v)) for t, v in by_typ_kwh_sold.items()}
    return out


def panel_benefit(ax, data, title, unit):
    x = np.arange(len(ALL_TYPOLOGIES))
    w = 0.35
    v1g_savings, v2g_total = [], []
    for t in ALL_TYPOLOGIES:
        v0 = data[COUNTERFACTUAL_V0][t]
        v1 = data[COUNTERFACTUAL_V1G][t]
        v2 = data[COUNTERFACTUAL_V2G][t]
        v1g_savings.append(v0 - v1)
        v2g_total.append(v0 - v2)
    ax.bar(x - w/2, v1g_savings, w, label="V1G savings (vs V0)", color="#9ca3af")
    ax.bar(x + w/2, v2g_total,   w, label="V2G total benefit (vs V0)", color="#10b981")
    for i in range(len(ALL_TYPOLOGIES)):
        ax.text(i - w/2, v1g_savings[i] + max(v1g_savings + v2g_total) * 0.02,
                f"{v1g_savings[i]:,.0f}", ha="center", fontsize=8.5)
        ax.text(i + w/2, v2g_total[i] + max(v1g_savings + v2g_total) * 0.02,
                f"{v2g_total[i]:,.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in ALL_TYPOLOGIES], fontsize=8)
    ax.set_ylabel(f"Annual driver benefit ({unit}/yr)")
    ax.set_title(title)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.legend(fontsize=7, loc="upper right")


def panel_payback(ax, data, title, smart_capex, v2g_premium, unit):
    x = np.arange(len(ALL_TYPOLOGIES))
    w = 0.35
    p_v0v1g, p_v1gv2g = [], []
    for t in ALL_TYPOLOGIES:
        v0 = data[COUNTERFACTUAL_V0][t]
        v1 = data[COUNTERFACTUAL_V1G][t]
        v2 = data[COUNTERFACTUAL_V2G][t]
        s = v0 - v1
        m = v1 - v2
        p_v0v1g.append(smart_capex / s if s > 0 else float("inf"))
        p_v1gv2g.append(v2g_premium / m if m > 0 else float("inf"))
    cap_a = [min(p, 30) for p in p_v0v1g]
    cap_b = [min(p, 30) for p in p_v1gv2g]
    ax.bar(x - w/2, cap_a, w, label=f"V0→V1G ({smart_capex:,.0f} {unit})", color="#9ca3af")
    ax.bar(x + w/2, cap_b, w, label=f"V1G→V2G ({v2g_premium:,.0f} {unit})", color="#10b981")
    for i in range(len(ALL_TYPOLOGIES)):
        la = "no payback" if p_v0v1g[i] == float("inf") else f"{p_v0v1g[i]:.1f}yr"
        lb = "no payback" if p_v1gv2g[i] == float("inf") else f"{p_v1gv2g[i]:.1f}yr"
        ax.text(i - w/2, min(cap_a[i] + 0.5, 27), la, ha="center", fontsize=8, fontweight="bold")
        ax.text(i + w/2, min(cap_b[i] + 0.5, 27), lb, ha="center", fontsize=8, fontweight="bold")
    ax.axhline(10, color="black", linestyle="--", linewidth=1, label="Charger life ~10y")
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in ALL_TYPOLOGIES], fontsize=8)
    ax.set_ylabel("Years to repay charger CAPEX")
    ax.set_title(title)
    ax.legend(fontsize=7, loc="upper left")
    ax.set_ylim(0, 30)


def panel_aggregator(ax, data, title, peak_price, unit):
    """Aggregator annual revenue per car: kWh sold × peak price × share."""
    x = np.arange(len(ALL_TYPOLOGIES))
    kwh = data.get("v2g_kwh_sold", {t: 0.0 for t in ALL_TYPOLOGIES})
    rev = [kwh[t] * peak_price * AGGREGATOR_REVENUE_SHARE for t in ALL_TYPOLOGIES]
    colors = [COLORS[t] for t in ALL_TYPOLOGIES]
    ax.bar(x, rev, color=colors)
    for i, v in enumerate(rev):
        ax.text(i, v + max(rev) * 0.02 if max(rev) > 0 else 1, f"{v:,.0f}",
                ha="center", fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in ALL_TYPOLOGIES], fontsize=8)
    ax.set_ylabel(f"Aggregator revenue ({unit}/car/yr)")
    ax.set_title(title)


def main() -> None:
    ev_agent_module.SEM_ENABLED = True
    print("Collecting Israel...")
    il = collect("Israel")
    print("Collecting UK...")
    uk = collect("UK")

    # UK CAPEX (rough conversion using GBP_TO_NIS)
    smart_uk = CHARGER_CAPEX_SMART_NIS / GBP_TO_NIS
    premium_uk = V2G_PREMIUM_2024_NIS / GBP_TO_NIS

    fig, axes = plt.subplots(2, 3, figsize=(20, 11))

    panel_benefit(axes[0][0], il, "(a) Israel driver annual benefit", "NIS")
    panel_payback(axes[0][1], il, "(b) Israel payback",
                  CHARGER_CAPEX_SMART_NIS, V2G_PREMIUM_2024_NIS, "NIS")
    panel_aggregator(axes[0][2], il, "(c) Israel aggregator revenue per car",
                     peak_price=1.6895, unit="NIS")

    panel_benefit(axes[1][0], uk, "(d) UK driver annual benefit", "GBP")
    panel_payback(axes[1][1], uk, "(e) UK payback",
                  smart_uk, premium_uk, "GBP")
    panel_aggregator(axes[1][2], uk, "(f) UK aggregator revenue per car",
                     peak_price=0.214, unit="GBP")

    fig.suptitle(
        "V2G business model: Israel residential TAOZ vs UK Octopus Go/Powerloop, "
        "annual horizon with GridAgent feeder constraint",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    out = OUTPUTS_DIR / "w9_two_country.png"
    fig.savefig(out, dpi=140, facecolor="white")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
