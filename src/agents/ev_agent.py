"""EV Agent — implements §3 of the rules document.

Key behavioural features:
  * Gaussian commute jitter (std 0.5h, Brinkel 2020).
  * Log-normal daily km (sigma 0.6, Liao 2025).
  * Weekend factor: Friday and Saturday (Israeli convention) use a shorter
    midday commute (11:00 to 17:00) and reduced km (factor 0.5).
  * Threshold Charger plugs in only when SoC falls below charge_threshold
    (0.461, Wong 2026 Table 1 "Mean SoC at plug-in"), and stays plugged in
    until target_soc (0.85, Wong Table 1 "Mean SoC after charge") is
    reached. Daily Charger by contrast plugs in whenever the vehicle is
    at home, regardless of current SoC.
  * Day-of-week is passed to pricing and aggregator so peak rates and
    discharge signals apply only Sunday through Thursday (TAOZ summer).

Day-of-week convention (Israeli): 0=Sunday ... 4=Thursday, 5=Friday, 6=Saturday.
The simulation week starts on Sunday hour 0.
"""

import math
import random
from dataclasses import dataclass

from src.pricing import (
    price_at_hour,
    CHEAP_THRESHOLD_FOR_V1G,
    PRICE_OFFPEAK,
    PRICE_PEAK,
)
from src.battery_aging import (
    calendar_aging_this_hour,
    cycle_aging_this_hour,
)
from src.vehicle_catalog import (
    VEHICLE_CATALOG,
    sample_vehicle,
)


# -----------------------------------------------------------------------------
# Typology — the four driver categories from Wong 2026 (rules §3.1)
# -----------------------------------------------------------------------------

DAILY_CHARGER = "Daily Charger"
PUBLIC_CHARGER = "Public Charger"
BEV_2ND_VEHICLE = "BEV 2nd Vehicle"
THRESHOLD_CHARGER = "Threshold Charger"

ALL_TYPOLOGIES = (
    DAILY_CHARGER,
    PUBLIC_CHARGER,
    BEV_2ND_VEHICLE,
    THRESHOLD_CHARGER,
)


# -----------------------------------------------------------------------------
# Per-typology default profiles (rules §3.1 + §3.2)
# -----------------------------------------------------------------------------
# Each profile describes a "typical" agent of that driver type. Individual
# agents get a random jitter applied at construction so they aren't all
# identical.

TYPOLOGY_PROFILES = {
    DAILY_CHARGER: {
        # Plugs in every time the vehicle is at home, regardless of current SoC.
        "daily_km_mean": 40.0,        # km/day, weekday
        "departure_hour_mean": 8,     # 08:00 morning out
        "return_hour_mean":   18,     # 18:00 evening back
        "drive_days_per_week": 6.43,  # Wong 2026 Table 1
        "drives_on_weekend":  True,
        "battery_kwh_usable": 60.0,
        "has_home_charger":  True,
        "target_soc":        0.892,   # Wong 2026 Table 1: Mean SoC after charge
        "starting_soc":      0.85,
        "charge_threshold":  0.0,     # 0 = no threshold; always plug in when home
        # Wong 2026 Table 1 "Mean number of charging events per week"
        # for the Daily Charger cluster is 6.11.  That is FEWER than the
        # 6.43 driving days per week, so even Daily Chargers do not plug in
        # every single home evening.  Modelled stochastically: probability
        # of plugging in on a given home evening = 6.11 / 7 = 0.873.
        "plugin_events_per_week": 6.11,
        # Annual V2G discharge per Wong 2026 Fig 5 mean.
        "annual_v2g_kwh_cap": 1259.0,
    },
    PUBLIC_CHARGER: {
        # Wong 2026: Public Chargers "lack home charging access and rely
        # primarily on DC fast charging from public chargers".  They
        # charge to 80 % SOC at public DC chargers, infrequently.
        # No home charger -> structurally cannot V2G.  This understates
        # Wong's small 111 kWh/yr V2G observation, but matches the
        # dominant Wong characterisation.
        "daily_km_mean": 48.0,
        "departure_hour_mean": 7,
        "return_hour_mean":   19,
        "drive_days_per_week": 6.41,  # Wong 2026 Table 1
        "drives_on_weekend":  True,
        "battery_kwh_usable": 60.0,
        "has_home_charger":  False,
        "has_workplace_charger": True,
        "target_soc":        0.747,   # Wong 2026 Table 1: Mean SoC after charge
        "starting_soc":      0.80,
        "charge_threshold":  0.0,
        "annual_v2g_kwh_cap": 111.0,  # Wong 2026 Fig 5; cap gate not applied
    },
    BEV_2ND_VEHICLE: {
        # Wong 2026 Table 1: 4.74 drive days per week, modelled
        # probabilistically (drive each day with probability 4.74 / 7).
        "daily_km_mean": 22.0,
        "departure_hour_mean": 10,
        "return_hour_mean":   16,
        "drive_days_per_week": 4.74,  # Wong 2026 Table 1
        "drives_on_weekend":  True,
        "battery_kwh_usable": 60.0,
        "has_home_charger":  True,
        "target_soc":        0.87,    # Wong 2026 Table 1: Mean SoC after charge
        "starting_soc":      0.80,
        "charge_threshold":  0.0,
        # Plug-in probability aligned with the Daily Charger
        # (Wong Table 1: 6.11 events/week = 87 %), so both active
        # typologies share a single plug-in calibration.
        "plugin_events_per_week": 6.11,
        "annual_v2g_kwh_cap": 576.0,   # Wong 2026 Fig 5
    },
    THRESHOLD_CHARGER: {
        # Plugs in only when SoC < charge_threshold, charges to target_soc,
        # then unplugs.  All three numbers from Wong 2026 Table 1.
        "daily_km_mean": 38.0,
        "departure_hour_mean": 8,
        "return_hour_mean":   18,
        "drive_days_per_week": 6.44,  # Wong 2026 Table 1
        "drives_on_weekend":  True,
        "battery_kwh_usable": 60.0,
        "has_home_charger":  True,
        "target_soc":        0.85,    # Wong 2026 Table 1: Mean SoC after charge
        "starting_soc":      0.50,
        "charge_threshold":  0.461,   # Wong 2026 Table 1: Mean SoC at plug-in
        "annual_v2g_kwh_cap": 204.0,   # Wong 2026 Fig 5
    },
}

# Israeli weekday convention: 0=Sunday ... 4=Thursday, 5=Friday, 6=Saturday.
WEEKEND_DAYS = (5, 6)
WEEKEND_KM_FACTOR = 0.5       # weekend trip kms = weekday × this
WEEKEND_DEPARTURE_HOUR = 11   # midday weekend trip start
WEEKEND_RETURN_HOUR = 17      # midday weekend trip end (before peak)

# Randomness parameters:
COMMUTE_JITTER_STD_HOURS = 0.5     # Brinkel 2020, Gandhi 2021
DAILY_KM_LOG_SIGMA = 0.6           # Liao 2025 (Chinese sample, transferred)

# Master toggle for the SEM behavioural layer.  When False, the SEM is
# bypassed: every V2G-capable agent opts in and uses a flat OSP of 1.00.
# Useful for ablation studies and the SEM-effect comparison plot.
SEM_ENABLED = True
SEM_DISABLED_FLAT_OSP = 1.00


# -----------------------------------------------------------------------------
# Behavioural willingness — SEM coefficients (Mehdizadeh-style 5-factor model)
# -----------------------------------------------------------------------------
# Coefficients taken from the Norwegian V2G acceptance SEM (Mehdizadeh 2024
# or equivalent).  Five latent attitudinal factors are sampled per agent from
# N(0, 1) (the standard SEM convention) and combined into Attitude and
# Intention by the path weights below.
#
# Attitude  = a_T * Trust + a_U * Usefulness + a_B * BatteryConcern
#           + a_E * EaseOfUse + a_S * SubjNorm
# Intention = b_T * Trust + b_A * Attitude + b_S * SubjNorm

SEM_ATTITUDE_FROM_TRUST            = 0.205
SEM_ATTITUDE_FROM_USEFULNESS       = 0.391
SEM_ATTITUDE_FROM_BATTERY_CONCERN  = -0.177
SEM_ATTITUDE_FROM_EASE_OF_USE      = 0.255
SEM_ATTITUDE_FROM_SUBJECTIVE_NORM  = 0.347

SEM_INTENTION_FROM_TRUST           = 0.388
SEM_INTENTION_FROM_ATTITUDE        = 0.174
SEM_INTENTION_FROM_SUBJECTIVE_NORM = 0.409


def compute_attitude(trust: float, usefulness: float, battery_concern: float,
                     ease_of_use: float, subjective_norm: float) -> float:
    return (
        SEM_ATTITUDE_FROM_TRUST            * trust
        + SEM_ATTITUDE_FROM_USEFULNESS       * usefulness
        + SEM_ATTITUDE_FROM_BATTERY_CONCERN  * battery_concern
        + SEM_ATTITUDE_FROM_EASE_OF_USE      * ease_of_use
        + SEM_ATTITUDE_FROM_SUBJECTIVE_NORM  * subjective_norm
    )


def compute_intention(trust: float, attitude: float, subjective_norm: float) -> float:
    return (
        SEM_INTENTION_FROM_TRUST           * trust
        + SEM_INTENTION_FROM_ATTITUDE        * attitude
        + SEM_INTENTION_FROM_SUBJECTIVE_NORM * subjective_norm
    )


def intention_to_osp(intention: float, country: str = "Israel") -> float:
    """Map a continuous Intention score to a per-agent OSP, bounded by the
    country's residential V2G price envelope.

    Israel: bounds are the residential TAOZ off-peak and peak rates,
    so OSP lies in [0.53, 1.69] NIS/kWh.

    United Kingdom: bounds are Octopus Go off-peak (cheap charging) and
    the Octopus Powerloop export rate (V2G revenue per kWh).  This
    anchors the UK OSP to the actual envelope the driver experiences
    rather than rescaling from NIS, and keeps the V2G discharge
    decision feasible at realistic UK retail tariffs.

    Note: battery aging is NOT folded into the OSP or the discharge
    gate; it is tracked physically and reported post hoc (see
    battery_aging.py docstrings).
    """
    if country in ("UK", "United Kingdom"):
        from src.pricing_uk import OCTOPUS_GO_OFFPEAK_GBP, POWERLOOP_EXPORT_GBP
        low_bound, high_bound = OCTOPUS_GO_OFFPEAK_GBP, POWERLOOP_EXPORT_GBP
    else:
        low_bound, high_bound = PRICE_OFFPEAK, PRICE_PEAK
    sigmoid = 1.0 / (1.0 + math.exp(-intention))
    # sigmoid in (0, 1).  Map so that high intention -> low OSP.
    return high_bound - (high_bound - low_bound) * sigmoid


# -----------------------------------------------------------------------------
# Israeli residential retailers — market shares after the July 2024 reform
# -----------------------------------------------------------------------------
# IEC dominates with about 70 percent of residential supply; the rest is
# divided across eight active alternative suppliers.  Source: PUA 2024
# Electricity Authority annual report, post-reform figures.

RETAILER_MARKET_SHARES = {
    "IEC":            0.70,
    "Electra Power":  0.05,
    "Pazgaz":         0.05,
    "Cellcom":        0.04,
    "Bezeq":          0.04,
    "Hot":            0.03,
    "Partner":        0.03,
    "Mashav":         0.03,
    "Amisragas":      0.03,
}


def sample_retailer(rng: random.Random) -> str:
    """Draw a retailer name from RETAILER_MARKET_SHARES."""
    names = list(RETAILER_MARKET_SHARES.keys())
    weights = list(RETAILER_MARKET_SHARES.values())
    return rng.choices(names, weights=weights, k=1)[0]


# -----------------------------------------------------------------------------
# Counterfactuals (rules §0)
# -----------------------------------------------------------------------------

COUNTERFACTUAL_V0 = "V0"     # naive: charge any time plugged in until full
COUNTERFACTUAL_V1G = "V1G"   # smart: defer to off-peak prices
COUNTERFACTUAL_V2G = "V2G"   # active: V1G plus selling back to grid


# -----------------------------------------------------------------------------
# Physical constants (rules §3.5)
# -----------------------------------------------------------------------------

CONSUMPTION_KWH_PER_KM = 0.18
V2G_SOC_FLOOR = 0.50         # §3.6  contractual minimum SoC for V2G discharge
# V2G-opted-in aggregator cap (Sciurus / Kaluza mobile-app pattern,
# Kempton & Tomic 2005 battery-longevity guidance, Wong 2026 Table 1
# observed 89.2 %).  Non-opted-in agents charge to 100 %.
V2G_MAX_SOC = 0.90

# -----------------------------------------------------------------------------
# V1G departure-aware top-up rule (Section 3.7)
# -----------------------------------------------------------------------------
# During the long overnight parked period the V1G agent targets a reduced
# state of charge (V1G_OVERNIGHT_TARGET_SOC) to slow calendar aging.  In the
# final V1G_RAMP_HOURS_BEFORE_DEPARTURE hours before the morning departure
# the rule reverts to the typology's normal target_soc so the agent leaves
# with full range.  Per Wong et al. (2026) Daily Chargers target ~89 %; the
# 70 % overnight floor cuts daily calendar exposure by roughly a fifth.
V1G_OVERNIGHT_TARGET_SOC          = 0.70
V1G_RAMP_HOURS_BEFORE_DEPARTURE   = 2


# -----------------------------------------------------------------------------
# State variables (rules §3.4)
# -----------------------------------------------------------------------------

@dataclass
class EVAgentState:
    """All persistent state for one EV agent, updated every hour."""

    # --- Battery (chemistry from sampled vehicle) ---
    soc: float = 0.80
    soh: float = 1.00
    battery_kwh_usable: float = 60.0
    chemistry: str = "NMC"
    vehicle_model: str = "Tesla Model Y NMC"   # set at agent init from country market shares
    # Aging accounting
    cumulative_throughput_kwh: float = 0.0     # |charge| + |discharge| over the run
    cumulative_v2g_discharge_kwh: float = 0.0  # V2G discharge only
    cumulative_calendar_aging: float = 0.0     # SoH lost to calendar aging
    cumulative_cycle_aging: float = 0.0        # SoH lost to cycling
    annual_v2g_kwh_cap: float = 9999.0         # Wong-anchored (Fig 5)

    # --- Power limits ---
    max_charge_power_kw: float = 7.0
    max_discharge_power_kw: float = 9.6
    charging_efficiency_c: float = 0.95
    charging_efficiency_d: float = 0.95
    v2g_capable: bool = False

    # --- Position and plug-in ---
    plugged_in: bool = False
    location: str = "home"
    has_home_charger: bool = True
    has_workplace_charger: bool = False

    # --- Daily driving (per-instance, derived from typology + jitter) ---
    daily_km_today: float = 40.0
    daily_km_mean: float = 40.0
    drives_today: bool = True
    drive_days_per_week: int = 7
    drives_on_weekend: bool = True
    # Today's actual commute hours (may differ from weekday on weekends)
    departure_hour: int = 8
    return_hour: int = 18
    # Agent's baseline weekday commute hours, set at init and reused
    weekday_departure_hour: int = 8
    weekday_return_hour: int = 18

    # --- Charging targets ---
    target_soc: float = 0.89
    charge_threshold: float = 0.0      # 0 = plug in any time; >0 = Threshold Charger behaviour
    # Fewer than 7 plug-in events per week even for Daily Chargers
    # (Wong 2026 Table 1).  7.0 = plug in every home night.
    plugin_events_per_week: float = 7.0

    # --- Behaviour ---
    range_anxiety_soc_floor: float = 0.30
    osp: float = 0.0
    v2g_opted_in: bool = False

    # --- Retail relationship ---
    retailer: str = "IEC"

    # --- Latent attitudinal scores (Mehdizadeh-style SEM) ---
    # Each is a z-score drawn from N(0, 1) at agent creation.  They feed
    # into Attitude and Intention via the path coefficients in the SEM.
    trust_in_v2g: float = 0.0
    perceived_usefulness: float = 0.0
    battery_concern: float = 0.0
    perceived_ease_of_use: float = 0.0
    subjective_norm: float = 0.0
    attitude_towards_v2g: float = 0.0
    intention_to_use_v2g: float = 0.0


# -----------------------------------------------------------------------------
# The EVAgent class
# -----------------------------------------------------------------------------

class EVAgent:
    """One electric vehicle in the simulation.

    Parameters
    ----------
    agent_id : int
        Unique identifier within the simulation.  Also used to seed this
        agent's personal random number generator so its commute jitter and
        per-day km variation are reproducible.
    typology : str
        One of ALL_TYPOLOGIES.
    counterfactual : str
        One of "V0", "V1G", "V2G".
    """

    def __init__(self, agent_id: int, typology: str, counterfactual: str, country: str = "Israel",
                 run_seed: int = 0):
        # Identity + validation
        assert typology in ALL_TYPOLOGIES, f"unknown typology {typology!r}"
        assert counterfactual in (COUNTERFACTUAL_V0,
                                  COUNTERFACTUAL_V1G,
                                  COUNTERFACTUAL_V2G), \
            f"unknown counterfactual {counterfactual!r}"
        self.id = agent_id
        self.typology = typology
        self.counterfactual = counterfactual
        self.country = country

        # Per-agent random number generator, seeded by run_seed + id + typology.
        # run_seed lets Monte Carlo runs draw genuinely different
        # realisations while staying fully reproducible (same run_seed + same
        # parameters -> identical simulation).  run_seed=0 gives the
        # single-realisation baseline.
        seed_int = run_seed * 10_000_000 + agent_id * 1000 + ALL_TYPOLOGIES.index(typology)
        self._rng = random.Random(seed_int)

        # Pull the typology profile and apply it to the agent's state
        profile = TYPOLOGY_PROFILES[typology]

        # Sample this agent's vehicle from the country's
        # market-share distribution.  Vehicle dictates battery capacity
        # and chemistry, overriding the typology default of 60 kWh.
        vehicle_model = sample_vehicle(self._rng, country=country)
        vehicle_spec = VEHICLE_CATALOG[vehicle_model]

        self.state = EVAgentState(
            battery_kwh_usable=vehicle_spec["battery_kwh"],
            chemistry=vehicle_spec["chemistry"],
            vehicle_model=vehicle_model,
            has_home_charger=profile["has_home_charger"],
            has_workplace_charger=profile.get("has_workplace_charger", False),
            target_soc=profile["target_soc"],
            charge_threshold=profile["charge_threshold"],
            plugin_events_per_week=profile.get("plugin_events_per_week", 7.0),
            daily_km_mean=profile["daily_km_mean"],
            drive_days_per_week=profile["drive_days_per_week"],
            drives_on_weekend=profile["drives_on_weekend"],
            soc=profile["starting_soc"],
            annual_v2g_kwh_cap=profile.get("annual_v2g_kwh_cap", 9999.0),
        )

        # Per-agent commute jitter, Gaussian std 0.5h (Brinkel 2020, Gandhi 2021).
        # Drawn once per agent at instantiation, then reused for every weekday.
        d_jitter = round(self._rng.gauss(0.0, COMMUTE_JITTER_STD_HOURS))
        r_jitter = round(self._rng.gauss(0.0, COMMUTE_JITTER_STD_HOURS))
        self.state.weekday_departure_hour = profile["departure_hour_mean"] + d_jitter
        self.state.weekday_return_hour = profile["return_hour_mean"] + r_jitter
        # Safety clip — make sure departure is before return
        if self.state.weekday_return_hour <= self.state.weekday_departure_hour:
            self.state.weekday_return_hour = self.state.weekday_departure_hour + 6
        # Today's commute hours start as the weekday values; _start_new_day
        # overrides them on weekends.
        self.state.departure_hour = self.state.weekday_departure_hour
        self.state.return_hour = self.state.weekday_return_hour

        # --- SEM-based behavioural willingness ---
        # Draw five latent attitudinal scores per agent as z-scores from
        # N(0, 1) (standard SEM convention).  Combine into Attitude and
        # Intention using the path coefficients from the Mehdizadeh-style SEM.
        self.state.trust_in_v2g           = self._rng.gauss(0.0, 1.0)
        self.state.perceived_usefulness   = self._rng.gauss(0.0, 1.0)
        self.state.battery_concern        = self._rng.gauss(0.0, 1.0)
        self.state.perceived_ease_of_use  = self._rng.gauss(0.0, 1.0)
        self.state.subjective_norm        = self._rng.gauss(0.0, 1.0)

        self.state.attitude_towards_v2g = compute_attitude(
            trust            = self.state.trust_in_v2g,
            usefulness       = self.state.perceived_usefulness,
            battery_concern  = self.state.battery_concern,
            ease_of_use      = self.state.perceived_ease_of_use,
            subjective_norm  = self.state.subjective_norm,
        )
        self.state.intention_to_use_v2g = compute_intention(
            trust            = self.state.trust_in_v2g,
            attitude         = self.state.attitude_towards_v2g,
            subjective_norm  = self.state.subjective_norm,
        )

        # V2G setup — only relevant for the V2G counterfactual.  Public
        # Chargers cannot V2G because they have no home charger.
        # Opt-in and OSP depend on SEM_ENABLED:
        #   SEM_ENABLED = True  -> opt-in if Intention > 0; OSP from sigmoid
        #   SEM_ENABLED = False -> opt-in always; OSP = SEM_DISABLED_FLAT_OSP
        if counterfactual == COUNTERFACTUAL_V2G and self.state.has_home_charger:
            self.state.v2g_capable = True
            if SEM_ENABLED:
                self.state.v2g_opted_in = self.state.intention_to_use_v2g > 0.0
                base_osp = intention_to_osp(self.state.intention_to_use_v2g, country=self.country)
            else:
                self.state.v2g_opted_in = True
                base_osp = SEM_DISABLED_FLAT_OSP
            # Aging cost is not baked into the OSP.  The driver's OSP is
            # the pure SEM-derived value (intention -> NIS).  Battery
            # aging is tracked as a physical consequence of operation and
            # reported as SoH at year 1 / 5 / 10 milestones (see
            # battery_aging.soh_after_years), not folded into prices.
            # This matches how Sciurus and Wong frame V2G aging in their
            # public reporting.
            self.state.osp = base_osp
            self.state.max_discharge_power_kw = 9.6

        # Sample this agent's electricity retailer from realistic Israeli
        # market shares (recorded per agent; available to retailer-level
        # analyses).
        self.state.retailer = sample_retailer(self._rng)

        # Sample today's driving for day 0
        self._start_new_day(day_of_week=0)

        # Hour-by-hour log
        self.hourly_log: list[dict] = []

    # ------------------------------------------------------------------
    # New-day sampling
    # ------------------------------------------------------------------
    def _start_new_day(self, day_of_week: int) -> None:
        """Decide whether the agent drives today, when, and how far.

        Called at the start of each simulated day (hour_of_day == 0).

        Israeli weekday convention: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu,
        5=Fri, 6=Sat.  Working days are Sun-Thu (0-4).

        Drive-days are now sampled probabilistically per day: each day,
        drive with probability `drive_days_per_week / 7`, matching the
        Wong 2026 Table 1 count in expectation.
        """
        is_weekend = day_of_week in WEEKEND_DAYS

        # Probabilistic drive-day decision based on Wong 2026 drive_days/wk.
        drive_probability = self.state.drive_days_per_week / 7.0
        will_drive = self._rng.random() < drive_probability

        # Typologies that explicitly don't drive on weekends override to False.
        if is_weekend and not self.state.drives_on_weekend:
            will_drive = False

        self.state.drives_today = will_drive

        # Set today's commute hours.  On weekends, use a shorter midday trip;
        # on weekdays, use the agent's personal weekday hours set at init.
        if self.state.drives_today and is_weekend:
            self.state.departure_hour = WEEKEND_DEPARTURE_HOUR
            self.state.return_hour = WEEKEND_RETURN_HOUR
        else:
            self.state.departure_hour = self.state.weekday_departure_hour
            self.state.return_hour = self.state.weekday_return_hour

        # Sample today's km from a log-normal distribution (Liao 2025).
        # The log-space sigma is 0.6.  Real-space mean is daily_km_mean.
        # For log-normal with desired arithmetic mean M and log-space sigma s,
        # mu = ln(M) - s**2 / 2.
        if self.state.drives_today:
            sigma = DAILY_KM_LOG_SIGMA
            mu = math.log(self.state.daily_km_mean) - 0.5 * sigma * sigma
            km = self._rng.lognormvariate(mu, sigma)
            if is_weekend:
                km *= WEEKEND_KM_FACTOR
            self.state.daily_km_today = km
        else:
            self.state.daily_km_today = 0.0

    # ------------------------------------------------------------------
    # Public step method — called once per simulated hour
    # ------------------------------------------------------------------
    def step(
        self,
        current_hour: int,
        current_price_per_kwh: float,
        month: int = 7,
        discharge_revenue_per_kwh: float | None = None,
    ) -> None:
        """Advance the agent by one simulated hour.

        The optional ``month`` argument (1..12, default 7 = July summer)
        is forwarded to the V2G discharge decision so the aggregator can
        evaluate the seasonal TAOZ peak window correctly over an annual
        horizon.  Defaulting to 7 keeps summer-only weekly runs
        unchanged.

        ``discharge_revenue_per_kwh`` allows the import price
        (used for charging) to differ from the export price (revenue per
        kWh discharged).  This matters for UK runs where the driver
        charges on Octopus Go but is paid the Powerloop export rate for
        V2G discharge.  When None (default), the Israeli convention of
        same-price for import and export at the residential meter is
        preserved.
        """
        hour_of_day = current_hour % 24
        day_of_week = (current_hour // 24) % 7
        self._current_month = month   # consumed by _rule_v2g
        self._current_hour_global = current_hour   # consumed by FeederAgent check
        self._current_export_price = (
            discharge_revenue_per_kwh
            if discharge_revenue_per_kwh is not None
            else current_price_per_kwh
        )

        # At the start of each day, decide whether to drive and how far
        if hour_of_day == 0:
            self._start_new_day(day_of_week)

        # Step A — mobility
        action_mobility = self._step_mobility(hour_of_day, day_of_week)

        # Step B — charging/discharging decision (only if not driving)
        if action_mobility == "DRIVING":
            energy_kwh = 0.0
            cost = 0.0
            action_charge = "DRIVING"
        else:
            action_charge, energy_kwh, cost = self._step_charging_decision(
                hour_of_day=hour_of_day,
                day_of_week=day_of_week,
                price_per_kwh=current_price_per_kwh,
            )

        # Step C — battery health (chemistry-aware).
        cal_loss = calendar_aging_this_hour(self.state.soc)
        cyc_loss = cycle_aging_this_hour(energy_kwh, self.state.chemistry)
        self.state.cumulative_calendar_aging += cal_loss
        self.state.cumulative_cycle_aging   += cyc_loss
        self.state.cumulative_throughput_kwh += abs(energy_kwh)
        self.state.soh = max(0.0, self.state.soh - cal_loss - cyc_loss)

        # Step D — log
        self.hourly_log.append({
            "hour": current_hour,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "typology": self.typology,
            "counterfactual": self.counterfactual,
            "location": self.state.location,
            "plugged_in": self.state.plugged_in,
            "soc": round(self.state.soc, 4),
            "soh": round(self.state.soh, 6),
            "action": action_charge,
            "energy_kwh": round(energy_kwh, 4),
            "price_per_kwh": current_price_per_kwh,
            "cost_currency": round(cost, 4),
        })

    # ------------------------------------------------------------------
    # Step A — mobility
    # ------------------------------------------------------------------
    def _step_mobility(self, hour_of_day: int, day_of_week: int) -> str:
        """Move the car.  Returns one of: 'DRIVING', 'AT_HOME', 'AT_WORK'."""
        if self._is_driving_now(hour_of_day):
            self.state.plugged_in = False
            self.state.location = "driving"
            km_this_hour = self.state.daily_km_today / 2.0
            kwh_consumed = (km_this_hour * CONSUMPTION_KWH_PER_KM) / self.state.soh
            soc_drop = kwh_consumed / self.state.battery_kwh_usable
            self.state.soc = max(0.0, self.state.soc - soc_drop)
            return "DRIVING"

        is_weekend = day_of_week in WEEKEND_DAYS

        # Agent is at home if (a) outside commute hours, or (b) not driving today.
        at_home = (
            (not self.state.drives_today)
            or hour_of_day >= self.state.return_hour
            or hour_of_day < self.state.departure_hour
        )
        if at_home:
            self.state.location = "home"
            self.state.plugged_in = self._decide_home_plug_in()
            return "AT_HOME"

        # Otherwise the agent is at work (only meaningful for Public Charger).
        self.state.location = "work"
        self.state.plugged_in = self.state.has_workplace_charger
        return "AT_WORK"

    def _decide_home_plug_in(self) -> bool:
        """Plug-in decision while at home.

        Even Daily Chargers do not plug in every home evening.
        Wong 2026 Table 1 reports 6.11 charging events per week for the
        Daily Charger cluster.  We model this by drawing ONCE per day
        (on the first home-hour of that day) whether the agent will
        plug in tonight, with probability plugin_events_per_week / 7.
        The decision persists for the rest of the day.

        Threshold Charger: plug in only once SoC has fallen below
        charge_threshold, then stay plugged in until target_soc is
        reached, then unplug.  This behaviour is unaffected by the
        Wong-Table-1 probability draw.
        """
        if not self.state.has_home_charger:
            return False

        # Threshold Charger branch first: hysteresis rule dominates.
        if self.state.charge_threshold > 0.0:
            if self.state.plugged_in:
                return self.state.soc < self.state.target_soc
            return self.state.soc < self.state.charge_threshold

        # Daily Charger / BEV 2nd Vehicle branch.
        # One Bernoulli draw per day for whether to plug in tonight.
        if self.state.plugin_events_per_week >= 7.0:
            return True   # plug in every home night
        current_day = getattr(self, "_current_hour_global", 0) // 24
        last_decision_day = getattr(self, "_last_plugin_decision_day", -1)
        if current_day != last_decision_day:
            p = self.state.plugin_events_per_week / 7.0
            self._plugin_decision_today = self._rng.random() < p
            self._last_plugin_decision_day = current_day
        return self._plugin_decision_today

    def _is_driving_now(self, hour_of_day: int) -> bool:
        """True for the single outbound hour and single inbound hour each day,
        provided the agent is driving today at all."""
        if not self.state.drives_today:
            return False
        return hour_of_day in (self.state.departure_hour,
                               self.state.return_hour - 1)

    # ------------------------------------------------------------------
    # Step B — charge / discharge decision
    # ------------------------------------------------------------------
    def _step_charging_decision(
        self,
        hour_of_day: int,
        day_of_week: int,
        price_per_kwh: float,
    ) -> tuple[str, float, float]:
        if not self.state.plugged_in:
            return "IDLE", 0.0, 0.0

        if self.counterfactual == COUNTERFACTUAL_V0:
            return self._rule_v0(price_per_kwh)
        if self.counterfactual == COUNTERFACTUAL_V1G:
            return self._rule_v1g(hour_of_day, price_per_kwh)
        if self.counterfactual == COUNTERFACTUAL_V2G:
            return self._rule_v2g(hour_of_day, day_of_week, price_per_kwh)
        raise ValueError(f"unknown counterfactual {self.counterfactual!r}")

    def _rule_v0(self, price_per_kwh: float) -> tuple[str, float, float]:
        if self.state.soc < 1.0:
            return self._do_charge(price_per_kwh)
        return "IDLE", 0.0, 0.0

    def _v1g_current_target_soc(self, hour_of_day: int) -> float:
        """Country-aware V1G target SoC (Section 3.7).

        Israel: under residential 2-band TAOZ the off-peak window is
        broad (everything outside 17-22 in summer Sun-Thu).  The agent
        targets V1G_OVERNIGHT_TARGET_SOC (0.70) through the overnight
        idle window and ramps to the typology target_soc in the final
        V1G_RAMP_HOURS_BEFORE_DEPARTURE hours before departure.  This
        reduces calendar aging without sacrificing departure range.

        United Kingdom: under Octopus Go the off-peak window is short
        (00:00-05:00, rounded from 00:30-04:30).  Aligning the V1G
        top-up with the cheap window matters more than the calendar-
        aging optimisation, so the agent fills to typology target_soc
        throughout the off-peak window regardless of departure time.
        Outside the off-peak window, the agent holds at the overnight
        floor.
        """
        if self.country in ("UK", "United Kingdom"):
            from src.pricing_uk import (
                OCTOPUS_GO_OFFPEAK_START_HOUR,
                OCTOPUS_GO_OFFPEAK_END_HOUR,
            )
            in_off_peak = (
                OCTOPUS_GO_OFFPEAK_START_HOUR
                <= hour_of_day
                < OCTOPUS_GO_OFFPEAK_END_HOUR
            )
            if in_off_peak:
                return self.state.target_soc
            return min(V1G_OVERNIGHT_TARGET_SOC, self.state.target_soc)

        # Israel (default): departure-aware ramp.
        dep = self.state.departure_hour
        hours_to_dep = (dep - hour_of_day) % 24
        if 0 < hours_to_dep <= V1G_RAMP_HOURS_BEFORE_DEPARTURE:
            return self.state.target_soc
        return min(V1G_OVERNIGHT_TARGET_SOC, self.state.target_soc)

    def _rule_v1g(self, hour_of_day: int, price_per_kwh: float) -> tuple[str, float, float]:
        # Priority 1 — emergency floor (range-anxiety) overrides everything.
        if self.state.soc < self.state.range_anxiety_soc_floor:
            return self._do_charge(price_per_kwh)
        # Priority 2 — smart charge to the departure-aware target at off-peak.
        current_target = self._v1g_current_target_soc(hour_of_day)
        if self.state.soc < current_target and price_per_kwh <= CHEAP_THRESHOLD_FOR_V1G:
            return self._do_charge(price_per_kwh)
        return "IDLE", 0.0, 0.0

    def _rule_v2g(
        self,
        hour_of_day: int,
        day_of_week: int,
        price_per_kwh: float,
    ) -> tuple[str, float, float]:
        # Priority 1 — emergency
        if self.state.soc < self.state.range_anxiety_soc_floor:
            return self._do_charge(price_per_kwh)

        # Priority 2 — V2G discharge.  Four-condition gate:
        #   1) agent has opted in
        #   2) agent is V2G capable (has home charger + bidirectional hardware)
        #   3) SoC is above the contractual V2G floor
        #   4) export price is at or above the agent's OSP
        # Export-side price (revenue per discharged kWh).  In Israel this
        # equals the retail peak price; in the UK it is the Octopus
        # Powerloop export rate, which is fed in via the optional
        # discharge_revenue_per_kwh argument of step().
        export_price = getattr(self, "_current_export_price", price_per_kwh)
        month = getattr(self, "_current_month", 7)

        # The agent discharges any hour where the export price beats its
        # OSP.  This price-driven strategy produces a higher annual V2G
        # volume than Wong 2026's window-bound strategy (overnight +
        # 6-9 PM only).  Battery aging is reported by scaling Wong's
        # published per-typology V2G effect linearly by
        # (our_kWh / Wong_kWh); see plot_w10q_pnl_two_panel.py.
        wants_to_sell = (
            self.state.v2g_opted_in
            and self.state.v2g_capable
            and self.state.soc > V2G_SOC_FLOOR
            and export_price >= self.state.osp
        )
        if wants_to_sell:
            return self._do_discharge(export_price)

        # Priority 3 — smart charge
        if self.state.soc < self.state.target_soc and price_per_kwh <= CHEAP_THRESHOLD_FOR_V1G:
            return self._do_charge(price_per_kwh)

        return "IDLE", 0.0, 0.0

    # ------------------------------------------------------------------
    # Physical actions
    # ------------------------------------------------------------------
    def _do_charge(self, price_per_kwh: float) -> tuple[str, float, float]:
        # V2G-opted-in agents cap SoC at V2G_MAX_SOC (90 %) per the
        # Sciurus / Kaluza mobile-app pattern and Kempton & Tomic 2005 battery
        # longevity guidance.  Non-opted-in agents charge to 100 %.
        soc_ceiling = V2G_MAX_SOC if self.state.v2g_opted_in else 1.0
        headroom_kwh = max(0.0,
            (soc_ceiling - self.state.soc) * self.state.battery_kwh_usable * self.state.soh
        )
        max_this_hour_kwh = self.state.max_charge_power_kw * 1.0
        energy_drawn_kwh = min(max_this_hour_kwh, headroom_kwh)

        # GridAgent check: feeder may refuse if transformer is saturated.
        feeder = getattr(self, "feeder", None)
        current_hour = getattr(self, "_current_hour_global", 0)
        if feeder is not None:
            if not feeder.can_charge(energy_drawn_kwh, current_hour):
                feeder.denied_charges += 1
                return "IDLE_GRID_LIMITED", 0.0, 0.0
            feeder.record_charge(energy_drawn_kwh, current_hour)

        energy_into_battery = energy_drawn_kwh * self.state.charging_efficiency_c
        soc_increase = energy_into_battery / (self.state.battery_kwh_usable * self.state.soh)
        self.state.soc = min(1.0, self.state.soc + soc_increase)

        cost = energy_drawn_kwh * price_per_kwh
        return "CHARGE", energy_drawn_kwh, cost

    def _do_discharge(self, price_per_kwh: float) -> tuple[str, float, float]:
        headroom_above_floor_kwh = (
            (self.state.soc - V2G_SOC_FLOOR)
            * self.state.battery_kwh_usable
            * self.state.soh
        )
        max_this_hour_kwh = self.state.max_discharge_power_kw * 1.0
        energy_out_of_battery_kwh = min(max_this_hour_kwh, max(0.0, headroom_above_floor_kwh))

        if energy_out_of_battery_kwh <= 0.0:
            return "IDLE", 0.0, 0.0

        # GridAgent check: feeder may refuse if transformer is saturated
        # in the export direction.  Conservative: query before committing.
        feeder = getattr(self, "feeder", None)
        current_hour = getattr(self, "_current_hour_global", 0)
        if feeder is not None:
            if not feeder.can_discharge(energy_out_of_battery_kwh, current_hour):
                feeder.denied_discharges += 1
                return "IDLE_GRID_LIMITED", 0.0, 0.0
            feeder.record_discharge(energy_out_of_battery_kwh, current_hour)

        energy_to_grid_kwh = energy_out_of_battery_kwh * self.state.charging_efficiency_d

        soc_decrease = energy_out_of_battery_kwh / (self.state.battery_kwh_usable * self.state.soh)
        self.state.soc -= soc_decrease

        # Track V2G discharge separately from total throughput so the
        # aging plot can show V2G as its own layer on cycle aging.
        self.state.cumulative_v2g_discharge_kwh += energy_out_of_battery_kwh

        # Driver keeps 100% of the V2G revenue at whichever rate the
        # scenario provides (retail tariff or wholesale price; passed in
        # via export_price).
        driver_revenue = energy_to_grid_kwh * price_per_kwh
        return "DISCHARGE", -energy_to_grid_kwh, -driver_revenue
