"""UK electricity prices.

Three retail tariffs are modelled, one per counterfactual:

  V0   - Ofgem default tariff cap (unit rate, flat).
         Source: Ofgem default cap published quarterly.
         Used for the uncontrolled-charging baseline because the
         majority of UK households not on a smart tariff buy at the
         cap-bound unit rate.

  V1G  - Octopus Go (off-peak 00:30-04:30, peak rest of day).
         Source: Octopus Energy public Go tariff.
         The driver shifts charging into the 4-hour off-peak window.

  V2G  - Octopus Powerloop.  Same import structure as Octopus Go
         on the consumption side; on the export side, the driver
         receives a flat per-kWh export rate during a defined
         discharge window (afternoon-to-evening UK grid peak).
         Source: Octopus Powerloop public terms.

All rates are GBP per kWh.  Convert to NIS using GBP_TO_NIS where
the dissertation needs cross-country comparison.

UK has no statutory residential weekend tariff differentiation, so
day_of_week is accepted but ignored.  Seasonality (winter heating
peak) is also ignored at this stage; UK retail tariffs do not
currently embed seasonal structure for residential customers.
"""

# ----------------------------------------------------------------------
# Rates (GBP per kWh)
# ----------------------------------------------------------------------

# Ofgem default cap rate (Q2 2025).  Used as the V0 baseline.
OFGEM_CAP_RATE_GBP = 0.245

# Octopus Go.  Used as the V1G smart-charging tariff.
OCTOPUS_GO_OFFPEAK_GBP = 0.085   # 00:30-04:30
OCTOPUS_GO_PEAK_GBP    = 0.281   # the rest of the day
OCTOPUS_GO_OFFPEAK_START_HOUR = 0    # rounded from 00:30 to 00:00 for the hourly model
OCTOPUS_GO_OFFPEAK_END_HOUR   = 5    # rounded from 04:30 to 05:00, exclusive

# Octopus Powerloop.
# Import side: identical to Octopus Go (V1G structure).
# Export side: flat per-kWh rate during the afternoon-to-evening peak
# window when the aggregator typically calls discharge.
POWERLOOP_EXPORT_GBP   = 0.214   # paid to the driver per discharged kWh
POWERLOOP_DISCHARGE_START_HOUR = 16
POWERLOOP_DISCHARGE_END_HOUR   = 19   # exclusive


# ----------------------------------------------------------------------
# Currency conversion (for joint NIS reporting).
# ----------------------------------------------------------------------
GBP_TO_NIS = 4.70


# ----------------------------------------------------------------------
# Public API.  Mirrors the signature of src.pricing.price_at_hour
# so the run loop can call either module by country flag.
# ----------------------------------------------------------------------
def ofgem_cap_rate_at_hour(hour_of_day: int = 0,
                           day_of_week: int = 0,
                           month: int = 1) -> float:
    """V0 import rate under the Ofgem default cap.  Flat per hour."""
    return OFGEM_CAP_RATE_GBP


def octopus_go_rate_at_hour(hour_of_day: int,
                            day_of_week: int = 0,
                            month: int = 1) -> float:
    """V1G import rate under Octopus Go.

    Off-peak 00:00-05:00 (rounded from the published 00:30-04:30
    half-hourly bands to the model's hourly grid), peak otherwise.
    """
    if OCTOPUS_GO_OFFPEAK_START_HOUR <= hour_of_day < OCTOPUS_GO_OFFPEAK_END_HOUR:
        return OCTOPUS_GO_OFFPEAK_GBP
    return OCTOPUS_GO_PEAK_GBP


def octopus_powerloop_export_at_hour(hour_of_day: int,
                                     day_of_week: int = 0,
                                     month: int = 1) -> float:
    """V2G discharge export rate paid to the driver.

    Zero outside the discharge window; the flat Powerloop export rate
    inside it.
    """
    if POWERLOOP_DISCHARGE_START_HOUR <= hour_of_day < POWERLOOP_DISCHARGE_END_HOUR:
        return POWERLOOP_EXPORT_GBP
    return 0.0


# ----------------------------------------------------------------------
# Counterfactual dispatch.  The fleet runner asks for "price the driver
# sees right now" via this function, with the counterfactual choosing
# the relevant tariff.
# ----------------------------------------------------------------------
def uk_price_at_hour(counterfactual: str,
                     hour_of_day: int,
                     day_of_week: int = 0,
                     month: int = 1) -> float:
    """Return the GBP/kWh import rate the UK driver pays under the
    selected counterfactual."""
    if counterfactual == "V0":
        return ofgem_cap_rate_at_hour(hour_of_day, day_of_week, month)
    if counterfactual in ("V1G", "V2G"):
        return octopus_go_rate_at_hour(hour_of_day, day_of_week, month)
    raise ValueError(f"unknown counterfactual {counterfactual!r}")


def uk_aggregator_signals_discharge(hour_of_day: int,
                                    day_of_week: int = 0,
                                    month: int = 1) -> bool:
    """UK aggregator (Octopus Powerloop) discharge signal.

    Fires inside the Powerloop discharge window (16:00-19:00 every day),
    when the GB grid evening ramp is at its steepest.  Independent of
    season because UK Powerloop terms do not vary seasonally for
    residential customers.
    """
    return POWERLOOP_DISCHARGE_START_HOUR <= hour_of_day < POWERLOOP_DISCHARGE_END_HOUR


if __name__ == "__main__":
    print(f"{'Hour':>4}  {'V0 Ofgem':>10}  {'V1G Octopus Go':>15}  "
          f"{'V2G export':>10}")
    for h in range(24):
        v0  = ofgem_cap_rate_at_hour(h)
        v1g = octopus_go_rate_at_hour(h)
        v2g_ex = octopus_powerloop_export_at_hour(h)
        print(f"{h:>4}  {v0:>10.3f}  {v1g:>15.3f}  {v2g_ex:>10.3f}")
