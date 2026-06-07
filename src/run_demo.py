"""W7 demo runner — Sunday Batch 3 version.

Now runs a fleet of 5 EVs per typology = 20 cars total, each with its
own random commute jitter and daily-km variation. Each car is simulated
under three counterfactuals (V0, V1G, V2G), so there are 60 individual
simulations behind one demo run.

For each (typology, counterfactual) combination we write one CSV file
containing all 5 cars' hourly logs (840 rows per file, with an agent_id
column). 12 files total.

Usage
-----
    python -m src.run_demo

Outputs
-------
    outputs/<typology>_<cf>.csv       — 12 files, 840 rows each
    Printed summary table grouped by typology, showing mean ± std across
    the 5 cars in each (typology, counterfactual) cell.
"""

import csv
import statistics
from pathlib import Path

from src.agents.ev_agent import (
    EVAgent,
    ALL_TYPOLOGIES,
    COUNTERFACTUAL_V0,
    COUNTERFACTUAL_V1G,
    COUNTERFACTUAL_V2G,
)
from src.pricing import price_at_hour


HOURS_IN_WEEK = 168
CARS_PER_TYPOLOGY = 5     # bump up for richer fleet-level statistics
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
COUNTERFACTUALS = (COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G)


def slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def run_one_car(typology: str, counterfactual: str, agent_id: int) -> EVAgent:
    """Simulate one car for one week."""
    agent = EVAgent(agent_id=agent_id, typology=typology, counterfactual=counterfactual)
    for hour in range(HOURS_IN_WEEK):
        price = price_at_hour(hour % 24)
        agent.step(current_hour=hour, current_price_per_kwh=price)
    return agent


def write_cars_to_csv(cars: list[EVAgent], path: Path) -> None:
    """Save many cars' logs into one CSV with an agent_id column."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cars or not cars[0].hourly_log:
        return
    fieldnames = ["agent_id"] + list(cars[0].hourly_log[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for car in cars:
            for row in car.hourly_log:
                writer.writerow({"agent_id": car.id, **row})


def summarise_one_car(agent: EVAgent) -> dict:
    kwh_bought = sum(r["energy_kwh"] for r in agent.hourly_log if r["action"] == "CHARGE")
    kwh_sold = sum(-r["energy_kwh"] for r in agent.hourly_log if r["action"] == "DISCHARGE")
    net_money = sum(r["cost_currency"] for r in agent.hourly_log)
    return {
        "kwh_bought": kwh_bought,
        "kwh_sold": kwh_sold,
        "net_week": net_money,
    }


def mean_std(values: list[float]) -> tuple[float, float]:
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def main() -> None:
    print(f"=== V2G ABM — W7 Sunday demo (4 typologies × {CARS_PER_TYPOLOGY} cars × 3 CFs × 1 week) ===\n")
    print("Prices: TAOZ summer (NIS/kWh)  —  off-peak 0.53, shoulder 0.85, peak 1.69\n")

    # Run everything and collect summaries
    summaries: dict[tuple[str, str], list[dict]] = {}
    for t_idx, typology in enumerate(ALL_TYPOLOGIES):
        for cf in COUNTERFACTUALS:
            cars = []
            for car_idx in range(CARS_PER_TYPOLOGY):
                # Unique agent_id per (typology, car_idx); same id reused across
                # the 3 counterfactuals so each "individual" lives 3 parallel lives.
                agent_id = t_idx * 1000 + car_idx + 1
                car = run_one_car(typology, cf, agent_id)
                cars.append(car)
            csv_path = OUTPUTS_DIR / f"{slug(typology)}_{cf.lower()}.csv"
            write_cars_to_csv(cars, csv_path)
            summaries[(typology, cf)] = [summarise_one_car(c) for c in cars]

    # Print summary: mean ± std across the 5 cars in each cell
    header = f"{'typology':>18} | {'CF':>4} | {'kWh bought':>20} | {'kWh sold':>18} | {'net ₪/wk':>20} | {'annual ₪':>14}"
    print(header)
    print("-" * len(header))
    for typology in ALL_TYPOLOGIES:
        for cf in COUNTERFACTUALS:
            rows = summaries[(typology, cf)]
            bm, bs = mean_std([r["kwh_bought"] for r in rows])
            sm, ss = mean_std([r["kwh_sold"] for r in rows])
            nm, ns = mean_std([r["net_week"] for r in rows])
            am = nm * 52
            print(
                f"{typology:>18} | {cf:>4}"
                f" | {bm:>9.1f} ± {bs:>6.1f}"
                f" | {sm:>8.1f} ± {ss:>5.1f}"
                f" | {nm:>9.2f} ± {ns:>6.2f}"
                f" | {am:>14.0f}"
            )
        print()

    print("Notes:")
    print(f" - {CARS_PER_TYPOLOGY} cars per typology, each with its own commute jitter and daily-km noise.")
    print(" - 'net ₪/wk' < 0 means the owner earned money on net.")
    print(" - 'annual ₪' = mean weekly × 52.")
    print(" - Public Charger uses workplace charging only (no overnight V2G possible).")
    print(" - BEV 2nd Vehicle drives only Mon-Thu (4 of 7 days).")


if __name__ == "__main__":
    main()
