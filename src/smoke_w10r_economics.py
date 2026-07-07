"""Economics smoke test — V2G driver P&L.

Surfaces the V2G driver economics in plain numbers, separately for
operating P&L (= revenue minus battery degradation) and for total
10-year P&L including the charger CAPEX.

The model runs its natural price-driven V2G volume (no annual cap).
Battery aging uses the Wong 2026 Appendix E regression slopes
(beta x annual kWh x 10), capped at +/- 20 pp so the linear
extrapolation does not produce nonsense at high-volume extremes.

For each combination of (country, typology, chemistry), prints:

  - Annual V2G discharge (kWh)        - model output, per opted-in EV
  - Annual V2G revenue                - revenue per kWh x annual kWh
  - Annual battery degradation cost   - Wong V2G effect category
                                        translated into pp delta x
                                        battery size x BNEF 2025 price
  - Annual operating P&L              - revenue minus battery cost
  - 10-year operating P&L             - x 10, no CAPEX
  - V2G premium CAPEX                 - Wallbox Quasar 2 midpoint
  - 10-year total P&L                 - operating minus premium
  - Charger payback years             - premium / annual operating P&L

Run:  python -m src.smoke_w10r_economics
"""

from __future__ import annotations

from src.aggregator_stub import (
    CHARGER_CAPEX_BIDIR_2024_NIS,
    CHARGER_CAPEX_BIDIR_2024_UK_NIS,
    CHARGER_CAPEX_SMART_NIS,
)
from src.aging_table_lit import v2g_delta_pp_10yr, WONG_V2G_KWH_PER_YEAR, WONG_V2G_EFFECT
from src.battery_aging import (
    BATTERY_REPLACEMENT_COST_NIS_PER_KWH_NMC,
    BATTERY_REPLACEMENT_COST_NIS_PER_KWH_LFP,
)
from src.pricing_uk import GBP_TO_NIS


V2G_PREMIUM_NIS = CHARGER_CAPEX_BIDIR_2024_NIS - CHARGER_CAPEX_SMART_NIS
# UK premium uses the UK-specific charger price (no Israeli VAT uplift)
V2G_PREMIUM_GBP = (CHARGER_CAPEX_BIDIR_2024_UK_NIS - CHARGER_CAPEX_SMART_NIS) / GBP_TO_NIS

V2G_DELTA_PCT_AT_WONG_VOL = {
    "IMPROVE":   -2.0,
    "NEUTRAL":    0.0,
    "SLIGHT":    +1.5,
    "DECREASE":  +3.0,
    "LARGE":     +6.0,
}
MAX_AGING_DELTA_PCT = 20.0   # cap linear scaling at +/- 20 pp

BATTERY_KWH = 67.0   # Israeli fleet weighted-average (see vehicle_catalog)
ISRAEL_RETAIL_PEAK_NIS = 1.6895
ISRAEL_OFFPEAK_NIS = 0.528
RTE = 0.9025   # 0.95 charge x 0.95 discharge
UK_POWER_PACK_GBP      = 0.12

# The Sciurus 2021 figures are TOTAL annual earnings, not additive
# layers.  Cenex 2021 report:
#   £340 / V2G EV / yr  = total under V2G smart charging alone
#   £513 / V2G EV / yr  = total when Firm Frequency Response is added
#   £725 / V2G EV / yr  = total when Dynamic Containment is added
# Adding Power Pack arbitrage (~£288) on top of the £725 would
# double-count arbitrage.  Correct framing = two business models:
#   Model A (retail tariff only): Power Pack 12 p export ~£288/yr
#   Model B (Sciurus aggregator): £725/yr total (INCLUDES arbitrage)
# Source: https://www.cenex.co.uk/news/4-pioneering-v2g-projects/
UK_SCIURUS_DC_TOTAL_GBP = 725.0   # Model B total annual earnings
UK_SCIURUS_BASE_GBP     = 340.0   # Sciurus pure V2G smart charging
UK_SCIURUS_FFR_GBP      = 513.0   # Sciurus + FFR total

# Observed V2G volumes from the uncapped model: a full-year 8,760-hour
# run of the 240-agent Israel V2G ABM, reported PER OPTED-IN EV
# (driver-facing numbers reflect what a participating driver actually
# earns, not a fleet mean that averages in non-participants
# dispatching zero).
# Public Charger has no home charger per the Wong characterisation
# ("lack home charging access").  BEV 2nd Vehicle is high by design:
# a 2nd vehicle that drives ~3 days a week is assumed
# parked-and-connected the rest of the time, and Fri+Sat retain peak
# in the winter TAOZ, so it gains substantial peak discharge
# opportunity Nov-Feb.  Volumes exceed Wong 2026's because dispatch
# here is price-driven rather than window-bound.
OBSERVED_V2G_KWH_PER_YEAR = {
    "Daily Charger":     4820,    # opt-in mean
    "Public Charger":       0,    # no home charger; structural
    "BEV 2nd Vehicle":   6220,    # opt-in mean
    "Threshold Charger":    2,    # SoC-floor rule dominates
}


def compute(country: str, typology: str, chemistry: str,
            uk_model: str = "B_sciurus") -> dict:
    """uk_model: 'A_powerpack' (retail arbitrage only at the 12 p export rate)
                 'B_sciurus'   (£725/yr total, aggregator + DC) - default
    """
    kwh = OBSERVED_V2G_KWH_PER_YEAR[typology]
    wong_kwh = WONG_V2G_KWH_PER_YEAR[typology]["mean"]

    if country == "Israel":
        currency = "NIS"
        premium = V2G_PREMIUM_NIS
        # NET revenue: peak-rate income minus the off-peak cost of
        # repurchasing the dispatched energy at the model round-trip
        # efficiency (same basis as the P&L figures and the manuscript).
        annual_revenue = (kwh * ISRAEL_RETAIL_PEAK_NIS
                          - kwh / RTE * ISRAEL_OFFPEAK_NIS)
    else:
        currency = "GBP"
        premium = V2G_PREMIUM_GBP
        if uk_model == "A_powerpack":
            # Retail-only arbitrage at Power Pack 12 p export rate
            annual_revenue = kwh * UK_POWER_PACK_GBP
        else:
            # The Sciurus £725 flat fee is intended for real V2G
            # participants, not for typologies producing rounding-artifact
            # kWh volumes (Threshold Charger 2 kWh/yr is a rare model
            # output that would otherwise trigger the full £725, giving
            # a false 5-year payback).  Sciurus Model B is restricted to
            # the two active typologies that Wong 2026 identifies as
            # genuine V2G participants.
            _SCIURUS_ELIGIBLE = ("Daily Charger", "BEV 2nd Vehicle")
            if typology in _SCIURUS_ELIGIBLE and kwh > 0:
                annual_revenue = UK_SCIURUS_DC_TOTAL_GBP
            else:
                annual_revenue = 0.0

    # Battery cost: 10-year capacity delta from the Wong 2026
    # Appendix E regression slopes (capped inside v2g_delta_pp_10yr).
    chem_key = "NMC_B1" if chemistry == "NMC" else "LFP"
    delta_pp = v2g_delta_pp_10yr(typology, chem_key, kwh)
    pct_delta = -delta_pp   # positive = loss (cost); improvement -> negative
    pct_delta = max(0.0, pct_delta)
    lost_kwh_10y = (pct_delta / 100.0) * BATTERY_KWH
    if chemistry == "NMC":
        cost_nis_per_kwh = BATTERY_REPLACEMENT_COST_NIS_PER_KWH_NMC
    else:
        cost_nis_per_kwh = BATTERY_REPLACEMENT_COST_NIS_PER_KWH_LFP
    battery_cost_10y_nis = lost_kwh_10y * cost_nis_per_kwh
    if currency == "NIS":
        battery_cost_10y = battery_cost_10y_nis
    else:
        battery_cost_10y = battery_cost_10y_nis / GBP_TO_NIS
    annual_battery_cost = battery_cost_10y / 10.0

    operating_pnl_annual = annual_revenue - annual_battery_cost
    operating_pnl_10y = operating_pnl_annual * 10.0
    total_10y = operating_pnl_10y - premium
    payback = (premium / operating_pnl_annual) if operating_pnl_annual > 0 else float("inf")

    return {
        "country":          country,
        "typology":         typology,
        "chemistry":        chemistry,
        "currency":         currency,
        "annual_kwh":       kwh,
        "annual_revenue":   annual_revenue,
        "annual_battery":   annual_battery_cost,
        "annual_op_pnl":    operating_pnl_annual,
        "op_pnl_10y":       operating_pnl_10y,
        "premium":          premium,
        "total_10y":        total_10y,
        "payback_years":    payback,
    }


def main() -> None:
    typologies = list(WONG_V2G_KWH_PER_YEAR.keys())
    chems = ("NMC", "LFP")

    print()
    print("Economics smoke test  -  V2G driver P&L")
    print("=" * 110)
    print("All values per single V2G-opted-in driver, Wong-anchored annual "
          "discharge volume.")
    print(f"V2G premium (Wallbox Quasar 2 mid): {V2G_PREMIUM_NIS:,.0f} NIS / "
          f"GBP {V2G_PREMIUM_GBP:,.0f}.")
    print("Battery cost from BloombergNEF 2025: NMC 600 NIS/kWh, "
          "LFP 380 NIS/kWh, 67 kWh pack (Israeli fleet average).")
    print()

    for country, uk_models in (("Israel", [None]),
                                ("UK", ["A_powerpack", "B_sciurus"])):
        for uk_model in uk_models:
            label = f"{country}"
            if uk_model is not None:
                label += f"  ({uk_model})"
            print(f"--- {label} ---")
            hdr = (f"{'Typology':>20} | {'Chem':>4} | {'kWh/yr':>7} | "
                   f"{'Rev/yr':>10} | {'Bat/yr':>8} | {'OP/yr':>10} | "
                   f"{'OP 10y':>11} | {'Tot 10y':>11} | {'Payback':>8}")
            print(hdr); print("-" * len(hdr))
            for typ in typologies:
                for chem in chems:
                    if uk_model is None:
                        r = compute(country, typ, chem)
                    else:
                        r = compute(country, typ, chem, uk_model=uk_model)
                    payback_str = (f"{r['payback_years']:>5.0f} y"
                                   if r['payback_years'] < 999 else " never")
                    ccy = r['currency']
                    print(f"{r['typology']:>20} | {r['chemistry']:>4} | "
                          f"{r['annual_kwh']:>6.0f}  | "
                          f"{r['annual_revenue']:>7,.0f} {ccy} | "
                          f"{r['annual_battery']:>5,.0f} {ccy[:1]} | "
                          f"{r['annual_op_pnl']:>+7,.0f} {ccy} | "
                          f"{r['op_pnl_10y']:>+8,.0f} {ccy} | "
                          f"{r['total_10y']:>+8,.0f} {ccy} | "
                          f"{payback_str:>8}")
            print()

    print("Reading the columns:")
    print("  Rev/yr     V2G annual revenue at the country's V2G export rate")
    print("  Bat/yr     Annualised 10-year battery degradation cost")
    print("  OP/yr      Annual operating P&L = revenue - battery cost")
    print("  OP 10y     10-year operating P&L = OP/yr x 10 (NO charger CAPEX)")
    print("  Tot 10y    10-year total P&L = OP 10y minus V2G premium")
    print("  Payback    Years to recoup the V2G premium from operating P&L")


if __name__ == "__main__":
    main()
