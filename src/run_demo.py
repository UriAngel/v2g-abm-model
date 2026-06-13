"""W8 demo runner — Batch A version.

W8 Batch A changes from W7 Sunday version:
  * Fleet composition now uses Hoke 2026 California shares instead of
    uniform 5 per typology: Daily Charger 5, Public Charger 4,
    BEV 2nd Vehicle 3, Threshold Charger 8 (total 20 cars, ratios
    26 / 19 / 17 / 38 percent rounded for n=20).
  * Pricing is now weekday-aware: peak rate applies only Sun-Thu.
  * BEV 2nd Vehicle drives Tue-Wed-Thu only (David W8 meeting).
  * Threshold Charger has real threshold plug-in behaviour.

For each (typology, counterfactual) combination we write one CSV file
containing all that typology's cars' hourly logs.  12 files total.
"""

import csv
import statistics
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
from src.aggregator_stub import (
    AGGREGATOR_CONTRACTED_RETAILER,
    RETAILER_GATE_ENABLED,
)
from src.pricing import price_at_hour


HOURS_IN_WEEK = 168

# California typology shares from Hoke 2026 Appendix B, rounded to fit a
# 20-car fleet for the W8 demo.  Underlying percentages: Daily 26, Public 19,
# BEV 2nd 17, Threshold 38.
CARS_PER_TYPOLOGY = {
    DAILY_CHARGER:    5,   # 25 % of fleet
    PUBLIC_CHARGER:   4,   # 20 %
    BEV_2ND_VEHICLE:  3,   # 15 %
    THRESHOLD_CHARGER: 8,  # 40 %
}
FLEET_SIZE = sum(CARS_PER_TYPOLOGY.values())  # 20

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
COUNTERFACTUALS = (COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G)


def slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def run_one_car(typology: str, counterfactual: str, agent_id: int) -> EVAgent:
    """Simulate one car for one week."""
    agent = EVAgent(agent_id=agent_id, typology=typology, counterfactual=counterfactual)
    for hour in range(HOURS_IN_WEEK):
        hour_of_day = hour % 24
        day_of_week = (hour // 24) % 7
        price = price_at_hour(hour_of_day, day_of_week)
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
    composition = ", ".join(f"{n} {t}" for t, n in CARS_PER_TYPOLOGY.items())
    print(f"=== V2G ABM — W8 Batch B demo ({FLEET_SIZE}-car fleet x 3 CFs x 1 week) ===")
    print(f"Fleet composition (Hoke 2026 California shares): {composition}")
    print("Prices: TAOZ summer (NIS/kWh)  off-peak 0.53, shoulder 0.85, peak 1.69")
    if RETAILER_GATE_ENABLED:
        print(f"Aggregator-retailer gate: ENABLED.  Only {AGGREGATOR_CONTRACTED_RETAILER} customers can V2G.")
    else:
        print("Aggregator-retailer gate: DISABLED.  All households can V2G regardless of retailer.")
    print()

    # Run everything and collect summaries
    summaries: dict[tuple[str, str], list[dict]] = {}
    for t_idx, typology in enumerate(ALL_TYPOLOGIES):
        n_cars = CARS_PER_TYPOLOGY[typology]
        for cf in COUNTERFACTUALS:
            cars = []
            for car_idx in range(n_cars):
                # Unique agent_id per (typology, car_idx); same id reused across
                # the 3 counterfactuals so each "individual" lives 3 parallel lives.
                agent_id = t_idx * 1000 + car_idx + 1
                car = run_one_car(typology, cf, agent_id)
                cars.append(car)
            csv_path = OUTPUTS_DIR / f"{slug(typology)}_{cf.lower()}.csv"
            write_cars_to_csv(cars, csv_path)
            summaries[(typology, cf)] = [summarise_one_car(c) for c in cars]

    # Print summary: mean ± std across the cars in each cell
    header = f"{'typology':>18} | {'CF':>4} | {'kWh bought':>20} | {'kWh sold':>18} | {'net NIS/wk':>20} | {'annual NIS':>14}"
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
                f" | {bm:>9.1f} +/- {bs:>5.1f}"
                f" | {sm:>8.1f} +/- {ss:>4.1f}"
                f" | {nm:>9.2f} +/- {ns:>5.2f}"
                f" | {am:>14.0f}"
            )
        print()

    print("Notes:")
    print(" - Negative net cost means the owner earned money on net.")
    print(" - 'annual' uses mean weekly cost x 52, ignoring seasonal variation.")
    print(" - Public Charger uses workplace charging only (no overnight V2G).")
    print(" - All typologies drive probabilistically per Hoke 2026 Table 1 drive-days/wk.")
    print(" - BEV 2nd Vehicle: 4.74 drive days/wk (Hoke).")
    print(" - Threshold Charger: plugs in below 46.1% SoC, charges to 85% (both Hoke).")
    print(" - Friday and Saturday treated as Israeli weekend for driving only.")
    print(" - TAOZ peak rate 17-23 applies every day in the standard residential schedule.")


if __name__ == "__main__":
    main()
