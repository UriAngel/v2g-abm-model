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

# Calendar aging per hour, NMC|Gr B1 (calendar-dominated chemistry).
# W10.I (June 2026): re-anchored to Wong 2026 Section 2.3.
#   * Wong NMC|Gr B1 V0 control 10-year total capacity loss ~18 %
#     (visual read of Wong Fig 3; replace with exact number when the
#     supplementary CSV becomes available).
#   * Wong reports calendar share of total degradation = 79.2 % for
#     NMC|Gr B1 (Sec 2.3 quote).
#   * Calendar-only 10-year loss = 0.18 x 0.792 = 0.1426 ~ 14.3 %.
# Was 0.20 / HOURS_10Y in W10.A-F; that 20 % figure was an internal
# approximation, NOT a published Wong number.  Reduced ~40 % to match
# the actual published values.
CALENDAR_AGING_PER_HOUR_BASELINE = 0.143 / _HOURS_10Y    # ~1.63e-6

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
    """DEPRECATED in W10.F.

    The original §3.8 formulation multiplied the per-kWh cycle aging
    coefficient (a fraction of SoH consumed) by the per-kWh-of-capacity
    battery replacement cost, which is dimensionally wrong and yields a
    figure that is roughly battery_size_kWh times too small.

    W10.F decision: stop folding aging into OSP at all.  Battery aging
    is reported as a physical consequence of operation, via the SoH
    milestones returned by `project_soh_milestones`, not priced into
    discharge decisions.  This matches Sciurus and Wong's public
    reporting style and dodges the §3.8 calibration question entirely.

    Left in place only so older plot scripts that import the name still
    work; should not influence any new model decision.
    """
    return cycle_aging_coefficient(chemistry) * battery_replacement_cost(chemistry)


def project_soh_milestones(
    cal_aging_observed: float,
    cyc_aging_observed: float,
    hours_observed: int = 168,
) -> dict[int, dict]:
    """W10.F: project SoH at year 1, 5, 10 from observed aging totals.

    Linearly extrapolates observed calendar + cycle SoH loss from a
    short simulation horizon (typically one week) to the year-1, 5, 10
    milestones David asked to see in the M6 follow-up.  Returns a dict
    keyed by years with both the cumulative SoH loss and the resulting
    SoH at that point.

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
