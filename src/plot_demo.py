"""W7 plot — 2×2 panel: four typologies, three counterfactuals each.

Reads the 12 CSV files produced by run_demo.py and draws SoC vs hour for
each (typology × counterfactual) combination. Layout is a 2×2 grid, one
panel per typology, three coloured lines per panel (V0, V1G, V2G).

Saves to outputs/w7_soc_four_typologies.png.

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


def main() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 7), sharey=True)
    axes_flat = axes.flatten()

    for ax, typology in zip(axes_flat, ALL_TYPOLOGIES):
        for cf in (COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G):
            csv_path = OUTPUTS_DIR / f"{slug(typology)}_{cf.lower()}.csv"
            if not csv_path.exists():
                continue
            hours, soc = read_soc_series(csv_path)
            ax.plot(
                hours,
                [s * 100 for s in soc],
                label=COUNTERFACTUAL_LABELS[cf],
                color=COUNTERFACTUAL_COLOURS[cf],
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


if __name__ == "__main__":
    main()
