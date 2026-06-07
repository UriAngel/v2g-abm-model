"""Hourly electricity prices.

For W7 we use a single simple daily curve. The same price applies to
every day of the simulated week. From W8 onward we swap this for the
real TAOZ (Israel) and Octopus Agile (UK) tariffs, see v8 rules §11.

This is intentionally minimal — the goal of W7 is to demonstrate that
the V0 and V1G charging rules behave differently in response to the same
price signal.
"""


# Currency-agnostic for W7 — units are "per kWh"
PRICE_OFFPEAK = 0.10
PRICE_SHOULDER = 0.20
PRICE_PEAK = 0.45

# A V1G agent charges only if the current price is at or below this number
CHEAP_THRESHOLD_FOR_V1G = 0.20


def price_at_hour(hour_of_day: int) -> float:
    """Return the electricity price at a given hour of the day.

    Parameters
    ----------
    hour_of_day : int
        0 through 23 (midnight = 0, noon = 12).

    Returns
    -------
    float
        Price per kWh in whatever currency the scenario uses.

    Notes
    -----
    Schedule used in the W7 demo (placeholder, replaced in W8):
      00:00 - 06:59   off-peak   (0.10)
      07:00 - 16:59   shoulder   (0.20)
      17:00 - 22:59   peak       (0.45)
      23:00 - 23:59   off-peak   (0.10)
    """
    assert 0 <= hour_of_day <= 23, f"hour_of_day must be 0-23, got {hour_of_day}"

    if hour_of_day < 7 or hour_of_day >= 23:
        return PRICE_OFFPEAK
    if hour_of_day < 17:
        return PRICE_SHOULDER
    return PRICE_PEAK
