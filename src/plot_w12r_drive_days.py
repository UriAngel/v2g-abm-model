"""Drive-days sensitivity  -  V2G revenue as function of driving days/week.

Sweeps the underlying "days-driven-per-week" parameter from 1 to 7 while holding
km-per-driving-day constant.  Runs both actively-dispatching typologies
(Daily Charger + BEV 2nd Vehicle).

Rationale
---------
Wong 2026 Table 1 fixes drive_days at typology-specific values:
    Daily Charger      6.43 d/wk
    BEV 2nd Vehicle    4.74 d/wk
The sweep asks how sensitive residential V2G revenue is to a driver's
actual driving schedule - a household with a 5-days-a-week commuter vs
a 2-days-a-week retiree.

The underlying arithmetic follows the same block-dispatch logic used
throughout the ABM:

    weekly_v2g_energy_kWh
        = eff_disc * P_disc *
          (weekday_peak_hours_home + weekend_peak_hours_home) *
          plug_prob * v2g_opted_in * soc_headroom_fraction

where soc_headroom_fraction depends on drive_days (higher drive days ->
lower start-of-evening SoC -> smaller headroom for export).

Numbers below are hard-coded from the underlying ABM run outputs.
Regenerate on demand.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


OUT = Path(__file__).resolve().parent.parent / "outputs" / "w12r_drive_days.png"


# --------------------------------------------------------------------------
# ABM output: annual V2G kWh per car, by drive-days-per-week
# --------------------------------------------------------------------------
# Numbers from the ABM sweep (sweep_w12w_drive_days.py):
# 120-agent fleet, Wong-Table-1 proportions, Israel V2G, full 8,760 h year.
# BEV plug-in probability aligned to Wong 87 %.
# Reported = mean V2G kWh per opted-in agent (each individual EV that
# actually participates in V2G).
drive_days = np.array([0, 1, 2, 3, 4, 5, 6, 7])
dc_v2g     = np.array([7038, 6789, 6587, 6349, 6114, 5882, 5650, 5344])
bev_v2g    = np.array([6915, 6869, 6819, 6741, 6725, 6636, 6556, 6495])
dc_rev_nis  = dc_v2g * 1.6895
bev_rev_nis = bev_v2g * 1.6895


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))

    # Left panel: annual V2G kWh
    ax = axes[0]
    ax.plot(drive_days, dc_v2g,  "-o", color="#2C5F2D", linewidth=2.2,
            markersize=9, label="Daily Charger (40 km/drive-day)")
    ax.plot(drive_days, bev_v2g, "-s", color="#02808F", linewidth=2.2,
            markersize=9, label="BEV 2nd Vehicle (22 km/drive-day)")
    for x, y in zip(drive_days, dc_v2g):
        ax.text(x, y - 200, f"{y:,}", ha="center", fontsize=9,
                fontweight="bold", color="#2C5F2D")
    for x, y in zip(drive_days, bev_v2g):
        ax.text(x, y + 130, f"{y:,}", ha="center", fontsize=9,
                fontweight="bold", color="#02808F")
    ax.axvline(6.43, color="#2C5F2D", linestyle=":", linewidth=1, alpha=0.7,
               label="DC baseline 6.43 d/wk")
    ax.axvline(4.74, color="#02808F", linestyle=":", linewidth=1, alpha=0.7,
               label="BEV baseline 4.74 d/wk")
    ax.set_xlabel("Driving days per week", fontsize=11)
    ax.set_ylabel("Annual V2G energy exported (kWh / car)", fontsize=11)
    ax.set_title("(a) Annual V2G energy vs driving-days per week",
                 fontsize=11.5, fontweight="bold")
    ax.set_xticks(drive_days)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(4800, 7800)

    # Right panel: annual revenue in NIS (Israel retail TAOZ peak)
    ax = axes[1]
    ax.plot(drive_days, dc_rev_nis,  "-o", color="#2C5F2D", linewidth=2.2,
            markersize=9, label="Daily Charger")
    ax.plot(drive_days, bev_rev_nis, "-s", color="#02808F", linewidth=2.2,
            markersize=9, label="BEV 2nd Vehicle")
    for x, y in zip(drive_days, dc_rev_nis):
        ax.text(x, y - 400, f"{y:,.0f}", ha="center", fontsize=9,
                fontweight="bold", color="#2C5F2D")
    for x, y in zip(drive_days, bev_rev_nis):
        ax.text(x, y + 230, f"{y:,.0f}", ha="center", fontsize=9,
                fontweight="bold", color="#02808F")
    ax.axvline(6.43, color="#2C5F2D", linestyle=":", linewidth=1, alpha=0.7)
    ax.axvline(4.74, color="#02808F", linestyle=":", linewidth=1, alpha=0.7)
    ax.set_xlabel("Driving days per week", fontsize=11)
    ax.set_ylabel("Annual V2G revenue (NIS / car)  -  Israel retail TAOZ peak",
                  fontsize=11)
    ax.set_title("(b) Annual driver-side revenue  -  Israel retail",
                 fontsize=11.5, fontweight="bold")
    ax.set_xticks(drive_days)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(8500, 13500)

    fig.suptitle("Drive-days sensitivity  -  actual ABM sweep (80-agent fleet, "
                 "mean per opted-in EV)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, facecolor="white")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
