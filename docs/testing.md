# Testing strategy

## Testing contract

The default test command must be safe to run on a laptop with no Go2, no Unitree SDK, no ROS2 installation, no credentials, and no network access. A default test is not allowed to discover hardware, open a socket, call a vendor SDK, publish to ROS, or depend on wall-clock timing.

The test suite should make that property structural rather than relying on developer caution:

- default targets link the hardware-independent core and fake/replay adapters only;
- every port is injected, and the default fixture supplies deterministic fakes;
- the default profile has no Unitree or ROS2 dependency and does not import or initialize them;
- network and device access are absent from the default test process; an attempted access is a failure, not a skipped test;
- clocks, random sources, environment, and filesystem locations used by tests are injectable or local to a temporary directory;
- test fixtures use fixed timestamps, IDs, units, and seeds;
- tests assert both the result and the recorded command/event stream, including suppressed actions and reasons;
- hardware-marked tests are excluded unless an operator explicitly selects a hardware profile and target.

If implementation tooling supports test labels, the safe default is the complement of `hardware`, `network`, `unitree`, `ros2`, and `acceptance` labels. If it does not, maintain separate test targets/processes with the same exclusion guarantee. Do not make the default safe by merely skipping a test after it has opened a connection.

## Test layers

### 1. Type and invariant tests

Test units, ranges, identifiers, status transitions, timestamps, freshness, result/error values, and serialization at the smallest possible scope. Include invalid construction and boundary values. These tests should be pure and run in every profile.

Examples:

- a negative duration or out-of-range battery fraction is rejected;
- a stale observation is distinguishable from a current fault;
- a velocity command carries units, bounds, and an expiry;
- `Stop` has defined precedence over a pending motion command;
- unknown external enum values map to an explicit `Unknown`/fault result rather than a valid state.

### 2. Core policy unit tests

Exercise safety and application policy with in-memory values and a controllable clock. No adapter should be needed beyond a test double. Cover the normal path and fail-closed paths:

- startup with no state;
- missing, stale, malformed, or conflicting observations;
- unavailable or rejected command sinks;
- expired supervision/deadman leases;
- stop during and immediately after a pending command;
- repeated commands and out-of-order timestamps;
- logging of decision, reason, source, and correlation ID.

These tests should be deterministic and fast enough to run for every change.

### 3. Port contract tests

Run the same contract suite against the fake, replay, MuJoCo (where applicable), and Unitree adapter doubles. A port contract states what every implementation must guarantee, for example:

- observations carry a source, timestamp, and health status;
- commands are acknowledged or rejected with a normalized reason;
- disconnects and stale data are visible to the caller;
- adapters do not reorder or silently drop safety-critical stop commands;
- all external values are converted to repository units before crossing the boundary.

The fake is not permitted to be “helpfully” more capable than the port. If the fake cannot model a failure that matters, add fault injection before trusting it as a test oracle.

### 4. Scenario and replay tests

Use short, local scenarios to verify sequences without physical motion: boot, healthy state, sensor loss, stale state, rejected command, stop precedence, and deadman expiry. Replay fixtures should be small, reviewable, and deterministic. A scenario should report a timeline of observations, decisions, commands, acknowledgements, and final safety state so a failure can be diagnosed offline.

### 5. Profile integration tests

Each optional profile gets a small explicit integration target:

- `offline`: core + fake/replay + local log, always available;
- `mujoco`: local simulation adapter only when the official API and a compatible model are installed;
- `unitree`: adapter translation and connection/error behavior against a controlled target or vendor-provided test facility;
- `ros2`: topic/service/action and QoS translation with fake/replay nodes before any robot is involved.

Profile integration tests should verify composition and dependency boundaries, not duplicate the core policy suite. A profile that cannot be built should report a missing optional dependency; it must not make the offline target fail.

## Hardware-marked acceptance

Physical acceptance is a separate, explicitly selected class of test. It is never part of the default test command and should require all of the following:

1. A named target and operator, with the target's identity confirmed before connecting.
2. A hardware profile selected explicitly; no discovery or “first robot found” behavior.
3. A pre-test checklist: charged/known battery, clear area, physical restraint where required, independent emergency stop, operator position, and a tested stop path.
4. A bounded test case with one intended behavior, a time limit, command limits, and a written abort condition.
5. Logging of normalized observations, commands, acknowledgements, timestamps, faults, and the result.
6. A post-test check that the robot is stopped and the adapter is disconnected or returned to its safe state.

Suggested labels are `hardware`, `unitree`, `acceptance`, and, where relevant, `network` or `ros2`. A hardware-marked acceptance test may be run only by an explicit command/profile and should fail closed when the required target, SDK, operator confirmation, or stop check is absent. A successful fake test is evidence of core behavior; it is not evidence that a physical Go2 is safe to move.

The first physical movement acceptance belongs to the narrow supervised stand/down/stop scope in milestone GO2-04. Velocity acceptance is not implied by stand acceptance; it begins only at GO2-05 and adds its own deadman and bound checks.

## Network and device isolation

Default testing should be runnable in an environment where network and device APIs are unavailable. The implementation should enforce this with one or more of:

- separate offline build targets with no adapter linkage;
- a test-only access guard that fails any socket/device attempt;
- dependency injection with no production factory reachable from default tests;
- CI sandboxing or an equivalent denied-by-default environment;
- assertions that no Unitree session, ROS executor, serial handle, or device path was created.

Do not use a network mock that permits an accidental real endpoint. Do not use a hardware environment variable as an implicit opt-in. An explicit profile and test label are required.

## MuJoCo and simulation scope

Official MuJoCo options can be useful for local experiments: the official `mujoco` Python bindings and the official native C/C++ API can drive an optional simulation adapter when a compatible model is available. Use those options for deterministic physics signals, timing, contact/actuator experiments, and adapter-contract tests.

They do **not** by themselves provide a complete high-level Go2 simulation. In particular, a MuJoCo run must not be presented as proof of Unitree SDK semantics, firmware behavior, onboard state estimation, camera/LiDAR realism, locomotion robustness, or safe physical control. If a Go2 model, sensor model, or actuator mapping is unavailable, keep the test at the fake/replay level and document the missing fidelity rather than inventing equivalence.

## Required evidence for a change

A change is ready to progress when its evidence matches its risk:

| Change | Minimum evidence |
| --- | --- |
| Core type or pure policy | Unit/invariant tests, including invalid and boundary cases |
| New port or adapter | Port contract tests, failure injection, and explicit profile coverage |
| Sensor/logging behavior | Deterministic replay or fake scenario with stale/disconnect cases |
| ROS2 integration | Offline core tests plus explicit ROS2 profile integration; no ROS dependency in default target |
| Simulation experiment | Reproducible local run and a statement of model/fidelity limits |
| Physical read-only behavior | Hardware-marked acceptance with operator and target record |
| Physical actuation | Hardware-marked acceptance, bounded scope, independent stop, logs, and review appropriate to the milestone |

Tests should be run in the narrowest safe profile first, then in any explicitly selected optional profile. A green offline suite is a release gate for the core, not permission to skip hardware acceptance when the change crosses the physical boundary.
