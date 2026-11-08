# Full-control integration

`robot-dog` supports full Unitree Go2 EDU programming through an explicit,
opt-in hardware profile. That scope includes high-level sport actions,
service and motion-mode management, Go2 peripherals, and an expert low-level
motor path. **Offline and read-only are the default bring-up and CI modes, not
the capability ceiling.**

This page describes the source-backed integration surface and its gates. It
does not claim that a particular Go2, firmware revision, host, network, sensor,
or onboard computer has been validated. The default package and its checked-in
probe remain intentionally non-actuating; that profile choice must not be read
as a claim that the robot-dog integration is read-only-only.

> **No casual execution.** The API shapes below are staged concepts and source
> references, not commands to run against a robot. Physical execution requires
> the [full-control checklist](../safety/full-control-checklist.md), a named
> operator and observer, and commissioning approval.

## Source baseline

The vendor surface documented here was inspected in the official
`unitree_sdk2_python` source at commit
`65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5`. The source links below are pinned
blob URLs; do not replace them with a branch or a floating release when
checking an API.

| Capability | Exact pinned API/source | What it provides |
| --- | --- | --- |
| DDS transport | [`ChannelFactoryInitialize`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/core/channel.py) | Creates the SDK channel factory; accepts a DDS domain and optional network interface. |
| High-level control | [`SportClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/sport/sport_client.py) and the [Go2 sport example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/example/go2/high_level/go2_sport_client.py) | Postures, velocity/heading commands, gait/action selection, stopping, and special motions. |
| Services | [`RobotStateClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/robot_state/robot_state_client.py) | `ServiceList`, `ServiceSwitch`, and `SetReportFreq`. |
| Motion mode | [`MotionSwitcherClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/comm/motion_switcher/motion_switcher_client.py) and the [mode-switch example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/example/motionSwitcher/motion_switcher_example.py) | `CheckMode`, `SelectMode`, and `ReleaseMode` for explicit mode ownership. |
| Video | [`VideoClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/video/video_client.py) and the [front-camera example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/example/go2/front_camera/capture_image.py) | `GetImageSample`, returning a result code and image bytes. |
| DDS peripherals | [`ChannelPublisher`/`ChannelSubscriber`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/core/channel.py) plus the [Go2 peripheral examples](https://github.com/unitreerobotics/unitree_sdk2_python/tree/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/example/go2) | Camera and low-state subscriptions, wireless-controller input, and peripheral publishers such as the UTLiDAR switch. |
| Expert low level | [`LowCmd_`/`LowState_` low-level example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/test/lowlevel/lowlevel_control.py) and the [Go2 low-level example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/example/go2/low_level/go2_stand_example.py) | Raw `rt/lowcmd` publication, `rt/lowstate` feedback, motor targets, gains, torque, and CRC handling. |

The Python package requires a supported Linux runtime and declares
`cyclonedds==0.10.2`, NumPy, and OpenCV dependencies. The repository pins
those inputs in the root-level `requirements-unitree.txt` profile.
The source pin is an integration input, not evidence that every API is
available on every Go2 firmware or hardware option.

## Capability map

### High-level sport actions

The pinned `SportClient` exposes the following Go2 actions. The names are
important: they are the upstream method names, not a promise that an action is
safe in every workspace.

- **Posture and stop:** `StandUp`, `StandDown`, `Sit`, `RiseSit`,
  `BalanceStand`, `RecoveryStand`, `Damp`, and `StopMove`.
- **Bounded command primitives:** `Move(vx, vy, vyaw)`, `Euler(roll, pitch,
  yaw)`, and `SpeedLevel(level)`.
- **Gaits and ordinary actions:** `StaticWalk`, `TrotRun`, `ClassicWalk`,
  `FreeWalk`, `WalkUpright`, `CrossStep`, `Stretch`, `Pose`, `Scrape`,
  `Hello`, `Heart`, `Dance1`, `Dance2`, and `Content`.
- **Special actions:** `HandStand`, `LeftFlip`, `BackFlip`, `FrontFlip`,
  `FrontJump`, `FrontPounce`, `FreeBound`, `FreeJump`, and `FreeAvoid`.
- **Mode/features:** `SwitchJoystick`, `SwitchAvoidMode`,
  `AutoRecoverySet(enabled)`, and `AutoRecoveryGet()`.

The API is available to an opt-in full-control adapter even when the
repository's default policy rejects writes. A full-control adapter must still
normalize units, enforce an application-owned authority lease, bound inputs,
make expiry and stop precedence explicit, and record the upstream result code.
`Move` is not a replacement for a deadman, and `StopMove` is not a physical
emergency stop.

### Services and motion modes

Service ownership and motion-mode ownership are separate decisions:

1. `RobotStateClient.ServiceList()` inventories service names, status values,
   and protection flags.
2. `RobotStateClient.ServiceSwitch(name, switch)` changes a service only after
   the operator has approved the exact service and transition.
3. `MotionSwitcherClient.CheckMode()` identifies the current mode.
4. `MotionSwitcherClient.SelectMode(nameOrAlias)` selects an explicitly
   approved mode such as the mode named by the target's integration plan.
5. `MotionSwitcherClient.ReleaseMode()` releases mode ownership before a
   separately approved low-level session or handoff.

A mode switch is not a harmless setup operation. It can change which controller
owns the robot. The application must enter a held/stopped state during a
handoff; it must not silently select a mode after a disconnect or retry a mode
change without a new acknowledgement.

### Peripherals and non-motion I/O

The pinned source also supports peripheral programming. Availability is
conditional on the exact unit and firmware; do not infer that a sensor or
accessory is installed merely because its API exists.

- `VideoClient.GetImageSample()` obtains a result code and encoded image bytes
  from the Go2 video service. Decode and retain images only under the project's
  data-handling rules.
- `ChannelSubscriber("rt/lowstate", LowState_)` can receive low-state data
  such as motor state, IMU state, and power fields in the upstream example.
  The wireless-controller example uses `rt/lf/lowstate` and parses
  `wireless_remote`; the topic must be confirmed for the target.
- The [UTLiDAR switch example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/example/go2/high_level/go2_utlidar_switch.py)
  publishes `String_` data on `rt/utlidar/switch` with `ON`/`OFF` values.
  This is a write-capable peripheral operation and needs the
  same authority and acknowledgement gate as motion.
- [`VuiClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/vui/vui_client.py)
  exposes `SetSwitch`/`GetSwitch`, `SetVolume`/`GetVolume`, and
  `SetBrightness`/`GetBrightness`.
- The Go2 [`ObstaclesAvoidClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/obstacles_avoid/obstacles_avoid_client.py)
  exposes `SwitchSet`/`SwitchGet`,
  `UseRemoteCommandFromApi`, and movement methods including `Move`,
  `MoveToAbsolutePosition`, and `MoveToIncrementPosition`. These are control
  APIs, not read-only sensor APIs.

The full-control profile therefore includes more than locomotion. It must
keep camera, low-state, remote, LiDAR, VUI, and obstacle-avoidance adapters
behind explicit capability declarations so a missing peripheral fails closed
rather than being guessed.

### Expert low-level motor path

The pinned SDK exposes a raw motor path in addition to the high-level sport
client. The upstream low-level examples use:

- `ChannelPublisher("rt/lowcmd", LowCmd_)` for command publication;
- `ChannelSubscriber("rt/lowstate", LowState_)` for feedback;
- `LowCmd_.motor_cmd[i]` fields including `mode`, `q`, `kp`, `dq`, `kd`, and
  `tau`;
- `CRC().Crc(low_cmd)` before publication; and
- a high-rate recurrent publisher in the example.

This is an **expert path**, not a missing feature to be filled by calling
`SportClient`. It can expose position, velocity, gain, and torque behavior
below the high-level service. The raw path is available in the full-control
integration surface but is never part of the default profile, default tests,
examples, or automatic recovery behavior.

Before a low-level owner is allowed to publish, the high-level service/mode
must be deliberately brought to the approved state and, where the experiment
requires it, released with `MotionSwitcherClient.ReleaseMode()`. The low-level
experiment then requires mechanical restraint or tethering appropriate to the
risk, bounded torque/current/position/velocity and duration, an independent
physical stop, an operator and observer, and a written abort and rollback
plan. Never use low-level control to bypass the authority stack or to discover
what an unverified robot will do.

## Linux and DDS setup

The full-control runtime is a Linux engineering-host profile. The offline
profile remains cross-platform and must not import or initialize the vendor
runtime. Prepare the hardware profile as follows, without putting target
identifiers or credentials in this repository:

1. **Stage immutable inputs.** Use Python `>=3.8`, the exact SDK commit above,
   `cyclonedds==0.10.2`, and the pinned dependency set. Build or install in an
   isolated environment outside the default offline environment. Keep source
   and build artifacts outside this checkout unless their licenses and scope
   have been reviewed.
2. **Use a dedicated link.** Use a wired Ethernet interface on a point-to-point
   link or approved isolated VLAN. There must be no corporate bridge, VPN,
   default route, hotspot, or Internet exposure on the DDS interface. Confirm
   the actual robot address and host interface from the target-specific intake;
   never copy an address from an unrelated example.
3. **Bind DDS explicitly.** The physical baseline uses DDS domain `0` and an
   explicitly named Linux interface. The first transport operation is
   conceptually `ChannelFactoryInitialize(0, validated_interface)`. The
   factory is process-global in the pinned source, so initialize it once,
   before constructing publishers, subscribers, or clients; restart the
   process to correct a wrong first selection.
4. **Keep security claims narrow.** The Python prebuilt CycloneDDS baseline
   does not provide an assumption of DDS Security. Treat the isolated segment
   as an exposed control network and rely on containment, expected-peer checks,
   host firewalling, and target identity verification. Isolation is not
   authentication or encryption; see [security](../security.md).
5. **Separate ROS 2 domains.** If ROS 2 is used, use the repository's explicit
   CycloneDDS profile and interface helper. Keep physical traffic on domain `0`
   and simulation on domain `1`; source the pinned Unitree ROS 2 workspace and
   use `rmw_cyclonedds_cpp`. ROS 2 remains an optional composition profile,
   not a dependency of the core.
6. **Perform the first connection read-only.** Verify identity, API versions,
   service list, available topics, and freshness before any service switch,
   publisher, mode change, or actuator path. Follow the [first connection
   checklist](../safety/first-connection-checklist.md).

The existing [Python SDK2 guide](python-sdk2.md),
[compatibility baseline](../compatibility.md), [security baseline](../security.md),
and [ROS 2 guide](ros2.md) contain the dependency and network boundaries. This
page adds the write-capable API surface; it does not relax those boundaries.

## Operator acknowledgement and authority

A write-capable session needs an explicit, recorded acknowledgement before an
API client is permitted to send a service, peripheral, sport, special-motion,
or low-level write. A vendor example's `input("Press Enter")` is not enough.
The acknowledgement must name:

- the exact target and the delivered manual/controller revision;
- the operator, observer, approver, and one active control authority;
- the approved API class and exact method/action set for this run;
- the Linux host, selected interface, DDS domain, and isolated-link result;
- workspace clearance, restraint/tether requirement, battery state, and the
  independently available physical safe-state action; and
- timeout, abort, rollback, and post-run safe-state criteria.

The application should represent this as an expiring lease or explicit
`operator_acknowledged` gate. On stale telemetry, conflicting authorities,
acknowledgement expiry, target mismatch, transport loss, unexpected motion, or
uncertain mode, suppress new writes and enter held/stopped state. Do not
transfer ownership automatically. A software timeout, RPC failure, process
exit, or `StopMove` call is not a certified emergency stop.

See [control authority](../safety/control-authority.md), [safety policy](../safety/safety-policy.md),
and the [full-control checklist](../safety/full-control-checklist.md).

## Staged implementation concepts

The implementation track and the physical commissioning track are separate.
The following sequence makes the full surface available without making the
default profile actuating:

1. **Source and fake contract:** map every upstream API above to repository
   ports and result types. Use fakes/replay to test acknowledgements, bounds,
   service ownership, mode handoff, stale input, stop precedence, peripheral
   failures, and low-level field validation. No SDK import or network access.
2. **Linux SDK profile:** import the pinned package and verify DDS/channel
   construction on the named Linux host with no target write. A package import
   or SDK build is optional-profile evidence, not Go2 hardware evidence.
3. **Read-only target baseline:** use `RobotStateClient` read paths and
   subscriptions to confirm the target, services, topics, and freshness. Do
   not switch services or modes during intake.
4. **High-level and service adapters:** add explicit clients for service/mode
   management and `SportClient`, with one-owner authority, bounded commands,
   result-code handling, and a write gate. Exercise fake/replay first, then
   only the approved stationary or bounded physical stage.
5. **Peripheral adapters:** add camera, low-state, remote, UTLiDAR, VUI, and
   obstacle-avoidance capabilities individually. A peripheral write is not
   exempt from acknowledgement just because it is not a leg command.
6. **Special motions:** keep all upstream methods available, but classify
   them as named hazardous actions. Each action gets its own explicit approval,
   environment, restraint/clearance, timeout, abort, and evidence record.
7. **Low-level adapter:** expose raw `LowCmd_`/`LowState_` only from a separate
   expert profile after the high-level ownership boundary and mechanical
   restraint review pass. Never make it a transitive dependency of the core.

A completed implementation stage means the adapter and its offline/source
contract are available. It does **not** mean the target was connected, a
command was sent, or hardware validation occurred.

## Hazardous actions are documented, not removed

The full-control surface intentionally does not hide hazardous vendor methods.
The following are especially unsuitable for casual bring-up: `Damp`,
`RecoveryStand`, `HandStand`, flips, jumps, pounces, `FreeBound`, `FreeJump`,
`FreeAvoid`, `WalkUpright`, `CrossStep`, dance/pose/scrape actions, and
`AutoRecoverySet`. The current project safety policy notes that damping can
make the robot collapse and that automatic recovery is prohibited by default.

For a special motion, the approved plan must additionally specify the exact
method, expected start posture and mode, clear area and hazard exclusion,
operator-visible stop/abort action, restraint or tether decision, one-action
execution, result/telemetry observation, and final safe state. Do not queue
special motions, retry them after an uncertain result, or use one special
motion as a recovery mechanism for another.

For low-level work, the plan must also specify motor indices, command fields,
units, gains/torque limits, publication rate, CRC handling, maximum duration,
mechanical restraint, power limits, independent stop, and rollback. A source
example demonstrates API mechanics only; it is not a safety envelope and does
not authorize a physical run.

## Evidence boundary

This page and the pinned-source inspection establish an API and integration
claim. They do not establish:

- compatibility with a particular Go2 SKU, firmware, controller, sensor, or
  accessory;
- a working Linux/DDS link to a target;
- safe behavior of a high-level or special action;
- correctness of a low-level motor experiment; or
- physical, hardware, commissioning, or production validation.

Record those facts in the approved private commissioning evidence, not in this
repository. The [roadmap](../roadmap.md) distinguishes implementation
availability from physical execution, and the [controlled test plan](../safety/controlled-test-plan.md)
remains the commissioning gate.

## Pinned source links

- [Pinned `unitree_sdk2_python` tree](https://github.com/unitreerobotics/unitree_sdk2_python/tree/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5)
- [`SportClient` source](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/sport/sport_client.py)
- [`RobotStateClient` source](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/robot_state/robot_state_client.py)
- [`MotionSwitcherClient` source](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/comm/motion_switcher/motion_switcher_client.py)
- [`VideoClient` source](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/video/video_client.py)
- [`VuiClient` source](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/vui/vui_client.py)
- [`ObstaclesAvoidClient` source](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/obstacles_avoid/obstacles_avoid_client.py)
- [UTLiDAR switch example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/example/go2/high_level/go2_utlidar_switch.py)
- [Wireless-controller example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/example/wireless_controller/wireless_controller.py)
- [`LowCmd_`/`LowState_` source example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/test/lowlevel/lowlevel_control.py)
- [Pinned Go2 high-level source example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/example/go2/high_level/go2_sport_client.py)
- [Pinned Go2 low-level source example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/example/go2/low_level/go2_stand_example.py)
