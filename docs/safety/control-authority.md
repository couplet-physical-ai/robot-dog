# Control authority and boundaries

**Status:** project command-ownership rule
**Reviewed:** 2026-08-21

## Invariant

There is **one active control authority across the whole system**: app, handheld remote(s), SDK processes, and ROS nodes. The authority is exclusive. The valid states are:

- **Unowned:** no command source may actuate; telemetry may be read.
- **Owned:** exactly one named source has a current lease and may issue the approved command class.
- **Held/stopped:** commands are inhibited pending an explicit human re-arm or handoff.

A process being connected, a remote being powered on, or a topic being visible does not grant ownership.

## Bring-up and ownership

Before a command-capable session:

1. Name the target and the intended owner in the private test record.
2. Inventory the app, every remote, SDK process, and ROS node that can send commands. Disable or close all unintended sources.
3. Confirm the isolated link and target identity. The first connection remains read-only.
4. Acquire an explicit, expiring lease. Show the owner and lease state to the operator.
5. Reject commands from every non-owner. Do not silently queue them for later execution.

A handoff is deliberate: the current owner stops and releases; the system enters **Held/stopped**; the new owner is identified and explicitly accepted; only then may the new lease be acquired. There is no automatic handoff after disconnect, timeout, process restart, or remote reconnect.

## Fail-closed behavior

On any of the following, revoke or hold authority, suppress new commands, and require human review:

- telemetry loss, stale or contradictory state, or target identity uncertainty;
- command loss, RPC failure, acknowledgement timeout, or transport disconnect;
- two sources requesting ownership or a source whose lease is stale;
- an app, remote, SDK, or ROS node appearing unexpectedly; or
- a fault, unexpected motion, or disagreement about the safe state.

A software `StopMove`, a command timeout, or an RPC timeout is not an emergency stop. It is only a software result to be logged and reviewed. The verified physical safe-state action remains required.

## Boundaries

- Telemetry readers have no control authority.
- High-level service ownership must be explicit. Low-level access is prohibited unless a separate review approves a restrained experiment **after releasing the high-level service**.
- No automatic recovery, roll-over, stand-up, damping, or special motion may run after a fault or lost authority.
- Never use a second app, remote, SDK, or ROS node to “rescue” a first source. Stop, hold, isolate, and obtain the approved physical response.
- The physical controller revision and emergency action must be checked on the delivered unit. The current manual describes **hold L2 + click B** for damping, which can make the robot collapse; it is not an assumed emergency stop.

## Acceptance checks

Before enabling any command path, the operator and observer must be able to answer **yes**:

- [ ] Exactly one source is named as owner; all other command sources are disabled or rejected.
- [ ] Ownership expires on the approved timeout and does not transfer automatically.
- [ ] A conflict produces hold/rejection, not last-writer-wins behavior.
- [ ] Telemetry loss, command loss, and acknowledgement timeout suppress new commands.
- [ ] Stop has precedence over queued or retrying commands.
- [ ] The delivered controller revision and physical emergency action are verified against the delivered manual.
- [ ] The operator knows that software stop/timeout is not an emergency stop.
- [ ] The run has physical commissioning approval; no casual motion is inferred from these checks.

## Sources

Official sources, accessed **2026-08-21**:

- [Unitree Go2 User Manual](https://marketing.unitree.com/article/en/Go2/User_Manual.html)
- [Unitree Document Center](https://support.unitree.com/main/en)

These sources document vendor controls and controller behavior. Exclusivity, lease, fail-closed, and approval rules above are **project requirements**. Inspect the delivered manual and controller before relying on any physical action.
