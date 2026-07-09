"""Real ABM sweeps for the plug-in-probability and return-hour panels.

Replaces the pre-cap data previously hardcoded in panels (4) and (6) of
the sensitivity figure.  Same harness as sweep_w12w_drive_days: 120-agent
fleet in the calibration proportions, Israel, V2G counterfactual, 90 %
max_soc cap active, per-opted-in means, multi-seed.

Sweep A (plugin):  Daily Charger plugin_events_per_week
                   in {5.50, 6.11, 6.50, 7.00}  (6.11 = Wong 87 % anchor)
Sweep B (return):  Daily Charger return_hour_mean in {16..20} (18 = base)

Each (point, seed) result is appended to a JSON store so the sweep can be
executed in short chunks.

Run:  python -m src.sweep_w13a_plugin_return <plugin|return> <seed> [points...]
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
    DAILY_CHARGER:     31,
    PUBLIC_CHARGER:    23,
    BEV_2ND_VEHICLE:   21,
    THRESHOLD_CHARGER: 45,
}

GRIDS = {
    "plugin": [5.50, 6.11, 6.50, 7.00],
    "return": [16, 17, 18, 19, 20],
}
KEYS = {
    "plugin": "plugin_events_per_week",
    "return": "return_hour_mean",
}

OUT = Path(__file__).resolve().parent.parent / "outputs" / "w13a_plugin_return_sweep.json"


def run_point(sweep: str, value: float, run_seed: int) -> dict:
    key = KEYS[sweep]
    orig = ev_module.TYPOLOGY_PROFILES[DAILY_CHARGER][key]
    ev_module.TYPOLOGY_PROFILES[DAILY_CHARGER][key] = value
    try:
        out = run_year(country="Israel", counterfactual=COUNTERFACTUAL_V2G,
                       shares=SWEEP_FLEET, verbose=False, run_seed=run_seed)
    finally:
        ev_module.TYPOLOGY_PROFILES[DAILY_CHARGER][key] = orig

    optin = [a.state.cumulative_v2g_discharge_kwh for a in out["agents"]
             if a.typology == DAILY_CHARGER and a.state.v2g_opted_in]
    return {
        "sweep": sweep, "value": value, "seed": run_seed,
        "dc_mean_optin": sum(optin) / len(optin) if optin else 0.0,
        "dc_n_optin": len(optin),
        "wall_time_s": out["wall_time_s"],
    }


def main() -> None:
    sweep = sys.argv[1]
    seed = int(sys.argv[2])
    points = [float(x) for x in sys.argv[3:]] or GRIDS[sweep]

    store = {"results": []}
    if OUT.exists():
        store = json.load(open(OUT))

    for v in points:
        if any(r["sweep"] == sweep and r["value"] == v and r["seed"] == seed
               for r in store["results"]):
            print(f"skip {sweep} {v} seed {seed} (done)")
            continue
        r = run_point(sweep, v, seed)
        store["results"].append(r)
        with open(OUT, "w") as f:
            json.dump(store, f, indent=1)
        print(f"{sweep} {v:>5} seed {seed}: DC opt-in "
              f"{r['dc_mean_optin']:>7,.0f} kWh (n={r['dc_n_optin']}, "
              f"{r['wall_time_s']:.1f}s)")


if __name__ == "__main__":
    main()
