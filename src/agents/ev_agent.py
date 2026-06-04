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
  1. moves the car if it is supposed to be driving
  2. checks whether it is currently plugged in
  3. if plugged in, decides: charge / discharge / idle
  4. updates battery health
  5. logs the hour's profit, energy in/out, and end-of-hour state

This file (Trinity W7, Thursday-night version) defines the STATE VARIABLES
only. The decision logic is added Friday-Saturday.
"""

from dataclasses import dataclass, field
from typing import Optional


# -----------------------------------------------------------------------------
# Typology — the four driver categories from Hoke 2026 (rules §3.1)
# -----------------------------------------------------------------------------
# Each entry is a string label. We use simple Python strings instead of an
# enum to keep the code readable for non-developers.

DAILY_CHARGER = "Daily Charger"        # 22% of IL, 36% of UK sample
PUBLIC_CHARGER = "Public Charger"      # 32% of IL, 31% of UK sample
BEV_2ND_VEHICLE = "BEV 2nd Vehicle"    # 15% of IL, 13% of UK sample
THRESHOLD_CHARGER = "Threshold Charger"  # 31% of IL, 20% of UK sample

ALL_TYPOLOGIES = (
    DAILY_CHARGER,
    PUBLIC_CHARGER,
    BEV_2ND_VEHICLE,
    THRESHOLD_CHARGER,
)


# -----------------------------------------------------------------------------
# State variables — rules §3.4
# -----------------------------------------------------------------------------
# A "dataclass" is a Python convenience that builds a class for us where each
# attribute has a default value. We use it here so the EVAgent's state is
# described in one place with explanations.

@dataclass
class EVAgentState:
    """All persistent state for one EV agent, updated every hour.

    Continuous values (state of charge, state of health) are floats between
    0.0 and 1.0. For example, soc = 0.654 means the battery is 65.4% full.
    """

    # --- Battery state ---
    soc: float = 0.80              # State of charge, 0.0 to 1.0
    soh: float = 1.00              # State of health, 0.0 to 1.0 (1.0 = brand new)
    battery_kwh_usable: float = 60.0   # Capacity in kWh; sampled from vehicle model

    # --- Battery technology ---
    chemistry: str = "NMC"         # "NMC" or "LFP" — affects aging behaviour
    v2g_capable: bool = False      # Whether the car can sell back to the grid
    max_charge_power_kw: float = 7.0   # Domestic AC charger default
    max_discharge_power_kw: float = 9.6  # SCE V2G pilot mid-tier
    charging_efficiency_c: float = 0.95  # One-way charging efficiency
    charging_efficiency_d: float = 0.95  # One-way discharging efficiency

    # --- Position and connection ---
    plugged_in: bool = False
    location: str = "home"         # one of: "home", "work", "public_dc", "driving"
    has_workplace_charger: bool = False

    # --- Today's driving distance (resampled each morning) ---
    daily_km_today: float = 0.0

    # --- Aging accumulators ---
    cumulative_throughput_kwh: float = 0.0
    cumulative_calendar_days: float = 0.0

    # --- Behavioural / psychological scores (sampled once at simulation start) ---
    psych_intention_z: float = 0.0       # SEM-derived intention score, §12
    wtp_W_u: float = 0.0                 # Liao willingness, §13
    v2g_opted_in: bool = False           # derived from intention × wtp
    range_anxiety_soc_floor: float = 0.30  # personal floor below which CHARGE
    osp: float = 0.0                     # personal minimum selling price


# -----------------------------------------------------------------------------
# Constants — rules §3.5
# -----------------------------------------------------------------------------

V2G_SOC_FLOOR = 0.50            # Contractual minimum SoC for V2G, §3.6
CONSUMPTION_KWH_PER_KM = 0.18   # Energy consumption while driving, §3.5
SECONDS_PER_HOUR = 3600
HOURS_PER_DAY = 24


# -----------------------------------------------------------------------------
# The EVAgent class itself
# -----------------------------------------------------------------------------

class EVAgent:
    """One electric vehicle in the simulation.

    Each EVAgent owns an EVAgentState object that holds its current state.
    The step() method is called once per simulated hour and updates the state.

    Logic added incrementally:
      W7 Friday  - mobility step (Step A in rules §3.5)
      W7 Friday  - V0 (naive) charging rule
      W7 Friday  - V1G (smart) charging rule
      W7 Saturday - V2G (active) charging rule, OSP gate, willingness check

    Parameters
    ----------
    agent_id : int
        Unique identifier within the simulation.
    typology : str
        One of the four ALL_TYPOLOGIES strings. Sets the initial driving
        pattern, target SoC, plug-in habits, etc.
    counterfactual : str
        One of "V0", "V1G", "V2G". Determines which decision rule the agent
        uses each hour. We run three parallel simulations, one per
        counterfactual, on identical fleets.
    """

    def __init__(self, agent_id: int, typology: str, counterfactual: str):
        # Identity
        self.id = agent_id
        self.typology = typology
        self.counterfactual = counterfactual

        # Validate inputs — fail loud and fast if a caller passes nonsense
        assert typology in ALL_TYPOLOGIES, f"unknown typology {typology!r}"
        assert counterfactual in ("V0", "V1G", "V2G"), \
            f"unknown counterfactual {counterfactual!r}"

        # State (defaults from EVAgentState; resampled in initialise())
        self.state = EVAgentState()

        # Hour-by-hour log of what happened — populated by step()
        self.hourly_log: list[dict] = []

    # ------------------------------------------------------------------
    # Placeholder — Friday's work
    # ------------------------------------------------------------------
    def step(self, current_hour: int, current_price_per_kwh: float) -> None:
        """Advance the agent by one simulated hour.

        For now this is a stub. Friday we add:
          Step A — mobility   (rules §3.5)
          Step B — charge/discharge decision per counterfactual
          Step C — update battery health
        """
        raise NotImplementedError(
            "EVAgent.step() is not implemented yet — Friday's work."
        )
