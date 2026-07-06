"""Aggregator stub.

Discharge signal mirrors the residential TAOZ peak window for the
relevant season and day of the week.  The aggregator delegates to
pricing.price_at_hour rather than carrying its own peak-window logic, so
that any change to the TAOZ schedule in pricing.py propagates
automatically to the aggregator's behaviour.

An optional aggregator-retailer link is included.  When the gate is
enabled, the aggregator will only accept V2G transactions from EVs whose
household electricity retailer matches the aggregator's contracted
retailer.  When the gate is disabled, the aggregator is retailer-agnostic
and any household can participate.
"""

from src.pricing import price_at_hour, PRICE_PEAK


# -----------------------------------------------------------------------------
# Plot-only constants (summer weekday peak window).
# Kept so plotting code can shade the peak band on time-series figures.
# Do NOT use these to gate aggregator logic — use
# aggregator_signals_discharge(hour, day, month) instead, which handles
# the seasonal and weekend variation correctly.
# -----------------------------------------------------------------------------
PEAK_DISCHARGE_START_HOUR = 17   # summer weekday start
PEAK_DISCHARGE_END_HOUR   = 22   # summer weekday end (exclusive)


# -----------------------------------------------------------------------------
# Aggregator-retailer link
# -----------------------------------------------------------------------------
# AGGREGATOR_CONTRACTED_RETAILER: the retailer brand that the V2G aggregator
# has a contract with.  In the tied-retailer variant, only customers of
# this retailer can participate in V2G.
#
# RETAILER_GATE_ENABLED: master flag.
#   True  = tied-retailer model.
#           Only customers of AGGREGATOR_CONTRACTED_RETAILER can V2G.
#   False = independent-aggregator model.
#           Any household can participate regardless of retailer.

AGGREGATOR_CONTRACTED_RETAILER = "IEC"
# The independent-aggregator model is the working baseline; the
# tied-retailer variant is retained as a sensitivity option and does
# not feature in headline numbers.
RETAILER_GATE_ENABLED = False


# -----------------------------------------------------------------------------
# Aggregator business model
# -----------------------------------------------------------------------------
# Driver pays the bidirectional charger CAPEX up front, then receives a
# share of every V2G discharge.  The aggregator keeps the residual share
# and earns no other income (fixed overhead is ignored).
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

# -----------------------------------------------------------------------------
# Charger CAPEX (NIS at ~4.7 NIS/GBP)
# -----------------------------------------------------------------------------
# Smart unidirectional charger baseline for the V2G premium calculation:
# Ohme Home Pro / Zappi / Tesla Wall Connector range £400-£700 unit plus
# install £400-£500, minus £350 OZEV grant.  Net ~£700 = ~3,300 NIS.
#
# Bidirectional anchor: Sigenergy 25 kW bidirectional DC charger.
# Unit price from Sun Supply PV (US wholesale):  $2,720 USD
#   Sigenergy EVDC 25 kW (model 11080031, CCS1)
#   https://sunsuppv.com/product/sigenergy-evdc-charger-25kw/
#
# Currency assumptions used to derive landed/installed numbers below:
#   1 USD = 3.7 NIS   (June 2026 mid)
#   1 USD = 0.79 GBP
#   1 GBP = 4.7 NIS
#
# UK installed build-up:
#   Unit                     $2,720 -> £2,149
#   Shipping US -> UK         £250
#   VAT 20 % on landed       £480
#   Import duty (none)        £0
#   Install (DC bidirectional, more complex than 7 kW AC) £1,500
#   ----------------------------
#   UK installed             ~£4,400
#   At 4.7 NIS/GBP           ~20,700 NIS
#
# Israeli installed build-up:
#   Unit                     $2,720 -> 10,064 NIS
#   Shipping US -> Israel    $400 -> 1,480 NIS
#   VAT 17 % on landed       ~1,960 NIS
#   Import duty ~10 %        ~1,150 NIS
#   Install                  ~8,000 NIS
#   ----------------------------
#   Israeli installed        ~22,650 NIS
#
# 2028-30 mass-production scenario: industry projects bidirectional
# prices to fall substantially as the supply chain matures; assume
# unit + install fall ~50 %.
CHARGER_CAPEX_BIDIR_2024_UK_NIS  = 20_700.0   # Sigenergy UK installed
CHARGER_CAPEX_BIDIR_2024_NIS     = 22_650.0   # Sigenergy Israel installed
CHARGER_CAPEX_BIDIR_2028_NIS     = 11_325.0   # 2028 mass-production projection

# Smart unidirectional charger (net of grant) - the baseline the driver
# would invest in anyway to enable V1G operation
CHARGER_CAPEX_SMART_NIS       = 3_300.0

# V2G premium = bidirectional cost minus what the driver would already pay
# for a smart unidirectional charger.  This is the relevant number for
# V1G->V2G investment decisions (the marginal cost of going bidirectional).
V2G_PREMIUM_2024_NIS = CHARGER_CAPEX_BIDIR_2024_NIS - CHARGER_CAPEX_SMART_NIS   # ~32,400
V2G_PREMIUM_2028_NIS = CHARGER_CAPEX_BIDIR_2028_NIS - CHARGER_CAPEX_SMART_NIS   # ~9,700

# Default scenario for headline payback figures.  Override in plotting
# scripts that want to show the 2028-30 scenario.
CHARGER_CAPEX_NIS = CHARGER_CAPEX_BIDIR_2024_NIS   # default-scenario alias

AGGREGATOR_REVENUE_SHARE = 0.25
DRIVER_REVENUE_SHARE = 1.0 - AGGREGATOR_REVENUE_SHARE


def aggregator_signals_discharge(
    hour_of_day: int,
    day_of_week: int = 0,
    month: int = 7,
) -> bool:
    """True if the aggregator wants V2G EVs to discharge right now.

    The signal fires exactly when the prevailing TAOZ price is at the
    peak rate.  Delegating to pricing keeps the aggregator's peak
    window automatically consistent with the residential TAOZ schedule
    across seasons and weekend rules.

    Parameters
    ----------
    hour_of_day : int
        0-23.
    day_of_week : int
        0=Sunday, 6=Saturday.
    month : int
        1-12.  Default 7 (July) preserves the summer-only
        assumption when callers do not pass a month.

    Returns
    -------
    bool
        True when the current TAOZ band is פסגה (peak).
    """
    return price_at_hour(hour_of_day, day_of_week, month) == PRICE_PEAK


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
