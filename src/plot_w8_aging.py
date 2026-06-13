"""W8 battery aging diagnostic plot.

Runs the V2G fleet, then extrapolates the weekly aging to a 10-year horizon
to make the (per-hour) tiny effects visible.

Three panels:
  (a) SoH trajectory per typology over the simulated week
  (b) 10-year extrapolated SoH per typology, calendar vs cycle decomposition
  (c) Effective OSP per agent (SEM-derived) and aging-cost add-on
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
    COUNTERFACTUAL_V2G,
)
from src.battery_aging import (
    aging_cost_per_kwh_discharged,
    EOL_SOH,
)
from src.pricing import price_at_hour
from src.run_demo import CARS_PER_TYPOLOGY, HOURS_IN_WEEK


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

COLORS = {
    DAILY_CHARGER:     "#1f77b4",
    PUBLIC_CHARGER:    "#ff7f0e",
    BEV_2ND_VEHICLE:   "#2ca02c",
    THRESHOLD_CHARGER: "#d62728",
}


def simulate_fleet() -> list[dict]:
    ev_agent_module.SEM_ENABLED = True
    recs = []
    for t_idx, typology in enumerate(ALL_TYPOLOGIES):
        n_cars = CARS_PER_TYPOLOGY[typology]
        for car_idx in range(n_cars):
            agent_id = t_idx * 1000 + car_idx + 1
            a = EVAgent(agent_id=agent_id, typology=typology, counterfactual=COUNTERFACTUAL_V2G)
            for hour in range(HOURS_IN_WEEK):
                hour_of_day = hour % 24
                day_of_week = (hour // 24) % 7
                price = price_at_hour(hour_of_day, day_of_week)
                a.step(current_hour=hour, current_price_per_kwh=price)
            recs.append({
                "agent_id":   a.id,
                "typology":   typology,
                "osp":        a.state.osp,
                "soh_traj":   [r["soh"] for r in a.hourly_log],
                "cal_aging_week": a.state.cumulative_calendar_aging,
                "cyc_aging_week": a.state.cumulative_cycle_aging,
                "throughput_week": a.state.cumulative_throughput_kwh,
                "v2g_capable": a.state.v2g_capable,
            })
    return recs


def panel_soh_trajectory(ax, recs):
    """SoH trajectory over the simulated week, per typology mean."""
    hours = np.arange(HOURS_IN_WEEK)
    for typology in ALL_TYPOLOGIES:
        traj_list = [r["soh_traj"] for r in recs if r["typology"] == typology]
        if not traj_list:
            continue
        mean_traj = np.mean(traj_list, axis=0)
        ax.plot(hours, mean_traj * 100, label=typology, color=COLORS[typology], linewidth=2)
    ax.set_xlabel("Hour of simulated week")
    ax.set_ylabel("Mean SoH (%)")
    ax.set_title("(a) SoH trajectory over the simulated week (per-typology mean)")
    ax.legend(fontsize=8, loc="lower left")
    ax.set_ylim(99.97, 100.005)
    ax.grid(True, alpha=0.3)


def panel_10y_decomposition(ax, recs):
    """Extrapolate weekly aging to 10 years, decompose calendar vs cycle."""
    typologies = list(ALL_TYPOLOGIES)
    x = np.arange(len(typologies))
    cal_10y = []
    cyc_10y = []
    for typology in typologies:
        sub = [r for r in recs if r["typology"] == typology]
        cal_w = np.mean([r["cal_aging_week"] for r in sub])
        cyc_w = np.mean([r["cyc_aging_week"] for r in sub])
        # 52 weeks * 10 years = 520 weeks of similar usage
        cal_10y.append(cal_w * 520 * 100)
        cyc_10y.append(cyc_w * 520 * 100)
    cal_10y = np.array(cal_10y)
    cyc_10y = np.array(cyc_10y)

    ax.bar(x, cal_10y, label="Calendar aging (10y)", color="#9ca3af")
    ax.bar(x, cyc_10y, bottom=cal_10y, label="Cycle aging (10y)", color="#dc2626")
    for i, (c, y) in enumerate(zip(cal_10y, cyc_10y)):
        total = c + y
        ax.text(i, total + 0.3, f"{total:.2f}%", ha="center", fontsize=10, fontweight="bold")
    ax.axhline(100 * (1 - EOL_SOH), color="black", linestyle="--", linewidth=1,
               label=f"EoL threshold ({(1-EOL_SOH)*100:.0f}%)")
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=9)
    ax.set_ylabel("Cumulative SoH loss over 10 years (%)")
    ax.set_title("(b) Calendar vs cycle aging  -  10-year extrapolation")
    ax.legend(fontsize=8, loc="upper right")


def panel_osp_components(ax, recs):
    """Show SEM-OSP and aging-cost add-on per agent."""
    capable = [r for r in recs if r["v2g_capable"]]
    capable.sort(key=lambda r: r["osp"])
    n = len(capable)
    x = np.arange(n)
    aging_add = aging_cost_per_kwh_discharged()
    base_osp = [r["osp"] - aging_add for r in capable]
    aging_add_arr = [aging_add for _ in capable]
    colors = [COLORS[r["typology"]] for r in capable]

    ax.bar(x, base_osp, color=colors, label="SEM-derived OSP", edgecolor="white", linewidth=0.5)
    ax.bar(x, aging_add_arr, bottom=base_osp, color="black", label=f"Aging cost (+{aging_add:.4f} NIS/kWh)", edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f"#{r['agent_id']}" for r in capable], rotation=60, fontsize=8, ha="right")
    ax.set_ylabel("OSP (NIS/kWh)")
    ax.set_title("(c) Per-agent OSP composition  -  SEM portion vs aging add-on")
    # Legend
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=COLORS[t], label=t) for t in ALL_TYPOLOGIES]
    handles.append(Patch(facecolor="black", label=f"Aging cost ({aging_add:.4f} NIS/kWh)"))
    ax.legend(handles=handles, fontsize=7, loc="upper left")


def main() -> None:
    recs = simulate_fleet()

    fig, axes = plt.subplots(1, 3, figsize=(22, 6.5))
    panel_soh_trajectory(axes[0], recs)
    panel_10y_decomposition(axes[1], recs)
    panel_osp_components(axes[2], recs)

    aging_add = aging_cost_per_kwh_discharged()
    fig.suptitle(
        f"Battery aging (Gasper 2023 calibration): cycle cost {aging_add:.4f} NIS/kWh, "
        "calendar from time + SoC + temperature",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    out = OUTPUTS_DIR / "w8_aging.png"
    fig.savefig(out, dpi=150, facecolor="white")
    print(f"Saved {out}")

    # Print summary
    print()
    print(f"{'Typology':>20} | {'cal_aging_10y':>14} | {'cyc_aging_10y':>14} | {'kWh throughput/wk':>17}")
    print("-" * 80)
    for typology in ALL_TYPOLOGIES:
        sub = [r for r in recs if r["typology"] == typology]
        cal_w = np.mean([r["cal_aging_week"] for r in sub])
        cyc_w = np.mean([r["cyc_aging_week"] for r in sub])
        thr_w = np.mean([r["throughput_week"] for r in sub])
        print(f"{typology:>20} | {cal_w*520*100:>13.2f}% | {cyc_w*520*100:>13.4f}% | {thr_w:>17.1f}")


if __name__ == "__main__":
    main()
