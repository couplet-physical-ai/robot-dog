# Safety policy

**Status:** project control for the Unitree Go2 EDU/configurable SKU
**Reviewed:** 2026-08-21

> **Stop and hold:** If the unit, controller revision, emergency action, battery, workspace, authority owner, or stop path is unknown, do not connect or command it. Move the work to review.

## Non-negotiable rules

1. **Treat the Go2 as civilian equipment, not safety-rated equipment.** It is not a certified safety controller, protective device, or emergency-stop system. Software, SDK, ROS, the app, and the remote cannot replace a qualified operator and an independently verified physical safe-state action.
2. **Operate only under direct observation.** The operator stays in line of sight on flat, dry, clear ground. The official manual advises at least **2 m** from obstacles or hazards; the operator may require more for the unit, test, payload, or workspace. No people, animals, traffic, stairs, edges, water, or unreviewed hazards enter the area.
3. **Keep one active control authority.** The app, handheld remote(s), SDK processes, and ROS nodes are one combined command surface: exactly one may own control, or none. Conflicts, stale ownership, or an uncertain owner fail closed. See [control authority](control-authority.md).
4. **Make the first connection read-only.** The first connection may inspect identity, firmware, health, and telemetry only. Do not issue motion, setpoint, configuration, service-release, or low-level commands during intake. See [first connection checklist](first-connection-checklist.md).
5. **Do not call software StopMove or an RPC timeout an emergency stop.** They are software behaviors and can fail, be delayed, or be unavailable. Verify the delivered unit's exact physical controller revision, its manual, and its emergency action before any command-capable work. The current manual describes holding **L2 + clicking B** for damping; this can make the robot collapse. Do not assume that action is an emergency stop or use it without target-specific verification and approval.
6. **Prohibit low-level control by default.** Low-level motor/torque/control access is allowed only under separate written approval, with the high-level service released, mechanical restraint appropriate to the experiment, an independent physical stop, and a named operator and observer. It is never an escape hatch from the authority stack.
7. **Do not add automatic recovery or special motions.** On lost telemetry, lost commands, timeout, fault, authority conflict, or uncertain state, suppress new commands and require human review. Do not add roll-over, stand-up, recovery gait, damping, or other special motion as an automatic response.
8. **Use only the official battery and charger.** Charge only an identified, undamaged battery with its matching official charger. For attended charging, remove the battery from the robot, switch it off, and place it on a nonflammable surface. Do not charge immediately after use; follow the delivered manual's cooling and charging instructions. See [battery and charging](battery-charging.md).

## Vendor facts versus project controls

| Label | Rule | Meaning |
| --- | --- | --- |
| **Official** | Unitree describes Go2 as a civilian robot and publishes the Go2 manual and product information. | Vendor material is not a safety rating. |
| **Official** | The Go2 manual gives the 2 m obstacle guidance and documents controller actions, including the current L2 + B damping description. | Confirm the revision that shipped with the delivered unit; web material can change. |
| **project requirement** | Line of sight, flat/dry/clear ground, one authority, read-only first connection, no automatic recovery, and explicit approval gates. | Conservative project controls; not vendor guarantees. |
| **project requirement** | More than 2 m may be required, based on risk assessment. | The 2 m vendor guidance is a floor, not a project promise of adequacy. |
| **project requirement** | Physical commissioning approval is required before command-capable or motion work. | Offline tests, simulations, imports, and documentation builds do not authorize hardware operation. |

## Approval gate

A physical task may proceed only when the named target, exact manual/controller revision, workspace, operator, observer, authority owner, battery state, network boundary, independent physical stop, abort criteria, and evidence plan are recorded in the approved private record. Do not put serial numbers, MAC addresses, IP addresses, credentials, or raw robot logs in this repository.

## Sources

Official sources, accessed **2026-08-21**:

- [Unitree Go2 User Manual](https://marketing.unitree.com/article/en/Go2/User_Manual.html)
- [Unitree Go2 product page](https://www.unitree.com/go2/)
- [Unitree Document Center](https://support.unitree.com/main/en)

The delivered unit's printed/current manual and controller are authoritative for target-specific details. If they differ from these links, stop and reconcile the difference before operating.
