# W7 walkthrough — what got built and why

Trinity Week 7 of the dissertation. Goal of the week: a working `EVAgent` class running three counterfactuals (V0, V1G, V2G) for one EV over one simulated week, with three CSV outputs and one comparison chart, demoable by Monday.

---

## Thursday (today) — project skeleton

| File | What it is | Why |
|---|---|---|
| `README.md` | Project overview | First thing anyone (including David, examiners) sees |
| `requirements.txt` | List of Python libraries needed | One command installs everything |
| `src/__init__.py` | Marks `src/` as a Python package | Lets us write `from src.agents import EVAgent` |
| `src/agents/__init__.py` | Marks `src/agents/` as a sub-package | Same reason |
| `src/agents/ev_agent.py` | The first agent class — state variables only, no decision logic yet | Foundation for Friday/Saturday work. Sections of the v8 rules document are cited inside the docstrings. |
| `src/config/default_config.yaml` | Default parameter values from v8 §2, §3.1, §3.2, §3.5 | One file holds all the numbers we'll later tune |
| `src/main.py` | The entry point that runs when you type `python -m src.main` | Currently just confirms the agent imports without errors |
| `outputs/.gitkeep` | Empty placeholder so the `outputs/` folder is tracked by git | CSVs will appear here Friday |
| `docs/w7_walkthrough.md` | This file | Plain-English record of what was built each day |

### What you can do right now to confirm everything works

Open a Terminal and run:

```bash
cd ~/Documents/GitHub/v2g-abm-model
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

You should see:

```
=== V2G ABM — Trinity Week 7, Thursday-night skeleton ===
Created EVAgent id=1, typology=Daily Charger, counterfactual=V0
Starting SoC = 80%, battery = 60.0 kWh, chemistry = NMC
Skeleton OK.  Next: Friday adds step() logic.
```

If you see that output, the project is correctly set up. If you see an error, send me the exact error message and we fix it.

If you don't want to run Terminal commands yourself, that's fine — GitHub Desktop will show you all the files I added under "Changes". Click **Commit to main**, then **Push origin**. The code lives in your repo and we can run it later together.

---

## Friday — mobility + V0 + V1G

(To be filled in tomorrow.)

## Saturday — V2G + first chart

(To be filled in Saturday.)
