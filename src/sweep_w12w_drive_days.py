"""Real ABM sweep over drive_days_per_week.

For D = 0, 1, 2, 3, 4, 5, 6, 7 (plus the Wong baseline values 4.74 and 6.43):
  1. Monkey-patch TYPOLOGY_PROFILES[Daily Charger]["drive_days_per_week"] = D
  2. Monkey-patch TYPOLOGY_PROFILES[BEV 2nd Vehicle]["drive_days_per_week"] = D
  3. Build a fleet of only DC + BEV (Public/Threshold produce ~0 V2G)
  4. Call run_year(country=Israel, counterfactual=V2G) for 8,760 hours
  5. Record mean annual V2G kWh per opted-in agent of each typology

Numbers are then written to a JSON so the plot script can consume them.

Run:  python -m src.sweep_w12w_drive_days
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from src.agents import ev_agent as ev_module
from src.agents.ev_agent import (
    DAILY_CHARGER,
    BEV_2ND_VEHICLE,
    COUNTERFACTUAL_V2G,
)
from src.run_w9_fleet import run_year


# 80-agent fleet with the SAME PROPORTIONS as DEFAULT_FLEET_SHARES (per
# smoke_w10d_twocountry.SMOKE_FLEET).  Keeps SEM opt-in mix and feeder
# loading representative of the 240-agent calibration used for slide 6.
from src.agents.ev_agent import (
    PUBLIC_CHARGER, THRESHOLD_CHARGER,
)
SWEEP_FLEET = {
    DAILY_CHARGER:     31,   # 26 %
    PUBLIC_CHARGER:    23,   # 19 %
    BEV_2ND_VEHICLE:   21,   # 17 %
    THRESHOLD_CHARGER: 45,   # 38 %
}   # 120 agents; more samples per typology to smooth Monte-Carlo jitter

DRIVE_DAYS_GRID = [0, 1, 2, 3, 4, 4.74, 5, 6, 6.43, 7]

OUT = Path(__file__).resolve().parent.parent / "outputs" / "w12w_drive_days_sweep.json"


def run_at_D(D: float) -> dict:
    # Snapshot originals so we can restore
    dc_orig  = ev_module.TYPOLOGY_PROFILES[DAILY_CHARGER]["drive_days_per_week"]
    bev_orig = ev_module.TYPOLOGY_PROFILES[BEV_2ND_VEHICLE]["drive_days_per_week"]
    # Also override BEV target_soc to match DC so the two typologies
    # converge physically at D=0 (only real difference then is km/drive-day).
    bev_soc_orig = ev_module.TYPOLOGY_PROFILES[BEV_2ND_VEHICLE]["target_soc"]

    ev_module.TYPOLOGY_PROFILES[DAILY_CHARGER]["drive_days_per_week"]   = D
    ev_module.TYPOLOGY_PROFILES[BEV_2ND_VEHICLE]["drive_days_per_week"] = D
    ev_module.TYPOLOGY_PROFILES[BEV_2ND_VEHICLE]["target_soc"] = \
        ev_module.TYPOLOGY_PROFILES[DAILY_CHARGER]["target_soc"]

    try:
        out = run_year(country="Israel", counterfactual=COUNTERFACTUAL_V2G,
                        shares=SWEEP_FLEET, verbose=False)
    finally:
        ev_module.TYPOLOGY_PROFILES[DAILY_CHARGER]["drive_days_per_week"]   = dc_orig
        ev_module.TYPOLOGY_PROFILES[BEV_2ND_VEHICLE]["drive_days_per_week"] = bev_orig
        ev_module.TYPOLOGY_PROFILES[BEV_2ND_VEHICLE]["target_soc"] = bev_soc_orig

    dc_v2g   = []
    bev_v2g  = []
    dc_optin_v2g  = []
    bev_optin_v2g = []
    for a in out["agents"]:
        kwh = a.state.cumulative_v2g_discharge_kwh
        if a.typology == DAILY_CHARGER:
            dc_v2g.append(kwh)
            if a.state.v2g_opted_in: dc_optin_v2g.append(kwh)
        elif a.typology == BEV_2ND_VEHICLE:
            bev_v2g.append(kwh)
            if a.state.v2g_opted_in: bev_optin_v2g.append(kwh)

    return {
        "D": D,
        "dc_mean_all":     sum(dc_v2g)/len(dc_v2g)   if dc_v2g else 0.0,
        "dc_mean_optin":   sum(dc_optin_v2g)/len(dc_optin_v2g)   if dc_optin_v2g else 0.0,
        "dc_n_optin":      len(dc_optin_v2g),
        "bev_mean_all":    sum(bev_v2g)/len(bev_v2g) if bev_v2g else 0.0,
        "bev_mean_optin":  sum(bev_optin_v2g)/len(bev_optin_v2g) if bev_optin_v2g else 0.0,
        "bev_n_optin":     len(bev_optin_v2g),
        "wall_time_s":     out["wall_time_s"],
    }


def main() -> None:
    results = []
    t0 = time.time()
    for D in DRIVE_DAYS_GRID:
        r = run_at_D(D)
        results.append(r)
        print(f"D={D:>5.2f}  DC(opt-in)={r['dc_mean_optin']:>7,.0f} kWh (n={r['dc_n_optin']:>2}), "
              f"BEV(opt-in)={r['bev_mean_optin']:>7,.0f} kWh (n={r['bev_n_optin']:>2}), "
              f"t={r['wall_time_s']:.1f}s")
    total_t = time.time() - t0
    print(f"\nTotal wall time: {total_t:.1f}s")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"results": results, "fleet": SWEEP_FLEET,
                   "country": "Israel", "counterfactual": "V2G"}, f, indent=2)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
