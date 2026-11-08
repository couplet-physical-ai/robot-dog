# Python with Unitree SDK2

This is a learning path for the Unitree Go2 EDU and the official
`unitree_sdk2_python` interface. It is deliberately **offline-first** and
**read-only until the final hardware probe**: set up the source and Python
environment without a robot, prove imports locally, then attach a robot only to
ask for status and service metadata.

> **Scope and safety.** Nothing in this path sends a motion, low-level motor, or
> service-switch command. Do not add one to the probe. A successful probe is not
> permission to move a robot; supervised motion is linked at the end rather
> than described here.

## Before starting

- Use a Linux host for the official robot-runtime path. **macOS and Windows are
  not official robot runtime targets for this guide.** They can be used to read
  the source and docs offline, but this guide does not claim that the SDK2 robot
  transport is supported there.
- Work from a wired Ethernet connection when a robot is attached. The DDS
  interface must be selected explicitly; do not rely on Wi-Fi, `lo`, or
  interface auto-detection for a robot run.
- Use the pinned vendor source below, not an unpinned checkout or a copied
  snippet from the current upstream README.

## The six checkpoints

1. **Baseline:** from this repository, create an isolated Python environment
   and stage the pinned vendor source and dependency wheelhouse.
2. **Local import:** with no robot connected, verify that Python can import the
   SDK and CycloneDDS.
3. **Wired network:** identify the actual Ethernet interface and verify the
   model-specific robot address before choosing a host address.
4. **DDS setup:** initialize SDK2's channel factory with **domain `0`** and the
   explicit interface before creating any SDK client or subscriber.
5. **Read-only probe:** ask only for the robot server API version and service
   list. Do not construct a publisher or a motion client.
6. **Record:** save the SDK commit, dependency versions, host/interface
   details, robot model and serial, server API version, and the firmware string
   reported by the Unitree app or maintenance workflow.

The exact commands, the address caveat, and a copy/paste-safe read-only probe
are in [Python SDK2 integration details](../integrations/python-sdk2.md).

## Baseline repository setup

From the root of this repository, keep the environment separate from the
source tree. This first step does not need a robot or network access:

```bash
cd /path/to/robot-dog
python3 --version                 # Python >= 3.8 is required by the vendor package
python3 -m venv .venv-sdk2
. .venv-sdk2/bin/activate
python -m pip --version
```

If the SDK archive and wheels were staged while online, install only from that
local wheelhouse. `--no-index` makes an accidental network lookup visible:

```bash
export WHEELHOUSE="$HOME/wheelhouse/unitree-sdk2"
export SDK_DIR="$HOME/src/unitree_sdk2_python-65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5"
python -m pip install --no-index --find-links "$WHEELHOUSE" \
  "cyclonedds==0.10.2" numpy opencv-python
python -m pip install --no-index --find-links "$WHEELHOUSE" -e "$SDK_DIR"
```

If those artifacts are not staged, stop at the baseline and stage them from
the immutable links in the integration page before disconnecting from the
network. Do not replace the SDK commit with `main` to make a download work.

## What ‘connected’ means

Use only an isolated wired adapter and an address verified for the exact unit and firmware. Choose an unused host address in the verified subnet; do not copy addresses from vendor examples or this repository. Record real network settings only in a private intake record. The detailed integration guide explains read-only verification.

## Local import before hardware

Run the import probe before connecting the robot. It tests package availability,
not DDS discovery and not motion:

```bash
python - <<'PY'
from importlib.metadata import version

import cyclonedds
import unitree_sdk2py
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.robot_state.robot_state_client import RobotStateClient

for distribution in ("unitree_sdk2py", "cyclonedds"):
    try:
        print(f"{distribution} distribution:", version(distribution))
    except Exception as exc:
        print(f"{distribution} distribution: unavailable ({exc})")

print("imports: OK")
print("channel initializer:", ChannelFactoryInitialize.__name__)
print("read-only client:", RobotStateClient.__name__)
PY
```

The final hardware probe and its expected fields are kept in the integration
page so that this short onboarding page remains a safe checkpoint, not a
motion tutorial.

## After the probe

Record the result before asking for any additional access. If the probe fails,
keep the robot stationary and troubleshoot the interface, static address,
CycloneDDS installation, or domain selection; do not “test” connectivity with a
movement command.

For supervised motion, leave this learning path and use the vendor's
model-specific safety procedure and service documentation. See the
[integration page's supervised-motion references](../integrations/python-sdk2.md#supervised-motion-references)
for links only.
