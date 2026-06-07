"""W7 plot — three charts.

  1. outputs/w7_soc_four_typologies.png
       2×2 grid, one panel per typology, three counterfactual lines per
       panel (V0 grey, V1G green dashed, V2G teal solid).

  2. outputs/w7_fleet_kwh_stored.png
       Single panel.  Sum of stored energy across all 4 typologies at each
       hour, one line per counterfactual.  Shows how V2G repeatedly empties
       the fleet during evening peaks.

  3. outputs/w7_soc_three_counterfactuals.png  (legacy — Daily Charger only)

Usage
-----
    python -m src.plot_demo
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt

from src.agents.ev_agent import (
    ALL_TYPOLOGIES,
    COUNTERFACTUAL_V0,
    COUNTERFACTUAL_V1G,
    COUNTERFACTUAL_V2G,
)


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

COUNTERFACTUAL_COLOURS = {
    COUNTERFACTUAL_V0:  "#888888",   # grey
    COUNTERFACTUAL_V1G: "#2C5F2D",   # forest green
    COUNTERFACTUAL_V2G: "#028090",   # teal
}

COUNTERFACTUAL_LABELS = {
    COUNTERFACTUAL_V0:  "V0 (naive)",
    COUNTERFACTUAL_V1G: "V1G (smart)",
    COUNTERFACTUAL_V2G: "V2G (active)",
}

# Line styles — V1G is dashed so it shows through when it overlaps V2G
# (which happens for typologies that can't actually V2G, like Public Charger).
COUNTERFACTUAL_LINESTYLES = {
    COUNTERFACTUAL_V0:  "-",
    COUNTERFACTUAL_V1G: "--",
    COUNTERFACTUAL_V2G: "-",
}


def slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def read_soc_series(csv_path: Path) -> tuple[list[int], list[float]]:
    """Return (hours, soc_values) read from one CSV."""
    hours = []
    soc = []
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            hours.append(int(row["hour"]))
            soc.append(float(row["soc"]))
    return hours, soc


def read_full_log(csv_path: Path) -> list[dict]:
    """Read every row of a CSV as a list of dicts."""
    with csv_path.open() as f:
        return list(csv.DictReader(f))


def plot_fleet_kwh_stored() -> None:
    """Chart 2 — total energy stored across the fleet (4 typologies summed).

    One line per counterfactual.  Each line is the sum of (SoC × battery_kWh)
    across all 4 typologies at each hour.  We approximate battery_kWh as a
    constant 60 kWh per car because the W7 model gives every typology the
    same battery size.
    """
    BATTERY_KWH_PER_CAR = 60.0
    fig, ax = plt.subplots(figsize=(11, 5))

    for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V2G, COUNTERFACTUAL_V1G):
        per_typology_socs = []
        for typology in ALL_TYPOLOGIES:
            csv_path = OUTPUTS_DIR / f"{slug(typology)}_{cf.lower()}.csv"
            if not csv_path.exists():
                continue
            rows = read_full_log(csv_path)
            per_typology_socs.append([float(r["soc"]) for r in rows])

        if not per_typology_socs:
            continue

        # Sum SoC across the 4 typologies hour-by-hour, then × battery size
        n_hours = len(per_typology_socs[0])
        fleet_kwh = []
        for h in range(n_hours):
            sum_soc = sum(s[h] for s in per_typology_socs)
            fleet_kwh.append(sum_soc * BATTERY_KWH_PER_CAR)

        ax.plot(
            range(n_hours),
            fleet_kwh,
            label=COUNTERFACTUAL_LABELS[cf],
            color=COUNTERFACTUAL_COLOURS[cf],
            linestyle=COUNTERFACTUAL_LINESTYLES[cf],
            linewidth=1.8,
        )

    # Day boundaries
    for d in range(1, 8):
        ax.axvline(d * 24, color="#DDDDDD", linewidth=0.5)

    # Reference line: maximum possible (4 cars × 60 kWh × 100% SoC)
    fleet_max = 4 * BATTERY_KWH_PER_CAR
    ax.axhline(fleet_max, color="#BBBBBB", linewidth=0.6, linestyle=":",
               label=f"Fleet maximum ({fleet_max:.0f} kWh)")

    ax.set_xlabel("Hour of simulated week  (D1 = Monday)")
    ax.set_ylabel("Total fleet energy stored  (kWh)")
    ax.set_title(
        "Fleet-level energy stored across all 4 typologies  —  V2G empties "
        "the fleet every evening peak"
    )
    ax.set_xticks([d * 24 for d in range(8)])
    ax.set_xticklabels([f"D{d}" for d in range(1, 9)])
    ax.set_xlim(0, 168)
    ax.set_ylim(0, fleet_max * 1.1)
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(True, alpha=0.3)

    out_path = OUTPUTS_DIR / "w7_fleet_kwh_stored.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Saved {out_path.relative_to(OUTPUTS_DIR.parent)}")


def main() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 7), sharey=True)
    axes_flat = axes.flatten()

    for ax, typology in zip(axes_flat, ALL_TYPOLOGIES):
        # Plot order: V0 first, then V2G, then V1G last so the dashed
        # green V1G line is visible on top wherever it coincides with V2G.
        for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V2G, COUNTERFACTUAL_V1G):
            csv_path = OUTPUTS_DIR / f"{slug(typology)}_{cf.lower()}.csv"
            if not csv_path.exists():
                continue
            hours, soc = read_soc_series(csv_path)
            ax.plot(
                hours,
                [s * 100 for s in soc],
                label=COUNTERFACTUAL_LABELS[cf],
                color=COUNTERFACTUAL_COLOURS[cf],
                linestyle=COUNTERFACTUAL_LINESTYLES[cf],
                linewidth=1.6,
            )

        # Day boundaries
        for d in range(1, 8):
            ax.axvline(d * 24, color="#DDDDDD", linewidth=0.4)

        ax.set_title(typology, fontsize=12, fontweight="bold")
        ax.set_xticks([d * 24 for d in range(8)])
        ax.set_xticklabels([f"D{d}" for d in range(1, 9)], fontsize=9)
        ax.set_xlim(0, 168)
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="lower right", fontsize=9)

    # Shared axis labels
    fig.supxlabel("Hour of simulated week  (D1 = Monday)")
    fig.supylabel("State of charge  (%)")
    fig.suptitle(
        "V0 vs V1G vs V2G  —  four driver typologies, one simulated week  "
        "(TAOZ summer prices)",
        fontsize=13,
    )

    out_path = OUTPUTS_DIR / "w7_soc_four_typologies.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Saved {out_path.relative_to(OUTPUTS_DIR.parent)}")

    # Also keep a single-EV chart for backwards compatibility
    fig_single, ax = plt.subplots(figsize=(11, 5))
    for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G):
        csv_path = OUTPUTS_DIR / f"{slug('Daily Charger')}_{cf.lower()}.csv"
        if not csv_path.exists():
            continue
        hours, soc = read_soc_series(csv_path)
        ax.plot(
            hours,
            [s * 100 for s in soc],
            label=COUNTERFACTUAL_LABELS[cf],
            color=COUNTERFACTUAL_COLOURS[cf],
            linewidth=1.8,
        )
    for d in range(1, 8):
        ax.axvline(d * 24, color="#DDDDDD", linewidth=0.5)
    ax.set_title("V0 vs V1G vs V2G — Daily Charger only (legacy single-panel view)")
    ax.set_xlabel("Hour of simulated week")
    ax.set_ylabel("State of charge (%)")
    ax.set_xticks([d * 24 for d in range(8)])
    ax.set_xticklabels([f"Day {d}" for d in range(1, 9)])
    ax.set_xlim(0, 168)
    ax.set_ylim(0, 110)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    out_path = OUTPUTS_DIR / "w7_soc_three_counterfactuals.png"
    fig_single.tight_layout()
    fig_single.savefig(out_path, dpi=150)
    print(f"Saved {out_path.relative_to(OUTPUTS_DIR.parent)}")

    # Chart 3 — fleet kWh stored
    plot_fleet_kwh_stored()


if __name__ == "__main__":
    main()
