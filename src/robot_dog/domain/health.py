"""Vendor-neutral robot health values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .errors import InvalidValueError


class HealthStatus(StrEnum):
    """Health information intentionally kept at a vendor-neutral level."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAULTED = "faulted"


@dataclass(frozen=True)
class Health:
    """A typed health value with no interpretation of vendor fault fields."""

    status: HealthStatus

    def __post_init__(self) -> None:
        if not isinstance(self.status, HealthStatus):
            raise InvalidValueError("health status must be a HealthStatus")

    @property
    def is_healthy(self) -> bool:
        return self.status is HealthStatus.HEALTHY


RobotHealth = Health
