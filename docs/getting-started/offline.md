# Offline getting started

## What this path is

The offline path is the required first path for robot-dog development. It is designed to work without a Go2, Unitree SDK, ROS2, credentials, or network access. It exercises the typed core, application policy, fakes, replay fixtures, deterministic time, and local logs.

A successful offline run proves that the repository's types and policies behave as specified against controlled inputs. It does **not** prove that a physical robot, firmware, vendor SDK, sensor, or onboard computer will behave the same way.

The current checkout provides a deterministic Python fake and pytest suite. Install public development dependencies with `uv sync` once (or use an existing cache); execution after installation requires no network or hardware. Run the offline commands below rather than any optional Unitree/ROS profile.

## Offline guarantees

The default profile must:

- compile and test the hardware-independent core without Unitree headers/libraries;
- avoid ROS2 imports, executors, topic publication, and message dependencies;
- instantiate fakes or replay adapters explicitly rather than discovering a device;
- use a deterministic clock and fixed fixtures/seeds;
- write only local, reviewable output (for example, a temporary directory or an explicitly chosen log path);
- make network/device access unavailable or fail immediately;
- keep actuation as recorded fake commands, never a live command;
- report unavailable, stale, malformed, and faulted inputs as safe results.

If an offline command attempts to open a socket, serial/device path, ROS graph, Unitree session, or remote endpoint, stop and treat that as a defect in composition or test isolation. Do not “make the test pass” by attaching a real robot.

## Setup checklist

1. In a clean checkout, install the default development profile with `uv sync` (do not select the optional Unitree, CycloneDDS, or ROS 2 extras).
2. Run the hardware-free suite: `uv run pytest`.
3. Run the deterministic fake demo and read-only offline inspection: `uv run robot-dog demo --json`, `uv run robot-dog capabilities`, and `uv run robot-dog status`.
4. Optionally run `uv run robot-dog doctor` for read-only local diagnostics. It may inspect the local OS interface index but sends no network packets.

The offline smoke behavior is:

```text
fake boot -> hello-state -> healthy logging -> inject stale sensor
       -> observe fail-closed decision -> record Stop/neutral result
```

The exact output format may evolve, but the behavior and absence of external side effects are not implementation-defined.

## First exercises

Work through these in order; each should be reproducible without a robot:

### 1. Hello-state

Feed a fixed healthy fake observation to the read-only state path. Confirm that status, source, timestamp, health, and units are explicit. Repeat with unknown, unavailable, and stale inputs and confirm that the system does not invent a healthy state.

### 2. Logging and health

Inject a disconnect, malformed value, stale timestamp, and rejected operation. Confirm that each event is normalized, timestamped, attributable to a source, and visible in the local log. Confirm that health failure suppresses any downstream action.

### 3. Stationary sensor replay

Use a local camera/LiDAR fixture or replay if one exists. Check frame/source identity, dimensions, units, timestamp ordering, freshness, and sensor-loss behavior. No movement or hardware connection is required.

### 4. Supervised command scenarios in a fake

Before any physical command is considered, exercise fake `Stand`, `Down`, and `Stop` with operator authority, missing authority, rejected acknowledgement, timeout, and stop precedence. For velocity later, test bounds, rate limits, deadman renewal, and deadman expiry entirely in fake time.

## Optional local simulation

If local dependencies and a compatible model are already available, an optional MuJoCo profile can add useful physics-oriented experiments. The official MuJoCo Python bindings (`mujoco`) and the official native C/C++ API are reasonable local options for a simulation adapter. Keep that adapter behind the same typed ports as the fake.

MuJoCo is not a requirement for the offline path. More importantly, it is not a complete high-level Go2 simulation by default. A MuJoCo run may help test timing, contact/actuator calculations, or adapter contracts for the model that is actually present. It does not establish Unitree SDK semantics, firmware behavior, onboard state estimation, camera/LiDAR fidelity, locomotion robustness, or physical safety. Record model and fidelity limits with any simulation result.

## What stays out of the offline path

Do not add any of the following to the default command or default test fixture:

- automatic Unitree SDK loading, network discovery, or “first robot found” behavior;
- ROS2 launch, executor, topic publication, or live graph access;
- camera/LiDAR device discovery;
- physical actuation, even if a target happens to be connected;
- cloud logging, remote dashboards, or credentials;
- low-level motor/torque commands;
- an environment variable that silently changes the target from fake to hardware.

Hardware-marked acceptance is a separate, explicit activity described in [the testing strategy](../testing.md). Physical stand/down/stop begins only at GO2-04; bounded velocity begins only at GO2-05; later milestones add their own gates.

## Troubleshooting offline failures

- **Optional SDK or ROS dependency is missing:** keep working in `offline`; do not install or invoke hardware profiles merely to satisfy the default suite.
- **A test has nondeterministic timestamps:** inject the deterministic clock and fixed fixture timestamps.
- **A fake accepts an invalid command:** strengthen the port contract and fake fault/validation behavior before adding a physical adapter.
- **A test tries to connect externally:** remove the production composition path from the default target and add an access guard; do not whitelist the endpoint.
- **A simulation result is being treated as robot proof:** record the model and missing fidelity, then narrow the claim to the tested simulation behavior.
- **A physical feature is requested before its milestone:** return to the roadmap, add the missing fake/replay and safety evidence, and do not bypass the gate.

## Offline completion checklist

Before calling an offline change complete, verify:

- [ ] The offline profile builds without Unitree SDK and ROS2 dependencies.
- [ ] Default tests use only injected fake/replay ports and deterministic time.
- [ ] No default test opens hardware, a socket, a ROS graph, or a remote endpoint.
- [ ] Invalid, stale, unavailable, and rejected inputs fail closed and are logged.
- [ ] Any new adapter has a port contract test and an explicit optional profile.
- [ ] Any MuJoCo evidence states exactly what model and behavior were tested.
- [ ] The change does not silently grant actuation or promote a later roadmap milestone.
