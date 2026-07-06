"""SEM worked-example plot.

Picks four representative agents (one per typology) and draws a full
"calculation card" for each so the SEM math is completely visible.

Each card shows:
  1. The agent's identity (typology + id)
  2. The 5 latent attitudinal factor values (Trust, Usefulness, Battery
     Concern, Ease of Use, Subjective Norm)
  3. The Attitude calculation written out: a sum of factor × coefficient
  4. The Attitude result
  5. The Intention calculation written out
  6. The Intention result
  7. The opt-in decision (OPTS IN green, or DOES NOT OPT IN red)
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
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
    SEM_ATTITUDE_FROM_TRUST,
    SEM_ATTITUDE_FROM_USEFULNESS,
    SEM_ATTITUDE_FROM_BATTERY_CONCERN,
    SEM_ATTITUDE_FROM_EASE_OF_USE,
    SEM_ATTITUDE_FROM_SUBJECTIVE_NORM,
    SEM_INTENTION_FROM_TRUST,
    SEM_INTENTION_FROM_ATTITUDE,
    SEM_INTENTION_FROM_SUBJECTIVE_NORM,
)


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

# Pick one agent per typology to feature on a card.
EXAMPLE_AGENTS = [
    (DAILY_CHARGER,     1),   # agent_id = 1
    (PUBLIC_CHARGER,    1),   # agent_id = 1001
    (BEV_2ND_VEHICLE,   2),   # agent_id = 2002
    (THRESHOLD_CHARGER, 5),   # agent_id = 3005
]


def build_one_agent(typology: str, car_idx: int) -> dict:
    t_idx = list(ALL_TYPOLOGIES).index(typology)
    agent_id = t_idx * 1000 + car_idx
    ev_agent_module.SEM_ENABLED = True
    a = EVAgent(agent_id=agent_id, typology=typology, counterfactual=COUNTERFACTUAL_V2G)
    return {
        "agent_id": a.id,
        "typology": typology,
        "trust":    a.state.trust_in_v2g,
        "useful":   a.state.perceived_usefulness,
        "battery":  a.state.battery_concern,
        "ease":     a.state.perceived_ease_of_use,
        "subj":     a.state.subjective_norm,
        "attitude": a.state.attitude_towards_v2g,
        "intention": a.state.intention_to_use_v2g,
        "opted_in": a.state.v2g_opted_in,
        "v2g_capable": a.state.v2g_capable,
        "osp": a.state.osp,
    }


def draw_card(ax, rec: dict) -> None:
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis("off")

    # Title bar
    ax.add_patch(Rectangle((0, 11.0), 10, 1.0, facecolor="#1F3864", edgecolor="none"))
    ax.text(0.2, 11.5, f"{rec['typology']}  #{rec['agent_id']}",
            fontsize=14, fontweight="bold", color="white", va="center")

    # Step 1: Sampled latent factor values
    ax.text(0.2, 10.3, "Step 1.  Five latent factors sampled from N(0, 1):",
            fontsize=11, fontweight="bold")
    factors = [
        ("Trust in V2G",          rec["trust"]),
        ("Perceived Usefulness",  rec["useful"]),
        ("Battery Concern",       rec["battery"]),
        ("Perceived Ease of Use", rec["ease"]),
        ("Subjective Norm",       rec["subj"]),
    ]
    for i, (name, val) in enumerate(factors):
        y = 9.85 - i * 0.45
        color = "#10b981" if val >= 0 else "#dc2626"
        ax.text(0.4, y, name, fontsize=10)
        ax.text(5.3, y, f"{val:+.3f}", fontsize=10, fontweight="bold", color=color, family="monospace")

    # Step 2: Attitude formula
    ax.text(0.2, 7.55, "Step 2.  Compute Attitude towards V2G:",
            fontsize=11, fontweight="bold")
    contribs_a = [
        ("0.205", rec["trust"],   SEM_ATTITUDE_FROM_TRUST,           "Trust"),
        ("0.391", rec["useful"],  SEM_ATTITUDE_FROM_USEFULNESS,      "Usefulness"),
        ("-0.177", rec["battery"], SEM_ATTITUDE_FROM_BATTERY_CONCERN, "BatteryConcern"),
        ("0.255", rec["ease"],    SEM_ATTITUDE_FROM_EASE_OF_USE,     "EaseOfUse"),
        ("0.347", rec["subj"],    SEM_ATTITUDE_FROM_SUBJECTIVE_NORM, "SubjNorm"),
    ]
    y_start = 7.05
    for i, (coef_s, val, coef, name) in enumerate(contribs_a):
        y = y_start - i * 0.35
        product = coef * val
        op = "+" if i > 0 else "="
        ax.text(0.4, y, f"{op}  {coef_s}  ×  {val:+.3f}  ({name})",
                fontsize=9.5, family="monospace")
        ax.text(7.0, y, f"= {product:+.3f}", fontsize=9.5, family="monospace",
                color="#374151")

    # Attitude result box
    att_color = "#10b981" if rec["attitude"] >= 0 else "#dc2626"
    ax.add_patch(FancyBboxPatch((0.4, 4.8), 9.2, 0.5,
                                  boxstyle="round,pad=0.05",
                                  facecolor="#f3f4f6", edgecolor=att_color, linewidth=1.5))
    ax.text(5.0, 5.05, f"Attitude  =  {rec['attitude']:+.3f}",
            fontsize=12, fontweight="bold", color=att_color, ha="center", va="center")

    # Step 3: Intention formula
    ax.text(0.2, 4.25, "Step 3.  Compute Intention to Use V2G:",
            fontsize=11, fontweight="bold")
    contribs_i = [
        ("0.388", rec["trust"],    SEM_INTENTION_FROM_TRUST,           "Trust"),
        ("0.174", rec["attitude"], SEM_INTENTION_FROM_ATTITUDE,        "Attitude"),
        ("0.409", rec["subj"],     SEM_INTENTION_FROM_SUBJECTIVE_NORM, "SubjNorm"),
    ]
    y_start = 3.75
    for i, (coef_s, val, coef, name) in enumerate(contribs_i):
        y = y_start - i * 0.35
        product = coef * val
        op = "+" if i > 0 else "="
        ax.text(0.4, y, f"{op}  {coef_s}  ×  {val:+.3f}  ({name})",
                fontsize=9.5, family="monospace")
        ax.text(7.0, y, f"= {product:+.3f}", fontsize=9.5, family="monospace",
                color="#374151")

    # Intention result box
    int_color = "#10b981" if rec["intention"] >= 0 else "#dc2626"
    ax.add_patch(FancyBboxPatch((0.4, 2.2), 9.2, 0.5,
                                  boxstyle="round,pad=0.05",
                                  facecolor="#f3f4f6", edgecolor=int_color, linewidth=1.5))
    ax.text(5.0, 2.45, f"Intention  =  {rec['intention']:+.3f}",
            fontsize=12, fontweight="bold", color=int_color, ha="center", va="center")

    # Step 4: Decision
    if not rec["v2g_capable"]:
        decision = "CANNOT V2G  (no home charger)"
        col = "#6b7280"
    elif rec["opted_in"]:
        decision = f"OPTS IN  (Intention > 0)   →   OSP = {rec['osp']:.2f} NIS/kWh"
        col = "#10b981"
    else:
        decision = "DOES NOT OPT IN  (Intention ≤ 0)"
        col = "#dc2626"

    ax.text(0.2, 1.55, "Step 4.  Decision (threshold = 0):", fontsize=11, fontweight="bold")
    ax.add_patch(FancyBboxPatch((0.4, 0.5), 9.2, 0.7,
                                  boxstyle="round,pad=0.05",
                                  facecolor=col, edgecolor="none"))
    ax.text(5.0, 0.85, decision, fontsize=12, fontweight="bold",
            color="white", ha="center", va="center")


def main() -> None:
    records = [build_one_agent(t, idx) for t, idx in EXAMPLE_AGENTS]

    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    for ax, rec in zip(axes.flat, records):
        draw_card(ax, rec)

    fig.suptitle(
        "How the SEM converts five latent factors into a V2G opt-in decision",
        fontsize=16, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.97))

    out = OUTPUTS_DIR / "w8_sem_worked_examples.png"
    fig.savefig(out, dpi=150, facecolor="white")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
