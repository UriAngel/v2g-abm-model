"""Smoke test: two-country, three-counterfactual end-to-end.

Confirms GridAgent and UK pricing work together end-to-end.  Runs
Israel (TAOZ) and UK (Ofgem cap / Octopus Go / Powerloop) for each
of V0, V1G, V2G, prints headline fleet results.

Run:  python -m src.smoke_w10d_twocountry
"""

from __future__ import annotations

from src.agents.ev_agent import (
    COUNTERFACTUAL_V0,
    COUNTERFACTUAL_V1G,
    COUNTERFACTUAL_V2G,
    DAILY_CHARGER,
    PUBLIC_CHARGER,
    BEV_2ND_VEHICLE,
    THRESHOLD_CHARGER,
)
from src.pricing_uk import GBP_TO_NIS
from src.run_w9_fleet import run_year


COUNTERFACTUALS = (COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G)

# Smaller fleet so the 6-run two-country sweep fits within a developer
# iteration cycle (~15 s).  For headline dissertation numbers use the
# full DEFAULT_FLEET_SHARES via run_w9_fleet directly.
SMOKE_FLEET = {
    DAILY_CHARGER:     21,
    PUBLIC_CHARGER:    15,
    BEV_2ND_VEHICLE:   14,
    THRESHOLD_CHARGER: 30,
}   # 80 agents


def summarise(country: str, cf: str) -> dict:
    """Run one country/counterfactual for a full year and return totals."""
    out = run_year(country=country, counterfactual=cf,
                   shares=SMOKE_FLEET, verbose=False)
    agents = out["agents"]

    total_v2g_kwh = sum(a.state.cumulative_v2g_discharge_kwh for a in agents)
    # Currency: ev_agent records driver currency (NIS for Israel, GBP for UK).
    total_revenue = sum(
        -r["cost_currency"] for a in agents for r in a.hourly_log
        if r["cost_currency"] < 0
    )
    total_cost = sum(
        r["cost_currency"] for a in agents for r in a.hourly_log
        if r["cost_currency"] > 0
    )
    n_opted_in = sum(1 for a in agents if a.state.v2g_opted_in)

    peak_export_kw = max(fs["peak_export_kw"] for fs in out["feeder_stats"])
    denied_total = sum(fs["denied_discharges"] for fs in out["feeder_stats"])

    return {
        "country": country,
        "counterfactual": cf,
        "n_agents": len(agents),
        "n_v2g_opted": n_opted_in,
        "v2g_kwh_yr": total_v2g_kwh,
        "import_cost_yr": total_cost,
        "v2g_revenue_yr": total_revenue,
        "net_yr": total_revenue - total_cost,
        "peak_export_kw": peak_export_kw,
        "denied_discharges": denied_total,
        "wall_time_s": out["wall_time_s"],
    }


def main() -> None:
    rows = []
    for country in ("Israel", "UK"):
        for cf in COUNTERFACTUALS:
            rows.append(summarise(country, cf))

    print()
    print(f"End-to-end fleet test (240 agents x 8760 hours)")
    print(f"{'-' * 100}")
    hdr = (f"{'Country':>8} | {'CF':>4} | {'V2G EVs':>8} | "
           f"{'V2G kWh/yr':>11} | {'Import':>11} | {'Revenue':>10} | "
           f"{'Net':>10} | {'PkExp':>6} | {'t':>5}")
    print(hdr); print("-" * len(hdr))

    for r in rows:
        ccy = "NIS" if r["country"] == "Israel" else "GBP"
        print(f"{r['country']:>8} | {r['counterfactual']:>4} | "
              f"{r['n_v2g_opted']:>8,} | {r['v2g_kwh_yr']:>11,.0f} | "
              f"{r['import_cost_yr']:>8,.0f} {ccy} | "
              f"{r['v2g_revenue_yr']:>6,.0f} {ccy} | "
              f"{r['net_yr']:>6,.0f} {ccy} | "
              f"{r['peak_export_kw']:>4.0f}kW | "
              f"{r['wall_time_s']:>3.1f}s")

    # Per-V2G-opted-EV headline (the citable number for the dissertation)
    print()
    print("Per V2G-opted-in EV (annual):")
    for r in rows:
        if r["counterfactual"] != "V2G" or r["n_v2g_opted"] == 0:
            continue
        ccy = "NIS" if r["country"] == "Israel" else "GBP"
        kwh = r["v2g_kwh_yr"] / r["n_v2g_opted"]
        rev = r["v2g_revenue_yr"] / r["n_v2g_opted"]
        print(f"  {r['country']:>8}: {kwh:>5,.0f} kWh/yr, {rev:>6,.0f} {ccy}/yr "
              f"({rev * (1 if ccy == 'NIS' else GBP_TO_NIS):>6,.0f} NIS-equivalent)")


if __name__ == "__main__":
    main()
