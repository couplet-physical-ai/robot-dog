"""Vendor-neutral telemetry and freshness values."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from .errors import InvalidValueError
from .health import Health, HealthStatus


class FreshnessState(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    INVALID = "invalid"


@dataclass(frozen=True)
class Freshness:
    """The result of comparing a monotonic sample time with a monotonic now."""

    age_seconds: float
    max_age_seconds: float
    state: FreshnessState

    def __post_init__(self) -> None:
        for name in ("age_seconds", "max_age_seconds"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise InvalidValueError(f"{name} must be numeric")
            if not math.isfinite(float(value)):
                raise InvalidValueError(f"{name} must be finite")
            if value < 0 and name == "max_age_seconds":
                raise InvalidValueError("max_age_seconds cannot be negative")
        if not isinstance(self.state, FreshnessState):
            raise InvalidValueError("state must be a FreshnessState")

    @property
    def is_fresh(self) -> bool:
        return self.state is FreshnessState.FRESH

    @classmethod
    def evaluate(
        cls, observed_at: float, now: float, max_age_seconds: float
    ) -> Freshness:
        for name, value in (
            ("observed_at", observed_at),
            ("now", now),
            ("max_age_seconds", max_age_seconds),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise InvalidValueError(f"{name} must be numeric")
            if not math.isfinite(float(value)):
                raise InvalidValueError(f"{name} must be finite")
        if max_age_seconds < 0:
            raise InvalidValueError("max_age_seconds cannot be negative")
        age = float(now) - float(observed_at)
        state = (
            FreshnessState.FRESH
            if 0.0 <= age <= float(max_age_seconds)
            else FreshnessState.STALE
        )
        return cls(age_seconds=age, max_age_seconds=float(max_age_seconds), state=state)


@dataclass(frozen=True)
class RobotTelemetry:
    """Minimal telemetry required by the safety policy.

    ``observed_at`` is a timestamp from the same monotonic time domain as the
    application's :class:`~robot_dog.ports.clock.MonotonicClock`.  The battery
    value is a percentage in the inclusive range 0..100; ``None`` means the
    adapter could not provide it and is intentionally unsafe for motion.
    ``health`` is a coarse, explicitly typed application value rather than a
    projection of any vendor field.
    """

    observed_at: float
    battery_percent: float | None = None
    health: Health | HealthStatus = Health(HealthStatus.UNKNOWN)

    def __post_init__(self) -> None:
        if not isinstance(self.observed_at, (int, float)) or isinstance(
            self.observed_at, bool
        ):
            raise InvalidValueError("observed_at must be numeric")
        if not math.isfinite(float(self.observed_at)):
            raise InvalidValueError("observed_at must be finite")
        object.__setattr__(self, "observed_at", float(self.observed_at))

        if self.battery_percent is not None:
            if not isinstance(self.battery_percent, (int, float)) or isinstance(
                self.battery_percent, bool
            ):
                raise InvalidValueError("battery_percent must be numeric or None")
            battery = float(self.battery_percent)
            if not math.isfinite(battery):
                raise InvalidValueError("battery_percent must be finite")
            if not 0.0 <= battery <= 100.0:
                raise InvalidValueError("battery_percent must be between 0 and 100")
            object.__setattr__(self, "battery_percent", battery)

        if isinstance(self.health, HealthStatus):
            object.__setattr__(self, "health", Health(self.health))
        elif not isinstance(self.health, Health):
            raise InvalidValueError("health must be Health or HealthStatus")

    @property
    def timestamp(self) -> float:
        """Readable alias for adapters that call the sample time a timestamp."""

        return self.observed_at

    @property
    def battery_pct(self) -> float | None:
        return self.battery_percent

    def freshness(self, now: float, max_age_seconds: float) -> Freshness:
        return Freshness.evaluate(self.observed_at, now, max_age_seconds)


Telemetry = RobotTelemetry
