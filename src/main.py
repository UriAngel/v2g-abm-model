"""V2G ABM — main entry point.

For now this script just confirms the project is wired up correctly:
  - imports the EV agent class (no errors)
  - prints a one-line summary

Friday it grows: load config → create one EVAgent → step it through a day
→ write the CSV log to outputs/.
"""

from src.agents.ev_agent import EVAgent, DAILY_CHARGER


def main() -> None:
    """Smoke test — runs in under a second."""
    agent = EVAgent(
        agent_id=1,
        typology=DAILY_CHARGER,
        counterfactual="V0",
    )
    print("=== V2G ABM — Trinity Week 7, Thursday-night skeleton ===")
    print(f"Created EVAgent id={agent.id}, "
          f"typology={agent.typology}, counterfactual={agent.counterfactual}")
    print(f"Starting SoC = {agent.state.soc:.0%}, "
          f"battery = {agent.state.battery_kwh_usable} kWh, "
          f"chemistry = {agent.state.chemistry}")
    print()
    print("Skeleton OK.  Next: Friday adds step() logic.")


if __name__ == "__main__":
    main()
