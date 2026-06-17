"""Hourly electricity prices.

Israeli residential TAOZ (תעריף עומס וזמן) as defined in the PUA tariff
book of January 2026 for low-voltage residential customers (מ"נ ביתי).

KEY STRUCTURAL FACTS:
  * Two bands only:  פסגה (peak) and שפל (off-peak).  There is no
    intermediate "shoulder" band in the residential schedule.  (A third
    band, גבע, exists in the medium- and high-voltage commercial
    schedules but is not used for residential.)
  * Peak windows differ by season.
  * Weekend rules differ by season.  Friday and Saturday are off-peak
    in summer and transition seasons, but in winter they retain the
    weekday peak window.

Schedule:

  Summer (Jun-Sep):
    - weekday Sun-Thu: peak 17:00-22:00, else off-peak
    - Fri-Sat:         off-peak all day

  Transition (Mar-May, Oct-Nov):
    - weekday Sun-Thu: peak 18:00-22:00, else off-peak
    - Fri-Sat:         off-peak all day

  Winter (Dec-Feb):
    - all days incl. Fri-Sat: peak 17:00-21:00, else off-peak

Rates source: PUA tariff book 01/2026, residential domestic TAOZ
(תעו"ז ברירתי ביתי).  Rates are VAT inclusive.

Convention:
  day_of_week:  0=Sunday, 1=Monday, ..., 5=Friday, 6=Saturday
                (matches the Israeli workweek of Sun-Thu and the
                EVAgent convention (hour // 24) % 7).
  month:        1-12 (Gregorian).  Default 7 (July) preserves the
                W7-W8 summer-only assumption when month is not given.
"""

# -----------------------------------------------------------------------------
# Rates (NIS per kWh, VAT included)
# -----------------------------------------------------------------------------
PRICE_OFFPEAK = 0.5283   # שפל  (off-peak)
PRICE_PEAK    = 1.6895   # פסגה  (peak)

# V1G charging threshold: charge only when current price is at or below this
# value.  Under the residential 2-band schedule this collapses to "charge
# only at off-peak", because the only non-peak band IS off-peak.
CHEAP_THRESHOLD_FOR_V1G = PRICE_OFFPEAK + 0.01


# -----------------------------------------------------------------------------
# Season classification
# -----------------------------------------------------------------------------
SUMMER_MONTHS     = {6, 7, 8, 9}
TRANSITION_MONTHS = {3, 4, 5, 10, 11}
WINTER_MONTHS     = {12, 1, 2}


def season_of(month: int) -> str:
    """Return 'summer', 'transition', or 'winter' for a 1-12 month index."""
    if month in SUMMER_MONTHS:
        return "summer"
    if month in TRANSITION_MONTHS:
        return "transition"
    if month in WINTER_MONTHS:
        return "winter"
    raise ValueError(f"month must be 1-12, got {month}")


def is_weekend(day_of_week: int) -> bool:
    """Israeli weekend: Friday (5) and Saturday (6)."""
    return day_of_week in (5, 6)


# -----------------------------------------------------------------------------
# Peak window per season
# -----------------------------------------------------------------------------
PEAK_WINDOWS = {
    # season  -> (peak_start_hour, peak_end_hour)  end is EXCLUSIVE
    "summer":     (17, 22),
    "transition": (18, 22),
    "winter":     (17, 21),
}


def _is_peak_hour(hour_of_day: int, day_of_week: int, month: int) -> bool:
    season = season_of(month)
    start, end = PEAK_WINDOWS[season]
    in_window = start <= hour_of_day < end
    if not in_window:
        return False
    # Weekend rules
    if is_weekend(day_of_week):
        # In summer and transition, weekend is fully off-peak.
        # In winter, weekend keeps the weekday peak window.
        return season == "winter"
    return True


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def price_at_hour(
    hour_of_day: int,
    day_of_week: int = 0,
    month: int = 7,
) -> float:
    """Return the Israeli residential TAOZ price for one hour.

    Parameters
    ----------
    hour_of_day : int
        0-23.  Hour starting at midnight.
    day_of_week : int
        0=Sunday, 6=Saturday.  Default 0 preserves a Sun-Thu weekday.
    month : int
        1-12.  Default 7 (July, summer) preserves the W7-W8 summer-only
        assumption when callers do not pass a month.

    Returns
    -------
    float
        NIS per kWh (VAT included).
    """
    assert 0 <= hour_of_day <= 23, f"hour_of_day must be 0-23, got {hour_of_day}"
    assert 0 <= day_of_week <= 6,  f"day_of_week must be 0-6, got {day_of_week}"

    if _is_peak_hour(hour_of_day, day_of_week, month):
        return PRICE_PEAK
    return PRICE_OFFPEAK


# -----------------------------------------------------------------------------
# Diagnostic helper - prints the 24h schedule for each season.
# Run:  python -m src.pricing
# -----------------------------------------------------------------------------
def _print_24h_schedule() -> None:
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    for season, months in [("summer", SUMMER_MONTHS),
                           ("transition", TRANSITION_MONTHS),
                           ("winter", WINTER_MONTHS)]:
        month = sorted(months)[0]   # representative month
        print(f"\n===== {season.upper()}  (representative month = {month}) =====")
        header = "Hour | " + " | ".join(f"{d:>3}" for d in day_names)
        print(header)
        print("-" * len(header))
        for h in range(24):
            cells = []
            for dow in range(7):
                p = price_at_hour(h, dow, month)
                cells.append("PK" if p == PRICE_PEAK else "op")
            print(f"{h:>4} | " + " | ".join(f"{c:>3}" for c in cells))


if __name__ == "__main__":
    _print_24h_schedule()
