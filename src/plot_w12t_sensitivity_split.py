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
    labels = ["Israel\n2024", "Israel\n2028", "UK Sciurus\n2024", "UK Sciurus\n2028"]
    paybacks = [4.4, 1.8, 5.1, 2.4]
    colors = ["#0f766e", "#0f766e", "#1d4ed8", "#1d4ed8"]
    bars = ax.bar(labels, paybacks, color=colors, edgecolor="white")
    for b, v in zip(bars, paybacks):
        ax.text(b.get_x() + b.get_width()/2, v + 0.15, f"{v:.1f} y",
                ha="center", fontsize=10, fontweight="bold")
    ax.axhline(10, color="#b91c1c", linestyle="--", linewidth=1,
               label="10-yr battery life")
    ax.set_ylabel("V2G premium payback (years)", fontsize=10)
    ax.set_title("(1) Sigenergy 2024 vs 2028",
                 fontsize=11, fontweight="bold")
    ax.set_ylim(0, 12)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, axis="y", alpha=0.3)


def panel_uk_rate(ax):
    rates = [8, 12, 16, 20, 25]
    pb = [17.7, 11.8, 8.8, 7.1, 5.7]
    ax.plot(rates, pb, "-o", color="#1d4ed8", linewidth=2, markersize=8)
    for r, p in zip(rates, pb):
        ax.text(r, p + 0.5, f"{p:.1f}y", ha="center", fontsize=9, fontweight="bold")
    ax.axhline(10, color="#b91c1c", linestyle="--", linewidth=1,
               label="10-yr battery life")
    ax.axvline(12, color="#475569", linestyle=":", linewidth=1,
               alpha=0.7, label="current Power Pack 12 p")
    ax.set_xlabel("Power Pack export rate (p/kWh)", fontsize=10)
    ax.set_ylabel("Payback (years)", fontsize=10)
    ax.set_title("(2) UK Power Pack rate sweep",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="upper right")
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
        ax.text(i - w/2, d + 200, f"{d:,}", ha="center", fontsize=8, fontweight="bold")
        ax.text(i + w/2, b + 200, f"{b:,}", ha="center", fontsize=8, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(ratios, fontsize=9)
    ax.set_ylabel("Annual GROSS V2G revenue (NIS/EV/yr)", fontsize=10)
    ax.set_title("(3) Israel TAOZ peak/off-peak spread\n"
                 "annual gross (subtract ~1,940 NIS/yr CAPEX amortisation for net)",
                 fontsize=10, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, axis="y", alpha=0.3)


def panel_plugin(ax):
    probs = [5.50, 6.11, 6.50, 7.00]
    prob_pct = [p/7*100 for p in probs]
    v2g_kwh = [2730, 3027, 3217, 3470]
    ax.plot(prob_pct, v2g_kwh, "-o", color="#0f766e", linewidth=2, markersize=8)
    for p, v in zip(prob_pct, v2g_kwh):
        ax.text(p, v + 60, f"{v:,}", ha="center", fontsize=9, fontweight="bold")
    ax.axvline(6.11/7*100, color="#b91c1c", linestyle=":", linewidth=1,
               label="Wong Table 1 anchor (87 %)")
    ax.set_xlabel("Plug-in probability (% of home evenings)", fontsize=10)
    ax.set_ylabel("Daily Charger V2G kWh/yr", fontsize=10)
    ax.set_title("(4) Plug-in probability robustness",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(True, alpha=0.3)


def panel_return_home(ax):
    hours = [16, 17, 18, 19, 20]
    v2g = [3463, 3266, 2724, 2740, 2241]
    ax.plot(hours, v2g, "-o", color="#0f766e", linewidth=2, markersize=8)
    ax.axvline(18, color="#b91c1c", linestyle=":", linewidth=1,
               label="baseline 18:00")
    ax.axvspan(17, 22, color="#d97706", alpha=0.10,
               label="TAOZ peak 17-22")
    for h, v in zip(hours, v2g):
        ax.text(h, v + 60, f"{v:,}", ha="center", fontsize=9, fontweight="bold")
    ax.set_xlabel("Arrival home hour", fontsize=10)
    ax.set_ylabel("Daily Charger V2G kWh/yr", fontsize=10)
    ax.set_title("(6) Return-home hour sensitivity",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(1800, 3800)


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
        ax.text(x, y - 180, f"{y:,}", ha="center", fontsize=8,
                fontweight="bold", color="#0f766e")
    for x, y in zip(drive_days, bev_v2g):
        ax.text(x, y + 110, f"{y:,}", ha="center", fontsize=8,
                fontweight="bold", color="#1d4ed8")
    ax.set_xlabel("Driving days per week", fontsize=10)
    ax.set_ylabel("Annual V2G kWh / car", fontsize=10)
    ax.set_title("(7) Drive-days sensitivity (3-seed avg, 90 % cap)\n"
                 "matched 87 % plug-in; curves converge at 0 d/wk",
                 fontsize=10, fontweight="bold")
    ax.set_xticks(drive_days)
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(4300, 7100)


def panel_grid(ax):
    bg = [0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 1.00]
    net = [-140, -107, -52, +14, +135, +245, +432]
    ax.axhline(0, color="black", linewidth=0.8)
    ax.plot([b*100 for b in bg], net, "-o", color="#0f766e",
            linewidth=2, markersize=8)
    ax.axhline(517 * 0.8, color="#b91c1c", linestyle="--", linewidth=1,
               label="80 % safety margin (413 kW)")
    ax.axhline(-517 * 0.8, color="#b91c1c", linestyle="--", linewidth=1)
    ax.axhline(517, color="#d97706", linestyle=":", linewidth=1, alpha=0.7,
               label="517 kVA transformer rating")
    ax.axhline(-517, color="#d97706", linestyle=":", linewidth=1, alpha=0.7)
    for b, n in zip(bg, net):
        ax.text(b*100, n + 20, f"{n:+d}", ha="center", fontsize=9,
                fontweight="bold")
    ax.set_xlabel(r"$\beta \cdot \gamma$  (%)", fontsize=10)
    ax.set_ylabel("Net feeder load (kW)   negative = import, positive = export",
                  fontsize=10)
    ax.set_title("(5) GridAgent constraint at IL residential feeder\n"
                 "(54 HH x 3 kW ADMD, 517 kVA)",
                 fontsize=10, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)


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
