# Contributing to robot-dog

Contributions require DCO sign-off (`git commit -s`); no CLA is required. Start with [AGENTS.md](AGENTS.md), [SECURITY.md](SECURITY.md), and the relevant [safety documents](docs/safety/safety-policy.md). The ordinary development path is `uv sync`, `uv run robot-dog demo`, and `uv run pytest`, without any robot, vendor SDK, or ROS 2 installation.

Use only synthetic fixtures. Do not submit credentials, real robot/network/serial identifiers, raw sensor data, SDK source or binaries, firmware, or unreviewed third-party assets. Preserve required [third-party notices](docs/third-party.md).

Hardware-facing changes—including network/session setup, motion, service control, authority/deadman/stop behavior, and low-level motors—need explicit independent safety review and qualified operator approval. Keep physical tests out of default CI. Offline test success is not physical validation.
