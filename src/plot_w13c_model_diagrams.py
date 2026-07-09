"""Methodology diagrams: hourly simulation flow + EVAgent state machine.

Rendered with Graphviz (dot). Near-monochrome design: ink boxes, one teal
accent, red reserved for the denial path.

Charging targets (per agents/ev_agent.py): V0 and V1G charge toward the
typology target_soc (Wong Table 1 mean SoC after charge, e.g. 89.2 % for
the Daily Charger; hard ceiling 1.0 never reached in practice); only
V2G-opted-in agents cap charging at V2G_MAX_SOC = 90 %.

Run:  python -m src.plot_w13c_model_diagrams
"""

import subprocess
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

INK   = "#1e293b"
GREY  = "#64748b"
TEAL  = "#0f766e"
RED   = "#b91c1c"
TEALF = "#f0f7f6"

FLOW_DOT = f"""
digraph flow {{
  graph [rankdir=TB, splines=ortho, nodesep=0.55, ranksep=0.5,
         fontname="Helvetica", bgcolor="white", dpi=200, pad=0.3];
  node  [shape=box, style="rounded,filled", fontname="Helvetica",
         fontsize=11, color="{INK}", fillcolor="white",
         fontcolor="{INK}", penwidth=1.0, margin="0.28,0.16"];
  edge  [color="{GREY}", penwidth=1.1, arrowsize=0.75,
         fontname="Helvetica", fontsize=9.5, fontcolor="{GREY}"];

  hour  [label=<<B>Hour h&nbsp; (1 &hellip; 8,760)</B>>,
         fillcolor="{TEALF}", color="{TEAL}"];
  agg   [label=<<B>AggregatorAgent</B><BR/><BR/>discharge signal for h &larr; pricing module<BR/>(inside the tariff peak window?)>];
  mob   [label=<<B>EVAgent mobility update</B> &nbsp;<I>(each agent, fixed order)</I><BR/><BR/>depart / drive / return per typology schedule;<BR/>trip energy drawn from state of charge>];
  dec   [label=<<B>Charging / discharging decision</B> &nbsp;<I>(counterfactual rule)</I><BR/><BR/>V0: charge at 7.0 kW when plugged and SoC &lt; typology target<BR/>V1G: charge off-peak only, departure-aware target<BR/>V2G: V1G charging + six-condition discharge gate (Figure 3.2);<BR/>opted-in agents cap charging at 90 % SoC>];
  grid  [label=<<B>GridAgent feeder check</B><BR/><BR/>can_charge / can_discharge against transformer kVA<BR/>(household baseline load included)>];
  commit[label=<<B>Commit action</B><BR/><BR/>energy, revenue / cost recorded; feeder net load updated>];
  aging [label=<<B>Battery health update</B><BR/><BR/>calendar + cycle aging applied to state of health>];
  log   [label=<<B>Log write</B> and end-of-hour reconciliation>];
  next  [label=<<B>next hour&nbsp; h &larr; h + 1</B>>,
         fillcolor="{TEALF}", color="{TEAL}"];

  hour -> agg -> mob -> dec;
  dec  -> grid  [label="  proposed action (kW)"];
  grid -> commit[label="  allowed"];
  grid -> aging [label="  denied: action skipped  ", fontcolor="{RED}",
                 color="{RED}", style=dashed];
  commit -> aging -> log -> next;
  next -> hour [style=dashed, color="{TEAL}", constraint=false];
}}
"""

SM_DOT = f"""
digraph sm {{
  graph [rankdir=TB, splines=true, nodesep=1.3, ranksep=1.7,
         fontname="Helvetica", bgcolor="white", dpi=200, pad=0.35];
  node  [shape=box, style="rounded,filled", fontname="Helvetica",
         fontsize=11, color="{INK}", fillcolor="white",
         fontcolor="{INK}", penwidth=1.1, margin="0.3,0.18"];
  edge  [fontname="Helvetica", fontsize=9, color="{GREY}",
         fontcolor="{INK}", penwidth=1.0, arrowsize=0.75];

  driving [label=<<B>DRIVING</B><BR/><BR/>away, SoC falling>];
  parked  [label=<<B>PARKED, NOT PLUGGED</B><BR/><BR/>home or away>];
  plugged [label=<<B>PLUGGED, IDLE</B><BR/><BR/>home charger connected>,
           color="{TEAL}", fillcolor="{TEALF}", penwidth=1.4];
  charging[label=<<B>CHARGING</B><BR/><BR/>7.0 kW, up to the typology target<BR/>(V2G opt-in capped at 90 %)>];
  discharging [label=<<B>DISCHARGING (V2G)</B><BR/><BR/>9.6 kW, down to the 50 % floor>];

  {{ rank=same; driving; parked; }}
  {{ rank=same; charging; discharging; }}

  driving -> parked   [label="return home, no plug-in (13 %)  "];
  parked  -> driving  [label="  departure hour"];
  driving -> plugged  [label="return home, plug in\\n(87 % of evenings)  "];
  parked  -> plugged  [label="  plug in later"];
  plugged -> driving  [label="departure hour (unplug)  "];
  plugged -> charging [label="charging rule fires\\n(V0: SoC below target;\\nV1G/V2G: off-peak)  "];
  charging -> plugged [label="  target reached"];
  plugged -> discharging [label="  six-condition gate TRUE\\n  (signal, opt-in, capable,\\n  SoC over 50 %, price at or\\n  above OSP, retailer match)"];
  discharging -> plugged [label="signal ends, SoC at 50 %,\\nor feeder denial  "];
}}
"""


def render(dot_src: str, out_png: Path) -> None:
    p = subprocess.run(["dot", "-Tpng", "-o", str(out_png)],
                       input=dot_src.encode(), capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode()[:2000])
    print("Saved", out_png)


if __name__ == "__main__":
    render(FLOW_DOT, OUT_DIR / "w13c_model_flow.png")
    render(SM_DOT, OUT_DIR / "w13c_state_machine.png")
