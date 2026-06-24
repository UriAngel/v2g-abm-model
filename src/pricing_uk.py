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

# W10.G: rate refresh against current public Octopus / Ofgem pages
# (verified via web search June 2026).  Historic Q2 2025 values kept
# as comments for traceability against the older W9.E commit.

# Ofgem default tariff cap, Apr-Jun 2026 (E&W&S average, direct debit,
# VAT inclusive).  Was 0.245 in Q2 2025, now 0.2467.
OFGEM_CAP_RATE_GBP = 0.2467

# Octopus Go / Intelligent Octopus Go (V1G smart-charging tariff).
# Was 0.085 / 0.281 in 4-h window in W9.E.  Public rate as of June 2026:
#   - Intelligent Octopus Go: 7p off-peak, 5- or 6-h smart window
#   - Standard Octopus Go:    6.99-9.5p off-peak depending on region
#   - Peak: 31.64p
# We use the headline Intelligent Go figures because they're the
# product Octopus is actively marketing for V2G drivers.
OCTOPUS_GO_OFFPEAK_GBP = 0.070   # 7 p, Intelligent Octopus Go
OCTOPUS_GO_PEAK_GBP    = 0.3164  # 31.64 p (was 28.1 p)
OCTOPUS_GO_OFFPEAK_START_HOUR = 0    # rounded from 23:30
OCTOPUS_GO_OFFPEAK_END_HOUR   = 6    # rounded to 05:30, exclusive (6 h window)

# Octopus Powerloop -> rebranded to Octopus Power Pack in 2026.
# Old Powerloop (Sciurus trial 2021): 21.4 p export, 16-19 window.
# Current Power Pack: "free miles" model; standard outgoing export
# rate is 12 p/kWh from March 2026.  We use 12 p as the V2G export
# rate the driver effectively receives, applied across the same
# afternoon-to-evening peak window for compatibility with the W9
# model structure.
POWERLOOP_EXPORT_GBP   = 0.12    # was 0.214 p (Sciurus trial era)
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
