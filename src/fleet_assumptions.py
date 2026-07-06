"""Fleet composition coefficients.

Two coefficients scale the per-agent ABM output up to fleet-level
estimates of V2G impact in Israel.

  alpha (alpha)  = share of the total vehicle fleet that is electric
                   The "EV penetration" knob.
  beta  (beta)   = share of the EV fleet that is V2G-capable (has a
                   bidirectional onboard charger plus a bidirectional
                   home wallbox the driver has chosen to enable)
                   The "V2G readiness" knob.

The downstream fleet-level V2G activity scales as alpha * beta * N_FLEET
where N_FLEET is the total Israeli passenger-car fleet.

References for the baseline values (June 2026):

  Israeli passenger-car fleet, 2026 estimate: ~3.5 million vehicles
    Source: Central Bureau of Statistics, Israel (CBS) annual fleet
    statistics, projected forward from 3.32M (2023) at the observed
    ~3% growth rate.

  Israeli EV stock, 2026: ~163,000 BEVs in service
    Source: Israeli EV Association / Ministry of Energy registry,
    May 2026 update.  ~70% YoY growth from 2024.

  alpha_today  = 163,000 / 3,500,000  =  0.0466
  alpha_2030   ~ 0.30  (Ministry of Energy 2030 target: 1M EVs)

  beta today: nearly zero in Israel.  Globally, ~10-15% of new EV models
  ship with bidirectional capability (Hyundai/Kia E-GMP, Ford F-150
  Lightning, Mitsubishi Outlander PHEV, Nissan Leaf, plus Tesla on
  expected 2025-26 firmware).  Of those, only a small fraction of
  drivers actually pair them with a bidirectional wallbox.
  beta realistic: 0.10 to 0.25 over the next 5 years; 0.50+ in mature
  V2G markets (UK Octopus Powerloop fleet operators).
"""

# -----------------------------------------------------------------------------
# Israeli fleet baseline (passenger cars)
# -----------------------------------------------------------------------------
N_FLEET_ISRAEL = 3_500_000   # total passenger cars, 2026 estimate

# Default fleet coefficients (Israeli baseline, today)
ALPHA_TODAY  = 0.047   # EV share of total fleet, May 2026
ALPHA_2030   = 0.300   # Ministry of Energy 2030 target (1M EVs / 3.5M fleet)

BETA_LOW     = 0.10    # conservative: only V2G-native EV models, early adoption
BETA_MID     = 0.25    # realistic 2028-30: most new EV models bidirectional
BETA_HIGH    = 0.75    # aspirational: V2G mandate / mass deployment

# Default values used by run_demo for headline results
ALPHA_DEFAULT = ALPHA_TODAY
BETA_DEFAULT  = BETA_LOW


def n_v2g_capable(
    alpha: float = ALPHA_DEFAULT,
    beta: float = BETA_DEFAULT,
    n_fleet: int = N_FLEET_ISRAEL,
) -> int:
    """Number of V2G-capable EVs in the fleet under (alpha, beta)."""
    return int(round(alpha * beta * n_fleet))


def n_evs(
    alpha: float = ALPHA_DEFAULT,
    n_fleet: int = N_FLEET_ISRAEL,
) -> int:
    """Number of EVs in the fleet under alpha."""
    return int(round(alpha * n_fleet))


if __name__ == "__main__":
    print("Fleet composition baseline (Israel, 2026 estimate)")
    print(f"  Total passenger-car fleet : {N_FLEET_ISRAEL:>10,} vehicles")
    print(f"  EVs today (alpha={ALPHA_TODAY:.3f})    : {n_evs(ALPHA_TODAY):>10,} EVs")
    print(f"  EVs 2030 target (alpha={ALPHA_2030:.2f}): {n_evs(ALPHA_2030):>10,} EVs")
    print()
    print(f"  V2G-capable EVs (today fleet, beta sweep):")
    for beta in (BETA_LOW, BETA_MID, BETA_HIGH):
        n = n_v2g_capable(ALPHA_TODAY, beta)
        print(f"    beta={beta:.2f} -> {n:>9,} V2G EVs")
    print()
    print(f"  V2G-capable EVs (2030 fleet, beta sweep):")
    for beta in (BETA_LOW, BETA_MID, BETA_HIGH):
        n = n_v2g_capable(ALPHA_2030, beta)
        print(f"    beta={beta:.2f} -> {n:>9,} V2G EVs")
