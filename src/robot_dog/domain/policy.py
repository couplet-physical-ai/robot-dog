"""Policy decisions shared by the application safety gate."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DenialReason(StrEnum):
    """Machine-readable reasons for a denied operation."""

    READ_ONLY = "read_only"
    TELEMETRY_INVALID = "telemetry_invalid"
    TELEMETRY_STALE = "telemetry_stale"
    UNKNOWN_CONTROL_OWNER = "unknown_control_owner"
    CONTROL_NOT_OWNED = "control_not_owned"
    INVALID_CONTROL_AUTHORITY = "invalid_control_authority"
    BATTERY_TOO_LOW = "battery_too_low"
    BATTERY_UNAVAILABLE = "battery_unavailable"
    HEALTH_UNSAFE = "health_unsafe"
    CHECKLIST_UNCONFIRMED = "checklist_unconfirmed"
    SESSION_REQUIRED = "session_required"
    SESSION_EXPIRED = "session_expired"
    COMMAND_INVALID = "command_invalid"
    COMMAND_OUT_OF_BOUNDS = "command_out_of_bounds"
    MOTION_WRITER_UNAVAILABLE = "motion_writer_unavailable"
    CLOCK_INVALID = "clock_invalid"


@dataclass(frozen=True)
class PolicyDecision:
    """An auditable allow/deny result; denied operations carry a reason."""

    allowed: bool
    reason: DenialReason | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        if self.allowed and self.reason is not None:
            raise ValueError("an allowed decision cannot have a denial reason")
        if not self.allowed and self.reason is None:
            raise ValueError("a denied decision must have a denial reason")

    @classmethod
    def allow(cls) -> PolicyDecision:
        return cls(allowed=True)

    @classmethod
    def deny(cls, reason: DenialReason, detail: str = "") -> PolicyDecision:
        return cls(allowed=False, reason=reason, detail=detail)
