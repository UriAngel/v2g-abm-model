"""Hourly electricity prices.

Israeli TAOZ summer schedule (IEC 2024, residential).  The standard
residential TAOZ product applies the same time-of-use window every day,
including Friday and Saturday.  A separate "Shabbat and holiday" opt-in
tariff exists but is not modelled here.

All prices are NIS per kWh, VAT included.
"""


# Israeli TAOZ summer  (NIS per kWh, VAT included)
PRICE_OFFPEAK = 0.53      # 23:00-07:00
PRICE_SHOULDER = 0.85     # 07:00-17:00
PRICE_PEAK = 1.69         # 17:00-23:00 every day

# A V1G agent charges only if the current price is at or below this number.
# Set just at shoulder so V1G can charge at off-peak (0.53) or shoulder
# (0.85), but refuses at peak (1.69).
CHEAP_THRESHOLD_FOR_V1G = 0.85


def price_at_hour(hour_of_day: int, day_of_week: int = 0) -> float:
    """Return the TAOZ summer electricity price.

    Parameters
    ----------
    hour_of_day : int
        0 through 23 (midnight = 0, noon = 12).
    day_of_week : int
        Kept in the signature for forward compatibility with future
        weekday-sensitive tariffs (Shabbat-Chag, winter peak shift, etc.).
        Currently unused: the standard TAOZ summer schedule is the same
        every day.

    Returns
    -------
    float
        Price per kWh in NIS (shekels), VAT included.
    """
    assert 0 <= hour_of_day <= 23, f"hour_of_day must be 0-23, got {hour_of_day}"

    if hour_of_day < 7 or hour_of_day >= 23:
        return PRICE_OFFPEAK
    if hour_of_day < 17:
        return PRICE_SHOULDER
    return PRICE_PEAK
