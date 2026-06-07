"""W7 demo runner.

Runs a single Daily-Charger EV through one simulated week (168 hours),
three times — once for each counterfactual (V0, V1G, V2G). Writes three
CSV files to outputs/ and prints a short summary.

Usage
-----
    python -m src.run_demo

What you'll see at the end:
    outputs/v0_ev01.csv     — naive charging behaviour
    outputs/v1g_ev01.csv    — smart-charging (off-peak only) behaviour
    outputs/v2g_ev01.csv    — same as V1G for now; Saturday adds real V2G

Plus a printed summary table showing energy bought, money spent, and
ending SoC for each counterfactual.
"""

import csv
from pathlib import Path

from src.agents.ev_agent import (
    EVAgent,
    DAILY_CHARGER,
    COUNTERFACTUAL_V0,
    COUNTERFACTUAL_V1G,
    COUNTERFACTUAL_V2G,
)
from src.pricing import price_at_hour


HOURS_IN_WEEK = 168  # 7 days × 24 hours

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


def run_one_counterfactual(counterfactual: str) -> EVAgent:
    """Create one EV agent and step it through one full week."""
    agent = EVAgent(
        agent_id=1,
        typology=DAILY_CHARGER,
        counterfactual=counterfactual,
    )
    for hour in range(HOURS_IN_WEEK):
        hour_of_day = hour % 24
        price = price_at_hour(hour_of_day)
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
        "counterfactual": agent.counterfactual,
        "kWh bought": round(kwh_bought, 1),
        "kWh sold": round(kwh_sold, 1),
        "net cost (- = earned)": round(net_money, 2),
        "charge hours": n_charge_hours,
        "discharge hours": n_discharge_hours,
        "ending SoC": round(final_soc, 3),
    }


def main() -> None:
    print("=== V2G ABM — W7 demo (one Daily Charger, one week, 3 counterfactuals) ===\n")

    summaries = []
    for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G):
        agent = run_one_counterfactual(cf)
        csv_path = OUTPUTS_DIR / f"{cf.lower()}_ev01.csv"
        write_log_to_csv(agent, csv_path)
        print(f"Wrote {csv_path.relative_to(OUTPUTS_DIR.parent)}  "
              f"({len(agent.hourly_log)} hourly rows)")
        summaries.append(summarise(agent))

    print("\n--- Headline numbers for the week ---")
    cols = list(summaries[0].keys())
    print(" | ".join(f"{c:>14}" for c in cols))
    print("-" * (16 * len(cols) + 3 * (len(cols) - 1)))
    for s in summaries:
        print(" | ".join(f"{str(s[c]):>14}" for c in cols))

    print("\nNotes:")
    print(" - Prices: TAOZ summer (NIS/kWh) — off-peak 0.53, shoulder 0.85, peak 1.69.")
    print(" - V0 always charges any hour it is plugged in, ignoring price.")
    print(" - V1G charges only when price is off-peak or shoulder (not peak).")
    print(" - V2G adds: discharge during evening peak (17:00-23:00) when SoC > 50%")
    print("   and current price >= the agent's OSP (₪1.00).")
    print(" - Negative net cost = the owner earned money on net.")
    print(" - Multiply weekly numbers by 52 for an annual estimate.")


if __name__ == "__main__":
    main()
