"""Wong-anchored aging plot, beta-based.

All V2G deltas come from Wong 2026 Appendix E regression slopes
(published values, verified against the paper text), evaluated at
Wong's own Figure-5 per-typology V2G volumes.

The calendar / cycle decomposition of the V2G bar also uses Wong's
published component regressions (cycle beta and calendar beta), so
the stacked split reflects the published components.

Layout: 4 typologies x 2 chemistries x 3 counterfactuals (V0/V1G/V2G),
stacked calendar (light) + cycle (dark), EoL dashed line at 20 pp.

Run:  python -m src.plot_w10h_aging_wong
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from src.aging_table_lit import (
    WONG_V0_10Y_LOSS_PCT,
    WONG_V2G_EFFECT,
    WONG_V2G_KWH_PER_YEAR,
    EOL_SOH_PCT,
)
from src.plot_style import apply_style, PALETTE

apply_style()

# Wong 2026 Section 2.3 / Figure 4: chemistry-specific calendar share
CAL_SHARE_BY_CHEM = {
    "NMC_B1": 0.794,   # Wong Sec 2.3: 79.4 % (95 % CI 78.5-80.3)
    "LFP":    0.392,
}

# Wong 2026 Appendix E component regressions (per typology, NMC|Gr B1;
# exact betas quoted in Section 2.4).  LFP components are published as
# bounds only ("all cycle beta < -5.93e-4, all calendar beta > +0.23e-4");
# the bounds are used.  Units: pp change per (kWh/yr) per year of the
# 10-year horizon — i.e. delta_pp = beta * kwh_per_year * 10.
WONG_BETA_CYC = {
    "Daily Charger":     {"NMC_B1": -1.92e-4,  "LFP": -5.93e-4},
    "BEV 2nd Vehicle":   {"NMC_B1": -1.84e-4,  "LFP": -5.93e-4},
    "Public Charger":    {"NMC_B1": -1.84e-4,  "LFP": -5.93e-4},   # proxy: BEV
    "Threshold Charger": {"NMC_B1": -1.434e-4, "LFP": -5.93e-4},
}
WONG_BETA_CAL = {
    "Daily Charger":     {"NMC_B1": +1.93e-4, "LFP": +0.23e-4},
    "BEV 2nd Vehicle":   {"NMC_B1": +0.97e-4, "LFP": +0.23e-4},
    "Public Charger":    {"NMC_B1": +0.97e-4, "LFP": +0.23e-4},    # proxy: BEV
    "Threshold Charger": {"NMC_B1": +3.83e-4, "LFP": +0.23e-4},
}

# V1G aging delta anchored to Etxandi-Santolaya et al. 2024 (DOI
# 10.52152/4066): "V1G smart charging ... reduces calendar ageing by up
# to 4 % over a decade" (UPPER BOUND).  NMC uses the full -4 pp
# (calendar-dominated); LFP scaled by calendar-share ratio to -2 pp.
V1G_DELTA_PCT_BY_CHEM = {"NMC_B1": -4.0, "LFP": -2.0}

CHEMS = ("NMC_B1", "LFP")
CFS   = ("V0", "V1G", "V2G")
TYPOLOGIES = list(WONG_V2G_KWH_PER_YEAR.keys())

OUT = (Path(__file__).resolve().parent.parent
       / "outputs" / "w10h_aging_wong.png")
OUT_ACTIVE = (Path(__file__).resolve().parent.parent
       / "outputs" / "w10h_aging_wong_active.png")


def split_losses(typology: str, chemistry: str, cf: str) -> tuple[float, float]:
    """(calendar_loss_pp, cycle_loss_pp) over 10 years for one bar."""
    v0_base = WONG_V0_10Y_LOSS_PCT[chemistry]
    cal_share = CAL_SHARE_BY_CHEM[chemistry]
    cal0 = v0_base * cal_share
    cyc0 = v0_base * (1 - cal_share)

    if cf == "V0":
        return cal0, cyc0

    if cf == "V1G":
        v1g_delta = V1G_DELTA_PCT_BY_CHEM[chemistry]
        # protective effect acts on the calendar component
        cal = max(0.0, cal0 + v1g_delta)
        return cal, cyc0

    # V2G: Wong component betas at Wong's own Figure-5 volume
    kwh = WONG_V2G_KWH_PER_YEAR[typology]["mean"]
    d_cyc = WONG_BETA_CYC[typology][chemistry] * kwh * 10.0   # negative = added loss
    d_cal = WONG_BETA_CAL[typology][chemistry] * kwh * 10.0   # positive = reduced loss
    cyc = max(0.0, cyc0 - d_cyc)   # d_cyc < 0 -> adds cycle loss
    cal = max(0.0, cal0 - d_cal)   # d_cal > 0 -> reduces calendar loss
    return cal, cyc


COLORS = {
    "NMC_B1": {"cal": PALETTE["amber_lt"], "cyc": PALETTE["amber"]},
    "LFP":    {"cal": PALETTE["israel_lt"], "cyc": PALETTE["israel"]},
}


def main(typologies=None, out=None) -> None:
    typologies = typologies or TYPOLOGIES
    out = out or OUT
    fig, ax = plt.subplots(figsize=(15 if len(typologies) > 2 else 9.5, 7.2))

    n_typ = len(typologies)
    bar_w = 0.13
    typ_centers = np.arange(n_typ) * 1.4
    chem_offset = {"NMC_B1": -0.27, "LFP": +0.27}

    for chem in CHEMS:
        col = COLORS[chem]
        for k, cf in enumerate(CFS):
            xs = typ_centers + chem_offset[chem] + (k - 1) * bar_w
            cal_vals, cyc_vals, totals, tags = [], [], [], []
            for typ in typologies:
                cal, cyc = split_losses(typ, chem, cf)
                cal_vals.append(cal); cyc_vals.append(cyc)
                totals.append(cal + cyc)
                tags.append(WONG_V2G_EFFECT[typ][chem] if cf == "V2G" else "")

            ax.bar(xs, cal_vals, width=bar_w, color=col["cal"],
                   edgecolor="white", linewidth=0.4)
            ax.bar(xs, cyc_vals, width=bar_w, bottom=cal_vals,
                   color=col["cyc"], edgecolor="white", linewidth=0.4)

            for x, t in zip(xs, totals):
                ax.text(x, -0.8, cf, ha="center", fontsize=7.5,
                        color=PALETTE["neutral"])
                ax.text(x, t + 0.3, f"{t:.1f}", ha="center", fontsize=11.5,
                        fontweight="bold", color="#1e293b")
            if cf == "V2G":
                for x, t, tag in zip(xs, totals, tags):
                    color = ("#15803d" if tag == "IMPROVE"
                             else PALETTE["neutral"] if tag == "NEUTRAL"
                             else PALETTE["cost"])
                    ax.text(x, t + 2.0, tag, ha="center", fontsize=7,
                            fontweight="bold", color=color)

    ax.set_xticks(typ_centers)
    ax.set_xticklabels([t.replace(" ", "\n") for t in typologies], fontsize=11.5)

    ax.axhline(100 - EOL_SOH_PCT, color="#1e293b", linestyle="--", linewidth=1.0)
    ax.text(typ_centers[-1] + 0.62, 100 - EOL_SOH_PCT + 0.35,
            "EoL (20 pp = 80 % SoH)", fontsize=11.5, color="#1e293b", ha="right")

    ax.set_ylabel("10-year capacity loss (percentage points)")
    ax.set_title("Battery aging by typology, chemistry, counterfactual — "
                 "Wong 2026 Appendix E regression slopes at Wong Fig-5 volumes")

    handles = [
        mpatches.Patch(facecolor=COLORS["NMC_B1"]["cal"], label="NMC|Gr B1 calendar"),
        mpatches.Patch(facecolor=COLORS["NMC_B1"]["cyc"], label="NMC|Gr B1 cycle"),
        mpatches.Patch(facecolor=COLORS["LFP"]["cal"],    label="LFP|Gr calendar"),
        mpatches.Patch(facecolor=COLORS["LFP"]["cyc"],    label="LFP|Gr cycle"),
    ]
    ax.legend(handles=handles, loc="upper left", ncol=2)
    ax.set_ylim(-2, 30)

    fig.text(0.5, 0.015,
             "V0 baseline: visual read of Wong Fig 3 (INTERPRET).  V1G: Etxandi-Santolaya 2024 upper bound.  "
             "V2G bars and calendar/cycle split: Wong Appendix E published betas (delta = beta x kWh/yr x 10).  "
             "Category tags: Wong Sec 2.4 statistics.",
             ha="center", fontsize=11.5, color=PALETTE["neutral"])

    fig.tight_layout(rect=(0, 0.045, 1, 1))
    fig.savefig(out)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
    main(typologies=["Daily Charger", "BEV 2nd Vehicle"], out=OUT_ACTIVE)
