"""SEM mechanics plot.

Decomposes the SEM calculation for every V2G-capable agent in the fleet
so it is visually clear how the five latent attitudinal factors plug into
the Attitude score, how the Attitude (plus Trust and Subjective Norm)
plugs into the Intention score, and finally how Intention drives opt-in.

Four panels:
  (a) Per-agent stacked bar of contributions to Attitude.  Each stack is
      factor_value × path_coefficient.  The total height of each bar is
      the agent's Attitude towards V2G.
  (b) Per-agent stacked bar of contributions to Intention.  Three
      contributions: Trust * 0.388, Attitude * 0.174, SubjNorm * 0.409.
      Total height = Intention.  Dashed line at 0 = opt-in threshold.
  (c) Scatter of Attitude vs Intention per agent.  Filled markers = opted
      in, hollow markers = did not opt in.
  (d) Opt-in counts per typology (with vs without SEM, fleet-level).
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
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
from src.run_demo import CARS_PER_TYPOLOGY


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

TYPOLOGY_COLORS = {
    DAILY_CHARGER:     "#1f77b4",
    PUBLIC_CHARGER:    "#ff7f0e",
    BEV_2ND_VEHICLE:   "#2ca02c",
    THRESHOLD_CHARGER: "#d62728",
}

# Contribution colors for the stacked bars.
FACTOR_COLORS = {
    "Trust × 0.205":             "#3b82f6",   # blue
    "Usefulness × 0.391":        "#10b981",   # green
    "BatteryConcern × -0.177":   "#dc2626",   # red (negative path)
    "EaseOfUse × 0.255":         "#f59e0b",   # amber
    "SubjNorm × 0.347":          "#8b5cf6",   # violet
}
INTENTION_COLORS = {
    "Trust × 0.388":             "#3b82f6",
    "Attitude × 0.174":          "#6b7280",
    "SubjNorm × 0.409":          "#8b5cf6",
}


def build_records() -> list[dict]:
    """Make an EVAgent per fleet slot and collect SEM state.

    Note: we only construct the agent (init) — no simulation run needed
    for the SEM mechanics, since the SEM math runs entirely in __init__.
    """
    ev_agent_module.SEM_ENABLED = True
    recs = []
    for t_idx, typology in enumerate(ALL_TYPOLOGIES):
        n_cars = CARS_PER_TYPOLOGY[typology]
        for car_idx in range(n_cars):
            agent_id = t_idx * 1000 + car_idx + 1
            a = EVAgent(agent_id=agent_id, typology=typology, counterfactual=COUNTERFACTUAL_V2G)
            recs.append({
                "agent_id":  a.id,
                "label":     f"{typology[:3]}#{a.id}",
                "typology":  typology,
                "trust":     a.state.trust_in_v2g,
                "useful":    a.state.perceived_usefulness,
                "battery":   a.state.battery_concern,
                "ease":      a.state.perceived_ease_of_use,
                "subj":      a.state.subjective_norm,
                "attitude":  a.state.attitude_towards_v2g,
                "intention": a.state.intention_to_use_v2g,
                "opted_in":  a.state.v2g_opted_in,
                "v2g_capable": a.state.v2g_capable,
            })
    return recs


def panel_attitude_decomp(ax, recs):
    """Per-agent stacked bar of contributions to Attitude."""
    n = len(recs)
    x = np.arange(n)
    contribs_t   = [r["trust"]   * SEM_ATTITUDE_FROM_TRUST           for r in recs]
    contribs_u   = [r["useful"]  * SEM_ATTITUDE_FROM_USEFULNESS      for r in recs]
    contribs_b   = [r["battery"] * SEM_ATTITUDE_FROM_BATTERY_CONCERN for r in recs]
    contribs_e   = [r["ease"]    * SEM_ATTITUDE_FROM_EASE_OF_USE     for r in recs]
    contribs_s   = [r["subj"]    * SEM_ATTITUDE_FROM_SUBJECTIVE_NORM for r in recs]
    attitude     = [r["attitude"] for r in recs]

    # Stack positives and negatives separately so a positive total stacks above zero
    # and negatives below.  Pile each contribution from zero in its own direction.
    pos_bottom = np.zeros(n)
    neg_bottom = np.zeros(n)
    for label, values, color in [
        ("Trust × 0.205",              contribs_t, FACTOR_COLORS["Trust × 0.205"]),
        ("Usefulness × 0.391",         contribs_u, FACTOR_COLORS["Usefulness × 0.391"]),
        ("BatteryConcern × -0.177",    contribs_b, FACTOR_COLORS["BatteryConcern × -0.177"]),
        ("EaseOfUse × 0.255",          contribs_e, FACTOR_COLORS["EaseOfUse × 0.255"]),
        ("SubjNorm × 0.347",           contribs_s, FACTOR_COLORS["SubjNorm × 0.347"]),
    ]:
        pos_vals = [max(0, v) for v in values]
        neg_vals = [min(0, v) for v in values]
        ax.bar(x, pos_vals, bottom=pos_bottom, color=color, label=label, edgecolor="white", linewidth=0.3)
        ax.bar(x, neg_vals, bottom=neg_bottom, color=color, edgecolor="white", linewidth=0.3)
        pos_bottom = pos_bottom + np.array(pos_vals)
        neg_bottom = neg_bottom + np.array(neg_vals)

    # Final Attitude score as a black diamond marker
    ax.scatter(x, attitude, color="black", marker="D", s=40, zorder=5, label="Attitude (sum)")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([r["label"] for r in recs], rotation=60, fontsize=7, ha="right")
    ax.set_ylabel("contribution / total")
    ax.set_title("(a) Attitude decomposition: factor × path coefficient")
    ax.legend(fontsize=7, ncol=2, loc="lower right")


def panel_intention_decomp(ax, recs):
    """Per-agent stacked bar of contributions to Intention."""
    n = len(recs)
    x = np.arange(n)
    contribs_t   = [r["trust"]    * SEM_INTENTION_FROM_TRUST           for r in recs]
    contribs_a   = [r["attitude"] * SEM_INTENTION_FROM_ATTITUDE        for r in recs]
    contribs_s   = [r["subj"]     * SEM_INTENTION_FROM_SUBJECTIVE_NORM for r in recs]
    intention    = [r["intention"] for r in recs]

    pos_bottom = np.zeros(n)
    neg_bottom = np.zeros(n)
    for label, values, color in [
        ("Trust × 0.388",     contribs_t, INTENTION_COLORS["Trust × 0.388"]),
        ("Attitude × 0.174",  contribs_a, INTENTION_COLORS["Attitude × 0.174"]),
        ("SubjNorm × 0.409",  contribs_s, INTENTION_COLORS["SubjNorm × 0.409"]),
    ]:
        pos_vals = [max(0, v) for v in values]
        neg_vals = [min(0, v) for v in values]
        ax.bar(x, pos_vals, bottom=pos_bottom, color=color, label=label, edgecolor="white", linewidth=0.3)
        ax.bar(x, neg_vals, bottom=neg_bottom, color=color, edgecolor="white", linewidth=0.3)
        pos_bottom = pos_bottom + np.array(pos_vals)
        neg_bottom = neg_bottom + np.array(neg_vals)

    ax.scatter(x, intention, color="black", marker="D", s=40, zorder=5, label="Intention (sum)")
    ax.axhline(0, color="red", linewidth=1, linestyle="--", label="opt-in threshold")
    ax.set_xticks(x)
    ax.set_xticklabels([r["label"] for r in recs], rotation=60, fontsize=7, ha="right")
    ax.set_ylabel("contribution / total")
    ax.set_title("(b) Intention decomposition: factor × path coefficient")
    ax.legend(fontsize=7, loc="lower right")


def panel_attitude_vs_intention(ax, recs):
    """Scatter showing how Attitude and Intention relate per agent."""
    for typology in ALL_TYPOLOGIES:
        sub = [r for r in recs if r["typology"] == typology and r["v2g_capable"]]
        if not sub:
            continue
        xs = [r["attitude"] for r in sub]
        ys = [r["intention"] for r in sub]
        colors = [TYPOLOGY_COLORS[typology]] * len(sub)
        # Filled if opted in, hollow if not
        edge = [TYPOLOGY_COLORS[typology]] * len(sub)
        face = [TYPOLOGY_COLORS[typology] if r["opted_in"] else "white" for r in sub]
        ax.scatter(xs, ys, facecolor=face, edgecolor=edge, s=80, linewidth=1.5, label=typology)
    ax.axhline(0, color="red", linestyle="--", linewidth=1, label="opt-in threshold")
    ax.axvline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Attitude towards V2G")
    ax.set_ylabel("Intention to Use V2G")
    ax.set_title("(c) Attitude vs Intention   (filled = opted in)")
    ax.legend(fontsize=7, loc="lower right")


def panel_optin_summary(ax, recs):
    """Bar of opted-in vs not-opted-in counts per typology."""
    typologies = list(ALL_TYPOLOGIES)
    x = np.arange(len(typologies))
    opted = []
    not_opted = []
    for typology in typologies:
        sub = [r for r in recs if r["typology"] == typology and r["v2g_capable"]]
        opted.append(sum(1 for r in sub if r["opted_in"]))
        not_opted.append(sum(1 for r in sub if not r["opted_in"]))
    ax.bar(x, opted,    label="opted in",     color="#10b981")
    ax.bar(x, not_opted, bottom=opted, label="did not opt in", color="#9ca3af")
    for i, t in enumerate(typologies):
        total = opted[i] + not_opted[i]
        if total > 0:
            pct = 100 * opted[i] / total
            ax.text(i, total + 0.15, f"{opted[i]}/{total}\n({pct:.0f}%)", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=9)
    ax.set_ylabel("agents")
    ax.set_title("(d) V2G opt-in count per typology")
    ax.legend(fontsize=8)
    ax.set_ylim(0, max(o + n for o, n in zip(opted, not_opted)) + 2)


def main() -> None:
    recs = build_records()
    # Order recs by typology for readable x-axis labels in panels (a) and (b)
    recs.sort(key=lambda r: (list(ALL_TYPOLOGIES).index(r["typology"]), r["agent_id"]))

    fig, axes = plt.subplots(2, 2, figsize=(18, 11))
    panel_attitude_decomp(axes[0][0], recs)
    panel_intention_decomp(axes[0][1], recs)
    panel_attitude_vs_intention(axes[1][0], recs)
    panel_optin_summary(axes[1][1], recs)

    fig.suptitle(
        "SEM mechanics: how 5 latent factors flow into Attitude, Intention, and opt-in",
        fontsize=14, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    out = OUTPUTS_DIR / "w8_sem_mechanics.png"
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")

    # Print the per-agent table to stdout
    print()
    print(
        f"{'agent':>14} | {'Trust':>6} | {'Useful':>7} | {'Battery':>7} | "
        f"{'Ease':>5} | {'Subj':>5} | {'Attitude':>8} | {'Intention':>9} | {'opt_in':>6}"
    )
    print("-" * 100)
    for r in recs:
        print(
            f"{r['label']:>14} | "
            f"{r['trust']:>+6.2f} | {r['useful']:>+7.2f} | {r['battery']:>+7.2f} | "
            f"{r['ease']:>+5.2f} | {r['subj']:>+5.2f} | {r['attitude']:>+8.3f} | "
            f"{r['intention']:>+9.3f} | {str(r['opted_in']):>6}"
        )


if __name__ == "__main__":
    main()
