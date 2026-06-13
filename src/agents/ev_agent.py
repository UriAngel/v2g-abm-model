"""EV Agent — implements §3 of the v8 rules document.

W8 Batch A changes (after Monday W7 supervisor meeting):
  * Gaussian commute jitter (std 0.5h, per Brinkel 2020) replaces uniform.
  * Log-normal daily km (sigma 0.6, per Liao 2025) replaces Gaussian.
  * Weekend factor: Friday and Saturday (Israeli convention) use shorter
    midday commute (11:00 to 17:00) and reduced km (factor 0.5).
  * BEV 2nd Vehicle now drives only Tuesday, Wednesday, Thursday
    (per David W8 meeting), down from Mon-Thu.
  * Threshold Charger gets real threshold behaviour: it plugs in only when
    SoC falls below charge_threshold (0.30), and stays plugged in until
    target_soc (0.95) is reached. Daily Charger by contrast plugs in
    whenever the vehicle is at home, regardless of current SoC.
  * Day-of-week is now passed to pricing and aggregator so peak rates and
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
    PRICE_SHOULDER,
    PRICE_PEAK,
)
from src.aggregator_stub import (
    aggregator_signals_discharge,
    aggregator_accepts_retailer,
)


# -----------------------------------------------------------------------------
# Typology — the four driver categories from Hoke 2026 (rules §3.1)
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
# Per-typology default profiles (matches v8 §3.1 + §3.2 with W7 simplifications)
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
        "drive_days_per_week": 6.43,  # Hoke 2026 Table 1
        "drives_on_weekend":  True,
        "battery_kwh_usable": 60.0,
        "has_home_charger":  True,
        "target_soc":        0.892,   # Hoke 2026 Table 1: Mean SoC after charge
        "starting_soc":      0.85,
        "charge_threshold":  0.0,     # 0 = no threshold; always plug in when home
    },
    PUBLIC_CHARGER: {
        # No home charger; uses workplace charging.  V2G is not possible
        # because they are never plugged in at home overnight.
        "daily_km_mean": 48.0,
        "departure_hour_mean": 7,
        "return_hour_mean":   19,
        "drive_days_per_week": 6.41,  # Hoke 2026 Table 1
        "drives_on_weekend":  True,
        "battery_kwh_usable": 60.0,
        "has_home_charger":  False,
        "has_workplace_charger": True,
        "target_soc":        0.747,   # Hoke 2026 Table 1: Mean SoC after charge
        "starting_soc":      0.80,
        "charge_threshold":  0.0,
    },
    BEV_2ND_VEHICLE: {
        # Hoke 2026 Table 1: 4.74 drive days per week, modelled
        # probabilistically (drive each day with probability 4.74 / 7).
        "daily_km_mean": 22.0,
        "departure_hour_mean": 10,
        "return_hour_mean":   16,
        "drive_days_per_week": 4.74,  # Hoke 2026 Table 1
        "drives_on_weekend":  True,
        "battery_kwh_usable": 60.0,
        "has_home_charger":  True,
        "target_soc":        0.87,    # Hoke 2026 Table 1: Mean SoC after charge
        "starting_soc":      0.80,
        "charge_threshold":  0.0,
    },
    THRESHOLD_CHARGER: {
        # Plugs in only when SoC < charge_threshold, charges to target_soc,
        # then unplugs.  All three numbers from Hoke 2026 Table 1.
        "daily_km_mean": 38.0,
        "departure_hour_mean": 8,
        "return_hour_mean":   18,
        "drive_days_per_week": 6.44,  # Hoke 2026 Table 1
        "drives_on_weekend":  True,
        "battery_kwh_usable": 60.0,
        "has_home_charger":  True,
        "target_soc":        0.85,    # Hoke 2026 Table 1: Mean SoC after charge
        "starting_soc":      0.50,
        "charge_threshold":  0.461,   # Hoke 2026 Table 1: Mean SoC at plug-in
    },
}

# Israeli weekday convention: 0=Sunday ... 4=Thursday, 5=Friday, 6=Saturday.
WEEKEND_DAYS = (5, 6)
WEEKEND_KM_FACTOR = 0.5       # weekend trip kms = weekday × this
WEEKEND_DEPARTURE_HOUR = 11   # midday weekend trip start
WEEKEND_RETURN_HOUR = 17      # midday weekend trip end (before peak)

# Randomness parameters agreed at W8:
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


def intention_to_osp(intention: float) -> float:
    """Map a continuous Intention score to a per-agent OSP, bounded by the
    TAOZ shoulder and peak rates.

    Uses the logistic transform so that very high Intention drives OSP to
    the shoulder rate (willing to sell at modest prices) and very low
    Intention pushes OSP toward the peak rate (only sells when prices are
    high).  Bounds come from IEC TAOZ summer schedule.
    """
    sigmoid = 1.0 / (1.0 + math.exp(-intention))
    # sigmoid in (0, 1).  Map so that high intention -> low OSP.
    return PRICE_PEAK - (PRICE_PEAK - PRICE_SHOULDER) * sigmoid


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


# -----------------------------------------------------------------------------
# State variables (rules §3.4)
# -----------------------------------------------------------------------------

@dataclass
class EVAgentState:
    """All persistent state for one EV agent, updated every hour."""

    # --- Battery ---
    soc: float = 0.80
    soh: float = 1.00
    battery_kwh_usable: float = 60.0
    chemistry: str = "NMC"

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

    # --- Behaviour ---
    range_anxiety_soc_floor: float = 0.30
    osp: float = 0.0
    v2g_opted_in: bool = False

    # --- Retail relationship (W8 Batch B) ---
    retailer: str = "IEC"

    # --- Latent attitudinal scores (W8 Batch C, Mehdizadeh-style SEM) ---
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

    def __init__(self, agent_id: int, typology: str, counterfactual: str):
        # Identity + validation
        assert typology in ALL_TYPOLOGIES, f"unknown typology {typology!r}"
        assert counterfactual in (COUNTERFACTUAL_V0,
                                  COUNTERFACTUAL_V1G,
                                  COUNTERFACTUAL_V2G), \
            f"unknown counterfactual {counterfactual!r}"
        self.id = agent_id
        self.typology = typology
        self.counterfactual = counterfactual

        # Per-agent random number generator, seeded by id+typology.  This makes
        # the jitter and daily-km noise reproducible: rerun the demo with the
        # same code and you get identical numbers.
        seed_int = agent_id * 1000 + ALL_TYPOLOGIES.index(typology)
        self._rng = random.Random(seed_int)

        # Pull the typology profile and apply it to the agent's state
        profile = TYPOLOGY_PROFILES[typology]
        self.state = EVAgentState(
            battery_kwh_usable=profile["battery_kwh_usable"],
            has_home_charger=profile["has_home_charger"],
            has_workplace_charger=profile.get("has_workplace_charger", False),
            target_soc=profile["target_soc"],
            charge_threshold=profile["charge_threshold"],
            daily_km_mean=profile["daily_km_mean"],
            drive_days_per_week=profile["drive_days_per_week"],
            drives_on_weekend=profile["drives_on_weekend"],
            soc=profile["starting_soc"],
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

        # --- W8 Batch C: SEM-based behavioural willingness ---
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
        # Chargers cannot V2G in W7 because they have no home charger.
        # Opt-in and OSP depend on SEM_ENABLED:
        #   SEM_ENABLED = True  -> opt-in if Intention > 0; OSP from sigmoid
        #   SEM_ENABLED = False -> opt-in always; OSP = SEM_DISABLED_FLAT_OSP
        if counterfactual == COUNTERFACTUAL_V2G and self.state.has_home_charger:
            self.state.v2g_capable = True
            if SEM_ENABLED:
                self.state.v2g_opted_in = self.state.intention_to_use_v2g > 0.0
                self.state.osp = intention_to_osp(self.state.intention_to_use_v2g)
            else:
                self.state.v2g_opted_in = True
                self.state.osp = SEM_DISABLED_FLAT_OSP
            self.state.max_discharge_power_kw = 9.6

        # Sample this agent's electricity retailer from realistic Israeli
        # market shares (used by the optional aggregator-retailer gate
        # in `_rule_v2g`).
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
        Hoke 2026 Table 1 count in expectation.
        """
        is_weekend = day_of_week in WEEKEND_DAYS

        # Probabilistic drive-day decision based on Hoke 2026 drive_days/wk.
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
    def step(self, current_hour: int, current_price_per_kwh: float) -> None:
        """Advance the agent by one simulated hour."""
        hour_of_day = current_hour % 24
        day_of_week = (current_hour // 24) % 7

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

        # Step C — battery health (placeholder until W8)

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

        Daily Charger and BEV 2nd Vehicle: plug in whenever home (so long as
        the household has a home charger).  Threshold Charger: plug in only
        once SoC has fallen below charge_threshold, then stay plugged in
        until target_soc is reached, then unplug.  This gives the
        characteristic "long stretches unplugged, short bursts of full
        charging" pattern that distinguishes Threshold Charger from the
        others.
        """
        if not self.state.has_home_charger:
            return False
        if self.state.charge_threshold <= 0.0:
            return True
        # Threshold behaviour with hysteresis.
        if self.state.plugged_in:
            # Already in a charging session — stay plugged in until full.
            return self.state.soc < self.state.target_soc
        # Not currently plugged in — only start a new session if SoC is low.
        return self.state.soc < self.state.charge_threshold

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
            return self._rule_v1g(price_per_kwh)
        if self.counterfactual == COUNTERFACTUAL_V2G:
            return self._rule_v2g(hour_of_day, day_of_week, price_per_kwh)
        raise ValueError(f"unknown counterfactual {self.counterfactual!r}")

    def _rule_v0(self, price_per_kwh: float) -> tuple[str, float, float]:
        if self.state.soc < 1.0:
            return self._do_charge(price_per_kwh)
        return "IDLE", 0.0, 0.0

    def _rule_v1g(self, price_per_kwh: float) -> tuple[str, float, float]:
        if self.state.soc < self.state.range_anxiety_soc_floor:
            return self._do_charge(price_per_kwh)
        if self.state.soc < self.state.target_soc and price_per_kwh <= CHEAP_THRESHOLD_FOR_V1G:
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

        # Priority 2 — V2G discharge.  Six-condition gate:
        #   1) aggregator signals discharge this hour
        #   2) agent has opted in
        #   3) agent is V2G capable (has home charger + bidirectional hardware)
        #   4) SoC is above the contractual V2G floor
        #   5) price is at or above the agent's OSP
        #   6) (W8 Batch B) agent's retailer matches the aggregator's
        #      contracted retailer.  Disabled by default; toggled with
        #      RETAILER_GATE_ENABLED in aggregator_stub.py.
        wants_to_sell = (
            aggregator_signals_discharge(hour_of_day, day_of_week)
            and self.state.v2g_opted_in
            and self.state.v2g_capable
            and self.state.soc > V2G_SOC_FLOOR
            and price_per_kwh >= self.state.osp
            and aggregator_accepts_retailer(self.state.retailer)
        )
        if wants_to_sell:
            return self._do_discharge(price_per_kwh)

        # Priority 3 — smart charge
        if self.state.soc < self.state.target_soc and price_per_kwh <= CHEAP_THRESHOLD_FOR_V1G:
            return self._do_charge(price_per_kwh)

        return "IDLE", 0.0, 0.0

    # ------------------------------------------------------------------
    # Physical actions
    # ------------------------------------------------------------------
    def _do_charge(self, price_per_kwh: float) -> tuple[str, float, float]:
        headroom_kwh = (1.0 - self.state.soc) * self.state.battery_kwh_usable * self.state.soh
        max_this_hour_kwh = self.state.max_charge_power_kw * 1.0
        energy_drawn_kwh = min(max_this_hour_kwh, headroom_kwh)

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

        energy_to_grid_kwh = energy_out_of_battery_kwh * self.state.charging_efficiency_d

        soc_decrease = energy_out_of_battery_kwh / (self.state.battery_kwh_usable * self.state.soh)
        self.state.soc -= soc_decrease

        revenue = energy_to_grid_kwh * price_per_kwh
        return "DISCHARGE", -energy_to_grid_kwh, -revenue
