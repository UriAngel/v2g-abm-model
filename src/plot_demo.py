"""W7 plot — three counterfactuals on one chart.

Reads the three CSV files produced by run_demo.py and draws SoC vs hour
for V0, V1G, V2G overlaid. Saves to outputs/w7_soc_three_counterfactuals.png.

Usage
-----
    python -m src.plot_demo
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


def read_soc_series(csv_path: Path) -> tuple[list[int], list[float]]:
    """Return (hours, soc_values) read from one CSV."""
    hours = []
    soc = []
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            hours.append(int(row["hour"]))
            soc.append(float(row["soc"]))
    return hours, soc


def main() -> None:
    csv_files = {
        "V0 (naive)":      OUTPUTS_DIR / "v0_ev01.csv",
        "V1G (smart)":     OUTPUTS_DIR / "v1g_ev01.csv",
        "V2G (Sat work)":  OUTPUTS_DIR / "v2g_ev01.csv",
    }

    # Make sure all three CSV files exist
    for label, path in csv_files.items():
        if not path.exists():
            print(f"missing: {path}  — run `python -m src.run_demo` first")
            return

    # Build the chart
    fig, ax = plt.subplots(figsize=(11, 5))
    colours = {"V0 (naive)": "#888888",
               "V1G (smart)": "#2C5F2D",
               "V2G (Sat work)": "#028090"}
    for label, path in csv_files.items():
        hours, soc = read_soc_series(path)
        ax.plot(hours, [s * 100 for s in soc],
                label=label, color=colours[label], linewidth=1.8)

    # Day boundaries
    for d in range(1, 8):
        ax.axvline(d * 24, color="#DDDDDD", linewidth=0.5)

    # Cosmetics
    ax.set_xlabel("Hour of the simulated week")
    ax.set_ylabel("State of charge  (%)")
    ax.set_title("V0 vs V1G vs V2G  —  one Daily Charger, one simulated week  "
                 "(W7 Trinity demo)")
    ax.set_xticks([d * 24 for d in range(8)])
    ax.set_xticklabels([f"Day {d}" for d in range(1, 9)])
    ax.set_xlim(0, 168)
    ax.set_ylim(0, 110)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

    out_path = OUTPUTS_DIR / "w7_soc_three_counterfactuals.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Saved {out_path.relative_to(OUTPUTS_DIR.parent)}")


if __name__ == "__main__":
    main()
