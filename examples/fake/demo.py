"""Run the deterministic fake robot demo without installing hardware SDKs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Keep this example runnable directly from a source checkout.  The installed
# package path takes precedence when the example is launched after installation.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from robot_dog.adapters import FakeRobotAdapter  # noqa: E402


def main() -> int:
    adapter = FakeRobotAdapter()
    payload = {
        "mode": "offline-fake",
        "read_only": True,
        "capabilities": adapter.capabilities(),
        "status": adapter.read_status().to_dict(),
        "telemetry": [frame.to_dict() for frame in adapter.telemetry_samples()],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
