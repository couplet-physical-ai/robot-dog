# Full-control commissioning checklist

**Purpose:** gate staged use of the complete Unitree Go2 EDU programming
surface. This checklist covers high-level sport actions, service and
motion-mode management, peripherals, and the expert low-level motor path.

> **Capability is not permission.** `robot-dog` supports full Go2 programming,
> but its offline/read-only profile is the default bring-up and CI mode. A
> full-control API being documented, installed, or implemented does not permit
> physical execution. Physical execution remains gated by this checklist and
> written commissioning approval for the named target.

> **Do not turn this page into a run command.** API names are included to make
> the approved surface auditable. Do not paste an upstream example into a live
> session without adapting it to the target-specific approval, authority,
> bounds, and stop plan.

## Source and scope

The API inventory was checked against the official Unitree Python SDK2 source
at pinned revision
`65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5`:

- [`SportClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/sport/sport_client.py)
  provides high-level postures, `Move`, gaits, stopping, and special actions.
- [`RobotStateClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/robot_state/robot_state_client.py)
  provides `ServiceList`, `ServiceSwitch`, and `SetReportFreq`.
- [`MotionSwitcherClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/comm/motion_switcher/motion_switcher_client.py)
  provides `CheckMode`, `SelectMode`, and `ReleaseMode`.
- [`VideoClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/video/video_client.py),
  [`VuiClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/vui/vui_client.py),
  `ChannelPublisher`, and `ChannelSubscriber` provide the
  source-backed peripheral paths.
- The [low-level source example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/test/lowlevel/lowlevel_control.py)
  uses `LowCmd_`, `LowState_`, `rt/lowcmd`, `rt/lowstate`, motor fields, and
  `CRC` for the expert motor path.

The exact unit, firmware, sensors, controller, and service availability remain
conditional until checked during intake. API presence is not hardware
validation.

## Approval record

The approver must complete a private commissioning record before any
write-capable client is enabled. Keep serial numbers, MAC addresses, IP
addresses, credentials, raw logs, and identifying telemetry out of this
repository.

- [ ] Exact target reference and Go2 SKU/configuration are named.
- [ ] Delivered firmware, controller revision, and applicable Unitree manual
      revision are recorded in the private record.
- [ ] The permitted capability class is named: service/mode, peripheral,
      ordinary high-level sport, special motion, or low level.
- [ ] The exact API methods/actions permitted for this run are listed. “Full
      access” is not a sufficient per-run action list.
- [ ] A qualified operator, an observer, an approver, and an owner of the
      active command authority are named.
- [ ] The operator has explicitly acknowledged the target, method set,
      workspace, restraint decision, battery state, independent physical stop,
      abort criteria, and final safe state. A vendor `input("Press Enter")`
      prompt is not this acknowledgement.
- [ ] The authority lease/ownership state is visible and expiring. No app,
      handheld remote, SDK process, or ROS node can silently take ownership.
- [ ] A written record identifies what evidence is expected and where the
      sanitized private evidence will be retained.

If any item is unknown, stop and hold. Do not resolve an approval gap with a
read, write, mode switch, or test motion.

## Host, Linux, and DDS gate

The full-control profile requires an explicit Linux/DDS setup. The default
offline profile must remain usable without these dependencies.

- [ ] The engineering host is supported Linux with Python `>=3.8`.
- [ ] The source and package inputs resolve to
      `unitree_sdk2_python@65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5`,
      `cyclonedds==0.10.2`, and the pinned dependencies in
      root-level `requirements-unitree.txt` profile.
- [ ] The vendor environment is isolated from the default offline/CI
      environment. Importing the core or running a fake test does not load the
      SDK or initialize DDS.
- [ ] The target is connected through a wired, point-to-point or approved
      isolated VLAN path. The DDS interface has no corporate bridge, VPN,
      hotspot, default route, or Internet exposure.
- [ ] The actual Linux network interface and target address were verified for
      this unit. No address from a different model, example, or unit was
      copied into the run.
- [ ] DDS domain `0` is selected for physical traffic and the process will
      conceptually initialize the pinned `ChannelFactoryInitialize(0,
      validated_interface)` exactly once before constructing clients or
      channels.
- [ ] The host firewall, expected-peer check, interface binding, and DDS
      configuration were reviewed. The Python prebuilt CycloneDDS baseline is
      not treated as authenticated or encrypted; isolation is containment, not
      DDS Security.
- [ ] If ROS 2 is part of the profile, `rmw_cyclonedds_cpp`, the pinned Unitree
      ROS 2 workspace, and the explicit physical/simulation domain separation
      are recorded. Physical uses domain `0`; simulation uses domain `1`.

A package import, build, or DDS configuration check is optional-profile
evidence only. None is Go2 hardware validation.

## Non-negotiable safety controls

- [ ] The unit is treated as civilian equipment, not a safety-rated controller
      or certified emergency-stop system.
- [ ] The operator remains in line of sight on flat, dry, clear ground. The
      official manual's 2 m obstacle guidance is a floor; the risk assessment
      may require more. People, animals, traffic, stairs, edges, water, and
      unreviewed hazards are excluded.
- [ ] The delivered physical safe-state action is verified against the actual
      controller/manual revision and is independently available. Software
      `StopMove`, an RPC timeout, process termination, or network loss is not a
      physical emergency stop.
- [ ] Exactly one command authority exists across app, remotes, SDK processes,
      and ROS nodes. A conflict produces rejection or held/stopped state, not
      last-writer-wins behavior.
- [ ] Telemetry, command acknowledgements, target identity, mode, and authority
      are fresh enough for the approved action. Stale, contradictory, missing,
      or uncertain state suppresses new writes.
- [ ] One command/action is outstanding at a time unless the approved profile
      explicitly documents a bounded stream and its watchdog. No unbounded
      retries, queued-command replay, or automatic handoff is allowed.
- [ ] A deadman/lease expiry, transport loss, fault, or acknowledgement timeout
      enters the reviewed held/stopped behavior and requires human review.
- [ ] The battery and charger state are approved for the run; charging is not
      occurring during command-capable work.

See [safety policy](safety-policy.md), [control authority](control-authority.md),
[controlled test plan](controlled-test-plan.md), and [battery controls](battery-charging.md).

## Staged gate sequence

### Stage 0 — offline/source contract

**Purpose:** prove the integration shape without a robot.

- [ ] Map the exact upstream methods to repository-owned ports and normalized
      result/error types.
- [ ] Use fakes/replay to cover acknowledgement, bounds, lease expiry, stale
      input, service conflicts, mode handoff, peripheral loss, stop precedence,
      and low-level field validation.
- [ ] Verify that imports, `doctor`, `demo`, and default tests do not discover a
      robot, open a socket, initialize DDS, publish to ROS, or issue a command.
- [ ] Keep special-motion and low-level adapters out of the default profile.

**Pass evidence:** deterministic offline/source-contract evidence only. It is
not a target or hardware result.

### Stage 1 — read-only target baseline

**Purpose:** establish identity and freshness before any write.

- [ ] Run the separate [first connection checklist](first-connection-checklist.md).
- [ ] Construct only approved read paths such as `RobotStateClient.ServiceList`
      and target-specific state/peripheral subscribers.
- [ ] Verify API/version responses, service names/protection, available topics,
      sensor presence, and freshness. Do not infer health from an unverified
      status integer or from API availability.
- [ ] Confirm that no `ServiceSwitch`, `SelectMode`, `ReleaseMode`, sport,
      peripheral-write, or low-level command occurred.

**Pass evidence:** a sanitized private intake record with the final stationary
safe state. A successful read-only probe does not authorize a write.

### Stage 2 — service and motion-mode management

**Purpose:** establish explicit ownership before high-level control.

- [ ] With a new operator acknowledgement, check the current mode using
      `MotionSwitcherClient.CheckMode()`.
- [ ] Name the service and mode transition before using
      `RobotStateClient.ServiceSwitch(...)` or
      `MotionSwitcherClient.SelectMode(...)`.
- [ ] Keep the unit stationary unless the approval explicitly includes a
      posture transition. Record the result code and resulting mode/service
      state.
- [ ] For a low-level handoff, use the approved sequence to leave high-level
      ownership and verify the result before publishing raw commands. Do not
      release a service as an improvised recovery action.

**Pass evidence:** fake/replay contract evidence plus a target-specific,
operator-approved service/mode record. A mode change alone is not a motion
validation or a physical stop test.

### Stage 3 — ordinary high-level sport actions

**Purpose:** introduce bounded, non-special high-level control one action at a
time.

- [ ] The approved action list names the exact methods, such as
      `StandUp`, `StandDown`, `Sit`, `RiseSit`, `BalanceStand`, `Move`,
      `Euler`, `SpeedLevel`, and `StopMove`.
- [ ] Bounds, units, duration, command rate, authority lease, freshness
      requirements, and stop precedence are defined before the action.
- [ ] Start with fakes/replay, then use the smallest approved physical action
      under direct observation. Do not infer a broader gait or speed envelope
      from one result.
- [ ] Stop on any unexpected posture, drift, fault, stale state, authority
      conflict, missing acknowledgement, or deviation from the approved plan.

**Pass evidence:** per-action fake/replay results and, if performed, a
hardware-marked record for the named target and envelope. Never describe a
fake, simulation, SDK build, or documentation build as hardware validation.

### Stage 4 — peripheral programming

**Purpose:** add non-locomotion I/O without treating it as exempt from control.

- [ ] Approve each peripheral separately: `VideoClient.GetImageSample`,
      `LowState_`/remote subscriptions, UTLiDAR switch publication,
      `VuiClient` settings, or obstacle-avoidance service methods.
- [ ] Confirm that the physical sensor/accessory exists and that its data
      handling, privacy, retention, and failure behavior are approved.
- [ ] Treat any publisher or service write as a command. It needs the same
      single authority, acknowledgement, timeout, and abort controls.
- [ ] Do not enable obstacle avoidance or remote-command forwarding as a
      substitute for operator authority or a physical stop.

**Pass evidence:** source/fake contract first, then a narrowly scoped target
record if physical peripheral use is approved. Sensor presence and API
presence are not interchangeable.

### Stage 5 — special sport motions

**Purpose:** expose the complete high-level action surface while treating
hazardous actions as separate experiments.

The full-control profile does not remove or conceal upstream methods. It does
require a separate acknowledgement and plan for each of these examples:

- `Damp` and `RecoveryStand`;
- `HandStand`, `LeftFlip`, `BackFlip`, `FrontFlip`, `FrontJump`, and
  `FrontPounce`;
- `FreeBound`, `FreeJump`, `FreeAvoid`, `WalkUpright`, and `CrossStep`;
- `Dance1`, `Dance2`, `Pose`, `Scrape`, `Stretch`, and other actions with
  unexpected balance or posture effects; and
- `AutoRecoverySet`, which is not permitted as automatic recovery under the
  default project policy.

For every selected method:

- [ ] The start posture/mode, clear area, expected result, maximum duration,
      and operator-visible abort are written in advance.
- [ ] Clearance and restraint/tether requirements are reviewed for the action;
      do not treat the official 2 m guidance as a complete special-motion risk
      assessment.
- [ ] The action is issued once, observed directly, and not automatically
      retried or followed by an unapproved recovery action.
- [ ] The operator knows that `Damp` can cause collapse and that software
      `StopMove` is not an emergency stop.

**Pass evidence:** per-action approval and evidence, not a blanket “sport
client validated” label.

### Stage 6 — expert low-level motor path

**Purpose:** make the raw motor path available to an expert without weakening
high-level or physical safety controls.

- [ ] Separate low-level approval names the exact motor indices, fields,
      units, gains, torque/current limits, rates, duration, and intended
      behavior.
- [ ] `MotionSwitcherClient.ReleaseMode()` or the target-specific approved
      handoff has completed, and high-level service ownership is not competing
      with the low-level publisher.
- [ ] Mechanical restraint/tethering appropriate to the experiment is in
      place. The operator, observer, independent physical stop, clear area,
      power limits, and abort criteria are confirmed.
- [ ] The adapter validates `LowCmd_` fields and CRC, rejects invalid or stale
      feedback, bounds publication rate, and stops on lost authority or
      acknowledgement/transport uncertainty.
- [ ] The first run is a single bounded mechanism/parameter. No uncontrolled
      gait, torque sweep, long-running stream, or field deployment is allowed.
- [ ] Low-level code is an explicit profile and does not become a dependency
      of offline CI, the fake adapter, or the default application.

**Pass evidence:** a separately approved low-level report with command fields,
restraint, independent-stop result, observed behavior, rollback, unresolved
unknowns, and disposition. A successful SDK build or fake test does not
authorize a motor experiment.

## Abort and hold conditions

Abort immediately and enter the verified physical safe-state procedure for any
of the following:

- unexpected motion, collapse, heat, odor, smoke, noise, or mechanical damage;
- loss of line of sight, person/animal entry, insufficient clearance, or a
  changed workspace;
- target mismatch, unknown controller/manual revision, service/mode conflict,
  or a second command authority;
- stale or contradictory telemetry, lost DDS/transport, missing result,
  acknowledgement timeout, retry, or queued-command replay;
- deadman/lease expiry, process failure, unapproved peripheral behavior, or
  uncertainty about the safe state; or
- any deviation from the approved method, bounds, restraint, or duration.

Do not continue collecting data after an abort without re-approval. Never use a
second SDK process, remote, or special motion to “rescue” the first control
source.

## Exit record and disposition

The private evidence record must contain sanitized time, target reference,
operator/observer/approver, source and dependency revisions, host/interface/
DDS-domain result, approved action list, prechecks, authority transitions,
commands accepted or suppressed, result codes, faults/aborts, physical stop
result, and final safe state.

Disposition the stage as **pass**, **conditional/hold**, or **fail**. A pass is
limited to the named target, method, envelope, and conditions. It does not
promote a peripheral, special motion, low-level path, autonomy behavior, or
onboard deployment to general use.

## Related documents

- [Full-control integration and pinned API map](../integrations/full-control.md)
- [Safety policy](safety-policy.md)
- [Control authority](control-authority.md)
- [Controlled test plan](controlled-test-plan.md)
- [First connection checklist](first-connection-checklist.md)
- [Compatibility baseline](../compatibility.md)
- [Security baseline](../security.md)
- [Roadmap](../roadmap.md)
