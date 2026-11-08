"""Module entry point for ``python -m robot_dog``."""

from __future__ import annotations

from robot_dog.cli import main

if __name__ == "__main__":  # pragma: no cover - exercised by Python itself
    raise SystemExit(main())
