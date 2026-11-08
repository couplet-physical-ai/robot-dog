# Go2 EDU hardware intake

**Status:** required before unit-specific development
**Baseline date:** 2026-08-21
**Record:** copy [unit-manifest.template.yaml](unit-manifest.template.yaml) to the approved private inventory; do not put real identifiers or secrets in this repository

Intake turns a configurable product family into a bounded, testable unit record. Do not fill gaps with a Go2 EDU marketing page, another team's robot, an SDK example, or a remembered port layout.

## Recording rules

- Use **Observed** for a fact captured from this physical unit or its exact artifact.
- Use **Reported** for a fact supplied by a vendor, purchaser, or operator that has not yet been checked.
- Use **Inferred** for a conclusion. An inference is never a substitute for a physical check.
- Use **Unknown** or `null` when evidence is missing.
- Keep the real serial number, MAC address, IP address, Wi-Fi details, tokens, passwords, keys, and private photo/log paths in the approved private inventory only. The committed template must remain non-identifying.
- Record the operator, date/time with timezone, tool/version, and evidence reference for every software observation.
- If inspection requires opening a cover, applying power, moving an actuator, or changing network configuration, stop and obtain the responsible operator's approval first.

## 1. Intake identity and chain of custody

- [ ] Assign a project asset/unit identifier that is not the serial number.
- [ ] Record manufacturer, family label (`Go2 EDU`), exact SKU/configuration if printed, purchaser/source, delivery date, and current custodian.
- [ ] Photograph the exterior, labels, accessories, charger, and shipping damage according to the site's approved handling policy. Store photos outside this repository and reference them by private evidence ID.
- [ ] Record the vendor-reported serial and firmware as **Reported** first; verify against the physical label and controlled readout before marking **Observed**.
- [ ] Record whether the unit is new, returned, loaned, modified, or previously enrolled in another system.
- [ ] Quarantine unknown or previously connected units until their network state and credentials are cleared by the responsible operator.

## 2. Safety and physical inspection (power off first)

- [ ] Confirm a clear test area, a safe lifting/handling plan, and an operator who is authorized to approve power and motion.
- [ ] Inspect chassis, covers, fasteners, legs, joints, actuators, cabling, connectors, antennas, battery enclosure, and charger for damage, looseness, corrosion, exposed conductors, or heat evidence.
- [ ] Check that protective covers and mechanical stops are present **where the unit is designed to have them**. Do not assume that a Go2 unit has a particular emergency-stop control; record whether one is actually present and where it is.
- [ ] Inspect battery and charger labels. Do not charge a damaged, swollen, wet, hot, or unidentified battery.
- [ ] Record optional accessories separately from the robot: controller, charger, camera/depth module, LiDAR, payload, network adapter, mounting hardware, and cables. A box or invoice is not proof that an option is installed.
- [ ] Record visible labels without copying a real serial/MAC into a committed document.
- [ ] Mark the unit **hold** for any unresolved safety defect, missing charger/battery information, water ingress, damaged connector, or unexplained modification.

## 3. Hardware and interface inventory

For each item, record `present`, `absent`, or `unknown`, how it was verified, and the evidence ID:

- [ ] compute module/board and any visible model marking;
- [ ] CPU architecture and accelerator, if exposed by an authorized readout — do not infer Orin;
- [ ] RAM size and storage type/capacity/free space — do not infer from a nominal product tier;
- [ ] cameras, depth module, LiDAR, IMU, GNSS, microphones, and other sensors — record model and mounting location if known;
- [ ] charging/power interfaces and adapter ratings;
- [ ] Ethernet, USB, serial, CAN, expansion, accessory, wireless, and debug interfaces — record only connectors actually present and usable;
- [ ] LEDs, buttons, controller links, and any emergency/physical stop controls that are actually present; and
- [ ] firmware/bootloader revision and any vendor configuration or option code.

A port is not considered available merely because an online drawing, SDK header, or another unit shows it. The manifest must identify the observed connector, its electrical/transport role if known, and the test that established it.

## 4. Controlled power-on and software observation

Perform this section only after the physical safety gate passes and an operator approves power:

- [ ] Power on without enabling motion or issuing a control command.
- [ ] Observe boot indicators, fault indicators, thermal behavior, and battery/charger behavior. Record exact observations and timestamps.
- [ ] If an authorized diagnostic path exists, capture OS release, kernel, architecture, RAM, storage, firmware, and installed runtime versions. Record the access method and authorization; do not record credentials.
- [ ] Check whether a shell exists, but do not guess credentials, bypass access controls, or enable a shell that the vendor/site has not authorized. `shell: unknown` is a valid result.
- [ ] Record which SDK/ROS 2 components are present locally and which will run only on the engineering host. A pinned repository is not proof that a unit contains that package.
- [ ] Store raw command output and photos in the approved private evidence store; commit only sanitized references and hashes if the project requires them.

## 5. Network and DDS intake

Network setup is a security boundary, not a convenience step:

- [ ] Use a dedicated point-to-point NIC or a dedicated VLAN/switch segment for robot/host traffic.
- [ ] Confirm the DDS NIC is not bridged to a corporate LAN, Wi-Fi uplink, VPN, hotspot, or Internet-facing interface.
- [ ] Confirm there is no default gateway or Internet route on the DDS path. Record the result, not private address values, in the committed documentation.
- [ ] Record the real interface name, MAC, address, VLAN/switch port, DDS domain, and expected peer in the private manifest only.
- [ ] Confirm host firewall/routing rules allow only the intended peer traffic required by the tested configuration. Do not invent a port allowlist from an example; derive it from the exact configuration and test.
- [ ] Treat the Python prebuilt Cyclone package as providing no DDS Security. Do not represent network reachability as authentication or encryption.
- [ ] With the link isolated, perform a read-only discovery/telemetry smoke test. Do not send motion, setpoint, actuator, or configuration commands during intake.

The detailed mandatory controls are in [security.md](../security.md).

## 6. Compatibility smoke test

Record evidence for the exact host/unit pair:

- [ ] host OS, kernel, architecture, Python, compiler/runtime, and ROS 2 distribution;
- [ ] `unitree_sdk2` pin `9754cd153af3da471b0fe5f3aa535e426fb11db3`;
- [ ] `unitree_sdk2_python` pin `65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5`;
- [ ] `unitree_ros2` pin `668d1ec5a05d1c38d3306bdca7d59f2ba3581a88`;
- [ ] CycloneDDS `0.10.2`, commit `9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd`;
- [ ] architecture/ABI evidence for every native library or wheel used;
- [ ] discovery, message/schema, and read-only telemetry results; and
- [ ] any deviation, patch, local build, or vendor-provided binary, with checksum and license evidence.

The upstream ROS 2 documentation lists Ubuntu 20.04/Foxy and Ubuntu 22.04/Humble as tested combinations and recommends Humble. Treat this as upstream evidence, not as an automatic acceptance decision. [R7]

## 7. Acceptance and disposition

Set one disposition in the private manifest:

- **Accepted for read-only development** — physical, network, evidence, and compatibility gates pass; no control path is enabled.
- **Accepted for controlled motion testing** — read-only evidence passes and a separate operator-approved motion procedure exists.
- **Hold** — any safety, identity, network-isolation, licensing, or evidence gate is unresolved.
- **Rejected/return** — unsafe, unidentifiable, materially modified without approval, or incompatible with the intended test.

A successful import or discovery test is not enough to accept a unit. Re-test after any firmware, sensor, network, SDK, ROS 2, CycloneDDS, or host-image change.

## References

- [technical-baseline.md](technical-baseline.md)
- [unit-manifest.template.yaml](unit-manifest.template.yaml)
- [../compatibility.md](../compatibility.md)
- [../security.md](../security.md)
- [../references.md](../references.md)
