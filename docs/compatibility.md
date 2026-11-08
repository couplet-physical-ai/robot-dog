# Compatibility baseline

**Baseline date:** 2026-08-21
**Decision rule:** compatibility is established per unit/host pair, not by the `Go2 EDU` family name

This matrix separates upstream claims from project acceptance requirements. An **upstream-supported** combination may still be rejected for a particular unit if its hardware options, ABI, network path, or safety evidence differ.

## Compatibility matrix

| Layer | Baseline pin / target | Status | What must be verified |
| --- | --- | --- | --- |
| Robot hardware | Unitree Go2 EDU, exact SKU/options recorded at intake | **Conditional** | Compute, RAM, storage, sensors, ports, firmware, accessories, and physical safety are unit-specific. |
| C++ SDK | `unitree_sdk2` at `9754cd153af3da471b0fe5f3aa535e426fb11db3` | **Pinned upstream input** | Host architecture/ABI, selected build path, runtime libraries, and robot firmware/API behavior. |
| Python SDK | `unitree_sdk2_python` at `65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5` | **Pinned upstream input** | Python version, wheel/native-library architecture, installation provenance, and DDS security limitation. |
| ROS 2 integration | `unitree_ros2` at `668d1ec5a05d1c38d3306bdca7d59f2ba3581a88` | **Pinned upstream input** | Message packages, ROS 2 distribution, RMW selection, generated interfaces, and exact build result. |
| DDS | CycloneDDS `0.10.2`, commit `9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd` | **Pinned upstream input** | Runtime ABI, XML/configuration, domain ID, peer discovery, interface binding, and firewall behavior. |
| ROS 2 / OS | Ubuntu 20.04/Foxy or Ubuntu 22.04/Humble are listed as upstream tested; Humble is recommended upstream | **Upstream evidence, not acceptance** | Exact OS image, kernel, compiler, ROS packages, lifecycle/support constraints, and host architecture. [R7] |
| Optional sensors | None assumed | **Unknown until intake** | Physical presence, model, driver/message support, calibration, and read-only data test. |
| Network | Point-to-point NIC or isolated VLAN | **Required** | No corporate bridge, default gateway, VPN/hotspot bridge, or Internet exposure on the DDS path. |
| DDS security | No security assumption; Python prebuilt Cyclone package lacks DDS Security | **Security constraint** | Isolation and routing checks must pass before discovery. Do not claim authentication or encryption. [R14] |

## Hardware compatibility rules

1. **No inferred compute.** Do not select an Orin/Jetson build, CUDA path, RAM requirement, or storage requirement unless the unit manifest has an observed value.
2. **No inferred sensors.** Depth, LiDAR, camera, IMU, GNSS, and payload support are individually conditional. A family-level accessory list is not proof of installation.
3. **No inferred ports.** Software may use only interfaces identified on the physical unit and mapped to the exact host path.
4. **No inferred shell.** A unit can be controlled through an API without giving the operator shell access. Do not make SSH, serial, root, or default credentials a prerequisite unless formally authorized and observed.
5. **Firmware matters.** Record firmware and API behavior with the hardware result. Do not treat a successful host-side package build as firmware compatibility.

## Host and artifact compatibility

The C++ SDK's pinned build layout includes architecture-specific native libraries for `aarch64` and `x86_64`. This is an upstream repository observation, not a claim about the robot's internal computer and not permission to redistribute those binaries. [R3]

For every native library, wheel, container image, or package used in a test, record:

- exact source URL and commit/tag;
- SHA-256 (or the organization's approved artifact digest);
- target architecture and ABI;
- compiler/runtime and relevant build flags;
- whether the artifact was built from source or supplied prebuilt;
- the license/notice inventory; and
- the unit/host test that used it.

Builds that fetch a branch, floating tag, or unrecorded package-manager version are not reproducible compatibility evidence. A deviation from the baseline must name the reason, owner, new immutable reference, and re-test result.

## Required validation sequence

Run this sequence on the isolated test link and record sanitized evidence in the unit manifest:

1. Verify the physical intake and exact unit identity.
2. Capture host OS, architecture, runtime, ROS 2 distribution, and native artifact architecture.
3. Verify the four baseline revisions and their checksums/provenance.
4. Bind the DDS process to the dedicated interface and verify the domain/peer configuration.
5. Confirm there is no corporate bridge, default gateway, or Internet route on that path.
6. Perform read-only DDS discovery and telemetry/message validation.
7. Exercise no actuator or motion path until the separate operator-approved procedure is in force.
8. Record failures as compatibility blockers rather than working around them with an unpinned dependency or a broader network.

## Compatibility outcomes

- **Pass — read-only development:** intake, host/runtime, immutable artifacts, isolation, discovery, and telemetry pass.
- **Pass — controlled motion testing:** read-only pass plus a reviewed safety/motion procedure and operator authorization.
- **Conditional:** one or more optional features are not present or not validated; only the validated subset may be used.
- **Blocked:** any hardware identity, safety, ABI, DDS isolation, security, or licensing gate is unresolved.

## References

- [hardware/technical-baseline.md](hardware/technical-baseline.md)
- [hardware/intake.md](hardware/intake.md)
- [security.md](security.md)
- [third-party.md](third-party.md)
- [references.md](references.md)
