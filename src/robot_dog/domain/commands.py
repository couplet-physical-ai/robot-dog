"""Bounded, high-level velocity command values."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .errors import InvalidValueError


def _finite_number(value: object, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InvalidValueError(f"{name} must be a real number")
    converted = float(value)
    if not math.isfinite(converted):
        raise InvalidValueError(f"{name} must be finite")
    return converted


@dataclass(frozen=True)
class VelocityLimits:
    """Policy limits for the three high-level planar velocity components."""

    max_forward_mps: float = 1.0
    max_lateral_mps: float = 1.0
    max_yaw_rad_s: float = 1.0

    def __post_init__(self) -> None:
        for name in ("max_forward_mps", "max_lateral_mps", "max_yaw_rad_s"):
            value = _finite_number(getattr(self, name), name)
            if value < 0:
                raise InvalidValueError(f"{name} cannot be negative")
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class HighLevelVelocityCommand:
    """A vendor-neutral planar velocity request.

    Values are in metres per second for translation and radians per second for
    yaw.  The command has no vendor-specific mode, gait, trajectory, or raw
    actuator fields.  A :class:`VelocityLimits` supplied by the application
    policy is required before a writer may receive it.
    """

    forward_mps: float = 0.0
    lateral_mps: float = 0.0
    yaw_rad_s: float = 0.0

    def __post_init__(self) -> None:
        for name in ("forward_mps", "lateral_mps", "yaw_rad_s"):
            object.__setattr__(self, name, _finite_number(getattr(self, name), name))

    @property
    def linear_x_mps(self) -> float:
        """Alias for integrations that use generic planar x terminology."""

        return self.forward_mps

    @property
    def linear_y_mps(self) -> float:
        return self.lateral_mps

    @property
    def angular_z_rad_s(self) -> float:
        return self.yaw_rad_s

    @property
    def is_zero(self) -> bool:
        return (
            self.forward_mps == 0.0
            and self.lateral_mps == 0.0
            and self.yaw_rad_s == 0.0
        )

    def within(self, limits: VelocityLimits) -> bool:
        if not isinstance(limits, VelocityLimits):
            raise InvalidValueError("limits must be VelocityLimits")
        return (
            abs(self.forward_mps) <= limits.max_forward_mps
            and abs(self.lateral_mps) <= limits.max_lateral_mps
            and abs(self.yaw_rad_s) <= limits.max_yaw_rad_s
        )

    def validate_against(self, limits: VelocityLimits) -> None:
        if not self.within(limits):
            raise InvalidValueError("velocity command exceeds configured limits")

    @classmethod
    def zero(cls) -> HighLevelVelocityCommand:
        return cls()


VelocityCommand = HighLevelVelocityCommand
