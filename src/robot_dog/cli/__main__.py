"""Allow ``python -m robot_dog.cli`` as a convenience entry point."""

from __future__ import annotations

from . import main

if __name__ == "__main__":
    raise SystemExit(main())
