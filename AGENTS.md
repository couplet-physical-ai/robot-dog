# Agent guidance for robot-dog

Start with the deterministic offline fake (`uv run robot-dog demo`) and tests (`uv run pytest`). Keep default behavior hardware-free, offline, and non-actuating; never initialize DDS, discover a device, or issue a command from imports, examples/fake, or default tests.

Do not commit robot or network identifiers, credentials, raw telemetry, captures, firmware, SDK source, or vendor binaries. The Unitree SDK is a separately obtained optional prerequisite and must never be bundled in this repository.

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [the safety policy](docs/safety/safety-policy.md) before changing a hardware-facing path. Any operation that can connect to or command a robot, change authority or a stop/deadman gate, or touch low-level motor controls requires a separate safety review and a qualified operator. Fake tests cannot establish hardware validation. Never run a hardware operation to validate a code edit.
