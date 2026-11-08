# robot-dog

Python-first, offline-testable adapters for Unitree Go2 EDU robotics, with separately gated optional SDK2 hardware controls.

![Status: provided as is](https://img.shields.io/badge/status-provided--as--is-lightgrey) ![License: Apache--2.0](https://img.shields.io/badge/license-Apache--2.0-blue)

Created at [Exowatt](https://exowatt.com). Published under the independently governed, vendor-neutral `couplet-physical-ai` organization.

## Status

**Provided as-is.** The deterministic fake and source-level adapter tests are available; no physical unit, firmware, network, SDK installation, or safety performance is validated by this release. There is no support or commissioning commitment. This is not a safety-rated controller or production autonomy system.

## Install

Install [uv](https://docs.astral.sh/uv/) and Python 3.11 or newer. From a checkout:

```sh
uv sync
```

The base package has no required runtime dependencies. The default development environment installs public test/development tools, not Unitree SDK, CycloneDDS, ROS 2, firmware, or vendor binaries. Do not attach a robot for the offline path.

## Quickstart — default offline fake

```sh
uv run robot-dog demo
uv run robot-dog capabilities
uv run robot-dog status
uv run pytest
```

`demo` uses deterministic telemetry and fake clock; `capabilities` and `status` inspect the offline adapter. After public development dependencies are installed, these commands require no hardware, SDK, runtime network access, ROS 2, credentials, or private services and never issue a robot command. `uv run robot-dog doctor` additionally performs read-only local environment diagnostics. See [offline getting started](docs/getting-started/offline.md) and [testing](docs/testing.md).

## Configuration and optional profiles

The default CLI mode is offline. Hardware is **never** selected by environment autodiscovery: the optional `robot-dog unitree` operator commands require an explicitly specified robot-facing interface, DDS domain, and hardware acknowledgement. Write-capable operations require additional operator intent; special motions and expert low-level commands have separate gates, disabled by default. An acknowledgement flag is not a substitute for a physical safety review.

For real hardware, follow the [Python SDK2 guide](docs/integrations/python-sdk2.md), [read-only first-connection checklist](docs/safety/first-connection-checklist.md), and [full-control safety checklist](docs/safety/full-control-checklist.md). Optional C++ SDK2 and ROS 2 profiles are documented separately in [C++](docs/integrations/cpp-sdk2.md) and [ROS 2](docs/integrations/ros2.md). The offline command `uv run robot-dog unitree catalog` lists available actions without opening DDS.

## Prerequisites for optional hardware use

A qualified operator must separately obtain the appropriate Unitree Go2 hardware/manual, pinned [Unitree SDK2 Python](https://github.com/unitreerobotics/unitree_sdk2_python) revision, a compatible Linux host and CycloneDDS runtime, and any C++ SDK2 or ROS 2 components relevant to the chosen profile. Review the SDK's entire dependency closure and platform compatibility; no Unitree SDK (including Python/C++/ROS), CycloneDDS native library, ROS distribution, firmware, or vendor binary is bundled here. See [third-party notices](docs/third-party.md).

## Safety and limits

**Do not treat tests, documentation, or an SDK import as hardware commissioning.** Before even a read-only connection, verify the exact robot and network in a private intake record and establish an isolated link. Before any motion or service mutation, obtain explicit authorization, a competent operator/observer, clear workspace/restraint as appropriate, a physical stop, authority handoff, and abort criteria. Expert low-level motor commands must remain disabled unless separately approved and all low-level gates are satisfied. Follow the delivered vendor manual and the [safety policy](docs/safety/safety-policy.md). Never commit real serials, robot/network identifiers, raw telemetry, or credentials.

## License

Original project code is [Apache-2.0](LICENSE). [NOTICE](NOTICE) describes separately obtained third-party components and their different licenses; the project license does not cover their code.

## Contributing

See the [contribution guide](CONTRIBUTING.md) and [organization contribution policy](https://github.com/couplet-physical-ai/.github/blob/main/CONTRIBUTING.md). Contributions require DCO sign-off (`git commit -s`), not a CLA. Hardware-facing changes need independent safety review.

## Security

Report vulnerabilities through [GitHub private vulnerability reporting](https://github.com/couplet-physical-ai/robot-dog/security/advisories/new). See [SECURITY.md](SECURITY.md) and the [organization security policy](https://github.com/couplet-physical-ai/.github/blob/main/SECURITY.md); never open a public issue for a vulnerability.
