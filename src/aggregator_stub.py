"""Aggregator stub.

Discharge signal mirrors the TAOZ peak window (17:00-23:00) every day.
The day_of_week argument is kept in the signature for forward
compatibility with future weekday-sensitive aggregator logic, but the
standard residential TAOZ peak applies the same way every day.

W8 Batch B adds the optional aggregator-retailer link.  When the gate is
enabled, the aggregator will only accept V2G transactions from EVs whose
household electricity retailer matches the aggregator's contracted
retailer.  When the gate is disabled, the aggregator is retailer-agnostic
and any household can participate.
"""


# Evening peak window — matches the IEC TAOZ summer schedule (17:00-23:00).
PEAK_DISCHARGE_START_HOUR = 17
PEAK_DISCHARGE_END_HOUR = 23   # exclusive — last discharge hour is 22


# -----------------------------------------------------------------------------
# Aggregator-retailer link (W8 Batch B)
# -----------------------------------------------------------------------------
# AGGREGATOR_CONTRACTED_RETAILER: the retailer brand that the V2G aggregator
# has a contract with.  In David's baseline design, only customers of this
# retailer can participate in V2G.
#
# RETAILER_GATE_ENABLED: master flag.
#   True  = tied model (David's baseline).
#           Only customers of AGGREGATOR_CONTRACTED_RETAILER can V2G.
#   False = independent-aggregator model.
#           Any household can participate regardless of retailer.

AGGREGATOR_CONTRACTED_RETAILER = "IEC"
RETAILER_GATE_ENABLED = True


# -----------------------------------------------------------------------------
# Aggregator business model (W8 Batch F)
# -----------------------------------------------------------------------------
# Driver pays the bidirectional charger CAPEX up front, then receives a
# share of every V2G discharge.  The aggregator keeps the residual share
# and earns no other income (we ignore fixed overhead for now).
#
# Reference costs:
#   Wallbox Quasar bidirectional unit  ~£5,500     (Sciurus 2021)
#   Installation + DNO approval       ~£500
#   Total charger CAPEX               ~£6,000  ~  28,000 NIS (at 4.7 NIS/GBP)
#
# Revenue split:
#   Default 25% to aggregator, 75% to driver.  Matches the public
#   reporting from Octopus Powerloop and other UK pilots (drivers
#   typically earn 60-80% of V2G margin).

CHARGER_CAPEX_NIS = 28_000.0
AGGREGATOR_REVENUE_SHARE = 0.25
DRIVER_REVENUE_SHARE = 1.0 - AGGREGATOR_REVENUE_SHARE


def aggregator_signals_discharge(hour_of_day: int, day_of_week: int = 0) -> bool:
    """True if the aggregator wants V2G EVs to discharge right now.

    Parameters
    ----------
    hour_of_day : int
        0-23.
    day_of_week : int
        Currently unused.  Kept for forward compatibility.

    Returns
    -------
    bool
        True during the evening peak window every day.
    """
    return PEAK_DISCHARGE_START_HOUR <= hour_of_day < PEAK_DISCHARGE_END_HOUR


def aggregator_accepts_retailer(agent_retailer: str) -> bool:
    """Return True if the aggregator will accept this agent's V2G energy.

    Always True when the retailer gate is disabled.  When the gate is
    enabled, returns True only if the agent's retailer matches the
    aggregator's contracted retailer.

    Parameters
    ----------
    agent_retailer : str
        The household's electricity retailer brand (e.g., "IEC",
        "Electra Power").  Sampled at EVAgent construction from
        RETAILER_MARKET_SHARES in ev_agent.py.

    Returns
    -------
    bool
    """
    if not RETAILER_GATE_ENABLED:
        return True
    return agent_retailer == AGGREGATOR_CONTRACTED_RETAILER
