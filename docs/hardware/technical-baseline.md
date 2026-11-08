# Robot-dog technical baseline

**Status:** intake baseline, not a statement that every Go2 EDU unit has the same hardware
**Baseline date:** 2026-08-21
**Scope:** the Unitree Go2 EDU development boundary: one robot unit, an authorized engineering host, and the isolated DDS link between them

This document is deliberately conservative. A Go2 EDU is a configurable family. The family name is not evidence of a particular compute module, memory size, storage device, sensor option, connector, network interface, or operating-system capability. Unit-specific facts come from the intake record, not from a product name or an example found online.

## Evidence labels

Use these labels in this document and in unit records:

- **Official** — stated by the vendor or upstream project at the cited source.
- **Observed** — captured from the exact unit, artifact, or immutable upstream revision on the stated date.
- **Inferred** — a project engineering conclusion from the evidence. It is useful for design, but must not be presented as a hardware fact.
- **Unknown** — not established. Unknown is the correct value until intake or a controlled compatibility test establishes it.
- **Required** — a gate for use; it is not a claim about what the unit currently provides.

A source citation proves only the scope of the source. For example, an SDK README can establish a middleware version, but cannot establish that a particular robot has an Orin module or a depth camera.

## Baseline facts and non-facts

| Area | Baseline | Evidence / disposition |
| --- | --- | --- |
| Product family | Go2 EDU is treated as a configurable family. Record the exact SKU/options for each unit. | **Official**, [R12]. The marketing page is a live source; it is not an immutable hardware record. |
| Compute module | No module is assumed. In particular, do not assume NVIDIA Orin. | **Unknown / required to inspect**. |
| RAM and storage | No capacity, type, partitioning, or free-space value is assumed. | **Unknown / required to inspect**. |
| Sensors | Depth, LiDAR, camera, GNSS, and other options are absent until physically and programmatically verified. | **Unknown / required to inspect**. |
| Ports and buses | No Ethernet, USB, serial, expansion, charging, or accessory port is assumed to exist or be exposed to the application. | **Unknown / required to inspect**. |
| Shell access | Shell access, credentials, privilege level, and a supported login method are not assumed. | **Unknown / authorization required**. |
| C++ SDK | Unitree `unitree_sdk2` baseline pin: `9754cd153af3da471b0fe5f3aa535e426fb11db3`. | **Official upstream pin observed 2026-08-21**, [R1]. |
| Python SDK | Unitree `unitree_sdk2_python` baseline pin: `65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5`. | **Official upstream pin observed 2026-08-21**, [R4]. The pin is a dependency input, not evidence of a unit-local Python installation. |
| ROS 2 integration | Unitree `unitree_ros2` baseline pin: `668d1ec5a05d1c38d3306bdca7d59f2ba3581a88`. | **Official upstream pin observed 2026-08-21**, [R6]. |
| DDS implementation | CycloneDDS `0.10.2`, commit `9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd`. | **Official upstream pin observed 2026-08-21**, [R9]. |
| DDS security | Do not assume DDS Security. The Python prebuilt Cyclone package used by the baseline lacks DDS Security. | **Observed / security constraint**, [R14]. Treat traffic as unauthenticated and unencrypted unless an independently tested replacement proves otherwise. |
| Network shape | The default is one robot-to-host point-to-point NIC or a dedicated VLAN with no corporate bridge, default gateway, or Internet exposure. | **Required project control**, detailed in [security.md](../security.md). |
| Binary distribution | Do not vendor upstream binary libraries by default. | **Required project control**. The pinned C++ SDK tree includes architecture-specific DDS libraries; their presence upstream is not approval to copy them into this repository or a release. [R3] |

## System boundary

The supported development shape has four trust zones:

1. **Robot unit** — the physical Go2 EDU and whatever firmware, compute, sensors, and interfaces are verified during intake.
2. **Authorized engineering host** — the host that runs the selected SDK/ROS 2 process. Its architecture, OS, ROS 2 distribution, and runtime packages are recorded as compatibility evidence.
3. **DDS link** — a dedicated point-to-point NIC or isolated VLAN carrying only the approved robot/host traffic. It is not a general-purpose corporate LAN.
4. **Evidence and release stores** — controlled locations for manifests, sanitized logs, source archives, checksums, license notices, and any credentials. Secrets never belong in this repository or in the unit manifest.

The baseline does **not** authorize a control path through a corporate network, a default route, a cloud service, an Internet-connected robot interface, or an unverified accessory. Those are separate designs requiring review.

## Compatibility target

The upstream ROS 2 documentation names Ubuntu 20.04/Foxy and Ubuntu 22.04/Humble as tested combinations and recommends Humble. That is upstream compatibility evidence, not a project acceptance guarantee. [R7]

An actual unit/host pair is accepted only after the following are recorded:

- exact unit SKU/options and firmware;
- verified compute architecture, RAM, storage, sensor inventory, and available interfaces;
- host OS, kernel, architecture, Python, ROS 2 distribution, and CycloneDDS runtime;
- the exact SDK and middleware pins above, or a reviewed deviation;
- a link test on the isolated NIC/VLAN; and
- a safe, read-only discovery/telemetry smoke test before any command path is exercised.

Do not make a compatibility decision from a successful import alone. A package can import while its binary ABI, DDS discovery, message definitions, network path, or device options are incompatible.

## Baseline control gates

A unit is **intake-complete** only when [intake.md](intake.md) is checked and the template in [unit-manifest.template.yaml](unit-manifest.template.yaml) has been copied to the approved private inventory with real values kept out of this repository.

A unit is **development-ready** only when all of these gates pass:

1. **Hardware gate** — physical inspection and exact option inventory are complete; no unresolved safety defect exists.
2. **Interface gate** — every interface used by the software is observed on that unit and its purpose is recorded.
3. **Compatibility gate** — host/runtime and all immutable dependency pins are captured; deviations are explicit.
4. **Security gate** — DDS traffic is confined to the isolated link, routes are checked, and no Internet/corporate bridge is present.
5. **License gate** — the dependency closure, notices, and redistribution decision are recorded in [third-party.md](../third-party.md).
6. **Evidence gate** — logs and photos are traceable to the unit without placing serials, MACs, IPs, or secrets in this repository.

Passing a gate does not authorize autonomous motion or production operation. Physical safety review and an operator-approved test procedure remain required.

## Explicit assumptions ledger

The following are intentionally **not** assumptions in any example or future implementation:

- `Orin`, Jetson, a particular CPU/GPU, or a particular Linux image;
- a RAM or storage capacity;
- a depth module, LiDAR, camera, or any other optional sensor;
- a specific port, connector, bus, interface name, or link speed;
- SSH, serial console, root access, default credentials, or any shell at all;
- a reachable default gateway, DNS server, corporate network, or Internet route;
- DDS authentication, encryption, peer identity, or access control;
- permission to redistribute Unitree or dependency binaries; or
- a product-page option that is not present in the unit manifest and backed by intake evidence.

When code needs one of these properties, it must fail closed with a clear unmet-prerequisite message rather than silently guessing.

## References

- Immutable upstream sources and access dates are maintained in [references.md](../references.md).
- Licensing and redistribution controls are in [third-party.md](../third-party.md).
- Network and DDS controls are in [security.md](../security.md).
