"""W7 demo runner — Sunday Batch 2 version.

Runs four EVs (one per typology) through one simulated week, three times
each (V0, V1G, V2G). That's 12 simulations total. Writes 12 CSV files
to outputs/ and prints a summary table grouped by typology.

Usage
-----
    python -m src.run_demo

Outputs
-------
    outputs/daily_charger_v0.csv,  daily_charger_v1g.csv,  daily_charger_v2g.csv
    outputs/public_charger_v0.csv, public_charger_v1g.csv, public_charger_v2g.csv
    outputs/bev_2nd_vehicle_v0.csv, bev_2nd_vehicle_v1g.csv, bev_2nd_vehicle_v2g.csv
    outputs/threshold_charger_v0.csv, threshold_charger_v1g.csv, threshold_charger_v2g.csv

Plus a printed summary showing energy bought, energy sold, net cost, and
ending SoC for every (typology × counterfactual) combination.
"""

import csv
from pathlib import Path

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
from src.pricing import price_at_hour


HOURS_IN_WEEK = 168  # 7 days × 24 hours
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
COUNTERFACTUALS = (COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G)


# Slugify typology names for filenames (e.g. "Daily Charger" → "daily_charger")
def slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def run_one(typology: str, counterfactual: str, agent_id: int) -> EVAgent:
    """Create one EV agent and step it through one full week."""
    agent = EVAgent(agent_id=agent_id, typology=typology, counterfactual=counterfactual)
    for hour in range(HOURS_IN_WEEK):
        price = price_at_hour(hour % 24)
        agent.step(current_hour=hour, current_price_per_kwh=price)
    return agent


def write_log_to_csv(agent: EVAgent, path: Path) -> None:
    """Save one agent's hourly log as a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not agent.hourly_log:
        return
    fieldnames = list(agent.hourly_log[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(agent.hourly_log)


def summarise(agent: EVAgent) -> dict:
    """Return a few headline numbers for one week of simulation."""
    kwh_bought = sum(
        row["energy_kwh"] for row in agent.hourly_log if row["action"] == "CHARGE"
    )
    kwh_sold = sum(
        -row["energy_kwh"] for row in agent.hourly_log if row["action"] == "DISCHARGE"
    )
    net_money = sum(row["cost_currency"] for row in agent.hourly_log)
    final_soc = agent.state.soc
    n_charge_hours = sum(1 for row in agent.hourly_log if row["action"] == "CHARGE")
    n_discharge_hours = sum(1 for row in agent.hourly_log if row["action"] == "DISCHARGE")
    return {
        "typology": agent.typology,
        "counterfactual": agent.counterfactual,
        "kWh bought": round(kwh_bought, 1),
        "kWh sold": round(kwh_sold, 1),
        "net ₪/week": round(net_money, 2),
        "annual ₪": round(net_money * 52, 0),
        "charge h": n_charge_hours,
        "discharge h": n_discharge_hours,
        "ending SoC": round(final_soc, 3),
    }


def main() -> None:
    print("=== V2G ABM — W7 Sunday demo (4 typologies × 3 counterfactuals × 1 week) ===\n")
    print("Prices: TAOZ summer (NIS/kWh)  —  off-peak 0.53, shoulder 0.85, peak 1.69\n")

    summaries = []
    for agent_id, typology in enumerate(ALL_TYPOLOGIES, start=1):
        for cf in COUNTERFACTUALS:
            agent = run_one(typology, cf, agent_id=agent_id)
            csv_path = OUTPUTS_DIR / f"{slug(typology)}_{cf.lower()}.csv"
            write_log_to_csv(agent, csv_path)
            summaries.append(summarise(agent))

    # Pretty print summary, grouped by typology
    cols = list(summaries[0].keys())
    print("--- Headline numbers (one EV per typology, one week each) ---\n")
    print(" | ".join(f"{c:>14}" for c in cols))
    print("-" * (16 * len(cols) + 3 * (len(cols) - 1)))
    for s in summaries:
        print(" | ".join(f"{str(s[c]):>14}" for c in cols))
        # blank line between typologies for readability
        if s["counterfactual"] == COUNTERFACTUAL_V2G:
            print()

    print("Notes:")
    print(" - 'net ₪/week' < 0 means the owner earned money on net.")
    print(" - 'annual ₪' = weekly × 52 (rough annual estimate).")
    print(" - Public Charger has no home charger in this version, so V2G is")
    print("   impossible for them — they need a future workplace-DC scenario.")
    print(" - BEV 2nd Vehicle drives only Mon-Thu (4 of 7 days).")
    print(" - Each agent gets ±1-2 h random jitter on departure/return so cars")
    print("   no longer all leave / arrive at the same time.")


if __name__ == "__main__":
    main()
