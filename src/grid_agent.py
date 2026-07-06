"""Grid agent: feeder-level transformer constraint.

A FeederAgent models a single low-voltage distribution feeder serving a
group of households.  It carries a transformer with a finite kVA rating.
The aggregator's discharge dispatch must respect this rating: at most
TRANSFORMER_KVA worth of net export can flow through the transformer in
any given hour, regardless of how many V2G-willing EVs are connected.

Design parameters:

  * Single layer (feeder only).  No separate SubstationAgent.
  * Feeder size and transformer rating are country-sourced (see the
    UK / Israel parameter blocks below).
  * Discharge dispatch: when a feeder is at constraint and not all
    V2G-willing EVs can fit, the lowest-OSP (most willing) agents are
    dispatched first.  Implemented at the run-loop level by sorting
    each feeder's EV list by OSP ascending before each hour's step
    (see run_w9_fleet.py).

Convention:
  load_kw[h] is the NET load on the transformer at hour h, measured as
    + positive when household consumption exceeds local generation
      (transformer importing from the grid),
    - negative when V2G discharge exceeds household consumption
      (transformer exporting to the grid).
  The transformer constraint is |load_kw[h]| <= TRANSFORMER_KVA.
"""

# =============================================================================
# Country-specific feeder parameters (sourced figures).
# =============================================================================
#
# UK numbers.  Source: Tang, Ashtine, Hua & Wallom (2024) "Sensitivity
# analysis of distributed photovoltaic system capacity estimation based
# on artificial neural network", Sustainable Energy, Grids and Networks
# vol 39 art 101396 (DOI 10.1016/j.segan.2024.101396), section 3.3.
#     "Since a single substation feeder typically serves a maximum of
#      75 households [36]" - ref [36] = Adams, personal communication 2022.
# Tang's case study uses 81 HH / feeder to fit a 162-HH London 2013 dataset.
# UK LV substations are typically 500 kVA (ENA standard sizes).
UK_TRANSFORMER_KVA        = 500.0
UK_AGENTS_PER_FEEDER      = 75
#
# Israel numbers.  Source: IEC Annual Report / Israeli Electricity
# Authority 2023 Summary + 2024 Trends report (September 2024).
# Distribution system: 55,758 transformers, 28,818 MVA total capacity,
# 2,987,000 customers, 43,150 km of LV lines.
# Arithmetic:
#     average transformer size = 28,818,000 / 55,758 = 516.9 kVA
#     average customers per transformer = 2,987,000 / 55,758 = 53.6
# These are NETWORK-WIDE averages (including commercial/industrial);
# residential-only feeders are typically smaller.
IL_TRANSFORMER_KVA        = 517.0
IL_AGENTS_PER_FEEDER      = 54
#
# Defaults used by callers that do not pass a country; map to the
# Israel network-average.
DEFAULT_TRANSFORMER_KVA   = IL_TRANSFORMER_KVA
DEFAULT_AGENTS_PER_FEEDER = IL_AGENTS_PER_FEEDER


# =============================================================================
# Household non-EV baseline load profile.
# =============================================================================
#
# A 50-75-HH feeder carries ~150-200 kW of household load before any EV
# does anything; ignoring it would understate the transformer
# constraint, so the baseline is included in every constraint check.
#
# Sources for the profile:
#   - UK Power Networks "Neighbourhood Green" project (2024-25): ADMD
#     1.5-2.0 kW per household for non-heat-pump homes, rising to 2.6-3.4
#     kW with heat pumps.
#   - Low Carbon London (LCL) dataset (Nov 2011 - Feb 2014, 5,567
#     London households, UK Power Networks): standard reference for
#     residential UK smart-meter half-hourly consumption.  The typical
#     week-day profile shows a morning ramp at 07:00-09:00 (~1.0-1.3
#     kW/HH), a midday dip (~0.5 kW/HH), an evening peak at 17:00-21:00
#     (~1.5-2.0 kW/HH), and overnight base (~0.3-0.4 kW/HH).
#   - Israeli summer profile differs mainly by A/C load: summer evening
#     peak is HIGHER (~3.0-3.5 kW/HH) than UK, and the midday dip is
#     narrower.  Winter Israeli load is comparable to UK.
#
# What we implement:
#   * A 24-value stylised weekday profile in kW/HH, LCL-consistent.
#   * A summer multiplier (1.4x) applied Jun-Sep to reflect Israeli A/C.
#   * Applied by the FeederAgent at the start of each hour, so V2G
#     discharge decisions face the transformer constraint including the
#     baseline load.
#
# Approximate working profile; exact values pending the NOGA
# per-settlement hourly dataset.

HH_BASELINE_24H_KW = [
    0.35, 0.32, 0.30, 0.29, 0.30, 0.35,   # 00-05 overnight base
    0.55, 0.95, 1.20, 1.10, 0.90, 0.75,   # 06-11 morning ramp, midday dip
    0.65, 0.60, 0.65, 0.80, 1.10, 1.60,   # 12-17 afternoon rise
    1.95, 2.00, 1.85, 1.55, 1.10, 0.65,   # 18-23 evening peak, night fall
]
HH_SUMMER_MULTIPLIER = 1.4    # Israeli summer A/C uplift (Jun-Sep)
HH_SUMMER_MONTHS = {6, 7, 8, 9}


def household_baseline_kw_per_hh(hour_of_day: int, month: int = 7) -> float:
    """LCL-anchored non-EV household load, kW per household.

    Returns kW at the given hour of the day, with a summer A/C
    multiplier applied in Israeli summer months (Jun-Sep) to reflect
    the higher observed evening peaks.
    """
    base = HH_BASELINE_24H_KW[hour_of_day % 24]
    if month in HH_SUMMER_MONTHS:
        return base * HH_SUMMER_MULTIPLIER
    return base


class FeederAgent:
    """A single LV feeder with a transformer capacity constraint."""

    def __init__(
        self,
        feeder_id: int,
        transformer_kva: float = DEFAULT_TRANSFORMER_KVA,
        hours_in_year: int = 8760,
    ) -> None:
        self.feeder_id = feeder_id
        self.transformer_kva = transformer_kva
        self.ev_agents: list = []
        # Per-hour net load (kW).  + = import, - = export.
        self.load_kw = [0.0] * hours_in_year
        # Diagnostics.
        self.denied_discharges = 0
        self.denied_charges    = 0

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------
    def register(self, ev_agent) -> None:
        """Attach an EVAgent to this feeder."""
        self.ev_agents.append(ev_agent)
        ev_agent.feeder = self    # backref for the constraint check

    # ------------------------------------------------------------------
    # Constraint check.  Called by the EVAgent before committing an
    # action.  If the action would push aggregate transformer load
    # outside +/- transformer_kva, the action is denied.
    #
    # Household non-EV baseline load is added to the tracked load_kw
    # at query time, so the transformer constraint bites when V2G
    # discharge exceeds household import (the real constraint), not
    # only when EV actions alone exceed the transformer rating.
    # ------------------------------------------------------------------
    def _baseline_this_hour(self, current_hour: int) -> float:
        hour_of_day = current_hour % 24
        day_of_year = current_hour // 24
        # Rough month lookup: cumulative days per month (non-leap year)
        cum = (31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365)
        month = 1
        for m in range(12):
            if day_of_year < cum[m]:
                month = m + 1; break
        return household_baseline_kw_per_hh(hour_of_day, month) * len(self.ev_agents)

    def can_charge(self, requested_kw: float, current_hour: int) -> bool:
        baseline = self._baseline_this_hour(current_hour)
        prospective = self.load_kw[current_hour] + baseline + requested_kw
        return prospective <= self.transformer_kva

    def can_discharge(self, requested_kw: float, current_hour: int) -> bool:
        baseline = self._baseline_this_hour(current_hour)
        # Discharge (V2G export) SUBTRACTS from the household import.
        # Net load = baseline - V2G_export.  Can go negative (export to grid).
        prospective = self.load_kw[current_hour] + baseline - requested_kw
        return prospective >= -self.transformer_kva

    def record_charge(self, power_kw: float, current_hour: int) -> None:
        self.load_kw[current_hour] += power_kw

    def record_discharge(self, power_kw: float, current_hour: int) -> None:
        self.load_kw[current_hour] -= power_kw

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    def stats(self) -> dict:
        peak_import = max(self.load_kw)
        peak_export = -min(self.load_kw)
        # Constrained hours: load within 1 % of the +/- rating.
        rated = self.transformer_kva
        constrained_import = sum(1 for l in self.load_kw if l >=  rated * 0.99)
        constrained_export = sum(1 for l in self.load_kw if l <= -rated * 0.99)
        return {
            "feeder_id": self.feeder_id,
            "n_agents": len(self.ev_agents),
            "transformer_kva": rated,
            "peak_import_kw": round(peak_import, 1),
            "peak_export_kw": round(peak_export, 1),
            "constrained_import_hours": constrained_import,
            "constrained_export_hours": constrained_export,
            "denied_discharges": self.denied_discharges,
            "denied_charges":    self.denied_charges,
        }


# ---------------------------------------------------------------------------
# Fleet wiring helper: partition a list of EVAgents into feeders.
# ---------------------------------------------------------------------------
def feeder_params_for_country(country: str) -> tuple[int, float]:
    """Return (agents_per_feeder, transformer_kva) for the given country.

    Parameters sourced from Tang et al 2024 (UK) and the Israeli
    Electricity Authority 2023-24 report (IL).
    """
    c = country.strip().lower()
    if c in ("uk", "gb", "united kingdom"):
        return UK_AGENTS_PER_FEEDER, UK_TRANSFORMER_KVA
    if c in ("israel", "il"):
        return IL_AGENTS_PER_FEEDER, IL_TRANSFORMER_KVA
    raise ValueError(f"unknown country {country!r}; expected 'UK' or 'Israel'")


def build_feeders(
    ev_agents: list,
    agents_per_feeder: int = DEFAULT_AGENTS_PER_FEEDER,
    transformer_kva: float = DEFAULT_TRANSFORMER_KVA,
    hours_in_year: int = 8760,
) -> list:
    """Group EVAgents into FeederAgents in declaration order.

    The simplest deterministic mapping: agent i lives on
    feeder i // agents_per_feeder.  Each feeder is sized to
    transformer_kva.
    """
    feeders: list = []
    for idx, agent in enumerate(ev_agents):
        feeder_idx = idx // agents_per_feeder
        while feeder_idx >= len(feeders):
            feeders.append(FeederAgent(
                feeder_id=feeder_idx,
                transformer_kva=transformer_kva,
                hours_in_year=hours_in_year,
            ))
        feeders[feeder_idx].register(agent)
    return feeders


if __name__ == "__main__":
    # Smoke test
    f = FeederAgent(feeder_id=0, transformer_kva=250.0, hours_in_year=24)
    print(f"Created {f}")
    print(f"can_discharge(11 kW, hour=0): {f.can_discharge(11, 0)}")
    f.record_discharge(220, 0)
    print(f"After 220 kW of discharge recorded, can_discharge(11 kW): {f.can_discharge(11, 0)}")
    f.record_discharge(11, 0)
    print(f"After total 231 kW of discharge, can_discharge(20 kW): {f.can_discharge(20, 0)}")
    print(f"stats: {f.stats()}")
