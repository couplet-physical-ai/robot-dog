# Robot-dog architecture

## Purpose and boundary

This repository is a learning and safety-oriented development surface for the Unitree Go2 EDU. The default product of the repository is **an offline, hardware-independent program**. A developer must be able to build and exercise the core without a Go2, a Unitree SDK installation, a ROS installation, credentials, or network access.

Hardware support is an adapter, not an architectural prerequisite. A build or test that silently discovers a robot, opens a network socket, or imports a vendor SDK is a design defect. Hardware and ROS are opt-in composition profiles selected explicitly by the operator.

The architecture is intentionally smaller than a complete robotics stack. It provides strong seams for learning, testing, and supervised control; it does not claim that a physics simulator, sensor replay, or the core state machine is a complete substitute for a Go2, its firmware, its state estimation, or a validated locomotion stack.

## Design principles

1. **Typed core first.** Commands, observations, health, time, units, and safety decisions use explicit types. Do not pass unvalidated dictionaries, magic strings, raw floats, or vendor structs through the core.
2. **Hardware independence by construction.** Core and application code depend on ports (interfaces), never on Unitree headers, ROS messages, sockets, serial devices, camera drivers, or filesystem layout.
3. **Fake before physical.** Every new capability gets a deterministic fake or replayable adapter before a physical adapter. The fake is the first place to define behavior, error cases, and safety limits.
4. **One-way dependency flow.** Domain types and policies sit below ports; adapters sit outside them. Vendor and middleware types are translated at the edge and do not leak inward.
5. **Default no hardware.** The default profile links only the core, fakes, deterministic clock, and local logging. Unitree, ROS, network, and hardware discovery are never implicit.
6. **Fail closed.** Missing data, stale data, invalid units, disconnected adapters, expired supervision, and unknown states produce a safe non-action rather than a best guess.
7. **Supervision is explicit.** Any actuation path identifies its authority, timeout, bounds, and stop behavior. Autonomous behavior is a later milestone, not an accidental property of the control loop.

## Layered model

```text
                         explicit composition only
     +-------------------+-------------------+--------------------+
     | offline/fake      | Unitree hardware  | ROS2               |
     | profile           | profile           | profile            |
     +---------+---------+---------+---------+----------+---------+
               |                   |                    |
     +---------v-------------------v--------------------v---------+
     |                    ports / translators                    |
     | typed sensor, actuator, clock, health, logging interfaces  |
     +-------------------------------+---------------------------+
                                     |
     +-------------------------------v---------------------------+
     | application/safety layer                                  |
     | lifecycle, supervision, command gating, state transitions |
     +-------------------------------+---------------------------+
                                     |
     +-------------------------------v---------------------------+
     | typed hardware-independent core                          |
     | units, identifiers, observations, commands, invariants,  |
     | deterministic policy and pure calculations                |
     +-----------------------------------------------------------+
```

### 1. Typed hardware-independent core

The core owns the vocabulary and invariants that should mean the same thing in a fake, a replay, a Unitree adapter, and a ROS node. Typical types include:

- strongly named quantities with units (for example, `MetersPerSecond`, `Radians`, `Seconds`, and `BatteryFraction`), with defined ranges;
- robot and component identifiers that cannot be confused with arbitrary strings;
- machine status and health values, including freshness and fault reasons;
- immutable sensor observations with timestamps and source metadata;
- bounded commands such as `Stand`, `Down`, `Stop`, and later a velocity command with an expiry/deadman deadline;
- safety decisions that say both what is permitted and why;
- explicit error/result types for unavailable, stale, malformed, rejected, and faulted inputs.

The core must not know whether an observation came from a Go2, a replay file, MuJoCo, a ROS message, or a unit test. It must not own threads, process-global configuration, vendor handles, or hidden clocks. Time is supplied through a port or a value passed into a pure function so that tests can control it.

### 2. Application and safety layer

This layer composes core types into an executable behavior: lifecycle, polling or event handling, health aggregation, supervision, command gating, and state transitions. It is responsible for rules such as:

- do not issue a command while the required authority or health condition is absent;
- reject stale observations and expired operator leases;
- make `Stop` take precedence over a pending motion command;
- emit a safe neutral/stop action when a deadman expires;
- report the reason for every rejected or suppressed action.

The application layer still talks only to ports. A policy that needs a Unitree-specific detail must receive a normalized capability or status type, not a vendor object.

### 3. Ports

Ports are narrow, typed contracts owned by the repository. They describe what the application needs, not what a vendor library happens to expose. Initial ports should include:

- `Clock`: monotonic time and deterministic time advancement;
- `StateSource`: current robot/component observations and freshness;
- `CommandSink`: bounded command submission and an acknowledgement/result;
- `CameraSource` and `LidarSource`: timestamped frames/scans plus health;
- `HealthSource`: connection, sensor, actuator, and process health;
- `Supervisor`: operator approval/deadman lease where actuation is permitted;
- `EventLog`: structured local events and safety decisions.

A port should define timeout, ownership, units, ordering, and failure semantics. It should not expose a raw socket, SDK session, ROS executor, or an unbounded `send(anything)` escape hatch.

### 4. Adapters

Adapters translate external mechanisms into ports and translate port commands back out. Every adapter has an explicit lifecycle and reports unavailable, stale, rejected, and faulted states rather than hiding them.

- **Fake adapter:** deterministic, in-process, no network, controllable clock, scripted observations, fault injection, and recorded commands. It is the reference behavior for examples and default tests.
- **Replay adapter:** reads checked-in or generated local fixtures and preserves timestamps/order. It must not require a live sensor or network.
- **MuJoCo adapter (optional):** may provide a local physics signal when an appropriate model is available. It is a simulation adapter, not proof of Go2 firmware behavior, high-level locomotion, perception, or SDK compatibility.
- **Unitree adapter (optional):** the only layer allowed to depend on Unitree SDK types. It maps SDK state and command results to repository types and translates repository commands back only after safety validation.
- **ROS2 adapter/profile (optional):** maps ROS topics, services, actions, and QoS behavior to the same ports. ROS message types remain at the boundary; ROS is not a dependency of the default core or fake profile.

Adapters must not be selected by “whatever is installed.” The composition profile supplies the adapter explicitly and fails with a clear configuration error when an opt-in dependency is unavailable.

## Lazy optional Unitree SDK boundary

The Unitree SDK is a deliberately lazy, optional boundary:

1. The offline core and default profile compile without Unitree headers, libraries, environment variables, or credentials.
2. SDK-dependent code lives in a separate adapter and, where supported by the build system, a separate optional target/profile.
3. SDK types are imported only inside that adapter. Conversion happens at the boundary into repository-owned types.
4. Construction of the adapter happens only after an explicit hardware profile is selected and the required endpoint/configuration is supplied. Importing the core, running a fake example, or running tests must not initialize a session or probe the network.
5. If the SDK is missing, incompatible, disconnected, or returns an unknown value, startup fails clearly or the safety layer remains non-actuating. It must never silently fall back from hardware to a live or remote target.
6. Unitree behavior is validated with contract fixtures and hardware-marked acceptance tests; vendor behavior is not guessed in the core.

“Lazy” means both **build-optional** and **runtime-explicit**. A transitive SDK dependency in the default target or an automatic hardware discovery scan violates this boundary.

## Separate C++ and ROS2 profiles

C++ and ROS2 are complementary deployment profiles, not one blended default:

| Profile | Intended use | Required dependencies | Default behavior |
| --- | --- | --- | --- |
| `offline` | Core learning, unit tests, fakes, replay, local logs | C++ toolchain and local test dependencies | No hardware, no network |
| `unitree` | Explicit Go2 adapter work and supervised bench tests | Unitree SDK plus a configured target | Refuses to act unless selected and healthy |
| `ros2` | ROS2 message/launch integration around the same ports | ROS2 and profile-specific packages | Fake/replay is still the first integration target |
| `mujoco` | Optional local physics experiments | Official MuJoCo package/API and an available model | Simulation only; no implied hardware semantics |

The exact build-system names may differ, but the separation is a contract: the core target stays usable from a plain C++ environment; ROS2 packages do not force ROS2 into core tests; and a profile documents every external dependency and side effect.

## Composition and ownership rules

A single composition root selects all ports and adapters. It should make the target, profile, clock, logging destination, and supervision mode visible at startup. No library constructor should reach into global configuration to decide whether to open hardware.

Prefer this dependency direction:

```text
core types/policies <- application <- ports <- adapters <- composition root
```

The arrow means “depends on.” The reverse direction is prohibited. In particular:

- core code must not include Unitree or ROS headers;
- ROS nodes must call the application through typed ports rather than duplicating policy;
- the Unitree adapter must not become the place where safety policy is bypassed;
- test fakes must implement the same ports as production adapters;
- logs must record normalized values and reasons, not only vendor-specific debug strings.

## Safety boundary

Movement is a separate capability from observation. Read-only state, logging, and stationary sensors can be developed without granting an actuator port. When actuation is introduced, the composition must make the following visible and testable:

- explicit operator/supervisor authority;
- command bounds and units;
- command expiry and deadman behavior;
- stop precedence and the adapter's acknowledgement;
- stale/faulted input behavior;
- a physical test plan, restraint, and emergency stop for hardware acceptance.

No architecture decision in this document authorizes a physical command. The staged gates in [the learning roadmap](roadmap.md) do that only for the named milestone and only within its stated scope.
