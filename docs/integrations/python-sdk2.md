# Unitree SDK2 Python: pinned, offline-first path

This page is the detailed setup and learning path for the Unitree Go2 EDU in
this repository. It uses Unitree's Python SDK2 source, but keeps the first
contact with a robot read-only. It is suitable for learning the package and
verifying DDS discovery; it is **not** a motion tutorial.

> **Safety boundary.** The commands and probe below do not publish motor or
> sport commands and do not switch services. Do not add a publisher, low-level
> command, `SportClient` call, or service switch to the probe. A passing probe
> only establishes that the host can communicate with the robot.

## Support boundary and fixed inputs

- The official robot-runtime path here is **Linux only**. In particular,
  **macOS and Windows are not official robot runtime targets for this guide**.
  They may be used for offline reading, source inspection, or editing, but this
  page does not claim that a macOS or Windows host can run the robot transport.
- The pinned Python source is
  `unitree_sdk2_python` commit
  `65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5`.
- The Python package declares Python `>= 3.8`, `cyclonedds==0.10.2`, `numpy`,
  and `opencv-python` as dependencies.
- For the optional native vendor build, use the official CycloneDDS `0.10.2`
  source commit `9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd`. The commit is the
  immutable source behind the `0.10.2` tag; the version is what matters to the
  SDK integration.
- Use a wired Ethernet link and an explicitly named interface. Do not use
  interface auto-detection, Wi-Fi, or `lo` for the robot run.
- Use DDS **domain `0`**. This is the domain used by the SDK2 examples and by
  the probe below.

The source and version choices are deliberate. The upstream README is mutable
when viewed on a branch such as `main`, and the pinned README also contains
stale example paths such as `/example/high_level/read_highstate.py` that do not
match the pinned tree's `example/go2/...` layout. Treat README prose as
background only; use the commit-pinned source paths in the links at the end of
this page.

## 1. Baseline repository setup (no robot required)

From the `robot-dog` repository root, create an isolated environment. Do not
install into the system Python:

```bash
cd /path/to/robot-dog
python3 --version                 # the vendor package requires >= 3.8
python3 -m venv .venv-sdk2
. .venv-sdk2/bin/activate
python -m pip --version
```

The rest of this page assumes these variables. Choose paths outside the
repository for downloaded vendor material so the application worktree remains
clean:

```bash
export SDK_COMMIT=65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5
export DDS_COMMIT=9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd
export SRC_ROOT="$HOME/src"
export WHEELHOUSE="$HOME/wheelhouse/unitree-sdk2"
export SDK_DIR="$SRC_ROOT/unitree_sdk2_python-$SDK_COMMIT"
mkdir -p "$SRC_ROOT" "$WHEELHOUSE"
```

### Stage immutable source while online

This is the only network-dependent part of the source setup. If the archives
are already on approved removable media or in a local cache, copy them into
place and start at `tar` instead. The archive URLs contain full commit IDs;
do not substitute a branch or a floating release URL.

```bash
curl -fL \
  "https://github.com/unitreerobotics/unitree_sdk2_python/archive/$SDK_COMMIT.tar.gz" \
  -o "$SRC_ROOT/unitree_sdk2_python-$SDK_COMMIT.tar.gz"

tar -xzf "$SRC_ROOT/unitree_sdk2_python-$SDK_COMMIT.tar.gz" -C "$SRC_ROOT"
```

For the optional Linux native build, stage the matching CycloneDDS source too:

```bash
curl -fL \
  "https://github.com/eclipse-cyclonedds/cyclonedds/archive/$DDS_COMMIT.tar.gz" \
  -o "$SRC_ROOT/cyclonedds-$DDS_COMMIT.tar.gz"
tar -xzf "$SRC_ROOT/cyclonedds-$DDS_COMMIT.tar.gz" -C "$SRC_ROOT"
```

Stage dependency wheels before going offline. This is a staging operation,
not a requirement for reading the docs. Use a Linux wheelhouse for the Linux
runtime path and retain the exact files used for a run:

```bash
python -m pip download --dest "$WHEELHOUSE" \
  "cyclonedds==0.10.2" numpy opencv-python setuptools wheel
```

After staging, package installation must be offline and must not silently
resolve a different version:

```bash
python -m pip install --no-index --find-links "$WHEELHOUSE" \
  "cyclonedds==0.10.2" numpy opencv-python setuptools wheel
```

## 2. Optional Linux-only vendor installation

This section is optional for offline source learning. It is the supported
vendor-runtime track for a Linux host with the build tools already available.
Do not run it as a macOS or Windows robot setup; those are not official robot
runtime targets here.

The SDK README recommends compiling CycloneDDS when the Python package cannot
find its native installation. Keep that native installation in a user-owned,
versioned prefix rather than relying on a system copy:

```bash
# Linux only; the source directory was staged in the previous section.
export DDS_SRC="$SRC_ROOT/cyclonedds-$DDS_COMMIT"
export DDS_PREFIX="$HOME/.local/unitree/cyclonedds-0.10.2"
export DDS_BUILD="$SRC_ROOT/cyclonedds-build-0.10.2"

cmake -S "$DDS_SRC" -B "$DDS_BUILD" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$DDS_PREFIX"
cmake --build "$DDS_BUILD" --parallel
cmake --install "$DDS_BUILD"

export CYCLONEDDS_HOME="$DDS_PREFIX"
export CMAKE_PREFIX_PATH="$CYCLONEDDS_HOME${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
```

Install the pinned Python dependency and the editable SDK from the local
wheelhouse. `--no-index` is intentional:

```bash
python -m pip install --no-index --find-links "$WHEELHOUSE" \
  "cyclonedds==0.10.2" numpy opencv-python
python -m pip install --no-index --find-links "$WHEELHOUSE" \
  --no-build-isolation -e "$SDK_DIR"
```

If the editable install reports `Could not locate cyclonedds`, check that
`CYCLONEDDS_HOME` points to the install prefix above and that the prefix is in
`CMAKE_PREFIX_PATH`. Do not “fix” the error by taking an unpinned CycloneDDS
branch or a newer Python package.

## 3. Local import probe (no robot required)

Run this before connecting Ethernet to a robot. It verifies that the Python
package, its declared DDS dependency, and the SDK2 read-only client symbols are
available. It performs no DDS initialization:

```bash
python - <<'PY'
from importlib.metadata import version

import cyclonedds
import unitree_sdk2py
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.robot_state.robot_state_client import RobotStateClient

for distribution in ("unitree_sdk2py", "cyclonedds"):
    try:
        print(f"{distribution} distribution: {version(distribution)}")
    except Exception as exc:
        print(f"{distribution} distribution: unavailable ({exc})")

print("imports: OK")
print("channel initializer:", ChannelFactoryInitialize.__name__)
print("read-only client:", RobotStateClient.__name__)
PY
```

Also retain the local package check as evidence of the environment:

```bash
python -m pip check
python -m pip show unitree_sdk2py cyclonedds numpy opencv-python
```

A package import result is not a hardware result. Continue to the wired setup
only after the import probe is clean.

## 4. Wired interface and static addressing

Connect the robot and host directly with Ethernet, or through an approved
isolated switch. Identify the interface; do not guess its name from an example:

```bash
ip -br link
ip -br -4 addr
```

Set the wired adapter through the host's normal network configuration tool.
For an isolated link, the intended shape is a manual address and
`255.255.255.0` (`/24`), with no gateway or DNS required. The exact host
address must be chosen after verifying the robot address.

### Verify both sides of the isolated link

Identify the robot address using the delivered manual or verified device configuration. Independently choose an unused host address in the verified subnet. Never copy a vendor example into a live network configuration or commit real addresses to this repository.

After the host adapter is configured, check the result without changing it:

```bash
export UNITREE_INTERFACE=enp2s0       # replace with the actual wired name
export ROBOT_IP="<verified-robot-address>"   # replace before use; record privately
ip -4 addr show dev "$UNITREE_INTERFACE"
ip route get "$ROBOT_IP"
ping -c 1 "$ROBOT_IP" || true        # useful hint; not a DDS proof
```

A ping failure is not by itself conclusive, and a ping success is not a DDS
proof. The SDK probe below is the relevant test. If the interface is wrong,
DDS multicast is blocked, or the robot address was assumed rather than
verified, stop there; do not test with motion.

## 5. DDS domain and channel initialization order

SDK2's `ChannelFactoryInitialize` creates the CycloneDDS domain and participant
and accepts the network interface name. For a robot run, initialize it in this
order:

1. Activate the venv and verify the local import probe.
2. Identify the wired interface and verify the static host/robot addressing.
3. Call `ChannelFactoryInitialize(0, UNITREE_INTERFACE)` **exactly once**, with
   domain `0` and the explicit interface.
4. Construct a read-only SDK client or subscriber.
5. Call that object's `Init()` method.
6. Invoke only a read-only API, then close the process.

The factory is a process-level singleton in the pinned source. If it was
initialized with the wrong interface or domain, restart the process rather than
trying to reconfigure it after clients have been created. Do not create a
client before step 3, and do not omit the interface to let the SDK auto-detect
an adapter.

## 6. Read-only hardware probe

Run this with the robot stationary and under the lab's normal operator
oversight. Set `UNITREE_INTERFACE` to the actual wired adapter. The probe only
initializes the DDS channel and calls `GetServerApiVersion()` and
`ServiceList()` on `RobotStateClient`; both calls read metadata. It does not
construct `SportClient`, `ChannelPublisher`, `LowCmd`, or a service-switch
request.

```bash
export UNITREE_INTERFACE=enp2s0       # actual wired interface, not an example

python - <<'PY'
import os

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.robot_state.robot_state_client import RobotStateClient

interface = os.environ.get("UNITREE_INTERFACE")
if not interface:
    raise SystemExit("UNITREE_INTERFACE must name the wired robot interface")

# Must happen before constructing the client; domain 0 is intentional.
ChannelFactoryInitialize(0, interface)

client = RobotStateClient()
client.SetTimeout(3.0)
client.Init()

local_api_version = client.GetApiVersion()
print("local_api_version:", local_api_version)

api_code, server_api_version = client.GetServerApiVersion()
print("server_api_code:", api_code)
print("server_api_version:", server_api_version)

services_code, services = client.ServiceList()
print("service_list_code:", services_code)
if services is not None:
    for service in services:
        print(
            "service:",
            service.name,
            "status:", service.status,
            "protected:", service.protect,
        )

if api_code != 0 or services_code != 0:
    raise SystemExit(1)
PY
```

Interpret the result narrowly:

- `imports: OK` proves local package availability.
- A nonzero `server_api_code` or `service_list_code` means the read-only
  hardware check did not complete. Check the selected interface, verified
  addresses, CycloneDDS prefix, and domain `0`.
- A successful service list proves that this process reached the robot's SDK2
  service endpoint. It does not prove that every service is healthy, that the
  robot is safe to move, or that the current firmware is approved.

The official pinned `RobotStateClient` also exposes service-switch methods.
They are intentionally not used here. Do not add them to this probe.

## 7. API and firmware record

Make a durable lab record for each hardware validation. At minimum, capture:

| Field | What to record |
| --- | --- |
| Host | OS release, Python version, host name, date/time and timezone |
| Wired transport | Interface name, host IPv4/CIDR, verified robot IPv4, and whether the link is direct or through an isolated switch |
| DDS | `cyclonedds` Python distribution version, native CycloneDDS prefix/version, and domain `0` |
| SDK | `unitree_sdk2_python` commit `65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5` and installed `unitree_sdk2py` distribution version |
| Robot identity | Model/variant, serial number, and the operator-approved hardware location |
| API result | local SDK API version, `server_api_version`, result codes, and the service names/status/protection fields returned by the read-only probe |
| Firmware | The exact human-readable firmware version reported by the Unitree app, robot UI, or approved maintenance record |

Do not label the SDK package version or server API version as robot firmware.
For Go2, the pinned low-state schema has a raw `version` pair and battery
version fields, but the SDK source does not define those raw integers as a
human-readable firmware release. If your approved telemetry record includes
them, preserve the raw values and label them as raw DDS fields; use the
Unitree app or maintenance record for the firmware string.

A local environment record can be captured without changing the worktree:

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
uname -a
python --version
python -m pip show unitree_sdk2py cyclonedds numpy opencv-python
printf 'sdk_commit=%s\ncyclonedds_native_commit=%s\ndomain=0\ninterface=%s\n' \
  "$SDK_COMMIT" "$DDS_COMMIT" "$UNITREE_INTERFACE"
```

Store the resulting record in the team's approved lab/ticket system rather
than adding an unrequested file to this repository.

## Troubleshooting without escalating privileges or motion

- **`ModuleNotFoundError: cyclonedds`:** confirm the venv is active and that
  the exact `cyclonedds==0.10.2` artifact is present in the wheelhouse.
- **`Could not locate cyclonedds` during SDK installation:** confirm the native
  CycloneDDS install completed and that `CYCLONEDDS_HOME` and
  `CMAKE_PREFIX_PATH` point to the same `0.10.2` prefix.
- **Import works but the hardware probe times out:** re-check the literal
  interface name from `ip -br link`, the verified robot address, and domain
  `0`. Do not fall back to auto-detection or a different host address without
  recording why.
- **A copied example cannot be found:** inspect only the pinned tree. The
  pinned source uses paths such as `example/go2/high_level/` and
  `unitree_sdk2py/test/lowlevel/`; old README paths like
  `example/high_level/read_highstate.py` are stale for this source snapshot.
- **A page suggests macOS or Windows:** treat it as outside this guide's
  official runtime support boundary. Return to a Linux host for robot
  validation.

## Supervised motion references

This page intentionally gives **links, not casual motion instructions**. Any
future movement work requires the responsible operator, the model-specific
Unitree safety procedure, a clear workspace, and a separately reviewed change.
The following are references only; do not run them as part of this setup:

- [Unitree Go2 Quick Start (live vendor documentation; verify the current model-specific network value)](https://support.unitree.com/home/en/developer/Quick_start)
- [Unitree sports services (live vendor developer documentation)](https://support.unitree.com/home/en/developer/sports_services)
- [Pinned Go2 high-level SDK2 example (official source; contains motion code and is not part of this probe)](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/example/go2/high_level/go2_sport_client.py)
- [Pinned official SDK2 source tree](https://github.com/unitreerobotics/unitree_sdk2_python/tree/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5)

## Immutable official sources

These links use full commit IDs so that the source cited by this guide cannot
silently move:

- [Python SDK2 README at the pinned commit](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/README.md)
- [Python SDK2 package metadata and dependency declarations](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/setup.py)
- [SDK2 channel factory and explicit-interface configuration](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/core/channel.py)
- [Pinned read-only Go2 robot-state client](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/go2/robot_state/robot_state_client.py)
- [Pinned official read-only low-state reader](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/test/lowlevel/read_lowstate.py)
- [Pinned Go2 low-state schema, including raw version fields](https://github.com/unitreerobotics/unitree_sdk2_python/blob/65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5/unitree_sdk2py/idl/unitree_go/msg/dds_/_LowState_.py)
- [Official Unitree ROS2 README with a host-address example (do not copy)](https://github.com/unitreerobotics/unitree_ros2/blob/668d1ec5a05d1c38d3306bdca7d59f2ba3581a88/README.md)
- [Official Unitree deployment README with a host-address example (do not copy)](https://github.com/unitreerobotics/unitree_rl_mjlab/blob/1425b15f73bd4095f0df53709d7c389c3eb9e790/README.md)
- [CycloneDDS source at the official `0.10.2` commit](https://github.com/eclipse-cyclonedds/cyclonedds/tree/9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd)
