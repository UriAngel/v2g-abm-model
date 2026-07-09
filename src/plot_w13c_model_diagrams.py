"""Methodology diagrams: hourly simulation flow + EVAgent state machine.

Rendered with Graphviz (dot) for publication-quality layout.
  w13c_model_flow.png     - one simulated hour, agent update order
  w13c_state_machine.png  - EVAgent operational states and transitions

Content mirrors run_w9_fleet.run_year and agents/ev_agent.py exactly:
update order (aggregator -> EV agents -> feeder), the V2G six-condition
gate, 7.0 kW charge / 9.6 kW discharge, 50 % floor, 90 % max_soc cap.

Run:  python -m src.plot_w13c_model_diagrams
"""

import subprocess
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

INK    = "#1e293b"
TEAL   = "#0f766e"
BLUE   = "#1d4ed8"
AMBER  = "#d97706"
RED    = "#b91c1c"
GREY   = "#475569"
TEAL_F = "#eef6f5"
BLUE_F = "#eef2fd"
AMBERF = "#fdf3e7"

FLOW_DOT = f"""
digraph flow {{
  graph [rankdir=TB, splines=ortho, nodesep=0.5, ranksep=0.42,
         fontname="Helvetica", bgcolor="white", dpi=150, pad=0.2];
  node  [shape=box, style="rounded,filled", fontname="Helvetica",
         fontsize=11, color="{GREY}", fillcolor="white",
         fontcolor="{INK}", penwidth=1.2, margin="0.22,0.12"];
  edge  [color="{GREY}", penwidth=1.2, arrowsize=0.8,
         fontname="Helvetica", fontsize=9.5, fontcolor="{GREY}"];

  hour  [label=<<B>Hour h&nbsp; (1 &hellip; 8,760)</B>>,
         fillcolor="{TEAL_F}", color="{TEAL}"];
  agg   [label=<<B>AggregatorAgent</B><BR/>discharge signal for h &larr; pricing module<BR/>(inside the tariff peak window?)>,
         fillcolor="{BLUE_F}", color="{BLUE}"];
  mob   [label=<<B>EVAgent mobility update</B> &nbsp;<I>(each agent, fixed order)</I><BR/>depart / drive / return per typology schedule;<BR/>trip energy drawn from state of charge>];
  dec   [label=<<B>Charging / discharging decision</B> &nbsp;<I>(counterfactual rule)</I><BR/>V0: charge at 7.0 kW when plugged and SoC &lt; target<BR/>V1G: charge off-peak only, departure-aware target (&le; 90 %)<BR/>V2G: V1G charging + six-condition discharge gate (Figure 3.2)>];
  grid  [label=<<B>GridAgent feeder check</B><BR/>can_charge / can_discharge against transformer kVA<BR/>(household baseline load included)>,
         fillcolor="{AMBERF}", color="{AMBER}"];
  commit[label=<<B>Commit action</B><BR/>energy, revenue / cost recorded; feeder net load updated>];
  aging [label=<<B>Battery health update</B><BR/>calendar + cycle aging applied to state of health>];
  log   [label=<<B>Log write</B> and end-of-hour reconciliation>];
  next  [label=<<B>next hour&nbsp; h &larr; h + 1</B>>,
         fillcolor="{TEAL_F}", color="{TEAL}"];

  hour -> agg -> mob -> dec;
  dec  -> grid  [label=" proposed action (kW)"];
  grid -> commit[label=" allowed", fontcolor="{TEAL}", color="{TEAL}"];
  grid -> aging [label=" denied: action skipped ", fontcolor="{RED}",
                 color="{RED}", style=dashed];
  commit -> aging -> log -> next;
  next -> hour [style=dashed, color="{TEAL}", constraint=false];
}}
"""

SM_DOT = f"""
digraph sm {{
  graph [rankdir=TB, splines=true, nodesep=0.9, ranksep=1.0,
         fontname="Helvetica", bgcolor="white", dpi=150, pad=0.25];
  node  [shape=box, style="rounded,filled", fontname="Helvetica",
         fontsize=11, fontcolor="{INK}", penwidth=1.4,
         margin="0.25,0.14"];
  edge  [fontname="Helvetica", fontsize=9, color="{GREY}",
         fontcolor="{INK}", penwidth=1.1, arrowsize=0.8,
         labeldistance=2.0];

  driving [label=<<B>DRIVING</B><BR/>away, SoC falling>,
           color="{RED}", fillcolor="#fdf0ef"];
  parked  [label=<<B>PARKED, NOT PLUGGED</B><BR/>home or away>,
           color="{GREY}", fillcolor="#f4f5f7"];
  plugged [label=<<B>PLUGGED, IDLE</B><BR/>home charger connected>,
           color="{TEAL}", fillcolor="{TEAL_F}"];
  charging[label=<<B>CHARGING</B><BR/>7.0 kW, up to target &le; 90 %>,
           color="{BLUE}", fillcolor="{BLUE_F}"];
  discharging [label=<<B>DISCHARGING (V2G)</B><BR/>9.6 kW, down to the 50 % floor>,
           color="{AMBER}", fillcolor="{AMBERF}"];

  {{ rank=same; driving; parked; }}
  {{ rank=same; charging; discharging; }}

  driving -> parked   [label="return home,\\nno plug-in (13 %)"];
  parked  -> driving  [label="departure\\nhour"];
  driving -> plugged  [label="return home, plug in\\n(87 % of evenings)"];
  parked  -> plugged  [label="plug in later"];
  plugged -> driving  [label="departure hour\\n(unplug)"];
  plugged -> charging [label="charging rule fires\\nV0: SoC &lt; target\\nV1G/V2G: off-peak"];
  charging -> plugged [label="target reached\\n(&le; 90 % cap)"];
  plugged -> discharging [label="six-condition gate TRUE\\nsignal &middot; opt-in &middot; capable &middot;\\nSoC &gt; 50 % &middot; price &ge; OSP &middot; retailer"];
  discharging -> plugged [label="signal ends, SoC &le; 50 %,\\nor feeder denial"];
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
