# Session Handoff — V2G Dissertation

Uri Angel, MSc Energy Systems, Oxford. Supervisor: Dr David Wallom (Oxford e-Research Centre).
Dissertation: comparing residential V2G economics between Israel and the UK.

**How to use this document**: read it top-to-bottom before doing anything. It captures the current state after ~2 days of intensive iteration. Do NOT invent numbers — every value here traces to a specific source. If you're unsure, re-run the ABM (`python3 -m src.calib_w12y_baseline`, ~10s) and compare.

---

## Current file versions (as of handoff)

All paths are on Uri's Mac.

| File | Version | Location |
|------|---------|----------|
| David deck | **v22** | `~/Desktop/Dissertation/Supervisor_Meetings/V2G_Meeting8_v22.pptx` |
| Regulator deck | **v15** | `~/Desktop/Dissertation/Supervisor_Meetings/V2G_Regulator_Deck_v15.pptx` |
| Chapter 4 Results | **v23** | `~/Desktop/Dissertation/Manuscript/04_Results_v23.docx` |
| Chapter 1 Introduction | v4 | `~/Desktop/Dissertation/Manuscript/01_Introduction_v4.docx` |
| Chapter 2 Literature Review | v4 | `~/Desktop/Dissertation/Manuscript/02_Literature_Review_v4.docx` |
| Chapter 3 Methodology | v5 | `~/Desktop/Dissertation/Manuscript/03_Methodology_v5.docx` |
| Chapter 5 Discussion | v3 | `~/Desktop/Dissertation/Manuscript/05_Discussion_v3.docx` |
| References | v5 | `~/Desktop/Dissertation/Manuscript/References_v5.docx` |
| Interactive dashboard | current | `~/Desktop/Dissertation/V2G_Sensitivity_Dashboard/index.html` |
| Code repo | live | `~/Documents/GitHub/v2g-abm-model/` |
| Code review guide | current | `~/Documents/GitHub/v2g-abm-model/CODE_REVIEW_GUIDE.md` |

Older versions are archived under each folder's `old_versions/` subfolder.

---

## The three big framing decisions we made

### 1. Per-opted-in-EV, NOT fleet-mean
Every number in the deck / Ch4 / dashboard refers to **one participating driver**, not the fleet-averaged (which would include non-participants dispatching zero).
- OBSERVED constant in `smoke_w10r_economics.py`: DC 4,820 kWh, BEV 6,220 kWh — these are `total_dispatched_kwh / n_opted_in_agents`.
- Verified live: fleet-mean would be ~2,410 / 2,427 (half the current values, since ~50% opt-in).

### 2. NET revenue, not gross
Revenue everywhere = kWh × peak_price − kWh / RTE × off_peak_price.
For Israel: 4,820 × 1.6895 − 4,820 / 0.9025 × 0.528 = 8,144 − 2,820 = **5,323 NIS/yr NET** for DC.
BEV: **6,870 NIS/yr NET**.
The kWh × peak = gross (8,144 / 10,509) also appears in the dashboard breakdown for transparency.

### 3. 90% max_soc cap for V2G-opted-in agents
Anchored on **Sciurus/Kaluza mobile app pattern** (users set min & max SoC bounds; aggregator dispatches within them) + **Kempton & Tomić 2005** (battery longevity 80% guideline) + **Wong 2026 Table 1** (observed 89.2% mean).
Code: `V2G_MAX_SOC = 0.90` in `ev_agent.py`, applied only when `self.state.v2g_opted_in == True`.
Effect: reduced DC opt-in from 5,485 → 4,820 kWh (−12%), BEV 6,920 → 6,220 (−10%).

---

## Model architecture (2-minute summary)

The ABM is written in Python, agent-based, hourly time-step over 8,760 h (one year).

```
src/
├── agents/ev_agent.py          # EVAgent class + TYPOLOGY_PROFILES + step() dispatch
├── grid_agent.py               # FeederAgent (transformer + household baseline load)
├── run_w9_fleet.py             # run_year() orchestrator
├── pricing.py                  # Israel TAOZ tariff (peak/off-peak by season/hour/day)
├── pricing_uk.py               # UK Ofgem cap + Octopus tariffs + BMRS wholesale
├── battery_aging.py            # calendar + cycle aging cost
├── aging_table_lit.py          # Wong 2026 categorical V2G effect table
├── aggregator_stub.py          # Sigenergy CAPEX + Sciurus £725 constants
├── vehicle_catalog.py          # 16 real EV models + IL/UK market shares
├── fleet_assumptions.py        # Israeli fleet size + α/β/γ ranges
├── smoke_w10r_economics.py     # driver P&L calc (OBSERVED table lives here)
├── calib_w12y_baseline.py      # OBSERVED calibration (240-agent run, 5 seeds)
├── sweep_w12w_drive_days.py    # drive-days sensitivity sweep
└── plot_w*.py                  # matplotlib plot scripts (~15 files)
```

**Key Wong Table 1 numbers** (in TYPOLOGY_PROFILES):
| Typology | drive_days_per_week | km/day | departure/return | target_soc |
|---|---|---|---|---|
| Daily Charger | 6.43 | 40 | 8:00 / 18:00 | 89.2% |
| Public Charger | 6.41 | 48 | 7:00 / 19:00 | 74.7% |
| BEV 2nd Vehicle | 4.74 | 22 | 10:00 / 16:00 | 87% |
| Threshold Charger | 6.44 | 38 | 8:00 / 18:00 | 85% |

Plug-in probability: DC and BEV both 6.11 events/week = **87%** (Wong Table 1). Others structural.

---

## The physics constants (`ev_agent.py` lines 265-275)

```python
CONSUMPTION_KWH_PER_KM = 0.18    # NOT 0.25 as I initially assumed
V2G_SOC_FLOOR = 0.50             # aggregator won't dispatch below
V2G_MAX_SOC = 0.90               # aggregator won't charge above (W12.AL)
```

Charger: 11 kW charge, 9.6 kW discharge, RTE 0.9025 (95% × 95%).
Battery: sampled from vehicle catalog, Israeli weighted-avg 67 kWh.

---

## TAOZ tariff structure (Israel, `pricing.py`)

- **Peak: 1.6895 NIS/kWh**, off-peak 0.528 NIS/kWh (ratio 3.2×)
- Summer (Jun–Sep): peak 17-22 weekdays, Fri-Sat off-peak
- Winter (Dec–Feb): peak 17-21 **all 7 days** (Fri-Sat retention)
- Transition (Mar-May, Oct-Nov): peak 18-22 weekdays only

Uri's ABM at one Daily Charger agent dispatches ~6,810 kWh/yr → cross-checked with hand-calc (~5,400 kWh naive × 365 × NET margin = 5,400 NIS/yr, within 15% of ABM). Physics is coherent.

---

## Israeli fleet (`vehicle_catalog.py`)

Market shares from Xinhua Jan 2025 (BYD 16,690 units 2024, Tesla 8,202, MG 6,276). Chinese OEMs ~64% total.

Weighted-average battery: **67.1 kWh**. Chemistries: 65% LFP (mostly Chinese), 35% NMC (Korean/German).

---

## Key `OBSERVED_V2G_KWH_PER_YEAR` values (four separate copies in code — bug pattern to watch)

`smoke_w10r_economics.py`, `plot_w11c_pnl_active.py`, `plot_w12m_retail_vs_retail.py`, `plot_w11b_aggregator_per_ev.py`, `plot_w11_aggregator_economics.py` — ALL have their own hardcoded copy. Every one currently has:
- Daily Charger: **4,820 kWh**
- BEV 2nd Vehicle: **6,220 kWh**
- Public Charger: 0
- Threshold Charger: ~2 (rounding artifact)

**If OBSERVED changes**, all 5 files must be updated. This has bitten us three times.

---

## Chart provenance map

| Deck slide / Ch4 fig | Script |
|---|---|
| Slide 5 / Fig 4.2 — Retail vs retail | `plot_w12m_retail_vs_retail.py` |
| Slide 6 / Fig 4.3 — Israel P&L | `plot_w11c_pnl_active.py` (Israel) |
| Slide 7 / Fig 4.4 — UK P&L | same (UK) |
| Slide 9 / Fig 4.5 — α × βγ heatmap | `plot_w11_aggregator_economics.py` |
| Slide 10 / Fig 4.6 — Per-EV aggregator | `plot_w11b_aggregator_per_ev.py` |
| Slide 11 — Wong aging | `plot_w10h_aging_wong.py` |
| Slides 12a/b/c / Figs 4.7a/b/c — Sensitivity split | `plot_w12t_sensitivity_split.py` |
| Ch4 Fig 4.7 combined | `plot_w12h_sensitivity_summary.py` |
| Ch4 Fig 4.1 — SoC over a week | `plot_w12ae_soc_week.py` |

Slides 3, 8, 15, 22 are text/table shapes drawn via `python-pptx` in the deck-build script — not matplotlib.

---

## Interactive HTML dashboard

Physics approximation anchored on ABM baseline. NOT a call to the ABM.

Baseline (Daily Charger): D=6.43, K=40 km, BAT=67 kWh, MAX=0.90, FL=0.50, P=87%, H=18:00, peak 17-22, RTE 90%, TAOZ 3.2× → **5,323 NIS/yr NET**.

BEV 2nd Vehicle preset: D=4.74, K=22, H=16:00 → **~6,974 NIS/yr NET** (matches slide 6's 6,870 within noise).

Formula: `kwh = 4820 × scaleHR × min(1, scaleWindow) × scaleP × scaleRTE × scaleWKD`. The `min(1, scaleWindow)` is important — peak window only REDUCES kWh when it shrinks below baseline (SoC headroom binds otherwise). Adding this after Uri caught a 2,000 NIS gap between dashboard and slide 6 at BEV preset.

**Sliders**: driving days, km/day, plug-in prob, return-home hour, battery size, SoC floor, MAX SoC (new), charger power, RTE, TAOZ ratio, peak start hour, peak end hour, weekend Fri-Sat toggle, charger CAPEX, battery cost NMC/LFP, γ, α, β, N.

**Output cards**: per-EV NET revenue, aggregator revenue, battery degradation NMC/LFP, charger payback NMC/LFP.

**Warning**: dashboard uses first-order multiplicative approximation. It captures single-slider effects well, but not multi-slider interactions accurately. For high-precision answers, re-run the ABM.

---

## What Uri already knows / cares about

- **Wants NET numbers everywhere**, never gross. If a chart shows gross, it must be labelled and secondary.
- **Wants real ABM output**, not hand-tuned physics. He explicitly caught me fabricating BEV drive-days curve once; won't tolerate again.
- **Cares about per-participating driver framing** (not fleet-mean).
- **Grew up in Israeli EV context** — knows the market, PUA tariff, NOGA. Israeli data trumps published assumptions when there's a conflict.
- **Reads code**. Was going to review the model himself. See `CODE_REVIEW_GUIDE.md`.

---

## Pending / open items

1. **NOGA data**: hourly SMP wholesale + hourly per-household consumption. Uri's brother in Israel was going to submit form to NOGA. Not yet received. Placeholder in Ch4 §4.4.1 uses UK Low Carbon London × 1.4 summer multiplier.
2. **Israeli residential ancillary services tariff**: NOGA opened market March 2024, tariff not yet located. Slide 8 flags it as "wip" (amber). Would unlock Israeli Sciurus-analogue analysis.
3. **Regulator deck** for Israel Ministry of Energy Head Scientist — currently v15, technical model-first briefing. Not yet delivered.
4. **Full sensitivity interaction ABM sweep** — Uri asked to run a Latin Hypercube Sample of ~1,000 combinations to properly quantify multi-slider interactions. Not done yet. Would take ~1 hour on his laptop. NO ARC needed.
5. **Ch6 Conclusion + Appendices A and B** — not yet drafted.

---

## Things that will bite you (gotchas)

1. **Five OBSERVED copies in different plot scripts** — always sed all of them together.
2. **python-pptx slide reordering is fragile** — when adding/removing slides, use `drop_rel` + `del sldIdLst[idx]` PLUS the "clone into fresh Presentation" pattern if reorders don't stick.
3. **inline_shapes[idx] indices in `docx`** — figures numbered 4.1-4.7 are indices 0-6 in `doc.inline_shapes`. Fig 4.7a/b/c are 6, 7, 8 (after splitting).
4. **Image sharing between figures** — if two `inline_shapes` share the same rId, updating one updates both. Fixed for Fig 4.1 vs 4.3 but watch for recurrence.
5. **Battery is NOT fixed 60 kWh** — the ABM samples from `VEHICLE_CATALOG` per country market shares. Israeli avg is 67 kWh.
6. **BEV plug-in was originally 100%** in the code (my simplification, not Wong-anchored). Now aligned to 87%.
7. **Cumulative_v2g_discharge_kwh tracks battery-side kWh**, not grid-side. Grid-side is `× discharge_efficiency (0.95)`. Minor accounting note.
8. **`target_soc` in TYPOLOGY_PROFILES does NOT cap charging** in the code — the ABM would charge to 100% without W12.AL's V2G_MAX_SOC gate.

---

## How to verify anything

```bash
cd ~/Documents/GitHub/v2g-abm-model

# Fresh 240-agent baseline (~10s):
python3 -m src.calib_w12y_baseline

# Two-country smoke test (~30s):
python3 -m src.smoke_w10d_twocountry

# Driver P&L smoke:
python3 -m src.smoke_w10r_economics

# Regenerate any single plot:
python3 src/plot_w12m_retail_vs_retail.py
python3 -m src.plot_w11c_pnl_active
```

---

## Style Uri wants

- Be **concise** in chat. He caught me being verbose.
- **No emojis**. He never asked for them.
- Show your work with hard numbers, not fluff.
- If you're uncertain, say so — never fabricate.
- Every plot's numbers must trace back to either (a) the ABM run, (b) Wong 2026, or (c) a specific published source.

Good luck.
