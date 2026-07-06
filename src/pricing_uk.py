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

# Rates verified against the public Octopus / Ofgem pages (June 2026).
# Historic Q2 2025 values noted in comments for traceability.

# Ofgem default tariff cap, Apr-Jun 2026 (E&W&S average, direct debit,
# VAT inclusive).  Q2 2025 value: 0.245.
OFGEM_CAP_RATE_GBP = 0.2467

# Octopus Go / Intelligent Octopus Go (V1G smart-charging tariff).
# (2025 tariff generation: 8.5 p off-peak / 28.1 p peak, 4-h window.)
# Public rate as of June 2026:
#   - Intelligent Octopus Go: 7p off-peak, 5- or 6-h smart window
#   - Standard Octopus Go:    6.99-9.5p off-peak depending on region
#   - Peak: 31.64p
# We use the headline Intelligent Go figures because they're the
# product Octopus is actively marketing for V2G drivers.
OCTOPUS_GO_OFFPEAK_GBP = 0.070   # 7 p, Intelligent Octopus Go
OCTOPUS_GO_PEAK_GBP    = 0.3164  # 31.64 p
OCTOPUS_GO_OFFPEAK_START_HOUR = 0    # rounded from 23:30
OCTOPUS_GO_OFFPEAK_END_HOUR   = 6    # rounded to 05:30, exclusive (6 h window)

# UK day-ahead wholesale curve from the BMRS Elexon API (June 2026 pull).
# Real data pulled from 25 June 2025 to 25 June 2026, APX MID provider,
# 17,084 deduplicated half-hour observations.  Endpoint:
#   https://data.elexon.co.uk/bmrs/api/v1/balancing/pricing/market-index
#
# Two access paths exposed below:
#
#   uk_wholesale_price_at_hour_of_year(hour_of_year)
#       Returns the REAL price for that specific hour of the simulated
#       year.  This is what the simulator should call when running an
#       annual horizon.  Uses the BMRS CSV under data/.
#
#   UK_WHOLESALE_24H_GBP
#       The hour-of-day MEAN across the year, used by plots that
#       need a "typical day".
#
# Annual mean of the 24 hour-of-day means: 8.47 p/kWh.
# Peak/off-peak spread: 7.24 p (03 h) -> 10.67 p (18 h), ~1.47x.

UK_WHOLESALE_24H_GBP = [
    0.0775, 0.0757, 0.0737, 0.0724, 0.0729, 0.0780,  # 00-05
    0.0845, 0.0911, 0.0901, 0.0845, 0.0825, 0.0780,  # 06-11
    0.0766, 0.0750, 0.0756, 0.0820, 0.0887, 0.1006,  # 12-17
    0.1067, 0.1058, 0.1013, 0.0936, 0.0864, 0.0793,  # 18-23
]

# Lazy-loaded BMRS year series (hour_of_year -> price in GBP/kWh)
_BMRS_YEAR_HOURLY: list[float] | None = None


def _load_bmrs_year_hourly() -> list[float]:
    """Load BMRS year CSV and aggregate half-hourly -> hourly means.

    Returns a list of length 8760 (or shorter if data has gaps).
    Hour 0 of the series corresponds to 25 June 2025 hour 0; the
    simulator's hour_of_year=0 maps to series index 0.
    """
    import csv
    from pathlib import Path
    here = Path(__file__).resolve().parent.parent
    csv_path = here / "data" / "uk_wholesale_2025_2026.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"BMRS CSV missing.  Run python -m src.build_bmrs_year_csv first.\n"
            f"Expected at: {csv_path}"
        )
    # Build a dict keyed by (date, hour_of_day) -> list of prices
    from collections import defaultdict
    bucket: dict[tuple[str, int], list[float]] = defaultdict(list)
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["settlement_date"], int(row["hour_of_day"]))
            bucket[key].append(float(row["price_gbp_per_kwh"]))
    # Sort dates ascending, build the 8760-length series
    sorted_keys = sorted(bucket.keys())
    series: list[float] = []
    annual_mean = sum(sum(v) for v in bucket.values()) / sum(len(v) for v in bucket.values())
    for key in sorted_keys:
        vals = bucket[key]
        series.append(sum(vals) / len(vals))
    # Pad to 8760 with the annual mean if any gap remains
    while len(series) < 8760:
        series.append(annual_mean)
    return series[:8760]


def uk_wholesale_price_at_hour_of_year(hour_of_year: int) -> float:
    """Real BMRS-derived wholesale price for the given hour of year.

    hour_of_year 0 corresponds to 25 June 2025 hour 0 (the BMRS pull
    start).  The simulator should wire its hour_of_year directly to
    this function when running wholesale scenarios.
    """
    global _BMRS_YEAR_HOURLY
    if _BMRS_YEAR_HOURLY is None:
        _BMRS_YEAR_HOURLY = _load_bmrs_year_hourly()
    return _BMRS_YEAR_HOURLY[hour_of_year % 8760]


def uk_wholesale_price_at_hour(hour_of_day: int,
                               day_of_week: int = 0,
                               month: int = 1) -> float:
    """UK day-ahead wholesale price (GBP/kWh) for the given hour.

    Shape encoded from N2EX / EPEX SPOT typical 2026 hourly profile.
    Annual average ~9.8 p/kWh.  Source: energy-stats.uk live tracker,
    BMRS Elexon market index prices.  This is a static profile - for
    a true day-ahead model, swap with a CSV import.
    """
    return UK_WHOLESALE_24H_GBP[hour_of_day]


# Octopus Powerloop -> rebranded to Octopus Power Pack in 2026.
# Old Powerloop (Sciurus trial 2021): 21.4 p export, 16-19 window.
# Current Power Pack: "free miles" model; standard outgoing export
# rate is 12 p/kWh from March 2026.  We use 12 p as the V2G export
# rate the driver effectively receives, applied across the same
# afternoon-to-evening peak window as in the model structure.
POWERLOOP_EXPORT_GBP   = 0.12    # Power Pack rate (Sciurus-trial-era Powerloop: 0.214)
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
