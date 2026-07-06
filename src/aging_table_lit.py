"""Literature-anchored aging table.

Design principle: keep aging simple and rely on directly published
rates rather than deriving degradation from first principles or
converting it into a NIS/kWh charge.  The anchors are the directly
published values from Wong 2026:
  - Annual V2G energy per typology (Figure 5)
  - Qualitative V2G impact direction per chemistry (Figure 6
    + Section 2.4 prose)
  - V0 baseline 10-year capacity loss read approximately off
    Figure 3 of the control runs.

Sources:

  - Wong et al. 2026 (arXiv 2603.10880).  Annual V2G energy from
    Section 2.4 / Figure 5 and accompanying text.  Qualitative
    chemistry findings from Section 2.4 / Figure 6.  V0 baseline
    visual approximations from Figure 3 (approximate read; exact
    values pending the supplementary dataset).

  - Gasper et al. 2023 (J. Power Sources).  Used only as the source
    for LFP|Gr cycle sensitivity being roughly 3x NMC|Gr at the
    same throughput; not used to derive any specific percentage.

What this script reports:
  1. The published annual V2G energy per typology (Wong Fig 5).
  2. V0 baseline 10-year capacity loss per chemistry (Wong Fig 3
     approximate visual read).
  3. The qualitative V2G impact per (typology, chemistry) per Wong
     Section 2.4: NEUTRAL / SLIGHT_DECREASE / DECREASE / IMPROVEMENT.

Quantitative 10-year V2G capacity deltas are computed from the Wong
2026 Appendix E regression slopes (see WONG_BETA_TOTAL and
v2g_delta_pp_10yr); the unit interpretation is validated against
Wong's cycle-share statistics and the Figure 6 scale, and capped at
+/- 20 pp.

Run:  python -m src.aging_table_lit
"""

from __future__ import annotations


# ------------------------------------------------------------------
# Wong 2026 published annual V2G energy per typology  (kWh/year)
# Section 2.4 / Figure 5.  CIs are 95 % confidence intervals.
# ------------------------------------------------------------------
WONG_V2G_KWH_PER_YEAR = {
    "Daily Charger":     {"mean": 1259.0, "ci_low": 1008.0, "ci_high": 1510.0},
    "Public Charger":    {"mean":  111.0, "ci_low":   40.0, "ci_high":  182.0},
    "BEV 2nd Vehicle":   {"mean":  576.0, "ci_low":  269.0, "ci_high":  882.0},
    "Threshold Charger": {"mean":  204.0, "ci_low":  144.0, "ci_high":  263.0},
}


# ------------------------------------------------------------------
# Wong 2026 V0 baseline 10-year capacity loss per chemistry.
# APPROXIMATE visual reads off Figure 3; exact values pending the
# supplementary dataset.  Order-of-magnitude correct.
# ------------------------------------------------------------------
WONG_V0_10Y_LOSS_PCT = {
    "NMC_B1": 18.0,   # calendar-dominated NMC, ~18 % loss over 10 yr
    "NMC_B2": 12.0,   # mixed NMC, ~12 %
    "LFP":    14.0,   # cycle-dominated LFP, ~14 %
}


# ------------------------------------------------------------------
# Wong 2026 qualitative V2G effect per (typology, chemistry).
# Section 2.4 prose + Figure 6.  Five categories:
#   IMPROVE   - V2G net IMPROVES capacity retention (Daily/Threshold +
#               NMC B1, per the calendar offset finding)
#   NEUTRAL   - no statistically significant change at p<0.05
#   SLIGHT    - small but significant capacity DECREASE
#   DECREASE  - meaningful capacity DECREASE
#   LARGE     - large capacity DECREASE
# ------------------------------------------------------------------
WONG_V2G_EFFECT = {
    "Daily Charger": {
        "NMC_B1": "NEUTRAL",    # beta = 0.008e-4, p = 0.966
        "NMC_B2": "DECREASE",   # beta = -2.7e-4
        "LFP":    "LARGE",      # beta = -5.5e-4
    },
    "Public Charger": {
        "NMC_B1": "SLIGHT",     # extrapolated; Wong shows small loss
        "NMC_B2": "DECREASE",
        "LFP":    "LARGE",
    },
    "BEV 2nd Vehicle": {
        "NMC_B1": "SLIGHT",     # beta = -0.87e-4, p = 4.1e-5
        "NMC_B2": "DECREASE",
        "LFP":    "LARGE",
    },
    "Threshold Charger": {
        "NMC_B1": "IMPROVE",    # beta = +2.40e-4, p = 3.7e-12
        "NMC_B2": "SLIGHT",
        "LFP":    "LARGE",
    },
}


EOL_SOH_PCT = 80.0


# ------------------------------------------------------------------
# Wong 2026 Appendix E regression slopes (published numbers,
# verified against the paper text).
#
# Wong regresses "change in total capacity after 10 years" on
# "V2G kWh/year" per (typology, chemistry).  Slopes below are the
# published beta values (x 1e-4 in the paper; stored here at full
# precision).  Unit interpretation, documented and cross-validated:
#
#     delta_capacity_pp_over_10yr = beta * annual_V2G_kwh * 10
#
# Validation of that interpretation (two independent checks):
#   1. Physics: LFP cycle-share data (Wong Fig 4) implies ~0.00025
#      pp/kWh cycling loss; the beta route gives the same order.
#   2. It reproduces the visual read of Fig 6 for the Daily
#      Charger LFP case (-5.5e-4 * 1259 * 10 = -6.9 pp ~ the "LARGE
#      ~6 pp" read) and the NEUTRAL DC/NMC-B1 case (+0.01 pp ~ 0).
#
# Where the paper gives only a bound for a (typology, chemistry) cell
# ("all beta < -5.18e-4" for LFP, "all beta < -1.55e-4" for NMC B2),
# the bound itself is used and tagged BOUND — a conservative-low
# magnitude for the non-DC typologies.
# Negative = capacity loss; positive = capacity improvement.
# ------------------------------------------------------------------
WONG_BETA_TOTAL = {
    # typology:  {chem: (beta, provenance)}
    "Daily Charger": {
        "NMC_B1": (+0.008e-4, "exact (p=0.966, n.s.)"),
        "NMC_B2": (-2.7e-4,   "exact"),
        "LFP":    (-5.5e-4,   "exact"),
    },
    "BEV 2nd Vehicle": {
        "NMC_B1": (-0.87e-4,  "exact (p=4.1e-5)"),
        "NMC_B2": (-1.55e-4,  "BOUND (all beta < -1.55e-4)"),
        "LFP":    (-5.18e-4,  "BOUND (all beta < -5.18e-4)"),
    },
    "Public Charger": {
        "NMC_B1": (-0.87e-4,  "proxy: BEV bound reused; PC has ~0 V2G kWh"),
        "NMC_B2": (-1.55e-4,  "BOUND"),
        "LFP":    (-5.18e-4,  "BOUND"),
    },
    "Threshold Charger": {
        "NMC_B1": (+2.40e-4,  "exact (p=3.7e-12, improvement)"),
        "NMC_B2": (-1.55e-4,  "BOUND"),
        "LFP":    (-5.18e-4,  "BOUND"),
    },
}

# Cap on the extrapolated 10-year delta (pp).  Our Israeli dispatch
# volumes are 4-10x Wong's; the linear model is the paper's own, but
# beyond ~20 pp the battery would be replaced/derated, so we cap.
MAX_BETA_DELTA_PP = 20.0


def v2g_delta_pp_10yr(typology: str, chemistry: str, annual_kwh: float) -> float:
    """10-year capacity change (pp) from V2G at the given annual volume,
    using Wong 2026 Appendix E regression slopes.  Negative = loss.

        delta_pp = beta * annual_kwh * 10
        (e.g. Daily Charger LFP: -5.5e-4 * 1,259 * 10 = -6.9 pp,
         matching the Fig 6 visual scale)

    Capped at +/- MAX_BETA_DELTA_PP because our Israeli volumes are
    4-10x Wong's observed range.
    """
    chem_key = chemistry if chemistry in ("NMC_B1", "NMC_B2", "LFP") else (
        "NMC_B1" if chemistry == "NMC" else "LFP")
    beta, _prov = WONG_BETA_TOTAL[typology][chem_key]
    delta_pp = beta * annual_kwh * 10.0
    return max(-MAX_BETA_DELTA_PP, min(MAX_BETA_DELTA_PP, delta_pp))


# ------------------------------------------------------------------
# Print the headline table
# ------------------------------------------------------------------
def main() -> None:
    typologies = list(WONG_V2G_KWH_PER_YEAR.keys())
    chems = ("NMC_B1", "NMC_B2", "LFP")

    print()
    print("Wong-anchored battery aging table")
    print("=" * 96)
    print("V2G annual energy per typology from Wong 2026 Fig 5.")
    print("Baseline 10-yr loss per chemistry from Wong 2026 Fig 3 (control).")
    print("V2G effect direction from Wong 2026 Sec 2.4 / Fig 6 prose.")
    print(f"End-of-life convention: SoH = {EOL_SOH_PCT:.0f} %.")
    print()
    print("V2G effect categories (Wong 2026, Section 2.4):")
    print("  IMPROVE  = net capacity IMPROVEMENT from V2G (calendar offset)")
    print("  NEUTRAL  = no statistically significant change (p > 0.05)")
    print("  SLIGHT   = small but significant capacity DECREASE")
    print("  DECREASE = meaningful capacity DECREASE")
    print("  LARGE    = large capacity DECREASE (LFP cycle-dominated)")
    print()

    # --- Annual V2G energy table ---
    print("Per-typology annual V2G energy supply  (Wong Fig 5):")
    print(f"{'Typology':>20} | {'mean':>6} | {'95 % CI':>14}")
    print("-" * 50)
    for typ in typologies:
        d = WONG_V2G_KWH_PER_YEAR[typ]
        print(f"{typ:>20} | {d['mean']:>5.0f}  | "
              f"{d['ci_low']:>5.0f} - {d['ci_high']:>5.0f}  kWh/yr")
    print()

    # --- Baseline V0 10y loss table ---
    print("V0 baseline 10-year capacity loss per chemistry  (Wong Fig 3):")
    for chem in chems:
        loss = WONG_V0_10Y_LOSS_PCT[chem]
        soh  = 100 - loss
        star = " " if soh >= EOL_SOH_PCT else "*"
        print(f"  {chem:>6}: {loss:>5.1f}% loss -> {soh:>5.1f}% SoH at year 10  {star}")
    print()

    # --- V2G qualitative effect table ---
    print("V2G effect on 10-year capacity, per (typology, chemistry)  (Wong Fig 6):")
    hdr = f"{'Typology':>20} | " + " | ".join(f"{c:>10}" for c in chems)
    print(hdr); print("-" * len(hdr))
    for typ in typologies:
        cells = [f"{WONG_V2G_EFFECT[typ][c]:>10}" for c in chems]
        print(f"{typ:>20} | " + " | ".join(cells))
    print()

    print("HEADLINE FINDING (Wong 2026 Sec 2.4):")
    print(" * NMC|Gr B1 (calendar-dominated): V2G NET NEUTRAL or IMPROVES")
    print("   capacity for Daily Charger and Threshold Charger profiles.")
    print("   The V2G strategy reduces time spent at high SOC, which lowers")
    print("   calendar aging enough to offset the added cycle aging.")
    print(" * LFP|Gr (cycle-dominated): V2G uniformly ACCELERATES loss")
    print("   across all four typologies.  Daily Chargers are hit hardest.")
    print(" * NMC|Gr B2 (mixed): intermediate, generally accelerates loss")
    print("   but less than LFP.")


if __name__ == "__main__":
    main()
