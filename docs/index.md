# robot-dog documentation

This project offers a deterministic offline fake and Python-first Unitree Go2 EDU adapters. **Offline tests are not physical robot validation.** No unit, firmware, SDK installation, or network configuration has been commissioned by this release.

## Start offline (default)

From the root, run `uv sync`, `uv run robot-dog demo`, and `uv run pytest`. No hardware, SDK, ROS 2, or credentials are required. See [offline getting started](getting-started/offline.md), [architecture](architecture.md), and [testing](testing.md).

## Optional hardware paths

All live profiles require deliberate selection of the interface and DDS domain. Read the [Python SDK2 integration](integrations/python-sdk2.md) and [read-only first-connection checklist](safety/first-connection-checklist.md) before even probing a target. The [full-control API map](integrations/full-control.md) documents explicitly gated sport, service/mode, peripheral, and expert low-level controls. Those commands are disabled by default and require the [full-control safety checklist](safety/full-control-checklist.md), a qualified operator, independent physical stop, and separate expert approval for motor commands. C++ and ROS 2 integrations are also [optional](integrations/cpp-sdk2.md) [profiles](integrations/ros2.md).

Use a separately obtained Unitree SDK and CycloneDDS; never bundle SDK source, firmware, or vendor binaries. See [third-party notices](third-party.md), [compatibility](compatibility.md), and [source references](references.md).

## Policies and records

Read the [safety policy](safety/safety-policy.md), [control authority](safety/control-authority.md), [battery and charging](safety/battery-charging.md), [hardware intake](hardware/intake.md), and [security guidance](security.md). A local or CI test cannot authorize a physical action. Keep all real identifiers and telemetry outside this repository.

See [contributing](https://github.com/couplet-physical-ai/robot-dog/blob/main/CONTRIBUTING.md), [security reporting](https://github.com/couplet-physical-ai/robot-dog/blob/main/SECURITY.md), [LICENSE](https://github.com/couplet-physical-ai/robot-dog/blob/main/LICENSE), and [NOTICE](https://github.com/couplet-physical-ai/robot-dog/blob/main/NOTICE).
