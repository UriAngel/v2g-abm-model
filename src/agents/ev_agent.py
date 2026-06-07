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

W7 Friday + Saturday version implements:
  * Step A — simple morning/evening commute
  * Step B for V0 (naive), V1G (smart-charging), V2G (active discharge)
  * V2G: discharges during the evening peak when SoC > 50% and
         price >= the agent's personal OSP (Optimal Selling Price)
  * Step C is a stub until W8
"""

from dataclasses import dataclass, field

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
# Counterfactuals (rules §0)
# -----------------------------------------------------------------------------

COUNTERFACTUAL_V0 = "V0"     # naive: charge any time plugged in until full
COUNTERFACTUAL_V1G = "V1G"   # smart: defer to off-peak prices
COUNTERFACTUAL_V2G = "V2G"   # active: V1G plus selling back to grid (Saturday)


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
    location: str = "home"   # "home", "work", "public_dc", "driving"
    has_home_charger: bool = True
    has_workplace_charger: bool = False

    # --- Daily driving ---
    daily_km_today: float = 40.0
    target_soc: float = 0.89    # typology-dependent

    # --- Behaviour (sampled once at agent start, stubbed for W7) ---
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
        Unique identifier within the simulation.
    typology : str
        One of ALL_TYPOLOGIES.
    counterfactual : str
        One of "V0", "V1G", "V2G".

    Examples
    --------
    >>> agent = EVAgent(agent_id=1, typology=DAILY_CHARGER,
    ...                 counterfactual=COUNTERFACTUAL_V0)
    >>> agent.step(current_hour=0, current_price_per_kwh=0.10)
    """

    # Default mobility schedule — see _is_driving_now()
    DEPARTURE_HOUR_MORNING = 8     # leaves home at 08:00
    RETURN_HOUR_EVENING = 18       # returns home at 18:00 (drives 17:00-18:00)
    # In W7 we model only one outbound and one inbound trip per day,
    # each occupying a single hour for simplicity.

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

        # Initial state — defaults to a Daily Charger profile for now.
        # W8 will sample these properly from the config.
        self.state = EVAgentState()
        if typology == DAILY_CHARGER:
            self.state.target_soc = 0.89
        elif typology == PUBLIC_CHARGER:
            self.state.target_soc = 0.75
            self.state.has_home_charger = False
        elif typology == BEV_2ND_VEHICLE:
            self.state.target_soc = 0.87
        elif typology == THRESHOLD_CHARGER:
            self.state.target_soc = 0.85

        # V2G setup — only relevant for the V2G counterfactual.
        # The agent's personal OSP (Optimal Selling Price) is the minimum price
        # at which it will agree to discharge.  Saturday simplification: set it
        # to a value just above the shoulder price so the agent accepts during
        # the evening peak (0.45) but refuses during shoulder hours (0.20).
        # W8 will derive OSP from Liao's marginal-cost equation per agent.
        if counterfactual == COUNTERFACTUAL_V2G:
            self.state.v2g_capable = True
            self.state.v2g_opted_in = True
            self.state.osp = 0.30
            self.state.max_discharge_power_kw = 9.6

        # Hour-by-hour log
        self.hourly_log: list[dict] = []

    # ------------------------------------------------------------------
    # Public step method — called once per simulated hour
    # ------------------------------------------------------------------
    def step(self, current_hour: int, current_price_per_kwh: float) -> None:
        """Advance the agent by one simulated hour."""
        hour_of_day = current_hour % 24

        # Step A — mobility
        action_mobility = self._step_mobility(hour_of_day)

        # Step B — charging/discharging decision
        # Step B is only relevant if not driving
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
        # In W8 we replace this with the Gasper 2023 equations.

        # Step D — log
        self.hourly_log.append({
            "hour": current_hour,
            "hour_of_day": hour_of_day,
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
    # Step A — mobility (rules §3.5)
    # ------------------------------------------------------------------
    def _step_mobility(self, hour_of_day: int) -> str:
        """Move the car.  Returns one of: "DRIVING", "AT_HOME", "AT_WORK"."""
        if self._is_driving_now(hour_of_day):
            self.state.plugged_in = False
            self.state.location = "driving"
            # Trip energy: half the daily km in this single hour.
            # (W8 splits across multiple hours for longer trips.)
            km_this_hour = self.state.daily_km_today / 2.0
            kwh_consumed = (km_this_hour * CONSUMPTION_KWH_PER_KM) / self.state.soh
            # Deplete SoC. Clip at zero — but in practice this should never reach zero
            # for a Daily Charger; W8 will flag if it does.
            soc_drop = kwh_consumed / self.state.battery_kwh_usable
            self.state.soc = max(0.0, self.state.soc - soc_drop)
            return "DRIVING"

        # Not driving — at home (or potentially at work, but W7 only models home plug-in)
        if hour_of_day >= self.RETURN_HOUR_EVENING or hour_of_day < self.DEPARTURE_HOUR_MORNING:
            self.state.location = "home"
            self.state.plugged_in = self.state.has_home_charger
            return "AT_HOME"

        # Daytime non-driving hours = at work
        self.state.location = "work"
        # W7 simplification: assume not plugged in at work
        self.state.plugged_in = self.state.has_workplace_charger
        return "AT_WORK"

    def _is_driving_now(self, hour_of_day: int) -> bool:
        """True for the single outbound hour and single inbound hour each day.

        W7 has exactly two driving hours per day:
          DEPARTURE_HOUR_MORNING (08:00-09:00)  — half the daily km
          RETURN_HOUR_EVENING - 1 (17:00-18:00) — the other half
        """
        return hour_of_day in (self.DEPARTURE_HOUR_MORNING,
                               self.RETURN_HOUR_EVENING - 1)

    # ------------------------------------------------------------------
    # Step B — charge / discharge decision
    # ------------------------------------------------------------------
    def _step_charging_decision(
        self,
        hour_of_day: int,
        price_per_kwh: float,
    ) -> tuple[str, float, float]:
        """Decide whether to charge / discharge / idle for this hour.

        Returns
        -------
        action : str
            One of "CHARGE", "DISCHARGE", "IDLE".
        energy_kwh : float
            Energy moved this hour (positive = bought from grid,
            negative = sold to grid, zero = idle or stationary).
        cost : float
            Money paid this hour (positive = expense, negative = income).
        """
        # If not plugged in, nothing to do (no decision possible)
        if not self.state.plugged_in:
            return "IDLE", 0.0, 0.0

        if self.counterfactual == COUNTERFACTUAL_V0:
            return self._rule_v0(price_per_kwh)
        if self.counterfactual == COUNTERFACTUAL_V1G:
            return self._rule_v1g(price_per_kwh)
        if self.counterfactual == COUNTERFACTUAL_V2G:
            return self._rule_v2g(hour_of_day, price_per_kwh)
        raise ValueError(f"unknown counterfactual {self.counterfactual!r}")

    # V0: naive charging — charge whenever plugged in and not full
    def _rule_v0(self, price_per_kwh: float) -> tuple[str, float, float]:
        if self.state.soc < 1.0:
            return self._do_charge(price_per_kwh)
        return "IDLE", 0.0, 0.0

    # V1G: smart charging — only charge when price is cheap (off-peak)
    # or when SoC is below the agent's personal range-anxiety floor
    def _rule_v1g(self, price_per_kwh: float) -> tuple[str, float, float]:
        if self.state.soc < self.state.range_anxiety_soc_floor:
            return self._do_charge(price_per_kwh)  # emergency
        if self.state.soc < self.state.target_soc and price_per_kwh <= CHEAP_THRESHOLD_FOR_V1G:
            return self._do_charge(price_per_kwh)
        return "IDLE", 0.0, 0.0

    # V2G: real Saturday logic — discharges during evening peak if profitable
    def _rule_v2g(
        self,
        hour_of_day: int,
        price_per_kwh: float,
    ) -> tuple[str, float, float]:
        """V2G decision rule (rules §3.5 priority order).

        Priority:
          1. If SoC < range-anxiety floor → CHARGE (driver protection)
          2. If aggregator says "discharge" AND price ≥ OSP AND SoC > V2G floor
             AND v2g_opted_in → DISCHARGE
          3. If SoC < target AND price is cheap → CHARGE
          4. Else → IDLE
        """
        # Priority 1 — emergency charge
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

        # Priority 3 — smart charge (V1G logic)
        if self.state.soc < self.state.target_soc and price_per_kwh <= CHEAP_THRESHOLD_FOR_V1G:
            return self._do_charge(price_per_kwh)

        # Priority 4 — idle
        return "IDLE", 0.0, 0.0

    # ------------------------------------------------------------------
    # Physical action: discharge the battery to the grid for one hour
    # ------------------------------------------------------------------
    def _do_discharge(self, price_per_kwh: float) -> tuple[str, float, float]:
        """Discharge as much as possible in one hour, bounded by:
          - max_discharge_power_kw         (charger speed)
          - SoC above V2G_SOC_FLOOR        (don't drain below 50%)
          - discharging efficiency loss    (some energy lost in conversion)

        Returns the energy as a NEGATIVE number (energy leaving the battery)
        and cost as a negative number (income to the owner).
        """
        # How much we can pull from the battery without breaching the floor
        headroom_above_floor_kwh = (
            (self.state.soc - V2G_SOC_FLOOR)
            * self.state.battery_kwh_usable
            * self.state.soh
        )
        max_this_hour_kwh = self.state.max_discharge_power_kw * 1.0  # 1 hour
        energy_out_of_battery_kwh = min(max_this_hour_kwh, max(0.0, headroom_above_floor_kwh))

        if energy_out_of_battery_kwh <= 0.0:
            # No headroom — nothing to sell
            return "IDLE", 0.0, 0.0

        # Discharging efficiency loss: battery loses X kWh, grid receives
        # X * efficiency_d kWh.
        energy_to_grid_kwh = energy_out_of_battery_kwh * self.state.charging_efficiency_d

        # Lower the SoC by what the battery actually lost (not what the grid received)
        soc_decrease = energy_out_of_battery_kwh / (self.state.battery_kwh_usable * self.state.soh)
        self.state.soc -= soc_decrease

        # Owner is PAID for what the grid received.  Cost is negative (income).
        revenue = energy_to_grid_kwh * price_per_kwh
        return "DISCHARGE", -energy_to_grid_kwh, -revenue

    # ------------------------------------------------------------------
    # Physical action: charge the battery for one hour
    # ------------------------------------------------------------------
    def _do_charge(self, price_per_kwh: float) -> tuple[str, float, float]:
        """Charge as much as we can in one hour, bounded by:
          - max_charge_power_kw          (charger speed)
          - remaining capacity to 100%   (don't overfill)
          - SoH                          (degraded batteries hold less)
        """
        headroom_kwh = (1.0 - self.state.soc) * self.state.battery_kwh_usable * self.state.soh
        max_this_hour_kwh = self.state.max_charge_power_kw * 1.0  # 1 hour
        energy_drawn_kwh = min(max_this_hour_kwh, headroom_kwh)

        # Charging efficiency loss: we pay for grid energy, but the battery
        # only sees efficiency_c × grid energy
        energy_into_battery = energy_drawn_kwh * self.state.charging_efficiency_c
        soc_increase = energy_into_battery / (self.state.battery_kwh_usable * self.state.soh)
        self.state.soc = min(1.0, self.state.soc + soc_increase)

        cost = energy_drawn_kwh * price_per_kwh
        return "CHARGE", energy_drawn_kwh, cost
