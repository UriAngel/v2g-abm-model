# V2G ABM — Code Review Guide

**Repo path**: `/Users/uriangel/Documents/GitHub/v2g-abm-model/`

Everything is Python. Start here if you want to inspect the model before your next supervisor meeting.

## Recommended reading order (roughly bottom-up)

### 1. The inputs (30 min)
Fixed data that everything else consumes. Read these first so you know what's baked in.

- `src/aging_table_lit.py` — Wong 2026 aging table (per-typology × chemistry V2G effect: NEUTRAL/SLIGHT/DECREASE/LARGE/IMPROVE). Also Wong Fig 5 annual V2G energy per typology and Wong Fig 3 V0 baseline capacity loss.
- `src/pricing.py` — Israeli TAOZ tariff schedule (summer/winter, weekday/weekend, hour-of-day).
- `src/pricing_uk.py` — UK Ofgem cap, Octopus Go, Octopus Power Pack, Powerloop discharge signal, BMRS wholesale.
- `src/battery_aging.py` — calendar + cycle aging cost functions, BNEF 2025 NMC/LFP prices.
- `src/aggregator_stub.py` — Sigenergy charger CAPEX build-up (Israel and UK), Sciurus £725 reference.
- `src/fleet_assumptions.py` — Israeli fleet size, α (EV share), β·γ combined.

### 2. The agents (60 min — the heart of the model)

- `src/agents/ev_agent.py` — the meat.
  - `TYPOLOGY_PROFILES` dict at the top: Wong Table 1 numbers per typology (Daily / Public / BEV 2nd / Threshold). This is where drive_days_per_week, km/day, target_soc, plug-in probability all live.
  - `EVAgent` class + `step()` method: hourly decision loop. Read `_should_plug_in`, `_is_driving_now`, `_dispatch_v2g`, `_should_charge`.
  - Wong Table 1 plug-in probability (6.11/week = 87%) is applied via `plugin_events_per_week` field.
- `src/grid_agent.py` — feeder + transformer constraint. `FeederAgent` class. Household non-EV baseline load (LCL 24-hour shape × 1.4 Israel summer multiplier). Check `check_v2g_export_allowed`.

### 3. The orchestrator (20 min)

- `src/run_w9_fleet.py` — `run_year(country, counterfactual, shares)` function. Runs 8,760 hours, builds fleet, dispatches OSP-priority per feeder. `DEFAULT_FLEET_SHARES` is Wong's California composition scaled to 240 agents.
- `src/main.py` — trivial entry point.

### 4. Economics (30 min)

- `src/smoke_w10r_economics.py` — driver P&L calculation.
  - `OBSERVED_V2G_KWH_PER_YEAR` dict — **the important table**. These are the numbers all P&L plots use. Current values are per-opted-in-EV means from a fresh 240-agent Israel V2G run.
  - `compute()` function — annual revenue, battery cost, operating P&L, 10-year P&L, payback.

### 5. Plots (skim, ~20 min)

Each plot script is standalone, reads OBSERVED (or its own hardcoded copy), builds a figure with matplotlib. Files are named `plot_wXXY_*.py` where XX is the work-package week and Y is a letter.

Key files to skim:
- `src/plot_w12m_retail_vs_retail.py` — slide 5 / Fig 4.2. **Has own `ACTIVE = {DC: 5485, BEV: 6920}` — a repeat of OBSERVED. Same for the two below.**
- `src/plot_w11c_pnl_active.py` — slide 6 / 7 P&L, Fig 4.3 / 4.4.
- `src/plot_w11b_aggregator_per_ev.py` — slide 10, Fig 4.6.
- `src/plot_w11_aggregator_economics.py` — slide 9 α×βγ heatmap, Fig 4.5.
- `src/plot_w12h_sensitivity_summary.py` — full 7-panel sensitivity (Ch4 Fig 4.7 combined).
- `src/plot_w12t_sensitivity_split.py` — three-slide sensitivity (12a/b/c on deck, 4.7a/b/c in Ch4).
- `src/plot_w12ae_soc_week.py` — SoC-over-week for all four typologies (Fig 4.1).

### 6. Sweeps (skim)

- `src/sweep_w12w_drive_days.py` — real ABM sweep over drive_days_per_week. Latest version overrides BEV target_soc to match DC so the two typologies converge at D=0 physically.
- `src/calib_w12y_baseline.py` — recalibration of OBSERVED with 240-agent run.

## What to look for while reviewing

1. **Are the hardcoded per-typology numbers in each `plot_*.py` still in sync with `OBSERVED_V2G_KWH_PER_YEAR`?**
   Search for `2900`, `4100`, `2742`, `2700`, `2619`, `3754` — those are OLD values I updated. Should now show 5485 / 6920 everywhere.

2. **Is Wong Table 1 applied consistently?**
   - drive_days_per_week (DC 6.43, Public 6.41, BEV 4.74, Threshold 6.44)
   - target_soc (DC 89.2%, BEV 87%, Threshold 85%)
   - plug-in probability (DC + BEV: 6.11/week = 87%; Public: 0; Threshold: threshold rule not probabilistic)

3. **Aging model coherence**:
   - `aging_table_lit.py` says LFP is in "LARGE" category under V2G for every typology (per Wong Fig 6).
   - That means LFP degrades FASTER than NMC in this model, not slower.
   - Slide 11 in the deck shows this.

4. **Grid constraint**:
   - `grid_agent.py` uses 517 kVA transformer for network-average configuration (54 HH per feeder, IEC 2024).
   - Alternative residential-only: 50 HH × 3 kW ADMD.
   - Should never bind at current β·γ (< 0.5).

## Fastest way to run the model yourself

```bash
cd ~/Documents/GitHub/v2g-abm-model
python3 -m src.smoke_w10d_twocountry   # 80-agent smoke test, both countries, ~30s
python3 -m src.smoke_w10r_economics    # driver P&L table
python3 -m src.calib_w12y_baseline     # 240-agent full baseline, ~10s
```

## If you find something wrong

Add a comment like `# WRONG: <issue>` in the code and I'll look at it next session.
