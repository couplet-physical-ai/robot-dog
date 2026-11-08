# Staged learning roadmap

This roadmap moves from understanding and simulation toward tightly supervised physical behavior. Each milestone is a gate, not a promise to suppress the next capability. **Full-control implementation availability and physical commissioning are separate axes:** the opt-in integration may expose the complete Go2 programming surface, while the default profile remains offline/read-only and every physical write remains gated. A later milestone cannot weaken an earlier safety boundary.

The repository supports full Unitree Go2 EDU programming through a source-pinned, explicit profile: high-level sport actions, service and motion-mode management, peripherals, and an expert low-level motor path. Read [full-control integration](integrations/full-control.md) for the API map and [the full-control checklist](safety/full-control-checklist.md) for execution gates. “Available” below means the implementation, adapter contract, and offline/source evidence exist; it never means a robot was connected or hardware was validated.

Every milestone has four parts:

- **Prerequisites:** evidence that must exist before starting;
- **Safe scope:** the behavior that is allowed in the milestone;
- **Exit evidence:** artifacts or test results required to call it complete;
- **Non-goals:** behavior explicitly out of scope, even if it appears technically easy.

The architecture and test contract are defined in [architecture.md](architecture.md) and [testing.md](testing.md).

## GO2-FC — Full-control implementation availability (opt-in)

This capability milestone runs alongside the staged bring-up milestones below. It replaces a documentation-only interpretation of the roadmap with an explicit implementation target: the repository may provide the complete programming surface without making that surface part of the default profile or authorizing physical execution.

### Prerequisites

- The official `unitree_sdk2_python` source is pinned to
  `65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5` and its exact API files have been
  inspected.
- The typed core, port boundaries, fake/replay seams, and authority/error
  vocabulary are defined. See [architecture](architecture.md) and
  [testing](testing.md).
- The Linux/DDS compatibility and isolation requirements are documented. No
  hardware identifier or credential is needed for implementation work.

### Safe scope

- Make an explicit hardware profile capable of adapting `SportClient`,
  `RobotStateClient`, `MotionSwitcherClient`, the Go2 peripheral clients and
  channels, and the `LowCmd_`/`LowState_` expert motor path.
- Keep service/mode writes, sport actions, peripheral publishers, special
  motions, and low-level publication behind typed bounds, one-owner authority,
  acknowledgement, expiry, result handling, and fail-closed behavior.
- Implement and test the full surface with fakes, replay, source inspection,
  and optional Linux package/build checks. The default offline/CI profile must
  not import the SDK, initialize DDS, discover a target, or send a command.
- Keep hazardous special motions and low-level control documented and reachable
  in the opt-in profile. Safety gates constrain execution; they do not remove
  vendor capability from the integration.

### Exit evidence

- A source-pinned API map covers high-level sport, service/mode, peripheral,
  transport, and low-level paths.
- Offline contract evidence covers acknowledgements, authority conflicts,
  stale/unknown input, bounds, stop precedence, peripheral failure, mode
  handoff, low-level field/CRC validation, and profile selection.
- The optional Linux/DDS profile is explicit about Python, CycloneDDS, NIC,
  domain, and isolation requirements, with no claim of target compatibility.
- Documentation distinguishes implementation availability, optional-profile
  evidence, and hardware-marked commissioning evidence.

### Non-goals

- No physical command, special motion, motor publication, or hardware
  validation is implied by this milestone.
- No default dependency on Unitree SDK, ROS 2, DDS, a network, or a robot.
- No bypass of [control authority](safety/control-authority.md), the physical
  stop, the [safety policy](safety/safety-policy.md), or the
  [commissioning checklist](safety/full-control-checklist.md).

## GO2-00 — Inventory and simulation

### Prerequisites

- A clean local checkout and an agreed offline build/test profile.
- Vendor and project documentation collected as references, without requiring a live robot.
- A list of expected Go2 capabilities, interfaces, units, statuses, sensors, actuator commands, and unknowns.
- A decision about which dependencies are optional: Unitree SDK, ROS2, and any MuJoCo installation/model.

### Safe scope

- Inventory the complete robot-facing surface and classify each item as
  read-only, supervised actuation, hazardous special motion, expert low level,
  or out of scope. Do not classify a capability as out of scope merely because
  the default profile is read-only.
- Define repository-owned typed values and port contracts before binding them to vendor or middleware types.
- Build deterministic fakes, scripted scenarios, and replay fixtures.
- Optionally exercise official MuJoCo Python bindings or native C/C++ API if a compatible model is locally available, clearly labeling what the model represents.
- Keep the default path entirely local and non-actuating.

### Exit evidence

- A reviewed capability/unknowns inventory with units, freshness, authority, and failure semantics.
- A dependency/profile matrix showing that the offline profile has no hardware, network, Unitree SDK, or ROS2 requirement.
- A fake/replay scenario that boots, reports state, injects stale/faulted inputs, and records decisions deterministically.
- If MuJoCo is used, a reproducible local experiment and an explicit model-fidelity statement.

### Non-goals

- No connection to or discovery of a physical robot.
- No network probing, SDK command, ROS deployment, or physical movement.
- No claim that MuJoCo is a complete high-level Go2 simulation, or that an available model proves locomotion or firmware behavior.
- No autonomous policy, perception stack, or low-level actuator experiment.

## GO2-01 — Hello-state

### Prerequisites

- GO2-00 exit evidence is complete.
- Typed state/health observations and a deterministic clock exist.
- The fake or replay adapter implements the read-only state port.

### Safe scope

- Read one normalized state snapshot from the fake/replay profile.
- Display or log status, timestamps, health, and clearly named units.
- Demonstrate unknown, unavailable, and stale states without guessing a valid robot state.

### Exit evidence

- A deterministic hello-state scenario with a fixed fixture and expected output.
- Unit/contract tests for healthy, stale, unavailable, and unknown observations.
- A check showing the default path creates no SDK session, socket, device handle, or ROS executor.

### Non-goals

- No actuation, command submission, hardware access, or network access.
- No inferred locomotion state beyond what the normalized observation contract actually provides.
- No dashboard, cloud telemetry, or autonomous reaction.

## GO2-02 — Logging and health

### Prerequisites

- GO2-01 read-only state path and test evidence.
- Structured local event logging and health/result types.
- A deterministic way to inject disconnects, stale values, malformed values, and adapter errors.

### Safe scope

- Record normalized observations, health transitions, policy decisions, errors, and correlation/timestamps locally.
- Define health for process, connection, sensor, and command paths without granting motion authority.
- Make stale, missing, and faulted inputs visible and fail closed.

### Exit evidence

- Replay/fake scenarios proving logging for healthy state, stale state, disconnect, malformed input, and rejected operation.
- Tests showing health failure suppresses downstream action and reports the reason.
- A local log format that is inspectable offline and does not require credentials or a service.

### Non-goals

- No physical commands or automatic recovery that could affect a robot.
- No cloud monitoring, remote control, alert routing, or fleet management.
- No claim that a health signal proves mechanical, firmware, or network safety.

## GO2-03 — Stationary camera/LiDAR

### Prerequisites

- GO2-02 logging/health evidence.
- Typed camera and LiDAR ports with timestamp, frame/source, validity, and health semantics.
- Fake/replay sensor fixtures and a defined stationary test setup if hardware is later used.

### Safe scope

- Acquire and timestamp camera frames and/or LiDAR scans through ports.
- Validate dimensions, units, frame identity, freshness, and disconnect behavior.
- Use a fixed, stationary setup for optional physical read-only acceptance; no movement is needed to learn the data path.

### Exit evidence

- Deterministic fake/replay tests for valid data, stale data, malformed data, and sensor loss.
- An offline log/replay that can be inspected without a live sensor.
- If physical acceptance is run, a hardware-marked record showing the robot stayed stationary, the target was confirmed, and the operator could stop/disconnect safely.

### Non-goals

- No locomotion, body motion, obstacle avoidance, navigation, or autonomous stopping.
- No claim that stationary data validates calibration under motion or production perception quality.
- No unbounded raw sensor stream, cloud upload, or automatic hardware discovery.

## GO2-04 — Supervised stand/down/stop

### Prerequisites

- GO2-03 health and logging evidence, or an explicit rationale for using only the read-only subset.
- A Unitree adapter that is optional, typed, and lazy, with command acknowledgements and fail-closed errors.
- Operator, target identity, clear-area, restraint/placement, emergency-stop, and abort procedures reviewed before physical testing.
- Fake scenarios for stand, down, stop, rejection, timeout, and stop precedence.

### Safe scope

- Add only the bounded, explicitly supervised `Stand`, `Down`, and `Stop` commands.
- Issue one command at a time with an explicit operator authority and acknowledgement.
- Keep the robot stationary except for the commanded posture transition; stop takes precedence and remains available.
- Run the behavior in the fake profile first and, only after the physical checklist, in a hardware-marked acceptance test.

### Exit evidence

- Unit and port-contract tests for command bounds, acknowledgement, rejection, timeout, and stop precedence.
- A fake/replay scenario showing safe behavior when authority, health, or acknowledgement is missing.
- A hardware-marked acceptance record, if physical testing is performed, showing the confirmed target, operator, setup, commands, acknowledgements, stop result, logs, and post-test safe state.

### Non-goals

- No walking, velocity, balance experimentation, repeated unattended commands, or autonomous posture policy.
- No remote/public control path.
- No assumption that a successful posture command validates any low-level SDK or motor behavior beyond the tested target and conditions.

## GO2-05 — Bounded deadman velocity

### Prerequisites

- GO2-04 physical and fake evidence, including an independently tested stop path.
- A reviewed velocity contract with units, maximum magnitude, acceleration/rate limits, command duration, and allowed modes.
- A deadman/supervisor lease, timeout behavior, neutral/stop action, and fault logging implemented and tested.
- A physical test plan with restraint/clear area, operator position, target confirmation, and immediate abort criteria.

### Safe scope

- Permit only low, bounded, operator-supervised velocity commands.
- Require a continuously renewed deadman lease; expiration, stale state, disconnect, or invalid input produces a safe neutral/stop result.
- Exercise short, simple motions in a controlled area, beginning with fake/replay and simulation where available.
- Keep command rate, duration, magnitude, and direction constraints visible in logs and test evidence.

### Exit evidence

- Deterministic tests for bound rejection, rate limiting, deadman renewal, timeout, disconnect, stale state, and stop precedence.
- Scenario evidence that every expired lease reaches a safe result within the specified bound.
- Hardware-marked acceptance evidence for each approved speed/direction envelope, with operator, target, logs, abort result, and post-test safe state.

### Non-goals

- No path planning, obstacle avoidance, navigation, remote internet control, or unsupervised motion.
- No speeds, durations, payloads, surfaces, or environments outside the reviewed envelope.
- No claim that deadman supervision replaces a physical emergency stop or a complete safety case.

## GO2-06 — ROS2

### Prerequisites

- Stable typed ports and offline/fake contract tests through GO2-05's currently approved scope.
- A clear decision about which ROS2 topics, services, actions, QoS, and message conversions are needed.
- A separate ROS2 profile that does not add ROS dependencies to the core or default tests.

### Safe scope

- Build a ROS2 adapter/profile around the existing ports and application policy.
- Test topic/service/action conversion, timestamps, QoS behavior, lifecycle, and error propagation with fake/replay data first.
- Keep actuation disabled by default in ROS2 composition; any later hardware actuation still requires the corresponding milestone's explicit physical acceptance.

### Exit evidence

- Offline tests still pass without ROS2 installed.
- A ROS2 profile integration run demonstrates typed state, health, logging, and fake/replay sensor flow.
- A documented launch/composition configuration makes target, namespace, authority, and actuation mode explicit.
- No ROS2 integration test silently reaches a physical target.

### Non-goals

- No assumption that ROS2 supplies safety, supervision, or a locomotion stack.
- No Nav2/autonomous navigation, fleet control, or public robot endpoint.
- No merging ROS-specific message types into the hardware-independent core.

## GO2-07 — Supervised autonomy

### Prerequisites

- GO2-05 bounded velocity and GO2-06 integration evidence where ROS2 is part of the proposed system.
- A written behavior/safety case, operator authority model, bounds/geofence, watchdog, stop precedence, and scenario matrix.
- Sensor freshness and failure behavior understood for the intended environment.
- Simulation/fake scenarios cover normal completion, lost sensors, stale state, blocked progress, operator stop, and process failure.

### Safe scope

- Run only narrowly defined autonomous behaviors under active human supervision and an explicit enable/abort gate.
- Keep the behavior bounded by time, speed, area, command rate, health, and recoverable states.
- Start with fake/replay or optional simulation, then expand physical acceptance one scenario at a time.
- Treat a stop, watchdog expiry, lost authority, or uncertain state as a terminal safe action for the run.

### Exit evidence

- Scenario matrix with expected decisions and logs for nominal, degraded, and abort paths.
- Reviewable evidence that bounds, watchdogs, deadman/authority, stop precedence, and recovery behavior are enforced by tests rather than operator habit.
- Hardware-marked acceptance for each named scenario, with a supervisor and a clear rollback/stop record.

### Non-goals

- No unsupervised deployment, production promise, remote unattended operation, or operation in unreviewed environments.
- No generalized intelligence, open-world obstacle avoidance, stairs, crowds, traffic, or novel terrain unless separately reviewed and evidenced.
- No bypass of the explicit stop, authority, or health gates for demonstration convenience.

## GO2-08 — Onboard app, only after compute access is verified

### Prerequisites

- GO2-07 scope and safety evidence for the behavior proposed to run onboard.
- **Verified compute access:** authorized access to the intended onboard compute, confirmed target identity, supported OS/runtime/architecture, sufficient CPU/GPU/RAM/storage, power/thermal budget, process permissions, and a recovery/rollback path.
- A deployment plan that does not assume SSH, root, a vendor runtime, or an undocumented service exists.
- A resource and failure test plan using the offline profile before any deployment attempt.

### Safe scope

- Proceed only if the compute-access gate is documented as passed by an authorized operator.
- Package a read-only or already-approved supervised application with explicit resource limits, logs, health reporting, and a way to stop/disable it.
- Validate installation, startup, resource usage, restart/rollback, and target identity before connecting the app to any actuation path.
- Keep the core and an offline reproduction of the app behavior available for debugging.

### Exit evidence

- A recorded compute-access verification: target, authorization, runtime, architecture, resource measurements, permissions, and rollback procedure.
- An isolated onboard smoke test and supervised behavior test with logs, resource/thermal observations, stop/disable result, and recovery evidence.
- Evidence that no deployment or startup occurs when access is absent, ambiguous, or outside the approved target.

### Non-goals

- No attempt to gain access, bypass permissions, alter vendor firmware, or assume undocumented onboard compute.
- No permanent service, boot modification, production rollout, or unattended actuation by default.
- No treating a desktop simulation or cross-compiled binary as evidence that onboard access or performance has been verified.

## GO2-09 — Expert low-level implementation and experiment after separate review/restraint

### Prerequisites

- A separate written review and explicit approval for the exact low-level experiment; completion of GO2-08 is not itself approval.
- Vendor documentation, command semantics, units, limits, and rollback behavior understood and recorded.
- A dedicated bench setup with mechanical restraint/tether as appropriate, independent emergency stop, power limits, operator, observer, and a test abort procedure.
- Fake/replay tests, adapter contract tests, and a hardware-safe staging path that prevents low-level commands from entering the default profile.

### Safe scope

- Make the named low-level adapter available only in an explicit expert
  profile, then conduct only the approved experiment, one parameter or
  mechanism at a time, under the reviewed restraint and limits.
- Keep low-level interfaces behind an explicitly opt-in adapter/profile with rate, torque/power, duration, and authority limits.
- Log every command, acknowledgement, fault, stop, and rollback event; stop immediately on uncertainty or unexpected behavior.
- Feed learnings back into typed contracts and safety documentation without making the experiment the default control path.

### Exit evidence

- The separate review/approval record and a bounded test plan tied to the exact target and command set.
- Bench evidence from fake/simulation plus hardware acceptance under restraint, including independent-stop and rollback results.
- A report of observed behavior, limits, unresolved unknowns, and whether the interface is rejected, retained as experimental, or promoted for a new review.

### Non-goals

- No default-profile dependency, uncontrolled motor/torque experiment, bypass of the authority stack, or field deployment.
- No assumption that low-level access improves safety or replaces vendor/robot safety mechanisms.
- No promotion to general locomotion, autonomous control, or onboard deployment without a new, explicit review and milestone.
