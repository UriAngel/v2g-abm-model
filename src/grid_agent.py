"""Grid agent: feeder-level transformer constraint (W9.F).

A FeederAgent models a single low-voltage distribution feeder serving a
group of households.  It carries a transformer with a finite kVA rating.
The aggregator's discharge dispatch must respect this rating: at most
TRANSFORMER_KVA worth of net export can flow through the transformer in
any given hour, regardless of how many V2G-willing EVs are connected.

Design parameters (per David's revised W9 spec):

  * Single layer (feeder only).  No separate SubstationAgent.
  * Default feeder size: 50 households, 250 kVA transformer.  Matches
    Israeli urban LV feeder norms (~5 kVA peak per household).
  * Discharge dispatch: when a feeder is at constraint and not all
    V2G-willing EVs can fit, the lowest-OSP (most willing) agents are
    dispatched first.  Implemented at the run-loop level by sorting
    each feeder's EV list by OSP ascending before each hour's step
    (see run_w9_fleet in plot scripts).

Convention:
  load_kw[h] is the NET load on the transformer at hour h, measured as
    + positive when household consumption exceeds local generation
      (transformer importing from the grid),
    - negative when V2G discharge exceeds household consumption
      (transformer exporting to the grid).
  The transformer constraint is |load_kw[h]| <= TRANSFORMER_KVA.
"""

DEFAULT_TRANSFORMER_KVA = 250.0
DEFAULT_AGENTS_PER_FEEDER = 50


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
    # ------------------------------------------------------------------
    def can_charge(self, requested_kw: float, current_hour: int) -> bool:
        prospective = self.load_kw[current_hour] + requested_kw
        return prospective <= self.transformer_kva

    def can_discharge(self, requested_kw: float, current_hour: int) -> bool:
        # Discharge appears on the feeder as negative kW.
        prospective = self.load_kw[current_hour] - requested_kw
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
