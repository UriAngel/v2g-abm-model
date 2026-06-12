"""Aggregator stub.

W8 update: now weekday-aware.  The TAOZ peak window applies only Sunday
through Thursday, so the aggregator only signals discharge on those days.
On Friday and Saturday the peak rate disappears and there is no point in
discharging for arbitrage.

Israeli weekday convention: 0=Sunday ... 4=Thursday, 5=Friday, 6=Saturday.
"""


# Evening peak window — matches the IEC TAOZ summer schedule (17:00-23:00).
PEAK_DISCHARGE_START_HOUR = 17
PEAK_DISCHARGE_END_HOUR = 23   # exclusive — last discharge hour is 22

WEEKEND_DAYS = (5, 6)  # Friday and Saturday


def aggregator_signals_discharge(hour_of_day: int, day_of_week: int = 0) -> bool:
    """True if the aggregator wants V2G EVs to discharge right now.

    Parameters
    ----------
    hour_of_day : int
        0-23.
    day_of_week : int
        0=Sunday, 6=Saturday.  Defaults to Sunday for backward compatibility.

    Returns
    -------
    bool
        True only during the evening peak window on a TAOZ workday.
    """
    if day_of_week in WEEKEND_DAYS:
        return False
    return PEAK_DISCHARGE_START_HOUR <= hour_of_day < PEAK_DISCHARGE_END_HOUR
