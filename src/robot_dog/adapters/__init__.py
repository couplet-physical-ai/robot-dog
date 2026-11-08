"""Adapters that are safe to use without a robot or vendor dependencies."""

from .fake import (
    DEFAULT_TELEMETRY,
    FAKE_ROBOT_ID,
    FakeAdapter,
    FakeRobot,
    FakeRobotAdapter,
    FakeStatus,
    FakeTelemetry,
    FakeTelemetryReader,
    ReadOnlyAdapterError,
    Status,
    Telemetry,
)

__all__ = [
    "DEFAULT_TELEMETRY",
    "FAKE_ROBOT_ID",
    "FakeAdapter",
    "FakeRobot",
    "FakeRobotAdapter",
    "FakeStatus",
    "FakeTelemetry",
    "FakeTelemetryReader",
    "ReadOnlyAdapterError",
    "Status",
    "Telemetry",
]
