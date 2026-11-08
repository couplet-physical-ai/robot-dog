# First connection checklist

**Purpose:** establish a target-specific, read-only baseline
**Reviewed:** 2026-08-21

> **First connection is read-only.** No motion, setpoint, configuration, service release, actuator, low-level, or “test stop” command is allowed during this checklist.

## Before power or network

- [ ] A named operator and observer have approval to inspect the delivered unit.
- [ ] The exact SKU/configuration, firmware, controller revision, battery, charger, and supplied manuals are recorded in the approved private inventory. Do not copy identifiers into this repository.
- [ ] The unit, legs, joints, covers, connectors, battery, charger, and accessories are physically inspected. Stop for damage, heat, swelling, water, exposed conductors, looseness, or unexplained modification.
- [ ] The workspace is flat, dry, clear, and observable from the operator's line of sight. Keep at least the official manual's **2 m** from hazards/obstacles; increase it whenever the operator's risk assessment requires more.
- [ ] People, animals, traffic, edges, stairs, water, and unreviewed hazards are excluded.
- [ ] The delivered manual is read for this exact unit. Verify the physical controller revision and the documented emergency action with the operator. The current manual describes **hold L2 + click B** for damping; it can make the robot collapse, so do not treat it as an emergency stop or invoke it without target-specific approval.
- [ ] The physical safe-state/stop response is identified and independently available. Software `StopMove` and RPC timeout are not substitutes.
- [ ] The battery is not being charged. If charging is needed, use [battery and charging](battery-charging.md), not this checklist.
- [ ] The robot/host path is an isolated, approved link with no corporate bridge, default route, or Internet exposure.
- [ ] The app, handheld remotes, SDK processes, and ROS nodes that could command are disabled or placed in read-only mode. No active control authority exists.

## Read-only bring-up

1. Power the unit only after the physical gate passes; do not enable a motion service.
2. Connect only to the named target through the approved interface. Never discover and select the first robot found.
3. Read identity, firmware/controller versions, power/battery state, health, available services, and telemetry freshness. Record sanitized evidence privately.
4. Confirm that no command, configuration write, service release, retrying motion, automatic recovery, or special motion occurred.
5. Disconnect cleanly and leave the robot in the approved safe state.

## Stop and hold conditions

Stop the checklist and obtain review if any item is unknown or if telemetry is stale, a command path is unexpectedly available, another authority appears, the target identity is uncertain, the physical stop cannot be verified, the unit behaves unexpectedly, or the manual conflicts with this document. Do not resolve uncertainty by sending a command.

## Exit record

The private record must state: target reference, date/time, operator and observer, exact manual/controller revisions, physical inspection result, workspace/clearance result, isolated-link result, read-only observations, unexpected sources, final safe state, and approver. Keep serials, MACs, IPs, credentials, and raw logs out of this repository.

## Sources

Official sources, accessed **2026-08-21**:

- [Unitree Go2 User Manual](https://marketing.unitree.com/article/en/Go2/User_Manual.html)
- [Unitree Document Center](https://support.unitree.com/main/en)
- [Unitree Go2 product page](https://www.unitree.com/go2/)

Use the manual delivered with the unit when it differs from a mutable web page. The read-only gate, clearance increase, authority isolation, and approval requirements are **project controls**.
