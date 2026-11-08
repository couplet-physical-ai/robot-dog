# Source and evidence ledger

**Ledger date:** 2026-08-21
**Rule:** use an immutable commit/tree/blob URL for source claims whenever the upstream system provides one. The access date records when the source was checked; it does not make a mutable URL immutable.

The labels below keep official statements, observed pins, and project inferences separate:

- **Official** — vendor/upstream material.
- **Observed** — exact content or revision checked on 2026-08-21.
- **Project control** — project requirement, not an upstream claim.
- **Inference** — engineering conclusion that must not be mistaken for hardware evidence.

## Immutable source ledger

| ID | Role / status | Immutable URL | Access date | Evidence used |
| --- | --- | --- | --- | --- |
| R1 | **Official, observed** — Unitree C++ SDK source | [unitree_sdk2 at `9754cd153af3da471b0fe5f3aa535e426fb11db3`](https://github.com/unitreerobotics/unitree_sdk2/tree/9754cd153af3da471b0fe5f3aa535e426fb11db3) | 2026-08-21 | SDK source and revision baseline. |
| R2 | **Official, observed** — Unitree C++ SDK license | [unitree_sdk2 LICENSE at the pinned commit](https://github.com/unitreerobotics/unitree_sdk2/blob/9754cd153af3da471b0fe5f3aa535e426fb11db3/LICENSE) | 2026-08-21 | Top-level BSD 3-Clause text. |
| R3 | **Official, observed** — C++ SDK third-party layout/build | [unitree_sdk2 thirdparty tree at the pinned commit](https://github.com/unitreerobotics/unitree_sdk2/tree/9754cd153af3da471b0fe5f3aa535e426fb11db3/thirdparty) | 2026-08-21 | Bundled headers/libraries and architecture-specific `libddsc`/`libddscxx` packaging; inspect exact files before distribution. |
| R4 | **Official, observed** — Unitree Python SDK source pin | [unitree_sdk2_python at `65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5`](https://github.com/unitreerobotics/unitree_sdk2_python/tree/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5) | 2026-08-21 | Python SDK revision baseline supplied by the verified intake record. |
| R5 | **Official, observed** — Unitree Python SDK license | [unitree_sdk2_python LICENSE at the pinned commit](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/LICENSE) | 2026-08-21 | Unitree Python SDK top-level BSD-3-Clause classification. |
| R6 | **Official, observed** — Unitree ROS 2 source | [unitree_ros2 at `668d1ec5a05d1c38d3306bdca7d59f2ba3581a88`](https://github.com/unitreerobotics/unitree_ros2/tree/668d1ec5a05d1c38d3306bdca7d59f2ba3581a88) | 2026-08-21 | ROS 2 integration revision baseline. |
| R7 | **Official, observed** — Unitree ROS 2 README | [unitree_ros2 README at the pinned commit](https://github.com/unitreerobotics/unitree_ros2/blob/668d1ec5a05d1c38d3306bdca7d59f2ba3581a88/README.md) | 2026-08-21 | Upstream-tested Ubuntu 20.04/Foxy and Ubuntu 22.04/Humble; Humble recommendation; upstream CycloneDDS 0.10.2 statement. |
| R8 | **Official, observed** — Unitree ROS 2 license | [unitree_ros2 LICENSE at the pinned commit](https://github.com/unitreerobotics/unitree_ros2/blob/668d1ec5a05d1c38d3306bdca7d59f2ba3581a88/LICENSE) | 2026-08-21 | Repository BSD 3-Clause text and package-level license declarations. |
| R9 | **Official, observed** — Eclipse CycloneDDS source | [CycloneDDS at commit `9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd`](https://github.com/eclipse-cyclonedds/cyclonedds/tree/9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd) | 2026-08-21 | Exact CycloneDDS 0.10.2 source revision. |
| R10 | **Official, observed** — CycloneDDS license/package metadata | [CycloneDDS LICENSE](https://github.com/eclipse-cyclonedds/cyclonedds/blob/9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd/LICENSE) and [package.xml](https://github.com/eclipse-cyclonedds/cyclonedds/blob/9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd/package.xml) | 2026-08-21 | EPL-2.0 or EDL-1.0 expression and version metadata. |
| R11 | **Official, observed** — CycloneDDS notices | [CycloneDDS NOTICE.md](https://github.com/eclipse-cyclonedds/cyclonedds/blob/9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd/NOTICE.md) | 2026-08-21 | Project notices, Zlib `libmd5-rfc`, and public-domain `getopt` entries. |
| R13 | **Official, observed** — bundled dependency license texts | [unitree_sdk2 licenses tree](https://github.com/unitreerobotics/unitree_sdk2/tree/9754cd153af3da471b0fe5f3aa535e426fb11db3/licenses) and [DDS C++ wrapper license](https://github.com/unitreerobotics/unitree_sdk2/blob/9754cd153af3da471b0fe5f3aa535e426fb11db3/thirdparty/include/ddscxx/dds/LICENSE) | 2026-08-21 | Eclipse CycloneDDS EPL/EDL text, Iceoryx Apache-2.0 text, RapidJSON MIT/third-party exception text, and the C++ wrapper's declared license. |
| R14 | **Observed baseline artifact note** — Python Cyclone dependency/security capability | [unitree_sdk2_python README at the pinned commit](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/README.md) and [CycloneDDS at the pinned commit](https://github.com/eclipse-cyclonedds/cyclonedds/tree/9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd) | 2026-08-21 | The Python SDK pins `cyclonedds==0.10.2` and documents prebuilt-binary installation; the verified Python prebuilt package lacks DDS Security. This is an artifact observation, not a claim that every CycloneDDS build lacks the feature. Record the exact wheel/artifact digest for each build. |

> **Python pin note:** R4/R5 preserve the official revision supplied in the verified 2026-08-21 baseline. The project must resolve and archive the exact source/license files used by the build; a URL that is not reachable in the build environment is a compatibility/provenance blocker, not a reason to substitute `main`.

## Official but mutable product source

| ID | Role / status | URL | Access date | Limitation |
| --- | --- | --- | --- | --- |
| R12 | **Official, mutable** — Unitree Go2 product page | [Unitree Go2](https://www.unitree.com/go2/) | 2026-08-21 | Product/configuration information can change and is not an immutable unit record. Use it to identify the family only; use physical intake and the private manifest for exact hardware. |

No immutable vendor product snapshot was used to infer Orin, RAM/storage, depth/LiDAR, ports, or shell access. Those values remain **unknown** until observed on a unit.

## Project controls and verification records

| ID | Type | Content |
| --- | --- | --- |
| P1 | **Project control** | DDS traffic must use an isolated point-to-point NIC/VLAN with no corporate bridge, default gateway, or Internet exposure. See [security.md](security.md). |
| P2 | **Project control** | Do not vendor upstream binaries by default; record provenance, checksum, license closure, and review for any exception. See [third-party.md](third-party.md). |
| P3 | **Project control** | Real unit serial/MAC/IP/secrets stay out of the repository and committed template. See [hardware/unit-manifest.template.yaml](hardware/unit-manifest.template.yaml). |
| P4 | **Observed baseline** | The Python prebuilt Cyclone package lacks DDS Security; the security baseline therefore makes no authentication/encryption claim. See [security.md](security.md) and [compatibility.md](compatibility.md). |

## Citation maintenance

When a dependency changes:

1. add a new row with the exact commit/blob/tree URL and access date;
2. update the pin in the compatibility and hardware-baseline documents;
3. re-run the license/transitive-closure review;
4. record new artifact checksums and ABI evidence; and
5. re-run the isolated read-only smoke test before considering the change compatible.

Do not edit an old row to point at a new revision; the old source record is part of the evidence history.
