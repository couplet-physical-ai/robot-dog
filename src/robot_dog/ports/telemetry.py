"""Read-only telemetry port."""

from __future__ import annotations

from typing import Protocol

from ..domain.telemetry import RobotTelemetry


class TelemetryReader(Protocol):
    """Read one vendor-adapted, application-owned telemetry sample."""

    def read_telemetry(self) -> RobotTelemetry: ...
