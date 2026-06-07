"""EV Agent — implements §3 of the v8 rules document.

Plain-English summary
---------------------
Each EVAgent represents one electric car. The car has:
  - a battery, with a state of charge (how full it is) and a state of health
    (how worn out it is)
  - a typical daily driving pattern, sampled from one of four driver types
    (Daily Charger, Public Charger, BEV 2nd Vehicle, Threshold Charger)
  - rules about when to drive, when to charge, and when (if at all) to sell
    power back to the grid

Every hour of the simulated year, the agent runs its step() method which:
  1. mobility (Step A) — drives if it should be driving this hour
  2. charging decision (Step B) — applies the rule that matches its counterfactual
  3. battery health (Step C) — placeholder until W8, then Gasper 2023
  4. log — records the hour's energy in/out, cost, end-of-hour state

W7 Sunday (Batch 2) version implements:
  * Per-typology profiles: each driver type has its own daily km, commute
    hours, target SoC, and (for BEV 2nd Vehicle) which days of the week
    they actually drive.
  * Per-agent jitter: every agent gets a ±1 hour random offset on their
    departure and return hours, seeded by agent_id so it's reproducible.
  * Per-day km variation: each morning we resample daily_km_today from a
    normal distribution centred on the typology mean.
  * Step B for V0, V1G, V2G — unchanged from Saturday.
"""

import random
from dataclasses import dataclass

from src.pricing import price_at_hour, CHEAP_THRESHOLD_FOR_V1G
from src.aggregator_stub import aggregator_signals_discharge


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
        "daily_km_mean": 40.0,        # km/day
        "daily_km_std":  6.0,
        "departure_hour_mean": 8,     # 08:00 morning out
        "return_hour_mean":   18,     # 18:00 evening back
        "hour_jitter":         1,     # ±1 hour per agent
        "drive_days_per_week": 7,     # Daily Charger drives every day
        "battery_kwh_usable": 60.0,
        "has_home_charger":  True,
        "target_soc":        0.89,
        "starting_soc":      0.85,
    },
    PUBLIC_CHARGER: {
        # No home charger.  W7 simplification: assume they have a workplace
        # charger they use during the day (real Public Chargers use DC fast
        # or workplace stations).  V2G is mostly meaningless for them in W7
        # because they are never plugged in at home overnight when the peak
        # hits — the aggregator's peak signal goes unanswered.
        "daily_km_mean": 48.0,
        "daily_km_std":  10.0,
        "departure_hour_mean": 7,
        "return_hour_mean":   19,
        "hour_jitter":         2,
        "drive_days_per_week": 7,
        "battery_kwh_usable": 60.0,
        "has_home_charger":  False,
        "has_workplace_charger": True,
        "target_soc":        0.75,
        "starting_soc":      0.80,
    },
    BEV_2ND_VEHICLE: {
        # Used less frequently — drives Mon-Thu only in our simplified week.
        "daily_km_mean": 22.0,
        "daily_km_std":  6.0,
        "departure_hour_mean": 10,    # later, off-peak commute
        "return_hour_mean":   16,     # earlier return — short outings
        "hour_jitter":         2,
        "drive_days_per_week": 4,     # 4 of the 7 sim days
        "battery_kwh_usable": 60.0,
        "has_home_charger":  True,
        "target_soc":        0.87,
        "starting_soc":      0.80,
    },
    THRESHOLD_CHARGER: {
        # Drives daily but charges only when needed.
        "daily_km_mean": 38.0,
        "daily_km_std":  6.0,
        "departure_hour_mean": 8,
        "return_hour_mean":   18,
        "hour_jitter":         1,
        "drive_days_per_week": 7,
        "battery_kwh_usable": 60.0,
        "has_home_charger":  True,
        "target_soc":        0.85,
        "starting_soc":      0.70,
    },
}


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
    daily_km_std: float = 6.0
    drives_today: bool = True
    drive_days_per_week: int = 7
    departure_hour: int = 8
    return_hour: int = 18

    # --- Charging targets ---
    target_soc: float = 0.89

    # --- Behaviour ---
    range_anxiety_soc_floor: float = 0.30
    osp: float = 0.0
    v2g_opted_in: bool = False


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
            daily_km_mean=profile["daily_km_mean"],
            daily_km_std=profile["daily_km_std"],
            drive_days_per_week=profile["drive_days_per_week"],
            soc=profile["starting_soc"],
        )

        # Per-agent commute jitter (±N hours, depending on typology)
        jitter = profile["hour_jitter"]
        self.state.departure_hour = profile["departure_hour_mean"] + self._rng.randint(-jitter, jitter)
        self.state.return_hour = profile["return_hour_mean"] + self._rng.randint(-jitter, jitter)
        # Safety clip — make sure departure is before return
        if self.state.return_hour <= self.state.departure_hour:
            self.state.return_hour = self.state.departure_hour + 6

        # V2G setup — only relevant for the V2G counterfactual.  Public Chargers
        # cannot V2G in W7 because they have no home charger.
        if counterfactual == COUNTERFACTUAL_V2G and self.state.has_home_charger:
            self.state.v2g_capable = True
            self.state.v2g_opted_in = True
            self.state.osp = 1.00
            self.state.max_discharge_power_kw = 9.6

        # Sample today's driving for day 0
        self._start_new_day(day_of_week=0)

        # Hour-by-hour log
        self.hourly_log: list[dict] = []

    # ------------------------------------------------------------------
    # New-day sampling
    # ------------------------------------------------------------------
    def _start_new_day(self, day_of_week: int) -> None:
        """Decide whether the agent drives today and how far.

        Called at the start of each simulated day (hour_of_day == 0).
        """
        # Drives today?  For typologies that drive every day, always True.
        # For BEV 2nd Vehicle (4 days/week), drive on Mon-Thu only (days 0-3).
        if self.state.drive_days_per_week >= 7:
            self.state.drives_today = True
        else:
            # Drive on the first `drive_days_per_week` days of the week
            self.state.drives_today = (day_of_week < self.state.drive_days_per_week)

        # Sample today's km
        if self.state.drives_today:
            km = self._rng.gauss(self.state.daily_km_mean, self.state.daily_km_std)
            self.state.daily_km_today = max(0.0, km)  # clip negatives
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
        action_mobility = self._step_mobility(hour_of_day)

        # Step B — charging/discharging decision (only if not driving)
        if action_mobility == "DRIVING":
            energy_kwh = 0.0
            cost = 0.0
            action_charge = "DRIVING"
        else:
            action_charge, energy_kwh, cost = self._step_charging_decision(
                hour_of_day=hour_of_day,
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
    def _step_mobility(self, hour_of_day: int) -> str:
        """Move the car.  Returns one of: 'DRIVING', 'AT_HOME', 'AT_WORK'."""
        if self._is_driving_now(hour_of_day):
            self.state.plugged_in = False
            self.state.location = "driving"
            km_this_hour = self.state.daily_km_today / 2.0
            kwh_consumed = (km_this_hour * CONSUMPTION_KWH_PER_KM) / self.state.soh
            soc_drop = kwh_consumed / self.state.battery_kwh_usable
            self.state.soc = max(0.0, self.state.soc - soc_drop)
            return "DRIVING"

        if hour_of_day >= self.state.return_hour or hour_of_day < self.state.departure_hour:
            self.state.location = "home"
            self.state.plugged_in = self.state.has_home_charger
            return "AT_HOME"

        self.state.location = "work"
        self.state.plugged_in = self.state.has_workplace_charger
        return "AT_WORK"

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
        price_per_kwh: float,
    ) -> tuple[str, float, float]:
        if not self.state.plugged_in:
            return "IDLE", 0.0, 0.0

        if self.counterfactual == COUNTERFACTUAL_V0:
            return self._rule_v0(price_per_kwh)
        if self.counterfactual == COUNTERFACTUAL_V1G:
            return self._rule_v1g(price_per_kwh)
        if self.counterfactual == COUNTERFACTUAL_V2G:
            return self._rule_v2g(hour_of_day, price_per_kwh)
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
        price_per_kwh: float,
    ) -> tuple[str, float, float]:
        # Priority 1 — emergency
        if self.state.soc < self.state.range_anxiety_soc_floor:
            return self._do_charge(price_per_kwh)

        # Priority 2 — V2G discharge
        wants_to_sell = (
            aggregator_signals_discharge(hour_of_day)
            and self.state.v2g_opted_in
            and self.state.v2g_capable
            and self.state.soc > V2G_SOC_FLOOR
            and price_per_kwh >= self.state.osp
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
