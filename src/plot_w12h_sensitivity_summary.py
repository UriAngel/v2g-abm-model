"""Sensitivity summary  -  seven sweeps on one figure.

Seven panels (4x2 layout; 8th cell holds a summary text):
  1. Charger CAPEX 2024 vs 2028 (bar)
  2. UK Power Pack export rate sweep (line)
  3. Israel TAOZ peak/off-peak spread (bar)
  4. Plug-in probability robustness (line)
  5. GridAgent beta*gamma sweep - net feeder load (line)
  6. Return-home hour sensitivity (line)
  7. Drive-days-per-week sensitivity (line)
  8. Headlines text panel

Drive-days sensitivity (Panel 7) - shape derivation
---------------------------------------------------
V2G export budget on a peak evening is set by SoC headroom above the
50 % contractual floor.  A driver who did not drive that day is home at
100 % SoC when the peak window opens; a driver who drove 40 km arrived
home at ~83 % SoC (10 kWh consumed).  Headroom above 50 % floor:
  - non-drive day: 30 kWh (50 % of 60 kWh capacity)
  - drive day  : ~20 kWh (33 % of 60 kWh capacity)
Weekend peak retention exists only in TAOZ winter (Fri-Sat) - so the
7-day driver picks up a small winter uplift on Sat.  Net effect: the
curve is monotonically decreasing from 0 drive days to 7, with a slight
flattening at the high end.

Numbers hard-coded from the sweep run outputs; regenerate on request.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


OUT = Path(__file__).resolve().parent.parent / "outputs" / "w12h_sensitivity_summary.png"


def main() -> None:
    fig, axes = plt.subplots(2, 4, figsize=(20, 9))

    # Panel 1: CAPEX 2024 vs 2028
    ax = axes[0, 0]
    labels = ["Israel\n2024", "Israel\n2028", "UK Sciurus\n2024", "UK Sciurus\n2028"]
    paybacks = [4.4, 1.8, 5.1, 2.4]
    colors = ["#2C5F2D", "#15803d", "#02808F", "#0891b2"]
    bars = ax.bar(labels, paybacks, color=colors, edgecolor="white")
    for b, v in zip(bars, paybacks):
        ax.text(b.get_x() + b.get_width()/2, v + 0.15, f"{v:.1f} y",
                ha="center", fontsize=10, fontweight="bold")
    ax.axhline(10, color="#dc2626", linestyle="--", linewidth=1,
               label="10-yr battery life")
    ax.set_ylabel("V2G premium payback (years)", fontsize=10)
    ax.set_title("(1) Sigenergy charger 2024 vs 2028 mass production",
                 fontsize=11, fontweight="bold")
    ax.set_ylim(0, 12)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, axis="y", alpha=0.3)

    # Panel 2: UK Power Pack rate
    ax = axes[0, 1]
    rates = [8, 12, 16, 20, 25]
    paybacks_uk = [17.7, 11.8, 8.8, 7.1, 5.7]
    ax.plot(rates, paybacks_uk, "-o", color="#02808F", linewidth=2, markersize=8)
    for r, p in zip(rates, paybacks_uk):
        ax.text(r, p + 0.5, f"{p:.1f}y", ha="center", fontsize=9,
                fontweight="bold")
    ax.axhline(10, color="#dc2626", linestyle="--", linewidth=1,
               label="10-yr battery life")
    ax.axvline(12, color="#8A8A8A", linestyle=":", linewidth=1,
               alpha=0.7, label="current Power Pack 12 p")
    ax.set_xlabel("Power Pack export rate (p/kWh)", fontsize=10)
    ax.set_ylabel("Payback (years)", fontsize=10)
    ax.set_title("(2) UK Power Pack rate sweep (Model A)",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.3)

    # Panel 3: Israel TAOZ spread  (moved to column 2)
    ax = axes[0, 2]
    ratios = ["2.0x\n(narrow)", "3.2x\n(current)", "4.5x\n(wide)", "6.0x\n(extreme)"]
    # Per-opted-in-EV gross revenue with the 90 % max_soc cap
    # (DC 4,820 kWh, BEV 6,220 kWh at the 3.2x baseline spread).
    dc_rev  = [5090, 8144, 11452, 15270]
    bev_rev = [6568, 10509, 14779, 19705]
    x = np.arange(len(ratios))
    w = 0.35
    ax.bar(x - w/2, dc_rev, w, color="#2C5F2D", label="Daily Charger", edgecolor="white")
    ax.bar(x + w/2, bev_rev, w, color="#0891b2", label="BEV 2nd Vehicle", edgecolor="white")
    for i, (d, b) in enumerate(zip(dc_rev, bev_rev)):
        ax.text(i - w/2, d + 200, f"{d:,}", ha="center", fontsize=8, fontweight="bold")
        ax.text(i + w/2, b + 200, f"{b:,}", ha="center", fontsize=8, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(ratios, fontsize=9)
    ax.set_ylabel("Annual GROSS V2G revenue (NIS/EV/yr)", fontsize=10)
    ax.set_title("(3) Israel TAOZ peak/off-peak spread\n"
                 "annual gross - subtract ~1,940 NIS/yr CAPEX amortisation for 10-yr net",
                 fontsize=10, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, axis="y", alpha=0.3)

    # Panel 4: Plug-in probability
    ax = axes[0, 3]
    probs = [5.50, 6.11, 6.50, 7.00]
    prob_pct = [p/7*100 for p in probs]
    v2g_kwh = [2730, 3027, 3217, 3470]
    ax.plot(prob_pct, v2g_kwh, "-o", color="#15803d", linewidth=2, markersize=8)
    for p, v in zip(prob_pct, v2g_kwh):
        ax.text(p, v + 60, f"{v:,}", ha="center", fontsize=9, fontweight="bold")
    ax.axvline(6.11/7*100, color="#dc2626", linestyle=":", linewidth=1,
               label="Wong Table 1 anchor (87 %)")
    ax.set_xlabel("Plug-in probability (% of home evenings)", fontsize=10)
    ax.set_ylabel("Daily Charger V2G kWh/yr", fontsize=10)
    ax.set_title("(4) Plug-in probability robustness",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(True, alpha=0.3)

    # Panel 5: GridAgent beta*gamma
    ax = axes[1, 0]
    bg = [0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 1.00]
    net = [-140, -107, -52, +14, +135, +245, +432]
    ax.axhline(0, color="black", linewidth=0.8)
    ax.plot([b*100 for b in bg], net, "-o", color="#2C5F2D", linewidth=2, markersize=8)
    ax.axhline(517 * 0.8, color="#dc2626", linestyle="--", linewidth=1,
               label="80 % safety margin (413 kW)")
    ax.axhline(-517 * 0.8, color="#dc2626", linestyle="--", linewidth=1)
    ax.axhline(517, color="#f59e0b", linestyle=":", linewidth=1, alpha=0.7,
               label="517 kVA transformer rating")
    ax.axhline(-517, color="#f59e0b", linestyle=":", linewidth=1, alpha=0.7)
    for b, n in zip(bg, net):
        ax.text(b*100, n + 20, f"{n:+d}", ha="center", fontsize=9, fontweight="bold")
    ax.set_xlabel(r"$\beta \cdot \gamma$  (%)", fontsize=10)
    ax.set_ylabel("Net feeder load (kW)   negative = import, positive = export",
                  fontsize=10)
    ax.set_title("(5) GridAgent constraint at IL residential feeder\n"
                 "(54 HH x 3 kW ADMD, 517 kVA)",
                 fontsize=10, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)

    # Panel 6: departure-time sensitivity
    ax = axes[1, 1]
    hours = [16, 17, 18, 19, 20]
    v2g = [3463, 3266, 2724, 2740, 2241]
    ax.plot(hours, v2g, "-o", color="#2C5F2D", linewidth=2, markersize=8)
    ax.axvline(18, color="#dc2626", linestyle=":", linewidth=1,
               label="baseline arrival 18:00")
    ax.axvspan(17, 22, color="#f59e0b", alpha=0.10,
               label="TAOZ summer peak 17-22")
    for h, v in zip(hours, v2g):
        ax.text(h, v + 60, f"{v:,}", ha="center", fontsize=9,
                fontweight="bold")
    ax.set_xlabel("Arrival home hour", fontsize=10)
    ax.set_ylabel("Daily Charger V2G kWh/yr", fontsize=10)
    ax.set_title("(6) Return-home hour sensitivity\n"
                 "one hour later -> earlier V2G window closes",
                 fontsize=10, fontweight="bold")
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(1800, 3800)

    # Panel 7: Drive-days-per-week sensitivity
    ax = axes[1, 2]
    drive_days = np.array([0, 1, 2, 3, 4, 5, 6, 7])
    # Real ABM 120-agent sweep with 87 % BEV plug-in, per-opted-in,
    # with BEV target_soc overridden to match DC (0.892).
    # DC and BEV physically converge at D=0 (only ~1.7% Monte-Carlo noise).
    # BEV curve is flat because BEV drives 22 km/day vs DC 40 km/day.
    dc_v2g  = np.array([7038, 6789, 6587, 6349, 6114, 5882, 5650, 5344])
    bev_v2g = np.array([6916, 6933, 6919, 6894, 6922, 6869, 6845, 6808])
    ax.plot(drive_days, dc_v2g,  "-o", color="#2C5F2D",
            linewidth=2, markersize=7, label="Daily Charger")
    ax.plot(drive_days, bev_v2g, "-s", color="#02808F",
            linewidth=2, markersize=7, label="BEV 2nd Vehicle")
    ax.axvline(6.43, color="#2C5F2D", linestyle=":", linewidth=1, alpha=0.6)
    ax.axvline(4.74, color="#02808F", linestyle=":", linewidth=1, alpha=0.6)
    for x, y in zip(drive_days, dc_v2g):
        ax.text(x, y - 220, f"{y:,}", ha="center", fontsize=8,
                fontweight="bold", color="#2C5F2D")
    for x, y in zip(drive_days, bev_v2g):
        ax.text(x, y + 130, f"{y:,}", ha="center", fontsize=8,
                fontweight="bold", color="#02808F")
    ax.set_xlabel("Driving days per week", fontsize=10)
    ax.set_ylabel("Annual V2G kWh / car", fontsize=10)
    ax.set_title("(7) Drive-days sensitivity\n"
                 "fewer drive days -> more SoC headroom -> more V2G",
                 fontsize=10, fontweight="bold")
    ax.set_xticks(drive_days)
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(4800, 7800)

    # Panel 8: headlines text
    ax = axes[1, 3]
    ax.axis("off")
    lines = [
        ("Headline sensitivities", "title"),
        ("* TAOZ spread is the biggest lever", None),
        ("* Charger CAPEX 2028 halves payback", None),
        ("* Plug-in prob relatively insensitive", None),
        ("* GridAgent binds only at beta*gamma=1", None),
        ("* Return-home 20:00 -> revenue -18 %", None),
        ("* Drive-days curve monotonic:", None),
        ("    - 0 d/wk DC = 7,038 kWh (ceiling)", None),
        ("    - 7 d/wk DC = 5,344 kWh (floor)", None),
        ("    - BEV within ~2 % of DC at 0 d/wk", None),
        ("      (both use Wong 87 % plug-in prob)", None),
        ("* Panel 3 shows ANNUAL gross NIS revenue", None),
        ("  (10-yr net after CAPEX ~half that)", None),
    ]
    y = 0.95
    for txt, kind in lines:
        w = "bold" if kind == "title" else "normal"
        sz = 12 if kind == "title" else 10.5
        ax.text(0.02, y, txt, fontsize=sz, fontweight=w,
                transform=ax.transAxes, va="top")
        y -= 0.09

    fig.suptitle("Sensitivity summary  -  seven sweeps around the baseline",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT, dpi=150, facecolor="white")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
