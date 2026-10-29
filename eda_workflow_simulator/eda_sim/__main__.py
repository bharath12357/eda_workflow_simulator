"""Allow ``python -m eda_sim`` to start the command-line interface."""

from eda_sim.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
