"""Methodology diagrams: hourly simulation flow + EVAgent state machine.

Two figures for Chapter 3 (supervisor request, Meeting 8):
  w13c_model_flow.png     - one simulated hour, agent update order
  w13c_state_machine.png  - EVAgent operational states and transitions

Content mirrors run_w9_fleet.run_year and agents/ev_agent.py exactly:
update order (aggregator -> EV agents -> feeder), the V2G six-condition
gate, 7.0 kW charge / 9.6 kW discharge, 50 % floor, 90 % max_soc cap.

Run:  python -m src.plot_w13c_model_diagrams
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from src.plot_style import apply_style, PALETTE

apply_style()

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

INK = "#14201d"


def box(ax, x, y, w, h, text, fc="#ffffff", ec=PALETTE["neutral"],
        fs=9.5, bold=False, tc=None):
    ax.add_patch(FancyBboxPatch((x - w/2, y - h/2), w, h,
                 boxstyle="round,pad=0.012", linewidth=1.1,
                 facecolor=fc, edgecolor=ec))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color=tc or INK)


def arrow(ax, x1, y1, x2, y2, text=None, color=None, style="-|>",
          conn="arc3,rad=0.0", fs=8, tx=None, ty=None):
    color = color or PALETTE["neutral"]
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                 mutation_scale=14, linewidth=1.2, color=color,
                 connectionstyle=conn))
    if text:
        ax.text(tx if tx is not None else (x1+x2)/2,
                ty if ty is not None else (y1+y2)/2,
                text, fontsize=fs, ha="center", va="center", color=color,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none",
                          alpha=0.9))


def flow() -> None:
    fig, ax = plt.subplots(figsize=(8.6, 10.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 14); ax.axis("off")

    teal, blue, amber, red = (PALETTE["israel"], PALETTE["uk"],
                              PALETTE["amber"], PALETTE["cost"])

    box(ax, 5, 13.3, 4.6, 0.75, "Hour h  (1 … 8,760)", fc="#e6f2f0",
        ec=teal, bold=True, fs=11)
    box(ax, 5, 12.1, 7.6, 0.95,
        "AggregatorAgent\ndischarge signal for h ← pricing module (inside tariff peak window?)",
        ec=blue)
    box(ax, 5, 10.6, 7.6, 1.15,
        "EVAgent mobility update  (each agent, fixed order)\n"
        "depart / drive / return per typology schedule;\n"
        "trip energy subtracted from state of charge", ec=teal)
    box(ax, 5, 8.9, 7.6, 1.3,
        "Charging / discharging decision (counterfactual rule)\n"
        "V0: charge at 7.0 kW when plugged and SoC < target\n"
        "V1G: charge only off-peak, departure-aware target (≤ 90 % cap)\n"
        "V2G: V1G charging + six-condition discharge gate (Fig. 3.2)", ec=teal)
    box(ax, 5, 7.0, 7.6, 1.0,
        "GridAgent feeder check\ncan_charge / can_discharge against transformer kVA\n"
        "(household baseline load included)", ec=amber)
    box(ax, 5, 5.5, 7.6, 0.85,
        "Commit action: energy, revenue / cost recorded;\nfeeder net load updated", ec=teal)
    box(ax, 5, 4.2, 7.6, 0.85,
        "Battery health update\ncalendar + cycle aging applied to state of health", ec=teal)
    box(ax, 5, 2.9, 7.6, 0.75,
        "Agent log write and end-of-hour reconciliation", ec=teal)
    box(ax, 5, 1.6, 4.6, 0.75, "next hour  h ← h + 1", fc="#e6f2f0",
        ec=teal, bold=True)

    ys = [(13.3, 12.1, 0.75, 0.95), (12.1, 10.6, 0.95, 1.15),
          (10.6, 8.9, 1.15, 1.3), (8.9, 7.0, 1.3, 1.0),
          (7.0, 5.5, 1.0, 0.85), (5.5, 4.2, 0.85, 0.85),
          (4.2, 2.9, 0.85, 0.75), (2.9, 1.6, 0.75, 0.75)]
    for y1, y2, h1, h2 in ys:
        arrow(ax, 5, y1 - h1/2, 5, y2 + h2/2)

    # denial branch
    arrow(ax, 8.8, 7.0, 8.8, 5.93, color=red, conn="arc3,rad=0.0")
    ax.text(9.0, 6.5, "denied →\naction skipped,\nstate unchanged", fontsize=8,
            color=red, ha="left", va="center")
    arrow(ax, 5+3.8, 7.0, 8.8, 7.0, color=red)
    arrow(ax, 8.8, 5.93, 5+3.8, 5.5, color=red)

    # loop back
    arrow(ax, 5-2.3, 1.6, 0.9, 1.6, color=teal)
    arrow(ax, 0.9, 1.6, 0.9, 13.3, color=teal, conn="arc3,rad=0.0")
    arrow(ax, 0.9, 13.3, 5-2.3, 13.3, color=teal)

    ax.set_title("One simulated hour: agent update order",
                 fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "w13c_model_flow.png")
    print("Saved", OUT_DIR / "w13c_model_flow.png")


def state_machine() -> None:
    fig, ax = plt.subplots(figsize=(10.5, 7.4))
    ax.set_xlim(0, 14); ax.set_ylim(0, 10); ax.axis("off")

    teal, blue, amber, red = (PALETTE["israel"], PALETTE["uk"],
                              PALETTE["amber"], PALETTE["cost"])

    # states
    box(ax, 2.4, 8.3, 3.4, 1.05, "DRIVING\n(away, SoC falling)", ec=red, bold=True)
    box(ax, 8.0, 8.3, 4.4, 1.05, "PARKED - NOT PLUGGED\n(home or away)", ec=PALETTE["neutral"], bold=True)
    box(ax, 8.0, 5.0, 4.4, 1.05, "PLUGGED - IDLE\n(home charger connected)", ec=teal, bold=True)
    box(ax, 2.6, 2.0, 3.8, 1.05, "CHARGING\n7.0 kW, up to target ≤ 90 %", ec=blue, bold=True)
    box(ax, 11.6, 2.0, 4.2, 1.05, "DISCHARGING (V2G)\n9.6 kW, down to 50 % floor", ec=amber, bold=True)

    arrow(ax, 4.1, 8.3, 5.8, 8.3, "return home,\nno plug-in (13 %)", conn="arc3,rad=0.25",
          tx=4.95, ty=9.2)
    arrow(ax, 5.8, 8.05, 4.1, 8.05, "departure hour", tx=4.95, ty=7.7)
    arrow(ax, 3.3, 8.3-0.52, 6.6, 5.0+0.55, "return home, plug in\n(87 % of evenings)",
          conn="arc3,rad=-0.15", tx=3.7, ty=6.4)
    arrow(ax, 8.0, 8.3-0.52, 8.0, 5.0+0.55, "plug in later", tx=8.75, ty=6.65)
    arrow(ax, 8.0-2.2, 5.0, 2.6, 2.0+0.55, "charging rule fires\n(V0: SoC<target;\nV1G/V2G: off-peak)",
          conn="arc3,rad=-0.1", tx=3.4, ty=4.1)
    arrow(ax, 3.6, 2.0+0.55, 8.0-1.2, 5.0-0.55, "target reached\n(≤ 90 % cap)",
          conn="arc3,rad=-0.15", tx=6.3, ty=2.9)
    arrow(ax, 8.0+2.2, 5.0, 11.6, 2.0+0.55, "six-condition gate TRUE\n(signal · opt-in · capable ·\nSoC>50 % · price≥OSP · retailer)",
          conn="arc3,rad=-0.1", tx=12.15, ty=4.35)
    arrow(ax, 10.8, 2.0+0.55, 8.0+1.2, 5.0-0.55, "signal ends, SoC≤50 %,\nor feeder denial",
          conn="arc3,rad=-0.15", tx=9.0, ty=2.75)
    arrow(ax, 6.6, 5.0+0.35, 2.4+1.2, 8.3-0.35, "departure hour (unplug)",
          conn="arc3,rad=0.35", tx=3.35, ty=5.4)

    ax.set_title("EVAgent operational state machine (V2G counterfactual)",
                 fontsize=13, fontweight="bold", pad=10)
    fig.text(0.5, 0.02,
             "States and transitions as implemented in agents/ev_agent.py.  V0 and V1G use the same machine "
             "without the DISCHARGING state;\nV1G additionally applies the off-peak charging window and the "
             "departure-aware overnight target.",
             ha="center", fontsize=8.5, color=PALETTE["neutral"])
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUT_DIR / "w13c_state_machine.png")
    print("Saved", OUT_DIR / "w13c_state_machine.png")


if __name__ == "__main__":
    flow()
    state_machine()
