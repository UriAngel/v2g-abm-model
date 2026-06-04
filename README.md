# v2g-abm-model

Agent-based model of vehicle-to-grid (V2G) economics for an MSc dissertation at the University of Oxford, Department of Engineering Science.

Compares household, business, EV, aggregator, and grid agents over one simulated year, across two countries (Israel and the UK) and three counterfactuals (V0 naive, V1G smart charging, V2G active). Built in Python with [Mesa](https://mesa.readthedocs.io/).

**Spec:** see `V2G_ABM_Agent_Rules_v8.md` in `~/Desktop/Dissertation/Agent_Rules/`.

**Supervisor:** Prof David Wallom, Course Director, MSc in Energy Systems.

## Status

Trinity Week 7. First EV agent in development. Other agents queued.

## Quick start

```bash
# 1. Create a virtual environment (one-time setup)
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the demo (currently just the EV-agent test)
python -m src.main
```

## Folder layout

```
v2g-abm-model/
├── README.md                    (this file)
├── requirements.txt             (Python dependencies)
├── src/
│   ├── agents/                  (one file per agent class)
│   │   └── ev_agent.py
│   ├── config/                  (parameter values from v8 spec)
│   │   └── default_config.yaml
│   └── main.py                  (entry point — runs the demo)
├── tests/                       (sanity-check scripts)
├── outputs/                     (CSVs and plots produced by runs)
└── docs/                        (week-by-week walkthrough notes)
```

## Mapping to the rules document

Every code file references the relevant section of the v8 rules document in its docstring. For example, `ev_agent.py` opens with:

```python
"""EV Agent — implements §3 of the rules document.

Represents one electric vehicle: state of charge, state of health,
driving pattern. Each hour the agent decides whether to drive,
charge, or sell energy back to the grid.
"""
```

You should be able to open any source file, read it top-to-bottom, and follow what it does without prior coding background. If a line is unclear, it's a comment bug — flag it.
