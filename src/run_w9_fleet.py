"""W9 fleet runner with GridAgent transformer constraint and OSP-priority
discharge dispatch.

Two differences from the W7-W8 demo runner:

  1. Annual horizon (8,760 hours) with seasonal TAOZ dispatch.
  2. Each hour, agents within a feeder step in ASCENDING OSP order
     (most willing first), so under feeder saturation the most willing
     V2G agents are dispatched first.  Agents whose action is denied
     by the feeder transformer constraint log "IDLE_GRID_LIMITED" and
     no energy or money changes hands.

This runner is independent of run_demo.py so the W7-W8 weekly demo can
still be replayed for comparison.
"""

from __future__ import annotations

import time

from src.agents.ev_agent import (
    EVAgent,
    ALL_TYPOLOGIES,
    DAILY_CHARGER,
    PUBLIC_CHARGER,
    BEV_2ND_VEHICLE,
    THRESHOLD_CHARGER,
    COUNTERFACTUAL_V0,
    COUNTERFACTUAL_V1G,
    COUNTERFACTUAL_V2G,
)
import src.agents.ev_agent as ev_agent_module

from src.pricing import price_at_hour as pricing_israel
from src.pricing_uk import (
    uk_price_at_hour,
    octopus_powerloop_export_at_hour,
)
from src.calendar_helper import hour_to_calendar, HOURS_IN_YEAR
from src.grid_agent import (
    build_feeders,
    DEFAULT_AGENTS_PER_FEEDER,
    DEFAULT_TRANSFORMER_KVA,
)


# Default fleet composition (matches Wong et al. 2026 California shares,
# scaled to a 240-vehicle fleet so each feeder serves ~50 households).
DEFAULT_FLEET_SHARES = {
    DAILY_CHARGER:     62,    # 26 %
    PUBLIC_CHARGER:    46,    # 19 %
    BEV_2ND_VEHICLE:   41,    # 17 %
    THRESHOLD_CHARGER: 91,    # 38 %
}                              # total 240


def _country_prices(country: str, counterfactual: str, hour_of_day: int,
                    day_of_week: int, month: int) -> tuple[float, float | None]:
    """Return (import_price, discharge_revenue) for the country and counterfactual.

    discharge_revenue is None when import==export (Israel convention)
    so that step() falls back to import price for V2G discharge.
    """
    if country == "Israel":
        p = pricing_israel(hour_of_day, day_of_week, month)
        return p, None
    if country in ("UK", "United Kingdom"):
        imp = uk_price_at_hour(counterfactual, hour_of_day, day_of_week, month)
        if counterfactual == COUNTERFACTUAL_V2G:
            exp = octopus_powerloop_export_at_hour(hour_of_day, day_of_week, month)
            return imp, exp
        return imp, None
    raise ValueError(f"unknown country {country!r}")


def build_fleet(
    country: str,
    counterfactual: str,
    shares: dict | None = None,
) -> list[EVAgent]:
    """Build the fleet of EVAgents for one (country, counterfactual) run."""
    ev_agent_module.SEM_ENABLED = True
    shares = shares or DEFAULT_FLEET_SHARES
    agents: list[EVAgent] = []
    next_id = 1
    for typology, n in shares.items():
        for _ in range(n):
            a = EVAgent(
                agent_id=next_id,
                typology=typology,
                counterfactual=counterfactual,
                country=country,
            )
            agents.append(a)
            next_id += 1
    return agents


def run_year(
    country: str,
    counterfactual: str,
    shares: dict | None = None,
    transformer_kva: float = DEFAULT_TRANSFORMER_KVA,
    agents_per_feeder: int = DEFAULT_AGENTS_PER_FEEDER,
    verbose: bool = True,
) -> dict:
    """Simulate one (country, counterfactual) run for a full year.

    Returns a dict with the fleet, per-agent results, and feeder stats.
    """
    agents = build_fleet(country, counterfactual, shares)
    feeders = build_feeders(
        agents,
        agents_per_feeder=agents_per_feeder,
        transformer_kva=transformer_kva,
        hours_in_year=HOURS_IN_YEAR,
    )

    if verbose:
        print(f"[run_year] {country} {counterfactual}: "
              f"{len(agents)} agents on {len(feeders)} feeders")

    t0 = time.time()
    for hour in range(HOURS_IN_YEAR):
        hod, dow, month = hour_to_calendar(hour)
        imp, exp = _country_prices(country, counterfactual, hod, dow, month)
        # OSP-priority dispatch: per feeder, step agents in ASCENDING OSP order.
        # This matters only under V2G when the transformer can saturate; for
        # V0/V1G the sort order is harmless.
        for feeder in feeders:
            agents_sorted = sorted(feeder.ev_agents, key=lambda a: a.state.osp)
            for agent in agents_sorted:
                agent.step(
                    current_hour=hour,
                    current_price_per_kwh=imp,
                    month=month,
                    discharge_revenue_per_kwh=exp,
                )
    dt = time.time() - t0
    if verbose:
        print(f"[run_year] {country} {counterfactual}: "
              f"completed in {dt:.1f}s")

    feeder_stats = [f.stats() for f in feeders]
    return {
        "country": country,
        "counterfactual": counterfactual,
        "agents": agents,
        "feeders": feeders,
        "feeder_stats": feeder_stats,
        "wall_time_s": dt,
    }


if __name__ == "__main__":
    # W9.F sanity gate: run Israel V2G for one year, report feeder stats.
    out = run_year(country="Israel", counterfactual=COUNTERFACTUAL_V2G)
    print("\n=== Feeder stats (Israel V2G) ===")
    for fs in out["feeder_stats"]:
        print(f"  Feeder {fs['feeder_id']}: "
              f"{fs['n_agents']:>2} agents, "
              f"peak_import={fs['peak_import_kw']:>5.0f} kW, "
              f"peak_export={fs['peak_export_kw']:>5.0f} kW, "
              f"export-constrained hours={fs['constrained_export_hours']:>3}, "
              f"discharges denied={fs['denied_discharges']:>4}")
