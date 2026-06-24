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

# Cycle aging per kWh throughput, NMC baseline.  Calibrated against a
# typical V2G participant in Wong et al. 2026: ~7,500 kWh of extra V2G
# throughput over 10 years -> 0.7% extra SoH loss for NMC|Gr.
CYCLE_AGING_PER_KWH_THROUGHPUT_NMC = 0.007 / 7_500       # ~9.3e-7

# LFP|Gr design shows higher sensitivity to cycle aging in Gasper 2023
# unified model output (Wong 2026 footnote: "the battery with the highest
# sensitivity to cycle aging (LFP|Gr)").  Multiplier roughly 3x NMC under
# the same V2G strategy.
CYCLE_AGING_LFP_MULTIPLIER = 3.0
CYCLE_AGING_PER_KWH_THROUGHPUT_LFP = CYCLE_AGING_PER_KWH_THROUGHPUT_NMC * CYCLE_AGING_LFP_MULTIPLIER

# Calendar aging is roughly equivalent between chemistries at 25°C
# (Gasper 2023, NMC vs LFP).  Use the same baseline.

# Battery replacement cost (NIS/kWh).  Differs by chemistry: LFP is
# cheaper because no cobalt or nickel; NMC is more expensive.
BATTERY_REPLACEMENT_COST_NIS_PER_KWH_NMC = 480.0   # NMC pack 2024 ~$130/kWh
BATTERY_REPLACEMENT_COST_NIS_PER_KWH_LFP = 350.0   # LFP pack 2024 ~$95/kWh

# Backwards-compatible name (used by older code; defaults to NMC).
BATTERY_REPLACEMENT_COST_NIS_PER_KWH = BATTERY_REPLACEMENT_COST_NIS_PER_KWH_NMC
CYCLE_AGING_PER_KWH_THROUGHPUT = CYCLE_AGING_PER_KWH_THROUGHPUT_NMC

# End-of-life convention: EV batteries are commonly retired at SoH = 0.80.
EOL_SOH = 0.80


def cycle_aging_coefficient(chemistry: str) -> float:
    """Per-kWh cycle aging coefficient for the chemistry."""
    if chemistry == "LFP":
        return CYCLE_AGING_PER_KWH_THROUGHPUT_LFP
    return CYCLE_AGING_PER_KWH_THROUGHPUT_NMC


def battery_replacement_cost(chemistry: str) -> float:
    """Per-kWh battery replacement cost (NIS) for the chemistry."""
    if chemistry == "LFP":
        return BATTERY_REPLACEMENT_COST_NIS_PER_KWH_LFP
    return BATTERY_REPLACEMENT_COST_NIS_PER_KWH_NMC


def calendar_aging_this_hour(soc: float = 0.6) -> float:
    """SoH loss from calendar aging in one hour.

    W10.A.2: flat per-hour rate, independent of SoC, so all typologies
    accumulate identical calendar aging given the same horizon.  The
    Gasper 2023 SoC-modulation is intentionally dropped here because
    typology SoC profiles vary widely and the resulting calendar-aging
    spread (35-40%) misleadingly amplifies typology effects.

    The `soc` argument is retained for backwards compatibility with the
    EVAgent step() call site and is currently unused.  A future revision
    may reintroduce SoC sensitivity as an explicit secondary term so it
    is visible separately from the time-driven baseline.
    """
    del soc  # currently unused; see docstring
    return CALENDAR_AGING_PER_HOUR_BASELINE


def cycle_aging_this_hour(kwh_throughput: float, chemistry: str = "NMC") -> float:
    """SoH loss from cycling, given throughput and chemistry."""
    return cycle_aging_coefficient(chemistry) * abs(kwh_throughput)


def aging_cost_per_kwh_discharged(chemistry: str = "NMC") -> float:
    """Aging cost (NIS) imputed to one kWh discharged in V2G operation.

    Differs by chemistry: LFP has higher cycle wear per kWh but lower
    replacement cost; NMC is the opposite.  Net per-kWh aging cost ends
    up roughly in the same ballpark for both, but LFP edges slightly
    higher because of the cycle-wear multiplier.
    """
    return cycle_aging_coefficient(chemistry) * battery_replacement_cost(chemistry)
