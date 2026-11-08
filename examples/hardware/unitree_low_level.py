#!/usr/bin/env python3
"""Run the explicit low-level Unitree CLI from a source checkout.

All safety gates, twelve-record JSON validation, DDS setup, and publishing are
implemented by ``robot-dog unitree low-level``.  This example is only a thin
runnable entry point and does not duplicate low-level or motion logic.

Examples::

    python examples/hardware/unitree_low_level.py --help
    python examples/hardware/unitree_low_level.py once commands.json \\
        --interface enp2s0 --domain-id 0 --hardware-enabled \\
        --operator-confirmed --expert-low-level-confirmed \\
        --robot-restrained-confirmed --motion-service-released \\
        --motion-ownership-confirmed
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from robot_dog.cli import main  # noqa: E402


def run(argv: Sequence[str] | None = None) -> int:
    """Delegate to the low-level Unitree command group."""

    selected = list(sys.argv[1:] if argv is None else argv)
    return main(["unitree", "low-level", *selected])


if __name__ == "__main__":
    raise SystemExit(run())
