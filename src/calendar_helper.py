"""Calendar helpers for the annual horizon simulation (W9.D).

Convert hour-of-year (0..8759) into (hour_of_day, day_of_week, month).

Conventions:
  * The model year starts on Sunday 1 January.  This is a modelling
    choice — Sunday is the first weekday of the Israeli workweek and
    starting on a Sunday means hour 0 is also the start of the working
    week.  Calendar drift across years is irrelevant because each agent
    is simulated for exactly one cycle.
  * Non-leap year:  365 days × 24 = 8760 hours.
  * Month boundaries follow the Gregorian calendar.
"""

HOURS_IN_YEAR = 8760

# Cumulative days at the start of each month (non-leap year).
# CUMULATIVE_DAYS[0] = 0 is the start of January.
# Used for fast hour_of_year -> month lookup.
_MONTH_LENGTHS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_CUMULATIVE_DAYS = []
_running = 0
for _len in _MONTH_LENGTHS:
    _CUMULATIVE_DAYS.append(_running)
    _running += _len
# _CUMULATIVE_DAYS == [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]


def hour_to_calendar(hour_of_year: int) -> tuple[int, int, int]:
    """Convert hour-of-year (0..8759) to (hour_of_day, day_of_week, month).

    Parameters
    ----------
    hour_of_year : int
        0..8759 inclusive.

    Returns
    -------
    tuple
        hour_of_day : int  in 0..23
        day_of_week : int  0=Sunday .. 6=Saturday  (Israeli convention)
        month       : int  1..12
    """
    if not 0 <= hour_of_year < HOURS_IN_YEAR:
        raise ValueError(f"hour_of_year must be 0..{HOURS_IN_YEAR-1}, got {hour_of_year}")
    day_of_year = hour_of_year // 24
    hour_of_day = hour_of_year % 24
    day_of_week = day_of_year % 7        # day 0 is Sunday by convention
    # Resolve month: largest cumulative-days threshold that is <= day_of_year.
    month = 12
    for m_idx in range(11, -1, -1):
        if day_of_year >= _CUMULATIVE_DAYS[m_idx]:
            month = m_idx + 1
            break
    return hour_of_day, day_of_week, month


def hour_to_month(hour_of_year: int) -> int:
    """Convenience: just the month for an hour-of-year."""
    return hour_to_calendar(hour_of_year)[2]


if __name__ == "__main__":
    # Sanity gate: print one row per month to confirm boundaries
    print(f"{'hour':>5}  {'day':>3}  {'hod':>3}  {'dow':>3}  {'month':>5}")
    for month_start_idx, start_day in enumerate(_CUMULATIVE_DAYS):
        hour = start_day * 24
        hod, dow, m = hour_to_calendar(hour)
        print(f"{hour:>5}  {start_day:>3}  {hod:>3}  {dow:>3}  {m:>5}")
    print("...")
    # Last hour of the year
    last = HOURS_IN_YEAR - 1
    hod, dow, m = hour_to_calendar(last)
    print(f"{last:>5}  {last//24:>3}  {hod:>3}  {dow:>3}  {m:>5}")
