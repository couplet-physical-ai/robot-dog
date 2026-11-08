# Controlled test plan

**Purpose:** gate target-specific commissioning and failure-behavior evidence
**Reviewed:** 2026-08-21

> **This is a commissioning gate, not a casual motion recipe.** No command-capable or motion test may start without written physical commissioning approval for the named delivered unit.

## Required approval and roles

Before the run, the approver must name the target, operator, observer, test owner, exact manual/controller revisions, permitted command class, workspace, battery state, independent physical stop, abort criteria, and evidence location. The operator remains in line of sight on flat, dry, clear ground. Keep at least the official manual's **2 m** from hazards/obstacles; the risk assessment may require more.

The delivered controller revision and physical emergency action must be verified before command-capable work. The current manual describes **hold L2 + click B** for damping, which can make the robot collapse. That action is not an assumed emergency stop and must not be casually tried.

## Entry gates

- [ ] [Safety policy](safety-policy.md), [control authority](control-authority.md), [first connection checklist](first-connection-checklist.md), and [battery controls](battery-charging.md) are accepted for this run.
- [ ] Physical inspection, exact target identity, firmware, controller revision, battery/charger match, and delivered manual review are complete in the private record.
- [ ] The area is flat, dry, clear, within line of sight, and has the required clearance. People and animals are excluded.
- [ ] One control authority is named across app, remotes, SDK, and ROS. All other command paths are disabled or rejected.
- [ ] The isolated network path and target binding are verified. No first-connection or discovery shortcut is used.
- [ ] Offline/fake tests cover the planned state transitions. Hardware-marked tests are explicitly selected and not part of the default suite.
- [ ] High-level service ownership and any low-level boundary are explicit. Low-level work is out of scope unless separately approved, restrained, and performed only after releasing the high-level service.

## Sequence

### 1. Read-only baseline

Run the first-connection checklist. Confirm identity, firmware, health, power, telemetry freshness, available services, and final stationary safe state. Do not issue motion, configuration, service-release, or stop commands in this phase.

### 2. Telemetry-loss test

Use fake/replay fault injection first. If physical commissioning requires a live-link observation, keep the unit stationary and use only the approved non-actuating setup. Remove or stale telemetry and verify that the application marks state unknown/stale, suppresses new commands, records the fault, and does not start automatic recovery or a special motion. Restore telemetry only after the operator approves.

**Pass:** no unsafe command is generated; recovery requires an explicit human decision.
**Fail:** any autonomous recovery, stale-data command, or unexplained state transition.

### 3. Command-loss and RPC-timeout test

Use fake/replay or an approved stationary hardware boundary to drop command acknowledgements, responses, or transport connectivity. Verify bounded timeout handling, no unbounded retries, no queued-command replay, and a held/stopped authority state. A timeout is not proof of physical stopping and is never an emergency stop.

**Pass:** the command path fails closed and the event is logged.
**Fail:** retries continue without authority, a command is replayed after recovery, or software timeout is represented as an emergency stop.

### 4. Authority-conflict test

Present competing ownership requests from two of app, remote, SDK, and ROS in fake/replay first. Verify that exactly one owner can hold a lease, the conflict is rejected or placed in held/stopped state, and no last-writer-wins or automatic handoff occurs. Repeat only within an approved stationary hardware boundary if needed.

**Pass:** one named owner or no owner; all conflict decisions are visible.
**Fail:** simultaneous command acceptance, silent takeover, or automatic handoff.

### 5. Stop-behavior review and test

First verify offline that Stop has precedence over queued/retrying commands and that authority loss inhibits new commands. Then review the delivered unit's physical safe-state procedure with the operator and observer. Any physical demonstration requires the separate commissioning approval, target-specific controller/manual match, clear area, independent stop readiness, one bounded action, and immediate abort criteria.

Do not substitute `StopMove`, RPC timeout, process termination, or network disconnection for a physical emergency stop. Do not invoke the manual's L2 + B damping action merely to prove an example; it can make the robot collapse. If the physical action cannot be verified safely, the run is blocked.

## Low-level boundary

No low-level motor/torque/control test belongs in this plan's normal path. A separately approved low-level experiment must use mechanical restraint appropriate to the risk, an independent physical stop, one parameter at a time, bounded duration/limits, an operator and observer, and the high-level service released before low-level ownership. No automatic recovery or special motion is permitted.

## Abort conditions

Abort and enter the approved physical safe-state procedure for unexpected motion, collapse, fault, heat/odor/smoke, loss of line of sight, person/animal entering the area, loss of authority, conflicting sources, stale/contradictory telemetry, command retry, target mismatch, stop-path uncertainty, or any deviation from the approved procedure. Do not continue to collect data after an abort without re-approval.

## Evidence and disposition

Record sanitized timestamps, target reference, operator/observer/approver, manual/controller revisions, prechecks, injected fault, expected result, observed result, commands suppressed/accepted, authority transitions, stop result, aborts, and final safe state. Keep serials, MACs, IPs, credentials, raw telemetry, captures, and unredacted logs in the approved private evidence store.

Disposition the run as **pass**, **conditional/hold**, or **fail**. A pass proves only the named behavior on the named target under the recorded conditions; it does not authorize broader motion, autonomy, low-level control, or production use.

## Sources

Official sources, accessed **2026-08-21**:

- [Unitree Go2 User Manual](https://marketing.unitree.com/article/en/Go2/User_Manual.html)
- [Unitree Document Center](https://support.unitree.com/main/en)
- [Unitree Go2 product page](https://www.unitree.com/go2/)

The 2 m guidance and vendor-documented controller behavior are **official** inputs. Line-of-sight operation, larger clearance when needed, fault scenarios, authority exclusivity, fail-closed behavior, and physical commissioning approval are **project requirements**.
