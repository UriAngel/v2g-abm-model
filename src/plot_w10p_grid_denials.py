"""GridAgent denial timing + lost revenue per country.

For each country (Israel + UK), runs a full annual sim, captures
every hour where an EVAgent's V2G discharge was denied by feeder
transformer saturation, and plots:

  - Top panel: time-of-day distribution of denied V2G discharge (kWh)
  - Bottom panel: cumulative annual lost driver revenue,
    with the 75/25 driver-aggregator split annotated separately

Two charts (one per country).

Run:  python -m src.plot_w10p_grid_denials
"""

from __future__ import annotations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.run_w9_fleet import run_year
from src.calendar_helper import hour_to_calendar
from src.pricing import price_at_hour
from src.pricing_uk import octopus_powerloop_export_at_hour
from src.agents.ev_agent import COUNTERFACTUAL_V2G


OUTDIR = Path(__file__).resolve().parent.parent / "outputs"

# Driver / aggregator split.  There is no in-model aggregator gate,
# but the dissertation still reports the 75/25 split for transparency.
DRIVER_SHARE     = 0.75
AGGREGATOR_SHARE = 0.25


def run_and_collect_denials(country: str) -> dict:
    """Run one country V2G annual sim, return per-hour denial stats."""
    out = run_year(country=country, counterfactual=COUNTERFACTUAL_V2G,
                   verbose=False)

    # Collect denial events from each agent's hourly log
    hod_denials_kwh = np.zeros(24)
    hod_lost_rev   = np.zeros(24)
    total_lost     = 0.0
    total_denied_kwh = 0.0

    for agent in out["agents"]:
        for entry in agent.hourly_log:
            if entry.get("status") != "IDLE_GRID_LIMITED":
                continue
            # We know the agent WANTED to discharge but couldn't.  Use the
            # agent's max discharge as the kWh that would have flowed.
            kwh = agent.state.max_discharge_power_kw   # 1 hour, so kWh = kW
            hod = entry["hour"] % 24

            # The price the driver would have received at that hour
            if country == "Israel":
                price = price_at_hour(hod, (entry["hour"] // 24) % 7,
                                      hour_to_calendar(entry["hour"])[2])
                # Israel: V2G revenue = retail tariff
            else:
                price = octopus_powerloop_export_at_hour(hod)
                if price <= 0:
                    continue   # Power Pack only pays inside 16-19 window
            lost_revenue = kwh * price
            hod_denials_kwh[hod] += kwh
            hod_lost_rev[hod] += lost_revenue
            total_lost += lost_revenue
            total_denied_kwh += kwh

    return {
        "country": country,
        "hod_kwh": hod_denials_kwh,
        "hod_rev": hod_lost_rev,
        "total_kwh": total_denied_kwh,
        "total_rev": total_lost,
        "feeders": out["feeder_stats"],
        "currency": "NIS" if country == "Israel" else "GBP",
    }


def draw_country_chart(stats: dict) -> Path:
    country = stats["country"]
    ccy = stats["currency"]
    fig, axes = plt.subplots(2, 1, figsize=(11, 7),
                              gridspec_kw={"height_ratios": [1.0, 1.0]})

    hours = np.arange(24)
    bar_w = 0.85

    # --- top: kWh denied by hour of day ---
    ax = axes[0]
    ax.bar(hours, stats["hod_kwh"], bar_w, color="#0891b2",
           edgecolor="white")
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}" for h in hours], fontsize=9)
    ax.set_xlabel("Hour of day", fontsize=10)
    ax.set_ylabel("Denied V2G discharge (kWh)", fontsize=10)
    ax.set_title(
        f"{country}: GridAgent transformer denials by hour of day  "
        f"(annual total {stats['total_kwh']:,.0f} kWh)",
        fontsize=11, fontweight="bold",
    )
    ax.grid(True, axis="y", alpha=0.3)

    # --- bottom: lost revenue, with 75/25 split ---
    ax = axes[1]
    driver_share = stats["hod_rev"] * DRIVER_SHARE
    aggr_share   = stats["hod_rev"] * AGGREGATOR_SHARE
    ax.bar(hours, driver_share, bar_w, color="#15803d",
           label=f"Driver share ({DRIVER_SHARE*100:.0f}%)",
           edgecolor="white")
    ax.bar(hours, aggr_share, bar_w, bottom=driver_share, color="#facc15",
           label=f"Aggregator share ({AGGREGATOR_SHARE*100:.0f}%)",
           edgecolor="white")
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}" for h in hours], fontsize=9)
    ax.set_xlabel("Hour of day", fontsize=10)
    ax.set_ylabel(f"Lost V2G revenue ({ccy})", fontsize=10)

    drv = stats["total_rev"] * DRIVER_SHARE
    agg = stats["total_rev"] * AGGREGATOR_SHARE
    ax.set_title(
        f"{country}: lost V2G revenue by hour of day  "
        f"(annual total {stats['total_rev']:,.0f} {ccy}: "
        f"driver {drv:,.0f} + aggregator {agg:,.0f})",
        fontsize=11, fontweight="bold",
    )
    ax.legend(loc="upper left", fontsize=9, framealpha=0.95)
    ax.grid(True, axis="y", alpha=0.3)

    fig.suptitle(
        f"GridAgent denials   -   {country}   "
        f"({len(stats['feeders'])} feeders, 250 kVA transformer each)",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = OUTDIR / f"w10p_grid_denials_{country.lower()}.png"
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    return out


def main() -> None:
    for country in ("Israel", "UK"):
        print(f"Running {country}...")
        stats = run_and_collect_denials(country)
        out = draw_country_chart(stats)
        print(f"  Saved {out}")
        print(f"  Total kWh denied:   {stats['total_kwh']:,.0f}")
        print(f"  Total revenue lost: {stats['total_rev']:,.0f} "
              f"{stats['currency']}")


if __name__ == "__main__":
    main()
