"""Real ABM sweep over the V2G contractual SoC floor.

Uri/supervisor request (draft-1 review): revenue-per-car sensitivity to
the 50 % floor.  Same harness as sweep_w13a: 120-agent fleet, Israel,
V2G, 90 % max_soc cap, per-opted-in Daily Charger mean, multi-seed,
resumable JSON store.

Run:  python -m src.sweep_w13b_soc_floor <seed> [floors...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.agents import ev_agent as ev_module
from src.agents.ev_agent import (
    DAILY_CHARGER, PUBLIC_CHARGER, BEV_2ND_VEHICLE, THRESHOLD_CHARGER,
    COUNTERFACTUAL_V2G,
)
from src.run_w9_fleet import run_year

SWEEP_FLEET = {
    DAILY_CHARGER: 31, PUBLIC_CHARGER: 23,
    BEV_2ND_VEHICLE: 21, THRESHOLD_CHARGER: 45,
}

FLOORS = [0.40, 0.45, 0.50, 0.55, 0.60]

OUT = Path(__file__).resolve().parent.parent / "outputs" / "w13b_soc_floor_sweep.json"


def run_floor(floor: float, run_seed: int) -> dict:
    orig = ev_module.V2G_MIN_SOC_FLOOR if hasattr(ev_module, "V2G_MIN_SOC_FLOOR") else None
    # locate the floor constant
    name = None
    for cand in ("V2G_MIN_SOC_FLOOR", "V2G_SOC_FLOOR", "V2G_FLOOR", "MIN_V2G_SOC"):
        if hasattr(ev_module, cand):
            name = cand
            break
    assert name, "floor constant not found"
    orig = getattr(ev_module, name)
    setattr(ev_module, name, floor)
    try:
        out = run_year(country="Israel", counterfactual=COUNTERFACTUAL_V2G,
                       shares=SWEEP_FLEET, verbose=False, run_seed=run_seed)
    finally:
        setattr(ev_module, name, orig)
    r = {}
    for typ in (DAILY_CHARGER, BEV_2ND_VEHICLE):
        opt = [a.state.cumulative_v2g_discharge_kwh for a in out["agents"]
               if a.typology == typ and a.state.v2g_opted_in]
        r[typ] = sum(opt) / len(opt) if opt else 0.0
    return {"floor": floor, "seed": run_seed,
            "dc_optin": r[DAILY_CHARGER], "bev_optin": r[BEV_2ND_VEHICLE],
            "wall_time_s": out["wall_time_s"]}


def main() -> None:
    seed = int(sys.argv[1])
    floors = [float(x) for x in sys.argv[2:]] or FLOORS
    store = {"results": []}
    if OUT.exists():
        store = json.load(open(OUT))
    for f in floors:
        if any(r["floor"] == f and r["seed"] == seed for r in store["results"]):
            print(f"skip {f} seed {seed}")
            continue
        r = run_floor(f, seed)
        store["results"].append(r)
        json.dump(store, open(OUT, "w"), indent=1)
        print(f"floor {f:.2f} seed {seed}: DC {r['dc_optin']:,.0f} kWh, "
              f"BEV {r['bev_optin']:,.0f} kWh ({r['wall_time_s']:.1f}s)")


if __name__ == "__main__":
    main()
