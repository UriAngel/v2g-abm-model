"""Demo plots — five charts from the 20-car weekly demo.

  1. outputs/w7_a_single_car.png
       2×2 grid, one car per typology, three counterfactual lines per panel.
       Peak-hour bands shaded.  V1G is dashed so it shows through V2G.

  2. outputs/w7_b_batch_5cars.png
       2×2 grid, ALL 5 cars per typology drawn as thin lines plus the
       mean as a bold line. Shows the variation across cars.

  3. outputs/w7_c_fleet_kwh.png
       Total kWh stored across all 20 cars, one line per counterfactual.

  4. outputs/w7_d_cumulative_money.png
       Running total cash flow (₪) across the fleet over the week,
       one line per counterfactual.

  5. outputs/w7_soc_three_counterfactuals.png  (single-panel — Daily Charger only)

Usage
-----
    python -m src.plot_demo
"""

import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

from src.agents.ev_agent import (
    ALL_TYPOLOGIES,
    COUNTERFACTUAL_V0,
    COUNTERFACTUAL_V1G,
    COUNTERFACTUAL_V2G,
)
from src.aggregator_stub import (
    PEAK_DISCHARGE_START_HOUR,
    PEAK_DISCHARGE_END_HOUR,
)


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
HOURS_IN_WEEK = 168

COUNTERFACTUAL_COLOURS = {
    COUNTERFACTUAL_V0:  "#888888",
    COUNTERFACTUAL_V1G: "#2C5F2D",
    COUNTERFACTUAL_V2G: "#028090",
}
COUNTERFACTUAL_LABELS = {
    COUNTERFACTUAL_V0:  "V0 (naive)",
    COUNTERFACTUAL_V1G: "V1G (smart)",
    COUNTERFACTUAL_V2G: "V2G (active)",
}
COUNTERFACTUAL_LINESTYLES = {
    COUNTERFACTUAL_V0:  "-",
    COUNTERFACTUAL_V1G: "--",
    COUNTERFACTUAL_V2G: "-",
}

PEAK_BAND_COLOUR = "#FFE4B5"   # light peach


def slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def csv_path_for(typology: str, cf: str) -> Path:
    return OUTPUTS_DIR / f"{slug(typology)}_{cf.lower()}.csv"


def read_grouped_by_agent(csv_path: Path) -> dict[int, list[dict]]:
    """Return a dict mapping agent_id → list of hourly rows."""
    by_agent: dict[int, list[dict]] = defaultdict(list)
    if not csv_path.exists():
        return {}
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            by_agent[int(row["agent_id"])].append(row)
    return dict(by_agent)


def add_peak_bands(ax) -> None:
    """Shade the daily peak-hour window (17-23) for each of the 7 days.
    The first band gets a label so it appears in the legend."""
    for d in range(7):
        ax.axvspan(
            d * 24 + PEAK_DISCHARGE_START_HOUR,
            d * 24 + PEAK_DISCHARGE_END_HOUR,
            color=PEAK_BAND_COLOUR,
            alpha=0.45,
            zorder=0,
            label="Peak hours 17-23" if d == 0 else None,
        )


def add_day_grid(ax) -> None:
    for d in range(1, 8):
        ax.axvline(d * 24, color="#DDDDDD", linewidth=0.4, zorder=1)


# ============================================================================
#  Chart 1 — Single representative car per typology
# ============================================================================

def plot_single_rep() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 7), sharey=True)

    for ax, typology in zip(axes.flatten(), ALL_TYPOLOGIES):
        add_peak_bands(ax)
        add_day_grid(ax)
        for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V2G, COUNTERFACTUAL_V1G):
            by_agent = read_grouped_by_agent(csv_path_for(typology, cf))
            if not by_agent:
                continue
            # Pick the first agent as the representative
            first_id = sorted(by_agent.keys())[0]
            rows = by_agent[first_id]
            hours = [int(r["hour"]) for r in rows]
            soc = [float(r["soc"]) * 100 for r in rows]
            ax.plot(
                hours, soc,
                label=COUNTERFACTUAL_LABELS[cf],
                color=COUNTERFACTUAL_COLOURS[cf],
                linestyle=COUNTERFACTUAL_LINESTYLES[cf],
                linewidth=1.6,
            )

        ax.set_title(typology, fontsize=12, fontweight="bold")
        ax.set_xticks([d * 24 for d in range(8)])
        ax.set_xticklabels([f"D{d}" for d in range(1, 9)], fontsize=9)
        ax.set_xlim(0, HOURS_IN_WEEK)
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="lower right", fontsize=8)

    fig.supxlabel("Hour of simulated week  (D1 = Monday) — peach bands = TAOZ peak window 17:00-23:00")
    fig.supylabel("State of charge  (%)")
    fig.suptitle(
        "Single representative car per typology  —  V0 vs V1G vs V2G  (TAOZ summer prices)",
        fontsize=13,
    )
    out = OUTPUTS_DIR / "w7_a_single_car.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"Saved {out.relative_to(OUTPUTS_DIR.parent)}")


# ============================================================================
#  Chart 2 — Batch of 5 cars per typology (all visible + mean overlay)
# ============================================================================

def plot_batch_per_typology() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 7.5), sharey=True)

    for ax, typology in zip(axes.flatten(), ALL_TYPOLOGIES):
        add_peak_bands(ax)
        add_day_grid(ax)
        for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V2G, COUNTERFACTUAL_V1G):
            by_agent = read_grouped_by_agent(csv_path_for(typology, cf))
            if not by_agent:
                continue

            agent_ids = sorted(by_agent.keys())

            # Thin individual lines for each car (so you can see spread)
            socs_per_hour: dict[int, list[float]] = defaultdict(list)
            for aid in agent_ids:
                rows = by_agent[aid]
                hours = [int(r["hour"]) for r in rows]
                soc = [float(r["soc"]) * 100 for r in rows]
                ax.plot(
                    hours, soc,
                    color=COUNTERFACTUAL_COLOURS[cf],
                    linestyle=COUNTERFACTUAL_LINESTYLES[cf],
                    linewidth=0.7,
                    alpha=0.35,
                )
                for h, s in zip(hours, soc):
                    socs_per_hour[h].append(s)

            # Bold mean line on top
            hours_sorted = sorted(socs_per_hour.keys())
            means = [statistics.mean(socs_per_hour[h]) for h in hours_sorted]
            ax.plot(
                hours_sorted, means,
                label=COUNTERFACTUAL_LABELS[cf],
                color=COUNTERFACTUAL_COLOURS[cf],
                linestyle=COUNTERFACTUAL_LINESTYLES[cf],
                linewidth=2.0,
            )

        ax.set_title(typology, fontsize=12, fontweight="bold")
        ax.set_xticks([d * 24 for d in range(8)])
        ax.set_xticklabels([f"D{d}" for d in range(1, 9)], fontsize=9)
        ax.set_xlim(0, HOURS_IN_WEEK)
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="lower right", fontsize=8)

    fig.supxlabel("Hour of simulated week — peach bands = peak window — thin lines = individual cars, bold = mean")
    fig.supylabel("State of charge  (%)")
    fig.suptitle(
        f"Batch of 5 cars per typology  —  individual cars (thin) + mean (bold) per counterfactual",
        fontsize=13,
    )
    out = OUTPUTS_DIR / "w7_b_batch_5cars.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"Saved {out.relative_to(OUTPUTS_DIR.parent)}")


# ============================================================================
#  Chart 3 — Fleet total kWh stored (all 20 cars summed)
# ============================================================================

def plot_fleet_kwh() -> None:
    BATTERY_KWH_PER_CAR = 60.0
    fig, ax = plt.subplots(figsize=(12, 5.5))

    add_peak_bands(ax)
    add_day_grid(ax)

    n_cars_total = 0
    for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V2G, COUNTERFACTUAL_V1G):
        fleet_soc_per_hour: dict[int, float] = defaultdict(float)
        n_cars = 0
        for typology in ALL_TYPOLOGIES:
            by_agent = read_grouped_by_agent(csv_path_for(typology, cf))
            for aid, rows in by_agent.items():
                n_cars += 1
                for r in rows:
                    fleet_soc_per_hour[int(r["hour"])] += float(r["soc"])

        if not fleet_soc_per_hour:
            continue
        n_cars_total = n_cars

        hours_sorted = sorted(fleet_soc_per_hour.keys())
        fleet_kwh = [fleet_soc_per_hour[h] * BATTERY_KWH_PER_CAR for h in hours_sorted]

        ax.plot(
            hours_sorted, fleet_kwh,
            label=COUNTERFACTUAL_LABELS[cf],
            color=COUNTERFACTUAL_COLOURS[cf],
            linestyle=COUNTERFACTUAL_LINESTYLES[cf],
            linewidth=2.0,
        )

    fleet_max = n_cars_total * BATTERY_KWH_PER_CAR
    ax.axhline(fleet_max, color="#BBBBBB", linewidth=0.6, linestyle=":",
               label=f"Fleet maximum ({fleet_max:.0f} kWh, {n_cars_total} cars)")

    ax.set_xlabel("Hour of simulated week  (D1 = Monday)")
    ax.set_ylabel("Total fleet energy stored  (kWh)")
    ax.set_title(
        f"Fleet-level energy stored across {n_cars_total} cars  —  V2G empties ~half the fleet every evening peak"
    )
    ax.set_xticks([d * 24 for d in range(8)])
    ax.set_xticklabels([f"D{d}" for d in range(1, 9)])
    ax.set_xlim(0, HOURS_IN_WEEK)
    ax.set_ylim(0, fleet_max * 1.1)
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(True, alpha=0.3)

    out = OUTPUTS_DIR / "w7_c_fleet_kwh.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"Saved {out.relative_to(OUTPUTS_DIR.parent)}")


# ============================================================================
#  Chart 4 — Cumulative cash flow over time (fleet-wide)
# ============================================================================

def plot_cumulative_money() -> None:
    fig, ax = plt.subplots(figsize=(12, 5.5))

    add_peak_bands(ax)
    add_day_grid(ax)

    for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V2G, COUNTERFACTUAL_V1G):
        fleet_cost_per_hour: dict[int, float] = defaultdict(float)
        for typology in ALL_TYPOLOGIES:
            by_agent = read_grouped_by_agent(csv_path_for(typology, cf))
            for rows in by_agent.values():
                for r in rows:
                    fleet_cost_per_hour[int(r["hour"])] += float(r["cost_currency"])

        if not fleet_cost_per_hour:
            continue

        hours_sorted = sorted(fleet_cost_per_hour.keys())
        # Cumulative running total (so the line shows TOTAL money paid so far)
        running = 0.0
        cumulative = []
        for h in hours_sorted:
            running += fleet_cost_per_hour[h]
            cumulative.append(running)

        ax.plot(
            hours_sorted, cumulative,
            label=COUNTERFACTUAL_LABELS[cf],
            color=COUNTERFACTUAL_COLOURS[cf],
            linestyle=COUNTERFACTUAL_LINESTYLES[cf],
            linewidth=2.2,
        )

    ax.axhline(0, color="#444444", linewidth=0.6, linestyle="-", alpha=0.5)

    ax.set_xlabel("Hour of simulated week  (D1 = Monday)")
    ax.set_ylabel("Cumulative fleet cost  (₪, NIS)    ↓ negative = owner earned")
    ax.set_title(
        "Cumulative cash flow — fleet of 20 cars  "
        "(positive = owner spent, negative = owner earned)"
    )
    ax.set_xticks([d * 24 for d in range(8)])
    ax.set_xticklabels([f"D{d}" for d in range(1, 9)])
    ax.set_xlim(0, HOURS_IN_WEEK)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)

    out = OUTPUTS_DIR / "w7_d_cumulative_money.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"Saved {out.relative_to(OUTPUTS_DIR.parent)}")


# ============================================================================
#  Single-panel chart (Daily Charger only)
# ============================================================================

def plot_legacy_single() -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    add_peak_bands(ax)
    add_day_grid(ax)
    for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V2G, COUNTERFACTUAL_V1G):
        by_agent = read_grouped_by_agent(csv_path_for("Daily Charger", cf))
        if not by_agent:
            continue
        rows = by_agent[sorted(by_agent.keys())[0]]
        hours = [int(r["hour"]) for r in rows]
        soc = [float(r["soc"]) * 100 for r in rows]
        ax.plot(
            hours, soc,
            label=COUNTERFACTUAL_LABELS[cf],
            color=COUNTERFACTUAL_COLOURS[cf],
            linestyle=COUNTERFACTUAL_LINESTYLES[cf],
            linewidth=1.8,
        )
    ax.set_title("V0 vs V1G vs V2G — Daily Charger only (single-panel view)")
    ax.set_xlabel("Hour of simulated week")
    ax.set_ylabel("State of charge (%)")
    ax.set_xticks([d * 24 for d in range(8)])
    ax.set_xticklabels([f"Day {d}" for d in range(1, 9)])
    ax.set_xlim(0, HOURS_IN_WEEK)
    ax.set_ylim(0, 110)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    out = OUTPUTS_DIR / "w7_soc_three_counterfactuals.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"Saved {out.relative_to(OUTPUTS_DIR.parent)}")


def main() -> None:
    plot_single_rep()
    plot_batch_per_typology()
    plot_fleet_kwh()
    plot_cumulative_money()
    plot_legacy_single()


if __name__ == "__main__":
    main()
