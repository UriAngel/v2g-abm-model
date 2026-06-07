"""Aggregator stub — W7 Saturday version.

Rules §8 describe a full aggregator agent that reads fleet state, bids into
markets, and dispatches discharge signals. The full implementation lives in
Trinity W8-W9 once the EV agent is settled.

For W7 we only need ONE behaviour: tell each EV "discharge now" during the
evening peak window. That's enough to demonstrate V2G economics in the
single-EV demo and let David see V2G visibly differ from V1G.
"""


# Evening peak window — matches the §11 IL TAOZ_summer schedule (17:00-23:00),
# trimmed to 17-22 because the price curve in pricing.py drops to off-peak
# at 23:00.
PEAK_DISCHARGE_START_HOUR = 17
PEAK_DISCHARGE_END_HOUR = 22   # exclusive — last discharge hour is 21


def aggregator_signals_discharge(hour_of_day: int) -> bool:
    """True if the aggregator wants V2G EVs to discharge right now.

    Parameters
    ----------
    hour_of_day : int
        0-23.

    Returns
    -------
    bool
        True only during the evening peak window (17:00-22:00).
    """
    return PEAK_DISCHARGE_START_HOUR <= hour_of_day < PEAK_DISCHARGE_END_HOUR
