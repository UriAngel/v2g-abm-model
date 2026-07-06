"""Battery aging — simplified Gasper 2023-style unified model.

Splits battery degradation into:
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
  - Cycle aging: order-of-magnitude per-kWh rate (~0.7% SoH per ~7,500 kWh
    of throughput).  Reported V2G aging figures come from Wong et al.
    2026's published per-typology effects, not from this coefficient.

Possible extensions:
  - LFP chemistry (Gasper 2023 reports cycle aging is roughly 3x higher for
    LFP|Gr designs than NMC|Gr).
  - Temperature variation (Arrhenius dependence in the calendar term).
  - Depth-of-discharge dependence (currently captured implicitly via
    throughput).
"""

# Hours in a 10-year horizon used for calibration.
_HOURS_10Y = 10 * 365 * 24   # 87,600

# Calendar aging per hour, NMC|Gr B1 (calendar-dominated chemistry).
# Anchored to Wong 2026 Section 2.3:
#   * Wong NMC|Gr B1 V0 control 10-year total capacity loss ~18 %
#     (visual read of Wong Fig 3; approximate — exact value pending the
#     supplementary dataset).
#   * Wong reports calendar share of total degradation = 79.4 % for
#     NMC|Gr B1 (Sec 2.3 quote).
#   * Calendar-only 10-year loss = 0.18 x 0.794 = 0.1429 ~ 14.3 %.
CALENDAR_AGING_PER_HOUR_BASELINE = 0.143 / _HOURS_10Y    # ~1.63e-6

# Cycle aging per kWh throughput, NMC baseline.
# The "0.7 % over 10 y for ~7,500 kWh" pairing is not a published Wong
# number (see aging_table_lit.py).  The coefficient below is an
# order-of-magnitude rate that produces plausible SoH deltas in the
# in-simulation tracker.  Reported 10-year V2G aging in
# plot_w10h_aging_wong.py comes NOT from this coefficient but from
# Wong's published categorical effect (IMPROVE / NEUTRAL / SLIGHT /
# DECREASE / LARGE via WONG_V2G_EFFECT) scaled by the observed/Wong
# volume ratio.
CYCLE_AGING_PER_KWH_THROUGHPUT_NMC = 0.007 / 7_500       # ~9.3e-7 (order-of-magnitude)

# LFP|Gr design shows higher sensitivity to cycle aging in Gasper 2023
# unified model output (Wong 2026 footnote: "the battery with the highest
# sensitivity to cycle aging (LFP|Gr)").  Multiplier roughly 3x NMC under
# the same V2G strategy.
CYCLE_AGING_LFP_MULTIPLIER = 3.0
CYCLE_AGING_PER_KWH_THROUGHPUT_LFP = CYCLE_AGING_PER_KWH_THROUGHPUT_NMC * CYCLE_AGING_LFP_MULTIPLIER

# Calendar aging is roughly equivalent between chemistries at 25°C
# (Gasper 2023, NMC vs LFP).  Use the same baseline.

# Battery replacement cost (NIS/kWh).  Anchored to the BloombergNEF
# 2025 lithium-ion battery price survey (published December 2025):
#   * BEV-grade NMC pack average: $128 / kWh   (was $130 in 2024)
#   * BEV-grade LFP pack average:  $81 / kWh   (was  $95 in 2024)
#   * 2026 outlook: roughly -3 % across the board (~$124 NMC, ~$78 LFP)
# Source: BloombergNEF "New record lows for battery prices" Dec 2025.
# USD -> NIS conversion at 4.7 (mid-2026 rate).
BATTERY_REPLACEMENT_COST_NIS_PER_KWH_NMC = 600.0   # $128/kWh * 4.7 NIS/USD
BATTERY_REPLACEMENT_COST_NIS_PER_KWH_LFP = 380.0   # $ 81/kWh * 4.7 NIS/USD

# Convenience aliases defaulting to NMC (imported by several scripts).
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

    Flat per-hour rate, independent of SoC, so all typologies
    accumulate identical calendar aging given the same horizon.  The
    Gasper 2023 SoC-modulation is intentionally omitted here because
    typology SoC profiles vary widely and the resulting calendar-aging
    spread (35-40%) misleadingly amplifies typology effects.

    The `soc` argument is retained for interface compatibility with the
    EVAgent step() call site and is currently unused.  A future revision
    may introduce SoC sensitivity as an explicit secondary term so it
    is visible separately from the time-driven baseline.
    """
    del soc  # currently unused; see docstring
    return CALENDAR_AGING_PER_HOUR_BASELINE


def cycle_aging_this_hour(kwh_throughput: float, chemistry: str = "NMC") -> float:
    """SoH loss from cycling, given throughput and chemistry."""
    return cycle_aging_coefficient(chemistry) * abs(kwh_throughput)


def aging_cost_per_kwh_discharged(chemistry: str = "NMC") -> float:
    """Deprecated; not used in any model decision.

    This §3.8-style formulation multiplies the per-kWh cycle aging
    coefficient (a fraction of SoH consumed) by the per-kWh-of-capacity
    battery replacement cost, which is dimensionally inconsistent and
    yields a figure roughly battery_size_kWh times too small.

    Aging is therefore not folded into the OSP.  Battery aging is
    reported as a physical consequence of operation, via the SoH
    milestones returned by `project_soh_milestones`, not priced into
    discharge decisions.  This matches Sciurus and Wong's public
    reporting style.

    Retained only so plot scripts that import the name still work.
    """
    return cycle_aging_coefficient(chemistry) * battery_replacement_cost(chemistry)


def project_soh_milestones(
    cal_aging_observed: float,
    cyc_aging_observed: float,
    hours_observed: int = 168,
) -> dict[int, dict]:
    """Project SoH at year 1, 5, 10 from observed aging totals.

    Linearly extrapolates observed calendar + cycle SoH loss from a
    short simulation horizon (typically one week) to year-1, 5 and 10
    milestones.  Returns a dict keyed by years with both the cumulative
    SoH loss and the resulting SoH at that point.

    Parameters
    ----------
    cal_aging_observed : float
        Cumulative calendar SoH loss observed over `hours_observed`.
    cyc_aging_observed : float
        Cumulative cycle SoH loss observed over `hours_observed`.
    hours_observed : int
        Length of the simulation window the aging was measured over.
    """
    hours_per_year = 8760
    annual_cal = cal_aging_observed * (hours_per_year / hours_observed)
    annual_cyc = cyc_aging_observed * (hours_per_year / hours_observed)
    out: dict[int, dict] = {}
    for years in (1, 5, 10):
        cal_loss = annual_cal * years
        cyc_loss = annual_cyc * years
        soh = max(0.0, 1.0 - cal_loss - cyc_loss)
        out[years] = {
            "cal_loss_pct": cal_loss * 100,
            "cyc_loss_pct": cyc_loss * 100,
            "total_loss_pct": (cal_loss + cyc_loss) * 100,
            "soh_pct": soh * 100,
            "above_eol": soh > EOL_SOH,
        }
    return out
