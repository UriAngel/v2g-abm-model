"""Literature-anchored aging table.

Per David M6 follow-up: keep aging simple, rely on published rates,
do not derive from first principles, no NIS/kWh tricks.

Aging rates come from three published anchors and nothing else:

  - Wong et al. 2026 (Joule).  NMC calendar at 25 C ~ 2.0% / year
    (control case, no V2G).  V2G excess ~ 0.7% over 10 years at the
    "conservative 50%-floor overnight-only" profile of ~750 kWh / yr.

  - Gasper et al. 2023 (J. Power Sources).  LFP|Gr calendar at 25 C
    is equivalent to NMC|Gr at the same temperature.  LFP|Gr cycle
    sensitivity is ~3x NMC|Gr under the same throughput.

  - Tesla fleet data (2024 impact report, Model 3/Y aggregate).
    Typical EV driver loses ~5-7% over 10 years of mixed AC and DC
    charging, attributable mostly to driving cycle wear.  We use
    0.5% / year as the driving baseline.

Per-typology V2G annual discharge is taken from the W10 ABM simulation
(retail scenario) and used only as a scaling factor on the Wong V2G
calibration:

    V2G_excess_per_year = 0.07 % * (annual_V2G_kWh / 750)        (NMC)
    V2G_excess_per_year = 0.21 % * (annual_V2G_kWh / 750)        (LFP)

Run:  python -m src.aging_table_lit
"""

from __future__ import annotations


# ------------------------------------------------------------------
# Literature anchors
# ------------------------------------------------------------------
CALENDAR_PCT_PER_YEAR_NMC  = 2.0    # Wong et al. 2026
CALENDAR_PCT_PER_YEAR_LFP  = 2.0    # Gasper et al. 2023

CYCLE_BASELINE_PCT_PER_YEAR = 0.5   # Tesla fleet data, mixed AC + DC

# Wong V2G calibration: 0.7% over 10 yr at 7,500 kWh of V2G discharge
# in 10 yr (i.e. 750 kWh/yr).  We express it per year per 750 kWh/yr.
WONG_V2G_BASELINE_KWH_PER_YEAR = 750.0
WONG_V2G_EXCESS_PCT_PER_YEAR_NMC = 0.07            # 0.7% / 10 yr
WONG_V2G_EXCESS_PCT_PER_YEAR_LFP = 0.07 * 3.0      # Gasper 3x LFP factor

EOL_SOH_PCT = 80.0


# ------------------------------------------------------------------
# Per-typology V2G annual discharge (from W10 ABM, retail scenario)
# ------------------------------------------------------------------
ANNUAL_V2G_KWH_PER_TYPOLOGY = {
    "Daily Charger":     2735.0,
    "Public Charger":       0.0,   # no home charger
    "BEV 2nd Vehicle":   3400.0,
    "Threshold Charger":    0.0,   # V2G floor + threshold rule blocks
}


# ------------------------------------------------------------------
# Annual SoH loss formula
# ------------------------------------------------------------------
def annual_soh_loss_pct(
    chemistry: str,
    counterfactual: str,
    annual_v2g_kwh: float,
) -> dict:
    """Annual SoH loss in percent, decomposed.

    chemistry        : "NMC" or "LFP"
    counterfactual   : "V0", "V1G", or "V2G"
    annual_v2g_kwh   : annual V2G discharge throughput for this typology
                       under V2G counterfactual; 0 for V0 and V1G
    """
    if chemistry == "NMC":
        cal = CALENDAR_PCT_PER_YEAR_NMC
        v2g_unit = WONG_V2G_EXCESS_PCT_PER_YEAR_NMC
    elif chemistry == "LFP":
        cal = CALENDAR_PCT_PER_YEAR_LFP
        v2g_unit = WONG_V2G_EXCESS_PCT_PER_YEAR_LFP
    else:
        raise ValueError(chemistry)

    cycle_base = CYCLE_BASELINE_PCT_PER_YEAR
    if counterfactual == "V2G":
        v2g_excess = v2g_unit * (annual_v2g_kwh / WONG_V2G_BASELINE_KWH_PER_YEAR)
    else:
        v2g_excess = 0.0

    total = cal + cycle_base + v2g_excess
    return {
        "calendar":   cal,
        "cycle_base": cycle_base,
        "v2g_excess": v2g_excess,
        "total":      total,
    }


def soh_at_year(annual_loss_pct: float, year: int) -> float:
    """SoH percent at `year` given annual loss percent."""
    return max(0.0, 100.0 - annual_loss_pct * year)


# ------------------------------------------------------------------
# Print the headline table
# ------------------------------------------------------------------
def main() -> None:
    typologies = list(ANNUAL_V2G_KWH_PER_TYPOLOGY.keys())
    cfs = ("V0", "V1G", "V2G")
    chems = ("NMC", "LFP")

    print()
    print("Literature-anchored battery aging table  (W10.F)")
    print("=" * 96)
    print("Aging rates: calendar 2.0 %/yr (Wong NMC, Gasper LFP @ 25 C).")
    print("Driving cycle baseline 0.5 %/yr (Tesla fleet data 2024).")
    print("V2G excess: 0.07 %/yr per 750 kWh/yr V2G (Wong); LFP = 3x NMC (Gasper).")
    print(f"End-of-life convention: SoH = {EOL_SOH_PCT:.0f} %.")
    print()

    hdr = (f"{'Typology':>20} | {'Chem':>4} | {'CF':>4} | "
           f"{'cal/yr':>7} | {'cyc/yr':>7} | {'V2G/yr':>7} | "
           f"{'total/yr':>9} | {'SoH 1y':>7} | {'SoH 5y':>7} | {'SoH 10y':>8}")
    print(hdr); print("-" * len(hdr))

    for typ in typologies:
        v2g_kwh = ANNUAL_V2G_KWH_PER_TYPOLOGY[typ]
        for chem in chems:
            for cf in cfs:
                d = annual_soh_loss_pct(chem, cf, v2g_kwh)
                soh1  = soh_at_year(d["total"], 1)
                soh5  = soh_at_year(d["total"], 5)
                soh10 = soh_at_year(d["total"], 10)
                star  = " " if soh10 >= EOL_SOH_PCT else "*"
                print(f"{typ:>20} | {chem:>4} | {cf:>4} | "
                      f"{d['calendar']:>6.2f}% | {d['cycle_base']:>6.2f}% | "
                      f"{d['v2g_excess']:>6.2f}% | {d['total']:>8.2f}% | "
                      f"{soh1:>6.1f}% | {soh5:>6.1f}% | {soh10:>6.1f}%{star}")
        print()

    print("*  marks runs that fall below the 80% SoH EoL convention by year 10.")


if __name__ == "__main__":
    main()
