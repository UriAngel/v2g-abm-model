"""V2G ABM — main entry point.

Delegates to run_demo, which simulates the demo fleet through
one week under three counterfactuals.

Usage:
    python -m src.main
"""

from src.run_demo import main as run_demo_main


def main() -> None:
    run_demo_main()


if __name__ == "__main__":
    main()
