"""Hourly electricity prices.

Batch 1 (Sunday W7): swapped from placeholder values to the real
Israeli TAOZ summer schedule (v8 rules §11).  All prices are NIS per
kWh, VAT included.

This makes the demo's headline numbers come out in real shekels so
David can react to them on Monday.

Source: IEC TAOZ residential tariff, summer schedule.
"""


# Israeli TAOZ summer  (NIS per kWh, VAT included)
PRICE_OFFPEAK = 0.53      # 23:00-07:00 + daytime off
PRICE_SHOULDER = 0.85     # 07:00-17:00 weekdays
PRICE_PEAK = 1.69         # 17:00-23:00 Sun-Thu

# A V1G agent charges only if the current price is at or below this number.
# Set just at shoulder so V1G can charge at off-peak (0.53) or shoulder
# (0.85), but refuses at peak (1.69).
CHEAP_THRESHOLD_FOR_V1G = 0.85


def price_at_hour(hour_of_day: int) -> float:
    """Return the TAOZ summer electricity price at a given hour of the day.

    Parameters
    ----------
    hour_of_day : int
        0 through 23 (midnight = 0, noon = 12).

    Returns
    -------
    float
        Price per kWh in NIS (shekels), VAT included.

    Notes
    -----
    Schedule (TAOZ summer, v8 §11):
      00:00 - 06:59   off-peak    (0.53 NIS/kWh)
      07:00 - 16:59   shoulder    (0.85 NIS/kWh)
      17:00 - 22:59   peak        (1.69 NIS/kWh)
      23:00 - 23:59   off-peak    (0.53 NIS/kWh)
    """
    assert 0 <= hour_of_day <= 23, f"hour_of_day must be 0-23, got {hour_of_day}"

    if hour_of_day < 7 or hour_of_day >= 23:
        return PRICE_OFFPEAK
    if hour_of_day < 17:
        return PRICE_SHOULDER
    return PRICE_PEAK
