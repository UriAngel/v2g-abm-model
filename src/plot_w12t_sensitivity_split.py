"""Split the seven-panel sensitivity summary into three deck slides.

Produces:
  outputs/w12t_sens_pricing.png     (panels 1, 2, 3)  Economic sensitivities
  outputs/w12t_sens_behaviour.png   (panels 4, 6, 7)  Behavioural sensitivities
  outputs/w12t_sens_grid.png        (panel  5 + headlines text)  Grid + headlines

Numbers stay identical to plot_w12h_sensitivity_summary.py.
"""

from pathlib import Path
import matplotlib.pyplot as plt

from src.plot_style import apply_style, PALETTE
apply_style()
import numpy as np


OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"


def panel_capex(ax):
    # Premiums: IL 19,350 NIS (2026) / 8,025 (2028); UK 3,702 GBP / 1,851.
    # Operating P&L: IL DC NMC 5,323 NIS/yr; UK Sciurus 725-46 = 679 GBP/yr.
    labels = ["Israel\n2026", "Israel\n2028", "UK Sciurus\n2026", "UK Sciurus\n2028"]
    paybacks = [3.6, 1.5, 5.5, 2.7]
    colors = ["#0f766e", "#0f766e", "#1d4ed8", "#1d4ed8"]
    bars = ax.bar(labels, paybacks, color=colors, edgecolor="white")
    for b, v in zip(bars, paybacks):
        ax.text(b.get_x() + b.get_width()/2, v + 0.15, f"{v:.1f} y",
                ha="center", fontsize=11.5, fontweight="bold")
    ax.axhline(10, color="#b91c1c", linestyle="--", linewidth=1,
               label="10-yr battery life")
    ax.set_ylabel("V2G premium payback (years)", fontsize=11.5)
    ax.set_title("(1) Bidirectional charger CAPEX, 2026 vs 2028",
                 fontsize=14.0, fontweight="bold")
    ax.set_ylim(0, 12)
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(True, axis="y", alpha=0.3)


def panel_uk_rate(ax):
    # NET basis (matches Fig 4.2/4.4): payback = premium / (kwh * (rate
    # - 0.070/0.9025)), kwh = 4,820 (DC opt-in), premium = 3,702 GBP.
    kwh, prem, go_rt = 4820, 3702, 0.070 / 0.9025
    rates = [10, 12, 16, 20, 25]
    pb = [prem / (kwh * (r / 100 - go_rt)) for r in rates]
    ax.plot(rates, pb, "-o", color="#1d4ed8", linewidth=2, markersize=8)
    for r, p in zip(rates, pb):
        ax.text(r, p + 0.5, f"{p:.1f}y", ha="center", fontsize=10.5, fontweight="bold")
    ax.axhline(10, color="#b91c1c", linestyle="--", linewidth=1,
               label="10-yr battery life")
    ax.axvline(12, color="#475569", linestyle=":", linewidth=1,
               alpha=0.7, label="current Power Pack 12 p")
    ax.set_xlabel("Power Pack export rate (p/kWh)", fontsize=11.5)
    ax.set_ylabel("Payback (years)", fontsize=11.5)
    ax.set_title("(2) UK Power Pack rate sweep (net of Go recharge)",
                 fontsize=14.0, fontweight="bold")
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(True, alpha=0.3)


def panel_taoz(ax):
    ratios = ["2.0x\n(narrow)", "3.2x\n(current)", "4.5x\n(wide)", "6.0x\n(extreme)"]
    # Per-opted-in-EV gross revenue with the 90 % max_soc cap.
    dc_rev  = [5090, 8144, 11452, 15270]
    bev_rev = [6568, 10509, 14779, 19705]
    x = np.arange(len(ratios)); w = 0.35
    ax.bar(x - w/2, dc_rev, w, color="#0f766e", label="Daily Charger", edgecolor="white")
    ax.bar(x + w/2, bev_rev, w, color="#1d4ed8", label="BEV 2nd Vehicle", edgecolor="white")
    for i, (d, b) in enumerate(zip(dc_rev, bev_rev)):
        ax.text(i - w/2, d + 200, f"{d:,}", ha="center", fontsize=10, fontweight="bold")
        ax.text(i + w/2, b + 200, f"{b:,}", ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(ratios, fontsize=10.5)
    ax.set_ylabel("Annual GROSS V2G revenue (NIS/EV/yr)", fontsize=11.5)
    ax.set_title("(3) Israel TAOZ peak/off-peak spread\n"
                 "annual gross (subtract ~1,940 NIS/yr CAPEX amortisation for net)",
                 fontsize=13.0, fontweight="bold")
    ax.legend(fontsize=10, loc="upper left")
    ax.grid(True, axis="y", alpha=0.3)


def panel_plugin(ax):
    # Real ABM 120-agent sweep, 3-seed average (seeds 0-2), 90 % max_soc
    # cap, per-opted-in.  Source: sweep_w13a_plugin_return.py ->
    # outputs/w13a_plugin_return_sweep.json (2026-07-09).
    probs = [5.50, 6.11, 6.50, 7.00]
    prob_pct = [p/7*100 for p in probs]
    v2g_kwh = [4437, 4919, 5239, 5654]
    ax.plot(prob_pct, v2g_kwh, "-o", color="#0f766e", linewidth=2, markersize=8)
    for p, v in zip(prob_pct, v2g_kwh):
        ax.text(p, v + 60, f"{v:,}", ha="center", fontsize=10.5, fontweight="bold")
    ax.axvline(6.11/7*100, color="#b91c1c", linestyle=":", linewidth=1,
               label="Wong Table 1 anchor (87 %)")
    ax.set_xlabel("Plug-in probability (% of home evenings)", fontsize=11.5)
    ax.set_ylabel("Daily Charger V2G kWh/yr", fontsize=11.5)
    ax.set_title("(4) Plug-in probability robustness (3-seed avg, 90 % cap)",
                 fontsize=14.0, fontweight="bold")
    ax.legend(fontsize=10, loc="lower right")
    ax.grid(True, alpha=0.3)


def panel_return_home(ax):
    # Real ABM 120-agent sweep, 3-seed average (seeds 0-2), 90 % max_soc
    # cap, per-opted-in.  Source: sweep_w13a_plugin_return.py ->
    # outputs/w13a_plugin_return_sweep.json (2026-07-09).
    hours = [16, 17, 18, 19, 20]
    v2g = [6010, 5373, 4919, 4685, 3983]
    ax.plot(hours, v2g, "-o", color="#0f766e", linewidth=2, markersize=8)
    ax.axvline(18, color="#b91c1c", linestyle=":", linewidth=1,
               label="baseline 18:00")
    ax.axvspan(17, 22, color="#d97706", alpha=0.10,
               label="TAOZ peak 17-22")
    for h, v in zip(hours, v2g):
        ax.text(h, v + 60, f"{v:,}", ha="center", fontsize=10.5, fontweight="bold")
    ax.set_xlabel("Arrival home hour", fontsize=11.5)
    ax.set_ylabel("Daily Charger V2G kWh/yr", fontsize=11.5)
    ax.set_title("(6) Return-home hour sensitivity (3-seed avg, 90 % cap)",
                 fontsize=14.0, fontweight="bold")
    ax.legend(fontsize=10, loc="lower left")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(3500, 6500)


def panel_drive_days(ax):
    drive_days = np.array([0, 1, 2, 3, 4, 5, 6, 7])
    # Real ABM 120-agent sweep, 3-seed average, 90 % max_soc cap,
    # per-opted-in, matched plug-in (87 %) and target_soc.  Curves
    # converge at 0 drive-days (+0.5 %); the gap at higher drive-days
    # comes from km/day (40 vs 22) and the later return hour (18:00
    # vs 16:00, missing the first peak hour).
    dc_v2g  = np.array([6455, 6190, 5985, 5749, 5506, 5267, 5055, 4772])
    bev_v2g = np.array([6424, 6415, 6387, 6346, 6344, 6336, 6312, 6271])
    ax.plot(drive_days, dc_v2g,  "-o", color="#0f766e",
            linewidth=2, markersize=7, label="Daily Charger")
    ax.plot(drive_days, bev_v2g, "-s", color="#1d4ed8",
            linewidth=2, markersize=7, label="BEV 2nd Vehicle")
    ax.axvline(6.43, color="#0f766e", linestyle=":", linewidth=1, alpha=0.6)
    ax.axvline(4.74, color="#1d4ed8", linestyle=":", linewidth=1, alpha=0.6)
    for x, y in zip(drive_days, dc_v2g):
        ax.text(x, y - 180, f"{y:,}", ha="center", fontsize=10,
                fontweight="bold", color="#0f766e")
    for x, y in zip(drive_days, bev_v2g):
        ax.text(x, y + 110, f"{y:,}", ha="center", fontsize=10,
                fontweight="bold", color="#1d4ed8")
    ax.set_xlabel("Driving days per week", fontsize=11.5)
    ax.set_ylabel("Annual V2G kWh / car", fontsize=11.5)
    ax.set_title("(7) Drive-days sensitivity (3-seed avg, 90 % cap)\n"
                 "matched 87 % plug-in; curves converge at 0 d/wk",
                 fontsize=13.0, fontweight="bold")
    ax.set_xticks(drive_days)
    ax.legend(fontsize=10, loc="lower left")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(4300, 7100)


def panel_grid(ax):
    # Analytical worst-case envelope, reproducible from model constants
    # (grid_agent.py): 54 HH x 1 EV, 517 kVA, discharge 9.6 kW/EV.
    # ALL participating EVs (beta*gamma share) discharge simultaneously.
    # Two bounding baselines from HH_BASELINE_24H_KW:
    #   winter 17:00 (peak-window minimum): 1.6 kW/HH ->  86.4 kW import
    #   summer 19:00 (peak-window maximum): 2.8 kW/HH -> 151.2 kW import
    # net(bg) = bg*54*9.6 - baseline.  At bg=1 the winter bound gives
    # 54*(9.6-1.6) = +432 kW, crossing the 413 kW ENA margin at bg=96%;
    # the 517 kVA nameplate is unreachable (max +432).
    bg = np.linspace(0.0, 1.0, 21)
    hh, kva, p_dis = 54, 517.0, 9.6
    net_winter = bg * hh * p_dis - 54 * 1.6
    net_summer = bg * hh * p_dis - 54 * 2.8
    ax.axhline(0, color="black", linewidth=0.8)
    ax.fill_between(bg*100, net_summer, net_winter, color="#0f766e", alpha=0.12)
    ax.plot(bg*100, net_winter, "-", color="#0f766e", linewidth=2,
            label="winter 17:00 baseline (86 kW) - export worst case")
    ax.plot(bg*100, net_summer, "--", color="#0f766e", linewidth=1.6,
            label="summer 19:00 baseline (151 kW)")
    ax.axhline(kva * 0.8, color="#b91c1c", linestyle="--", linewidth=1,
               label="80 % planning margin (413 kW)")
    ax.axhline(kva, color="#d97706", linestyle=":", linewidth=1, alpha=0.8,
               label="517 kVA nameplate rating")
    ax.plot([100], [432], "o", color="#0f766e", markersize=8)
    ax.text(99, 432 + 18, "+432", ha="right", fontsize=10.5, fontweight="bold")
    ax.plot([96.4], [413.6], "x", color="#b91c1c", markersize=9)
    ax.annotate("margin crossed at 96 %", xy=(96.4, 413.6), xytext=(58, 470),
                fontsize=10, color="#b91c1c",
                arrowprops=dict(arrowstyle="->", color="#b91c1c", linewidth=0.9))
    ax.set_xlabel(r"$\beta \cdot \gamma$  (% of the feeder's 54 EVs "
                  "discharging simultaneously)", fontsize=11.5)
    ax.set_ylabel("Net feeder load (kW)   negative = import, positive = export",
                  fontsize=11.5)
    ax.set_title("(5) Feeder worst-case envelope, all participants discharging\n"
                 "at once (54 HH x 1 EV, 517 kVA; simulated year: zero denials)",
                 fontsize=13.0, fontweight="bold")
    ax.legend(fontsize=9.5, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(-260, 620)


def panel_headlines(ax):
    ax.axis("off")
    lines = [
        ("Headlines", "title"),
        ("* TAOZ spread is the largest lever", None),
        ("* CAPEX 2028 halves payback", None),
        ("* Plug-in prob relatively insensitive", None),
        ("* GridAgent binds only at beta*gamma=1", None),
        ("* Return-home 20:00 -> revenue -18 %", None),
        ("* Drive-days curve monotonic:", None),
        ("    - 0 d/wk DC 7,038 kWh (ceiling)", None),
        ("    - 7 d/wk DC 5,344 kWh (floor)", None),
        ("    - BEV within ~2 % of DC at 0 d/wk", None),
        ("      (both Wong 87 % plug-in)", None),
        ("", None),
        ("* Panel 3 numbers = ANNUAL GROSS", None),
        ("  10-yr net = gross x 10 - CAPEX 19.4k", None),
    ]
    y = 0.98
    for txt, kind in lines:
        w = "bold" if kind == "title" else "normal"
        sz = 14 if kind == "title" else 11
        ax.text(0.02, y, txt, fontsize=sz, fontweight=w,
                transform=ax.transAxes, va="top")
        y -= 0.075


def main() -> None:
    # Slide A: pricing sensitivities (1, 2, 3)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))
    panel_capex(axes[0])
    panel_uk_rate(axes[1])
    panel_taoz(axes[2])
    fig.tight_layout()
    fig.savefig(OUT_DIR / "w12t_sens_pricing.png", dpi=150, facecolor="white")
    plt.close(fig)

    # Slide B: behavioural sensitivities, 2 panels (drive-days lives on
    # slide C so no slide carries a lone stretched panel)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    panel_plugin(axes[0])
    panel_return_home(axes[1])
    fig.tight_layout()
    fig.savefig(OUT_DIR / "w12t_sens_behaviour.png", dpi=150, facecolor="white")
    plt.close(fig)

    # Slide C: drive-days + grid constraint, 2 panels
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    panel_drive_days(axes[0])
    panel_grid(axes[1])
    fig.tight_layout()
    fig.savefig(OUT_DIR / "w12t_sens_grid.png", dpi=150, facecolor="white")
    plt.close(fig)

    print(f"Saved 3 slide panels to {OUT_DIR}")


if __name__ == "__main__":
    main()
