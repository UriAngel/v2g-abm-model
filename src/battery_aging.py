"""Battery aging — simplified Gasper 2023-style unified model.

W8 Batch D.  Splits battery degradation into:
  - Calendar aging: continuous SoH loss from time, modulated by SoC and
    temperature.  Happens every hour, regardless of charge or discharge.
  - Cycle aging:    SoH loss from throughput (kWh moved in or out of the
    battery this hour).  Happens only on charge or discharge.

Both reduce SoH (state of health), which starts at 1.0 (new battery) and
declines toward 0.8 (end-of-life convention for EV batteries).

Calibration anchors (NMC chemistry, 25°C Israeli summer):
  - Calendar aging: ~20% SoH loss over 10 years at baseline SoC = 0.6 with
    no cycling.  This matches industry consensus for NMC at typical
    temperatures (Wong et al. 2026 Figure 6 control case; Gasper et al.
    2023 unified model output).
  - Cycle aging: 0.7% additional SoH loss over 10 years from V2G operation
    on top of normal driving cycles, per Wong et al. 2026 Section 3.4
    finding for the conservative 50%-floor + overnight-only V2G strategy.

Future-batch extensions:
  - LFP chemistry (Gasper 2023 reports cycle aging is roughly 3x higher for
    LFP|Gr designs than NMC|Gr).
  - Temperature variation (Arrhenius dependence in the calendar term).
  - Depth-of-discharge dependence (currently captured implicitly via
    throughput).
"""

# Hours in a 10-year horizon used for calibration.
_HOURS_10Y = 10 * 365 * 24   # 87,600

# Calendar aging per hour at baseline SoC = 0.60, 25°C, NMC chemistry.
# Calibrated so 87,600 hours of pure rest gives 20% loss.
CALENDAR_AGING_PER_HOUR_BASELINE = 0.20 / _HOURS_10Y     # ~2.28e-6

# Cycle aging per kWh throughput.  Calibrated against a typical V2G
# participant in Wong et al. 2026: ~7,500 kWh of extra V2G throughput over
# 10 years -> 0.7% extra SoH loss.
CYCLE_AGING_PER_KWH_THROUGHPUT = 0.007 / 7_500           # ~9.3e-7

# NMC pack 2024 wholesale price ~$130/kWh.  Converted at ~3.7 NIS/USD.
BATTERY_REPLACEMENT_COST_NIS_PER_KWH = 480.0

# End-of-life convention: EV batteries are commonly retired at SoH = 0.80.
EOL_SOH = 0.80


def calendar_aging_this_hour(soc: float) -> float:
    """SoH loss from calendar aging in one hour at the given SoC.

    Higher SoC accelerates calendar aging.  Multiplier is centred at
    SoC = 0.6 (industry-typical resting SoC for EV batteries).  At SoC = 1.0
    aging is 1.2x baseline; at SoC = 0.3 it is 0.85x baseline.
    """
    multiplier = max(0.0, 1.0 + 0.5 * (soc - 0.6))
    return CALENDAR_AGING_PER_HOUR_BASELINE * multiplier


def cycle_aging_this_hour(kwh_throughput: float) -> float:
    """SoH loss from cycling, given the magnitude of throughput this hour.

    Throughput is the energy moved into or out of the battery (kWh).
    Aging scales linearly with throughput, matching the Gasper 2023
    unified model in the low-throughput regime.
    """
    return CYCLE_AGING_PER_KWH_THROUGHPUT * abs(kwh_throughput)


def aging_cost_per_kwh_discharged() -> float:
    """Aging cost (NIS) imputed to one kWh discharged in V2G operation.

    This number is added to each agent's OSP so the agent demands a
    higher price before agreeing to discharge.  It reflects the value
    of the battery wear induced by each discharged kWh.
    """
    # SoH loss per kWh × battery cost per kWh.
    # Useable battery is the SoH-effective portion, so cost is over the
    # full nameplate kWh.
    return CYCLE_AGING_PER_KWH_THROUGHPUT * BATTERY_REPLACEMENT_COST_NIS_PER_KWH
