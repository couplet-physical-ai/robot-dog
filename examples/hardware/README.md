# Hardware examples

These examples are **opt-in hardware profiles**, not default CI commands. The
repository now implements the full source-pinned control surface, but examples
never claim that a particular Go2, firmware, host, network, sensor, or onboard
computer has been validated. Complete the target-specific intake and the
[full-control checklist](../../docs/safety/full-control-checklist.md) before
using any write-capable API.

## Read-only first connection

`unitree_readonly_probe.py` is the first target-facing entry point. It requires
a named robot-facing Linux interface and defaults to DDS domain `0`:

```console
python examples/hardware/unitree_readonly_probe.py --interface <validated-linux-interface>
```

The example uses only the source-verified `RobotStateClient` read path: local
and server API versions plus the service list. It does not subscribe to an
unverified topic, create a publisher, change host network configuration, or
issue a robot command. A successful probe establishes only that this process
completed the selected read path; it is not hardware validation or permission
to write.

## Full-control and low-level CLI examples

The repository-owned operator CLI is the single composition root for the
write-capable adapters. Inspect its complete high-level action inventory and
both thin hardware entry points without a vendor SDK or DDS session:

```console
uv run robot-dog unitree catalog
python examples/hardware/unitree_full_control.py --help
python examples/hardware/unitree_low_level.py --help
```

`robot-dog unitree` also exposes the actual `sport-invoke`, bounded `move`,
`service`, `motion`, `video`, `vui`, `obstacles`, and `low-level once`/`timed`
operations. The full-control example delegates to `robot-dog unitree`; the
low-level example delegates to `robot-dog unitree low-level`. The low-level
operations require a JSON file containing exactly twelve records with `q`,
`dq`, `kp`, `kd`, `tau`, and `mode`, plus all of the explicit operator,
expert, restraint, motion-service, and motion-ownership confirmations.

`catalog` and `--help` are offline inspection only. Target operations require
the named interface and DDS domain, the relevant hardware/operator gates, and
the [full-control checklist](../../docs/safety/full-control-checklist.md).

The SDK is optional and must not be installed by the baseline/offline or macOS
CI profile. On an approved Linux engineering host, install the exact pins from
the repository root with `requirements-unitree.txt` after the DDS link and
physical unit have passed the intake/security gates.

## Full-control Python entry points

The public classes and results are re-exported from
`robot_dog.adapters.unitree_sdk2`. Construction remains lazy and side-effect
free: importing the package does not import `unitree_sdk2py` or initialize DDS.
The following is a composition example, not a command to run against an
unapproved unit:

```python
from robot_dog.adapters.unitree_sdk2 import (
    AuthoritySafetyAcknowledgements,
    Go2SportClient,
    SportClientSafetyAcknowledgements,
    UnitreeGo2LowLevel,
    UnitreeSdk2Authority,
    UnitreeSdk2Peripherals,
)

interface = "<validated-linux-interface>"

# False is intentional until a named, approved run supplies the acknowledgements.
sport = Go2SportClient(
    network_interface=interface,
    domain_id=0,
    acknowledgements=SportClientSafetyAcknowledgements(),
)
authority = UnitreeSdk2Authority(
    network_interface=interface,
    domain_id=0,
    acknowledgements=AuthoritySafetyAcknowledgements(),
)
peripherals = UnitreeSdk2Peripherals(
    network_interface=interface,
    domain_id=0,
    acknowledgements=AuthoritySafetyAcknowledgements(),
)
low_level = UnitreeGo2LowLevel(
    interface=interface,
    domain_id=0,
    hardware_enabled=False,
    operator_confirmed=False,
    expert_low_level_confirmed=False,
    robot_restrained_confirmed=False,
    motion_service_released=False,
    motion_ownership_confirmed=False,
)
```

The implemented entry points are:

- **High level and special motion:** `Go2SportClient` exposes every pinned
  `SportClient` action through named methods and `invoke(..., intentional=True)`;
  inspect `command_catalog()`, and use `move_for(...)` for a bounded `Move`
  session. Special motions such as flips, jumps, pounces, free modes, dance,
  and handstand require the separate hazardous-motion acknowledgement.
- **Service and mode:** `UnitreeSdk2Authority` exposes
  `read_service_list()`, `switch_service()`, `set_report_frequency()`,
  `check_mode()`, `select_mode()`, and `release_mode()`. Mutations require
  `hardware_enabled=True`, `operator_acknowledged=True`, a named `target_id`,
  and `confirmation` exactly equal to that target.
- **Peripherals:** `UnitreeSdk2Peripherals` groups `.video`, `.vui`, and
  `.obstacles`. Use their read methods for image/VUI/obstacle state and their
  write methods only with both explicit hardware and operator gates. Results
  are normalized as `UnitreePeripheralResult`.
- **Expert low level:** `UnitreeGo2LowLevel` exposes `read_low_state()`,
  `build_low_command()`, `publish_once()`, and finite `publish_timed(...)`.
  Construct commands with exactly twelve `MotorCommand` records. Low-level
  publication additionally requires expert and restraint confirmations plus an
  explicit motion-service release or ownership confirmation; `stop()` only
  suppresses future writes and is not a physical emergency stop.

The code snippets in this README do not invoke a sport action, service switch,
peripheral mutation, or low-level write. The thin CLI entry points can invoke
their delegated operations only when a caller supplies the required explicit
gates. Read [full-control integration](../../docs/integrations/full-control.md)
for the pinned API/source map and [the safety checklist](../../docs/safety/full-control-checklist.md)
for approval, authority, stop, abort, and evidence requirements.
