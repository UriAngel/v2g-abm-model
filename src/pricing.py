"""Hourly electricity prices.

Israeli TAOZ summer schedule (IEC 2024, residential).  W8 update: now
weekday-aware.  Peak rates apply only Sunday through Thursday (working
days under Israeli convention).  Friday and Saturday have off-peak and
shoulder only, no peak.

Israeli weekday convention: 0=Sunday ... 4=Thursday, 5=Friday, 6=Saturday.

All prices are NIS per kWh, VAT included.
"""


# Israeli TAOZ summer  (NIS per kWh, VAT included)
PRICE_OFFPEAK = 0.53      # nights and most weekend hours
PRICE_SHOULDER = 0.85     # weekday daytime, also covers Fri/Sat afternoons
PRICE_PEAK = 1.69         # 17:00-23:00 Sunday through Thursday only

# A V1G agent charges only if the current price is at or below this number.
# Set just at shoulder so V1G can charge at off-peak (0.53) or shoulder
# (0.85), but refuses at peak (1.69).
CHEAP_THRESHOLD_FOR_V1G = 0.85

WEEKEND_DAYS = (5, 6)  # Friday and Saturday


def price_at_hour(hour_of_day: int, day_of_week: int = 0) -> float:
    """Return the TAOZ summer electricity price.

    Parameters
    ----------
    hour_of_day : int
        0 through 23 (midnight = 0, noon = 12).
    day_of_week : int
        0=Sunday, 6=Saturday.  Defaults to Sunday for backward compatibility.

    Returns
    -------
    float
        Price per kWh in NIS (shekels), VAT included.

    Notes
    -----
    Schedule (TAOZ summer, IEC 2024):
      00:00 - 06:59   off-peak    (0.53 NIS/kWh)  every day
      07:00 - 16:59   shoulder    (0.85 NIS/kWh)  every day
      17:00 - 22:59   peak        (1.69 NIS/kWh)  Sun-Thu only
                       shoulder    (0.85 NIS/kWh)  Fri-Sat
      23:00 - 23:59   off-peak    (0.53 NIS/kWh)  every day
    """
    assert 0 <= hour_of_day <= 23, f"hour_of_day must be 0-23, got {hour_of_day}"

    if hour_of_day < 7 or hour_of_day >= 23:
        return PRICE_OFFPEAK
    if hour_of_day < 17:
        return PRICE_SHOULDER
    # 17:00-22:59 evening window: peak on workdays, shoulder on weekends.
    if day_of_week in WEEKEND_DAYS:
        return PRICE_SHOULDER
    return PRICE_PEAK
