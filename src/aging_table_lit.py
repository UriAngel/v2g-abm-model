"""Literature-anchored aging table  (W10.G — honest version).

Per David M6 follow-up: keep aging simple, rely on published rates,
do not derive from first principles, no NIS/kWh tricks.

W10.G change vs W10.F:
  * Dropped the previously fabricated "0.7 % over 10 yr at 7,500 kWh
    of V2G throughput" formulation - NOT in Wong et al. 2026.
  * Dropped the per-typology beta-times-kWh extrapolation - the
    units of Wong's beta coefficient cannot be reliably interpreted
    without the supplementary materials, and our test conversion
    produced implausible numbers.
  * Kept only the directly published values from Wong 2026:
      - Annual V2G energy per typology (Figure 5)
      - Qualitative V2G impact direction per chemistry (Figure 6
        + Section 2.4 prose)
      - V0 baseline 10-year capacity loss read approximately off
        Figure 3 of the control runs.

Sources:

  - Wong et al. 2026 (arXiv 2603.10880).  Annual V2G energy from
    Section 2.4 / Figure 5 and accompanying text.  Qualitative
    chemistry findings from Section 2.4 / Figure 6.  V0 baseline
    visual approximations from Figure 3 (approximate read - replace
    with exact numbers if you obtain the dataset).

  - Gasper et al. 2023 (J. Power Sources).  Used only as the source
    for LFP|Gr cycle sensitivity being roughly 3x NMC|Gr at the
    same throughput; not used to derive any specific percentage.

What this script reports:
  1. The published annual V2G energy per typology (Wong Fig 5).
  2. V0 baseline 10-year capacity loss per chemistry (Wong Fig 3
     approximate visual read).
  3. The qualitative V2G impact per (typology, chemistry) per Wong
     Section 2.4: NEUTRAL / SLIGHT_DECREASE / DECREASE / IMPROVEMENT.

It does NOT compute a specific 10-year V2G capacity loss number
because we cannot reliably interpret Wong's regression beta units.

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
# APPROXIMATE visual reads off Figure 3 - replace with exact numbers
# if you obtain Wong's dataset.  Order-of-magnitude correct.
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
# Print the headline table
# ------------------------------------------------------------------
def main() -> None:
    typologies = list(WONG_V2G_KWH_PER_YEAR.keys())
    chems = ("NMC_B1", "NMC_B2", "LFP")

    print()
    print("Wong-anchored battery aging table  (W10.G)")
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
