#!/usr/bin/env python3
"""Run the full-control Unitree operator CLI from a source checkout.

This entry point intentionally delegates all parsing, acknowledgements, lazy
SDK loading, and error handling to ``robot-dog unitree``.  It does not contain a
second hardware-control implementation.

Examples::

    python examples/hardware/unitree_full_control.py --help
    python examples/hardware/unitree_full_control.py catalog
    python examples/hardware/unitree_full_control.py sport-invoke StandUp \\
        --interface enp2s0 --domain-id 0 --hardware-enabled \\
        --operator-acknowledged --intentional
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from robot_dog.cli import main  # noqa: E402


def run(argv: Sequence[str] | None = None) -> int:
    """Delegate to the installed/source-checkout robot-dog CLI."""

    selected = list(sys.argv[1:] if argv is None else argv)
    return main(["unitree", *selected])


if __name__ == "__main__":
    raise SystemExit(run())
