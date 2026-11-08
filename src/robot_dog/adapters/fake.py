"""Offline, read-only adapter used by the fake developer experience.

The fake adapter deliberately has no transport, socket, SDK, or ROS imports.  It
is safe to use in a laptop-only checkout and is also useful as a small contract
fixture for the application layer.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from typing import Any

from robot_dog.domain.health import HealthStatus
from robot_dog.domain.telemetry import RobotTelemetry
from robot_dog.ports.telemetry import TelemetryReader

FAKE_ROBOT_ID = "fake-go2"


class ReadOnlyAdapterError(RuntimeError):
    """Raised when code attempts to issue a command through the fake adapter."""


@dataclass(frozen=True)
class FakeTelemetry:
    """One deterministic telemetry sample.

    Values are intentionally boring and stable.  In particular, no wall-clock
    time, random number generator, host information, or hardware SDK is used.
    """

    sample: int
    timestamp: str
    battery_percent: float
    battery_voltage: float
    temperature_c: float
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    mode: str = "standby"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of this sample."""

        value = asdict(self)
        value["position_m"] = list(self.position_m)
        value["velocity_mps"] = list(self.velocity_mps)
        # ``observed_at`` is the deterministic monotonic value consumed by the
        # repository-owned telemetry port.  The ISO timestamp is retained as a
        # human-friendly fixture field for the demo.
        value["observed_at"] = float(self.sample)
        value["health"] = HealthStatus.HEALTHY.value
        return value

    def to_core(self) -> RobotTelemetry:
        """Translate this fixture into the typed read-only telemetry port."""

        return RobotTelemetry(
            observed_at=float(self.sample),
            battery_percent=self.battery_percent,
            health=HealthStatus.HEALTHY,
        )


@dataclass(frozen=True)
class FakeStatus:
    """Read-only status of the simulated robot."""

    robot_id: str = FAKE_ROBOT_ID
    state: str = "standby"
    connected: bool = False
    transport: str = "offline"
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_TELEMETRY: tuple[FakeTelemetry, ...] = (
    FakeTelemetry(
        sample=0,
        timestamp="2024-01-01T00:00:00Z",
        battery_percent=87.5,
        battery_voltage=51.20,
        temperature_c=28.0,
        position_m=(0.0, 0.0, 0.0),
        velocity_mps=(0.0, 0.0, 0.0),
    ),
    FakeTelemetry(
        sample=1,
        timestamp="2024-01-01T00:00:01Z",
        battery_percent=87.4,
        battery_voltage=51.18,
        temperature_c=28.1,
        position_m=(0.02, 0.0, 0.0),
        velocity_mps=(0.02, 0.0, 0.0),
    ),
    FakeTelemetry(
        sample=2,
        timestamp="2024-01-01T00:00:02Z",
        battery_percent=87.3,
        battery_voltage=51.16,
        temperature_c=28.2,
        position_m=(0.04, 0.0, 0.0),
        velocity_mps=(0.02, 0.0, 0.0),
    ),
)


class FakeRobotAdapter(TelemetryReader):
    """A deterministic and explicitly read-only robot adapter.

    ``read_telemetry`` walks through a fixed sequence and then holds on the
    final sample.  A newly-created adapter always starts at sample zero, so a
    demo or test gets the same output on every run.

    The adapter intentionally exposes no working command path.  Command-shaped
    methods are present only to fail loudly if application code accidentally
    wires a write operation into the offline path.
    """

    name = "fake"
    robot_id = FAKE_ROBOT_ID

    def __init__(self, telemetry: Iterable[FakeTelemetry] | None = None) -> None:
        samples = tuple(telemetry) if telemetry is not None else DEFAULT_TELEMETRY
        if not samples:
            raise ValueError("FakeRobotAdapter requires at least one telemetry sample")
        self._telemetry: tuple[FakeTelemetry, ...] = samples
        self._cursor = 0

    def capabilities(self) -> dict[str, Any]:
        """Describe the operations supported by this adapter."""

        return {
            "adapter": self.name,
            "robot_id": self.robot_id,
            "offline": True,
            "read_only": True,
            "telemetry": True,
            "status": True,
            "hardware_commands": False,
            "low_level_commands": False,
            "network_access": False,
            "network_configuration_mutation": False,
            "sdk_required": False,
        }

    # Common port spellings are intentionally supported while the core ports
    # package is being developed.  They all remain read-only aliases.
    get_capabilities = capabilities

    def read_status(self) -> FakeStatus:
        return FakeStatus()

    def status(self) -> FakeStatus:
        return self.read_status()

    get_status = status

    def _read_frame(self) -> FakeTelemetry:
        sample = self._telemetry[self._cursor]
        if self._cursor < len(self._telemetry) - 1:
            self._cursor += 1
        return sample

    def read_telemetry(self) -> RobotTelemetry:
        """Read one normalized sample through the repository-owned port."""

        return self._read_frame().to_core()

    def read_frame(self) -> FakeTelemetry:
        """Read the richer fixture used by the human-facing demo."""

        return self._read_frame()

    # Common adapter spellings remain typed read-only aliases.
    get_telemetry = read_telemetry
    telemetry = read_telemetry

    def telemetry_samples(self, count: int | None = None) -> tuple[FakeTelemetry, ...]:
        """Return a deterministic sequence without changing adapter state.

        If a caller asks for more samples than the fixture contains, the final
        safe reading is held with a deterministic sample number.  There is no
        wall clock or random extension of the fixture.
        """

        if count is None:
            return self._telemetry
        if count < 0:
            raise ValueError("count must be non-negative")
        if count <= len(self._telemetry):
            return self._telemetry[:count]
        last = self._telemetry[-1]
        return self._telemetry + tuple(
            replace(last, sample=index) for index in range(len(self._telemetry), count)
        )

    def observe(self) -> dict[str, Any]:
        """Return the read-only state bundle used by the CLI."""

        frame = self.read_frame()
        return {
            "capabilities": self.capabilities(),
            "status": self.read_status().to_dict(),
            "telemetry": frame.to_dict(),
        }

    def _reject_command(self, *_args: Any, **_kwargs: Any) -> None:
        raise ReadOnlyAdapterError(
            "the fake adapter is offline and read-only; no hardware command was issued"
        )

    # Keep accidental command wiring safe.  These methods never call a
    # transport and always raise before changing adapter state.
    command = _reject_command
    send_command = _reject_command
    execute = _reject_command
    write_velocity = _reject_command
    send_velocity = _reject_command
    move = _reject_command
    stand = _reject_command
    sit = _reject_command
    stop = _reject_command
    power_off = _reject_command


# Short aliases make the adapter easy to discover and preserve room for the
# core ports package to name its concrete adapter differently.
FakeAdapter = FakeRobotAdapter
FakeRobot = FakeRobotAdapter
FakeTelemetryReader = FakeRobotAdapter
Telemetry = FakeTelemetry
Status = FakeStatus


__all__ = [
    "DEFAULT_TELEMETRY",
    "FAKE_ROBOT_ID",
    "FakeAdapter",
    "FakeRobot",
    "FakeTelemetryReader",
    "FakeRobotAdapter",
    "FakeStatus",
    "FakeTelemetry",
    "ReadOnlyAdapterError",
    "Status",
    "Telemetry",
]
