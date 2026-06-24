"""W10.A.3 battery aging plot.

David's M6 ask: show V2G discharge as its own visible layer on cycle aging,
so the V2G aging penalty is readable directly against the V0/V1G baselines.

Calendar aging is now flat per hour (W10.A.2) so it is identical across
typologies and counterfactuals; the visible spread comes from cycle aging.

Layout: 4 typologies on the x-axis, 3 grouped bars per typology
(V0, V1G, V2G), each stacked as:

  - calendar aging          (gray)
  - baseline cycle aging    (orange)  driving + opportunistic charging
  - V2G discharge layer     (red)     V2G discharge throughput only
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import src.agents.ev_agent as ev_agent_module
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
from src.battery_aging import (
    cycle_aging_coefficient,
    EOL_SOH,
)
from src.pricing import price_at_hour
from src.run_demo import CARS_PER_TYPOLOGY, HOURS_IN_WEEK


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
COUNTERFACTUALS = (COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G)
WEEKS_IN_10Y = 520


N_PER_TYPOLOGY_FOR_AGING_PLOT = 60   # oversample so V2G opt-in rate is stable


def simulate_one_run(typology: str, counterfactual: str) -> dict:
    """Simulate one typology under one counterfactual and return mean aging."""
    cal_w, cyc_w, v2g_kwh_w, chemistry = [], [], [], None
    # Deterministic agent IDs so the run is reproducible; oversample to
    # average out SEM opt-in randomness in the V2G branch.
    base = abs(hash((typology, counterfactual))) % 100_000
    for car_idx in range(N_PER_TYPOLOGY_FOR_AGING_PLOT):
        agent_id = base * 1000 + car_idx
        a = EVAgent(agent_id=agent_id, typology=typology, counterfactual=counterfactual)
        for hour in range(HOURS_IN_WEEK):
            hour_of_day = hour % 24
            day_of_week = (hour // 24) % 7
            price = price_at_hour(hour_of_day, day_of_week)
            a.step(current_hour=hour, current_price_per_kwh=price)
        cal_w.append(a.state.cumulative_calendar_aging)
        cyc_w.append(a.state.cumulative_cycle_aging)
        v2g_kwh_w.append(a.state.cumulative_v2g_discharge_kwh)
        chemistry = a.state.chemistry
    return {
        "cal_w":     float(np.mean(cal_w)),
        "cyc_w":     float(np.mean(cyc_w)),
        "v2g_kwh_w": float(np.mean(v2g_kwh_w)),
        "chemistry": chemistry,
    }


def main() -> None:
    ev_agent_module.SEM_ENABLED = True

    # Collect mean weekly aging for each (typology, counterfactual)
    table: dict[tuple[str, str], dict] = {}
    for typology in ALL_TYPOLOGIES:
        for cf in COUNTERFACTUALS:
            table[(typology, cf)] = simulate_one_run(typology, cf)

    # 10-year extrapolation per stack component
    def stack_10y(typology: str, cf: str) -> tuple[float, float, float]:
        row = table[(typology, cf)]
        cal_10y = row["cal_w"] * WEEKS_IN_10Y * 100
        # V2G discharge aging share of cycle aging (uses chemistry coeff)
        coef = cycle_aging_coefficient(row["chemistry"])
        v2g_aging_w = row["v2g_kwh_w"] * coef
        v2g_10y = v2g_aging_w * WEEKS_IN_10Y * 100
        # Baseline cycle = total cycle minus V2G layer
        cyc_total_10y = row["cyc_w"] * WEEKS_IN_10Y * 100
        cyc_baseline_10y = max(0.0, cyc_total_10y - v2g_10y)
        return cal_10y, cyc_baseline_10y, v2g_10y

    # --- plot ---
    fig, ax = plt.subplots(figsize=(13, 7))
    typologies = list(ALL_TYPOLOGIES)
    x_base = np.arange(len(typologies))
    bar_width = 0.26
    offsets = {COUNTERFACTUAL_V0: -bar_width, COUNTERFACTUAL_V1G: 0.0, COUNTERFACTUAL_V2G: bar_width}

    CAL_COLOR  = "#9ca3af"  # gray
    CYC_COLOR  = "#f59e0b"  # amber
    V2G_COLOR  = "#dc2626"  # red

    for cf in COUNTERFACTUALS:
        xs = x_base + offsets[cf]
        cal_arr, cyc_arr, v2g_arr = [], [], []
        for t in typologies:
            c, b, v = stack_10y(t, cf)
            cal_arr.append(c); cyc_arr.append(b); v2g_arr.append(v)
        cal_arr = np.array(cal_arr); cyc_arr = np.array(cyc_arr); v2g_arr = np.array(v2g_arr)

        ax.bar(xs, cal_arr, width=bar_width, color=CAL_COLOR, edgecolor="white", linewidth=0.5,
               label="Calendar (flat)" if cf == COUNTERFACTUAL_V0 else None)
        ax.bar(xs, cyc_arr, width=bar_width, bottom=cal_arr, color=CYC_COLOR, edgecolor="white", linewidth=0.5,
               label="Cycle - driving baseline" if cf == COUNTERFACTUAL_V0 else None)
        ax.bar(xs, v2g_arr, width=bar_width, bottom=cal_arr + cyc_arr, color=V2G_COLOR, edgecolor="white", linewidth=0.5,
               label="Cycle - V2G discharge layer" if cf == COUNTERFACTUAL_V0 else None)

        # total labels
        for xi, t in zip(xs, typologies):
            c, b, v = stack_10y(t, cf)
            total = c + b + v
            ax.text(xi, total + 0.05, f"{total:.2f}%", ha="center", fontsize=8,
                    fontweight="bold", color="black")
            ax.text(xi, -0.15, cf, ha="center", fontsize=7, color="#555")

    ax.axhline(100 * (1 - EOL_SOH), color="black", linestyle="--", linewidth=1.0,
               label=f"EoL threshold ({(1 - EOL_SOH) * 100:.0f}%)")

    ax.set_xticks(x_base)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=10)
    ax.set_ylabel("Cumulative SoH loss over 10 years (%)", fontsize=11)
    ax.set_title(
        "Battery aging by typology and counterfactual  -  V2G discharge layer broken out\n"
        "Calendar aging is flat (W10.A.2); V2G penalty visible only in V2G column",
        fontsize=12, fontweight="bold",
    )
    ax.legend(loc="upper left", fontsize=9, framealpha=0.95)
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(0, max(ax.get_ylim()[1], 100 * (1 - EOL_SOH) + 5))

    fig.tight_layout()
    out = OUTPUTS_DIR / "w10_aging.png"
    fig.savefig(out, dpi=150, facecolor="white")
    print(f"Saved {out}")

    # Console summary
    print()
    hdr = f"{'Typology':>20} | {'CF':>4} | {'cal_10y':>8} | {'cyc_base_10y':>13} | {'v2g_10y':>8} | {'v2g_kwh/wk':>11}"
    print(hdr); print("-" * len(hdr))
    for t in typologies:
        for cf in COUNTERFACTUALS:
            c, b, v = stack_10y(t, cf)
            row = table[(t, cf)]
            print(f"{t:>20} | {cf:>4} | {c:>7.3f}% | {b:>12.4f}% | {v:>7.4f}% | {row['v2g_kwh_w']:>11.1f}")


if __name__ == "__main__":
    main()
