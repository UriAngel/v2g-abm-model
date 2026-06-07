# W7 walkthrough — what got built and why

Trinity Week 7 of the dissertation. Goal of the week: a working `EVAgent` class running three counterfactuals (V0, V1G, V2G) for one EV over one simulated week, with three CSV outputs and one comparison chart, demoable by Monday.

---

## Thursday — project skeleton

| File | What it is | Why |
|---|---|---|
| `README.md` | Project overview | First thing anyone sees |
| `requirements.txt` | List of Python libraries | One command installs everything |
| `src/agents/ev_agent.py` | The first agent class — state variables only | Foundation for Friday's logic |
| `src/config/default_config.yaml` | Default parameter values from v8 | One file holds all the numbers |
| `src/main.py` | The entry point | Runs the demo |

Smoke test result: ✅ runs successfully on user's machine, prints the expected startup line.

---

## Friday — mobility + V0 + V1G + chart

| File added | What it adds |
|---|---|
| `src/pricing.py` | Simple hourly electricity-price function: off-peak / shoulder / peak |
| `src/agents/ev_agent.py` (extended) | Step A (mobility), Step B (V0 rule + V1G rule + V2G stub), Step C (placeholder), hourly logging |
| `src/run_demo.py` | Driver script that runs the EV through one week for each counterfactual |
| `src/plot_demo.py` | Generates the V0-vs-V1G-vs-V2G comparison chart |
| `src/main.py` (updated) | Now calls the demo runner directly |
| `outputs/v0_ev01.csv` | One row per simulated hour, V0 counterfactual |
| `outputs/v1g_ev01.csv` | Same, V1G counterfactual |
| `outputs/v2g_ev01.csv` | Same, V2G stub (= V1G until Saturday) |
| `outputs/w7_soc_three_counterfactuals.png` | The headline chart for Monday |

### Headline numbers from the W7 demo

For one Daily Charger over one simulated week:

| Counterfactual | kWh bought | Money spent | Charge hours | Ending SoC |
|---|---|---|---|---|
| **V0 (naive)** | 65.68 | **25.14** | 86 | 100.0 % |
| **V1G (smart)** | 63.00 | **6.30** | 9 | 95.8 % |
| **V2G (stub)** | 63.00 | 6.30 | 9 | 95.8 % |

V1G uses **4× less money** than V0 for almost the same energy bought.  The chart shows V0 (gray) hugging 100% throughout the week while V1G (green) sits at 80-95% — only topping up during cheap hours.

### How to reproduce locally

```bash
cd ~/Documents/GitHub/v2g-abm-model
source venv/bin/activate
python -m src.main           # runs the simulation, writes 3 CSVs
python -m src.plot_demo      # makes the chart
open outputs/w7_soc_three_counterfactuals.png  # view it
```

---

## Saturday — V2G real (replaces stub)

| File added | What it adds |
|---|---|
| `src/aggregator_stub.py` | Tells each EV "discharge now" between 17:00 and 22:00 — the simplest possible aggregator signal |
| `src/agents/ev_agent.py` (extended) | New `_rule_v2g` method implementing the priority order from v8 §3.5: emergency charge → V2G discharge (OSP gate + aggregator signal + SoC floor) → smart charge → idle |
| `src/agents/ev_agent.py` (`_do_discharge`) | Physical discharge logic: pulls from battery, respects max-discharge power and the 50% SoC floor, applies discharging efficiency, records the energy and revenue |

The agent's OSP (Optimal Selling Price) is set to 0.30 — between the shoulder (0.20) and peak (0.45) prices. That means the agent accepts every discharge offer during the peak window and rejects every offer outside it. W8 will make OSP a per-agent value derived from Liao's marginal-cost equation.

### Headline numbers after Saturday

| Counterfactual | kWh bought | kWh sold | Net cost (− = earned) | Charge h | Discharge h | Ending SoC |
|---|---|---|---|---|---|---|
| V0 (naive) | 65.7 | 0 | **25.14** | 86 | 0 | 100% |
| V1G (smart) | 63.0 | 0 | **6.30** | 9 | 0 | 95.8% |
| V2G (active) | 182.0 | 127.2 | **−39.02** | 26 | 20 | 61.1% |

The V2G owner ends the week with **a net income of 39.02 currency units**, versus V0 paying 25.14 and V1G paying 6.30. V2G buys more energy because it has to refill the battery after each evening discharge — but it sells that energy back at 4.5× the buying price, so the net is strongly positive.

### What the chart shows

`outputs/w7_soc_three_counterfactuals.png`:

- **V0 (gray)** hugs 100% almost continuously, dipping only during the morning and evening commute.
- **V1G (green)** sits at 80–95%, charging only during cheap hours.
- **V2G (teal)** has a distinctive sawtooth: drops to the 50% floor every evening peak as the car discharges to the grid, then climbs back to 90%+ during off-peak hours overnight.

The visible discharge events on V2G are the entire point — V1G saves money, V2G makes money.

---

## Monday — demo prep

Materials ready for the meeting:
- `outputs/v0_ev01.csv`, `outputs/v1g_ev01.csv`, `outputs/v2g_ev01.csv` — the raw data
- `outputs/w7_soc_three_counterfactuals.png` — the chart
- This walkthrough — the explanation
