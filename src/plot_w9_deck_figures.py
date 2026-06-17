"""Four supporting figures for the Meeting 6 deck (W9).

Generates:
  1. taoz_seasonal_heatmap.png       7x24 heatmap per season showing peak/off-peak
  2. v1g_soc_trajectory.png          one-week SoC trace for a Daily Charger under V1G
                                     showing the departure-aware overnight floor + ramp
  3. feeder_load_curve.png           transformer load on one feeder over the full year,
                                     plus daily peak import/export annotated
  4. uk_v2g_breakeven.png            Daily Charger UK annual benefit vs Powerloop
                                     export rate sweep
"""

from __future__ import annotations
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

import src.agents.ev_agent as ev_agent_module
from src.agents.ev_agent import (
    EVAgent, DAILY_CHARGER,
    COUNTERFACTUAL_V0, COUNTERFACTUAL_V1G, COUNTERFACTUAL_V2G,
    V1G_OVERNIGHT_TARGET_SOC,
)
from src.pricing import price_at_hour, PRICE_OFFPEAK, PRICE_PEAK
from src.pricing_uk import (
    uk_price_at_hour, octopus_powerloop_export_at_hour,
    OCTOPUS_GO_OFFPEAK_GBP, POWERLOOP_EXPORT_GBP,
)
from src.calendar_helper import hour_to_calendar, HOURS_IN_YEAR
from src.grid_agent import build_feeders
from src.run_w9_fleet import run_year, DEFAULT_FLEET_SHARES


OUTPUTS = Path(__file__).resolve().parent.parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Figure 1: seasonal TAOZ heatmap
# ---------------------------------------------------------------------------
def fig_taoz_heatmap() -> None:
    """3 horizontal panels, one per season.  Each panel is a 7-day x 24-hour
    grid coloured peak (red) vs off-peak (green)."""
    seasons = [
        ("Summer (Jun-Sep)",      7,  "summer"),
        ("Transition (Mar-May, Oct-Nov)", 4, "transition"),
        ("Winter (Dec-Feb)",       1, "winter"),
    ]
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 4.5))

    cmap = ListedColormap(["#bbf7d0", "#fca5a5"])   # off-peak green, peak red

    for ax, (title, month, _) in zip(axes, seasons):
        grid = np.zeros((7, 24), dtype=int)
        for dow in range(7):
            for hod in range(24):
                p = price_at_hour(hod, dow, month)
                grid[dow, hod] = 1 if p == PRICE_PEAK else 0

        ax.imshow(grid, aspect="auto", cmap=cmap, vmin=0, vmax=1)
        ax.set_yticks(range(7))
        ax.set_yticklabels(day_names, fontsize=9)
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 2)], fontsize=8)
        ax.set_xlabel("Hour of day")
        ax.set_title(title, fontsize=11, fontweight="bold")
        # Annotate peak windows
        for dow in range(7):
            in_peak = grid[dow, :].nonzero()[0]
            if len(in_peak):
                start, end = in_peak[0], in_peak[-1] + 1
                ax.text((start + end) / 2 - 0.5, dow, f"{start:02d}-{end:02d}",
                        ha="center", va="center", fontsize=8, color="black", fontweight="bold")

    fig.suptitle(
        "Israeli residential TAOZ peak windows  -  PUA tariff book 01/2026\n"
        f"Peak (red) = {PRICE_PEAK:.2f} NIS/kWh  -  Off-peak (green) = {PRICE_OFFPEAK:.2f} NIS/kWh  -  ratio 3.2x",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    out = OUTPUTS / "taoz_seasonal_heatmap.png"
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


# ---------------------------------------------------------------------------
# Figure 2: V1G departure-aware SoC trajectory
# ---------------------------------------------------------------------------
def fig_v1g_soc_trajectory() -> None:
    """One Daily Charger, one summer week (168h), under V1G."""
    ev_agent_module.SEM_ENABLED = True
    a = EVAgent(agent_id=42, typology=DAILY_CHARGER,
                counterfactual=COUNTERFACTUAL_V1G, country="Israel")
    socs = []
    targets = []
    prices = []
    actions = []
    for hour in range(168):
        hod, dow, m = hour_to_calendar(hour + 24*150)   # mid-summer week, starts on a Sunday
        p = price_at_hour(hod, dow, m)
        target = a._v1g_current_target_soc(hod)
        a.step(current_hour=hour, current_price_per_kwh=p, month=m)
        socs.append(a.state.soc)
        targets.append(target)
        prices.append(p)
        actions.append(a.hourly_log[-1]["action"])

    fig, ax = plt.subplots(figsize=(14, 6))
    hours = np.arange(168)
    ax.plot(hours, socs,    label="State of charge", color="#1f77b4", linewidth=2)
    ax.plot(hours, targets, label="V1G target SoC (departure-aware)",
            color="#10b981", linestyle="--", linewidth=2)
    ax.axhline(V1G_OVERNIGHT_TARGET_SOC, color="#6b7280", linestyle=":", linewidth=1,
               label=f"Overnight floor ({V1G_OVERNIGHT_TARGET_SOC:.0%})")

    # Shade peak hours
    for h in range(168):
        if prices[h] == PRICE_PEAK:
            ax.axvspan(h, h + 1, color="#fee2e2", alpha=0.5, zorder=0)

    # Mark charge events
    charge_hours = [h for h, act in enumerate(actions) if act == "CHARGE"]
    ax.scatter(charge_hours, [socs[h] for h in charge_hours],
               marker="^", color="#2563eb", s=40, label="CHARGE event", zorder=5)
    drive_hours = [h for h, act in enumerate(actions) if act == "DRIVING"]
    ax.scatter(drive_hours, [socs[h] for h in drive_hours],
               marker="v", color="#9ca3af", s=20, label="DRIVING", zorder=4)

    # Day boundaries
    for d in range(1, 7):
        ax.axvline(d * 24, color="#6b7280", linewidth=0.5, linestyle=":")
    ax.set_xticks([12 + d*24 for d in range(7)])
    ax.set_xticklabels(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], fontsize=10)
    ax.set_ylabel("State of charge")
    ax.set_xlabel("Day of week")
    ax.set_ylim(0.4, 1.0)
    ax.set_xlim(0, 168)
    ax.set_title(
        "V1G departure-aware overnight rule  -  Daily Charger, summer week  -  Israel\n"
        "70% overnight floor, ramp to typology target (89%) two hours before morning departure",
        fontsize=11, fontweight="bold",
    )
    ax.legend(fontsize=9, loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = OUTPUTS / "v1g_soc_trajectory.png"
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


# ---------------------------------------------------------------------------
# Figure 3: Feeder load curve over the year
# ---------------------------------------------------------------------------
def fig_feeder_load_curve() -> None:
    """Run Israel V2G for the default 240-vehicle fleet on 5 feeders.
    Plot transformer net load for feeder 0 over the year, plus a zoomed-in
    one-week panel that shows the daily structure clearly."""
    print("  running Israel V2G fleet for feeder diagnostics...")
    out = run_year(country="Israel", counterfactual=COUNTERFACTUAL_V2G,
                   shares=DEFAULT_FLEET_SHARES, verbose=False)
    feeder = out["feeders"][0]
    load = np.array(feeder.load_kw)
    rating = feeder.transformer_kva

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(16, 9),
                                          gridspec_kw={"height_ratios": [2, 1]})

    # Top: full year
    hours = np.arange(HOURS_IN_YEAR)
    ax_top.plot(hours, load, color="#1f3864", linewidth=0.3, alpha=0.7)
    ax_top.axhline( rating, color="#dc2626", linestyle="--", linewidth=1.5,
                   label=f"+{rating:.0f} kVA transformer cap (import limit)")
    ax_top.axhline(-rating, color="#dc2626", linestyle="--", linewidth=1.5,
                   label=f"-{rating:.0f} kVA transformer cap (export limit)")
    ax_top.axhline(0, color="black", linewidth=0.5)
    peak_in = load.max()
    peak_out = -load.min()
    ax_top.annotate(f"peak import = {peak_in:.0f} kW  ({peak_in/rating*100:.0f}% of rating)",
                    xy=(8000, peak_in), xytext=(7000, rating*0.7),
                    arrowprops=dict(arrowstyle="->"), fontsize=10, fontweight="bold")
    ax_top.annotate(f"peak export = {peak_out:.0f} kW  ({peak_out/rating*100:.0f}% of rating)",
                    xy=(4500, -peak_out), xytext=(5000, -rating*0.5),
                    arrowprops=dict(arrowstyle="->"), fontsize=10, fontweight="bold")
    ax_top.set_xlim(0, HOURS_IN_YEAR)
    ax_top.set_ylim(-rating*1.1, rating*1.1)
    ax_top.set_xticks([0, 744, 2160, 4344, 6552, HOURS_IN_YEAR-1])
    ax_top.set_xticklabels(["Jan", "Feb", "Apr", "Jul", "Oct", "Dec"], fontsize=10)
    ax_top.set_ylabel("Feeder net load (kW)\n+ = import to households\n- = export to grid")
    ax_top.set_title(
        f"GridAgent feeder load over the full year  -  Israel V2G run  -  "
        f"Feeder 0, {len(feeder.ev_agents)} households, {rating:.0f} kVA transformer",
        fontsize=12, fontweight="bold",
    )
    ax_top.legend(fontsize=9, loc="upper right")
    ax_top.grid(alpha=0.3)

    # Bottom: zoom on a representative summer week
    summer_start = 4344                # roughly 1 July
    week_load = load[summer_start:summer_start + 168]
    ax_bot.plot(range(168), week_load, color="#1f3864", linewidth=1.2)
    ax_bot.axhline( rating, color="#dc2626", linestyle="--", linewidth=1)
    ax_bot.axhline(-rating, color="#dc2626", linestyle="--", linewidth=1)
    ax_bot.axhline(0, color="black", linewidth=0.5)
    for d in range(1, 7):
        ax_bot.axvline(d * 24, color="#6b7280", linewidth=0.4, linestyle=":")
    ax_bot.set_xticks([12 + d*24 for d in range(7)])
    ax_bot.set_xticklabels(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], fontsize=10)
    ax_bot.set_xlim(0, 168)
    ax_bot.set_ylim(-rating*1.1, rating*1.1)
    ax_bot.set_ylabel("kW")
    ax_bot.set_title(
        "Zoom: one summer week  -  diurnal pattern visible.  Overnight charging spikes; "
        "evening export valley at 17:00-22:00.",
        fontsize=11,
    )
    ax_bot.grid(alpha=0.3)

    fig.tight_layout()
    out = OUTPUTS / "feeder_load_curve.png"
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


# ---------------------------------------------------------------------------
# Figure 4: UK V2G break-even sensitivity
# ---------------------------------------------------------------------------
def fig_uk_breakeven() -> None:
    """Sweep Powerloop export rate, plot UK Daily Charger annual benefit.

    Holds everything else constant.  Finds the export rate at which UK
    V2G breaks even with V0 (annual benefit = 0)."""
    import src.pricing_uk as pricing_uk_mod
    print("  running UK V2G break-even sweep...")

    # Baseline V0 cost for comparison
    ev_agent_module.SEM_ENABLED = True
    v0 = EVAgent(agent_id=1, typology=DAILY_CHARGER,
                 counterfactual=COUNTERFACTUAL_V0, country="UK")
    for hour in range(HOURS_IN_YEAR):
        hod, dow, m = hour_to_calendar(hour)
        p = uk_price_at_hour("V0", hod, dow, m)
        v0.step(current_hour=hour, current_price_per_kwh=p, month=m)
    v0_year = sum(r["cost_currency"] for r in v0.hourly_log)

    sweep = np.linspace(0.10, 0.45, 12)
    v2g_costs = []
    original_export = pricing_uk_mod.POWERLOOP_EXPORT_GBP

    for export_rate in sweep:
        pricing_uk_mod.POWERLOOP_EXPORT_GBP = float(export_rate)
        a = EVAgent(agent_id=1, typology=DAILY_CHARGER,
                    counterfactual=COUNTERFACTUAL_V2G, country="UK")
        # Re-derive OSP with the new bounds
        from src.agents.ev_agent import intention_to_osp
        a.state.osp = intention_to_osp(a.state.intention_to_use_v2g, country="UK")
        for hour in range(HOURS_IN_YEAR):
            hod, dow, m = hour_to_calendar(hour)
            imp = uk_price_at_hour("V2G", hod, dow, m)
            exp = octopus_powerloop_export_at_hour(hod, dow, m)
            a.step(current_hour=hour, current_price_per_kwh=imp, month=m,
                   discharge_revenue_per_kwh=exp)
        v2g_year = sum(r["cost_currency"] for r in a.hourly_log)
        v2g_costs.append(v2g_year)

    pricing_uk_mod.POWERLOOP_EXPORT_GBP = original_export

    benefits = [v0_year - c for c in v2g_costs]
    sweep_p = sweep * 100   # to pence/kWh
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(sweep_p, benefits, color="#1f3864", linewidth=2.5, marker="o", markersize=7)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(POWERLOOP_EXPORT_GBP * 100, color="#dc2626", linestyle="--", linewidth=1.5,
               label=f"Today's Powerloop rate ({POWERLOOP_EXPORT_GBP*100:.1f} p/kWh)")
    # Find the break-even point (first crossing of y=0)
    benefits_arr = np.array(benefits)
    crossing_idx = np.where(np.diff(np.sign(benefits_arr)))[0]
    if len(crossing_idx):
        i = crossing_idx[0]
        # Linear interpolation
        x0, x1 = sweep_p[i], sweep_p[i+1]
        y0, y1 = benefits_arr[i], benefits_arr[i+1]
        be = x0 - y0 * (x1 - x0) / (y1 - y0)
        ax.axvline(be, color="#10b981", linestyle="--", linewidth=1.5,
                   label=f"Break-even at {be:.1f} p/kWh")
        ax.scatter([be], [0], color="#10b981", s=120, zorder=5, edgecolors="black", linewidths=1.5)
    ax.set_xlabel("Octopus Powerloop export rate  (pence per kWh)", fontsize=11)
    ax.set_ylabel(f"UK Daily Charger annual benefit vs V0  (GBP/yr)", fontsize=11)
    ax.set_title(
        "Sensitivity: at what export rate does UK V2G break even for a Daily Charger?\n"
        "Holding Octopus Go import and Wong typology shares constant",
        fontsize=12, fontweight="bold",
    )
    ax.legend(fontsize=10, loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = OUTPUTS / "uk_v2g_breakeven.png"
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    fig_taoz_heatmap()
    fig_v1g_soc_trajectory()
    fig_feeder_load_curve()
    fig_uk_breakeven()
