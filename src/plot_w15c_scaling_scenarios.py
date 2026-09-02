"""Scaling scenarios for Section 5.7: what changes when the fleet grows.

Left panel:  feeder worst-case export envelope as EVs per household rise
             from today's fraction to two per household (all participants
             discharging at once; constants from grid_agent.py).
Right panel: national annual NET V2G revenue pool as the EV share of the
             fleet grows from today (5.7%) to the 2030 target (30%),
             at three capable-and-participating shares (beta*gamma).

All inputs are model constants; no new simulation is required because the
worst case is analytic (every participant discharging simultaneously) and
the pool scales linearly in alpha and beta*gamma at constant per-vehicle
economics.

Run:  python -m src.plot_w15c_scaling_scenarios
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.plot_style import apply_style, PALETTE
from src.fleet_assumptions import N_FLEET_ISRAEL

apply_style()

OUT = Path(__file__).resolve().parent.parent / "outputs" / "w15c_scaling_scenarios.png"

# Feeder constants (grid_agent.py, IEC-derived)
HH = 54           # households per Israeli transformer
KVA = 517.0       # average transformer rating
P_DIS = 9.6       # discharge power per EV, kW
BASE_WINTER = 1.6 # kW per household, winter 17:00 (peak-window minimum)
BASE_SUMMER = 2.8 # kW per household, summer 19:00 (peak-window maximum)
MARGIN = 0.8      # ENA planning margin

# Per-EV NET pool (driver + aggregator), NIS/yr - w11 constants
_KWH = {"Daily Charger": 4820, "BEV 2nd Vehicle": 6220}
_PEAK, _OFF, _RTE = 1.6895, 0.528, 0.9025
PER_EV_NET = sum(k * _PEAK - k / _RTE * _OFF for k in _KWH.values()) / len(_KWH)


def main() -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.6))

    # ---- left: EVs per household ----
    n = np.linspace(0.0, 2.0, 41)
    net_w = HH * (n * P_DIS - BASE_WINTER)
    net_s = HH * (n * P_DIS - BASE_SUMMER)
    ax1.fill_between(n, net_s, net_w, color=PALETTE["israel"], alpha=0.12)
    ax1.plot(n, net_w, "-", color=PALETTE["israel"], lw=2.2,
             label="winter 17:00 baseline - export worst case")
    ax1.plot(n, net_s, "--", color=PALETTE["israel"], lw=1.8,
             label="summer 19:00 baseline")
    ax1.axhline(KVA * MARGIN, color=PALETTE["cost"], ls="--", lw=1.2,
                label="80% planning margin (413 kW)")
    ax1.axhline(KVA, color=PALETTE["amber"], ls=":", lw=1.4,
                label="517 kVA nameplate rating")
    ax1.axhline(0, color="black", lw=0.8)

    n_margin = (KVA * MARGIN / HH + BASE_WINTER) / P_DIS
    n_plate = (KVA / HH + BASE_WINTER) / P_DIS
    ax1.plot([n_margin], [KVA * MARGIN], "x", color=PALETTE["cost"], ms=10)
    ax1.annotate(f"margin crossed at {n_margin:.2f} EV/HH",
                 xy=(n_margin, KVA * MARGIN), xytext=(0.15, 640),
                 fontsize=10.5, color=PALETTE["cost"],
                 arrowprops=dict(arrowstyle="->", color=PALETTE["cost"], lw=1))
    ax1.plot([n_plate], [KVA], "x", color=PALETTE["amber"], ms=10)
    ax1.annotate(f"nameplate at {n_plate:.2f} EV/HH",
                 xy=(n_plate, KVA), xytext=(1.45, 200),
                 fontsize=10.5, color=PALETTE["amber"],
                 arrowprops=dict(arrowstyle="->", color=PALETTE["amber"], lw=1))
    share_2ev = (KVA * MARGIN / HH + BASE_WINTER) / (2 * P_DIS)
    ax1.text(0.06, -215,
             f"at 2 EV/HH only ~{share_2ev*100:.0f}% of vehicles can discharge\n"
             "at once: dispatch scheduling becomes the binding layer",
             fontsize=10.5, color=PALETTE["neutral"], style="italic")

    ax1.set_xlabel("EVs per household on the feeder (all discharging at once)")
    ax1.set_ylabel("Net feeder load (kW)")
    ax1.set_title("(a) Feeder worst case as ownership deepens", fontsize=17)
    ax1.legend(fontsize=9.5, loc="upper left")
    ax1.set_ylim(-260, 900)

    # ---- right: fleet penetration ----
    alpha = np.linspace(0.057, 0.30, 41)
    for bg, color, tag in ((0.10, PALETTE["israel_lt"], "beta*gamma = 0.10"),
                           (0.20, PALETTE["israel"], "beta*gamma = 0.20"),
                           (0.40, "#0a4f49", "beta*gamma = 0.40")):
        pool = alpha * bg * N_FLEET_ISRAEL * PER_EV_NET / 1e6
        ax2.plot(alpha * 100, pool, lw=2.4, color=color, label=tag)
        ax2.text(30.3, pool[-1], f"{pool[-1]:,.0f}", fontsize=10.5,
                 color=color, va="center", fontweight="bold")
    ax2.axvline(5.7, color=PALETTE["neutral"], ls=":", lw=1.2)
    ax2.text(6.0, ax2.get_ylim()[1] * 0.02, "today 5.7%", fontsize=10.5,
             color=PALETTE["neutral"])
    ax2.set_xlabel("EV share of the national fleet, alpha (%)")
    ax2.set_ylabel("National NET V2G pool (millions of NIS per year)")
    ax2.set_title("(b) National pool toward the 2030 target", fontsize=17)
    ax2.legend(fontsize=9.5, loc="upper left")
    ax2.set_xlim(4, 33)

    fig.tight_layout()
    fig.savefig(OUT)
    print(f"Saved {OUT}")
    print(f"n_margin={n_margin:.3f}, n_plate={n_plate:.3f}, share@2EV={share_2ev:.3f}, "
          f"per_ev_net={PER_EV_NET:.0f}")


if __name__ == "__main__":
    main()
