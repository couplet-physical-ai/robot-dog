"""Arming checklist and short-lived control sessions."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .authority import ControlAuthority, ControlOwner
from .errors import InvalidValueError


def _finite(value: object, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InvalidValueError(f"{name} must be numeric")
    converted = float(value)
    if not math.isfinite(converted):
        raise InvalidValueError(f"{name} must be finite")
    return converted


@dataclass(frozen=True)
class SafetyChecklist:
    """Explicit confirmations required to create a motion session.

    Both confirmations default to false.  The core does not infer either one
    from telemetry, a UI action, or a vendor mode.
    """

    operator_confirmed: bool = False
    safety_confirmed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.operator_confirmed, bool):
            raise InvalidValueError("operator_confirmed must be bool")
        if not isinstance(self.safety_confirmed, bool):
            raise InvalidValueError("safety_confirmed must be bool")

    @property
    def is_confirmed(self) -> bool:
        return self.operator_confirmed and self.safety_confirmed


@dataclass(frozen=True)
class ArmSession:
    """An expiring application-owned lease for high-level motion writes."""

    session_id: str
    authority: ControlAuthority
    started_at: float
    expires_at: float
    checklist: SafetyChecklist

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise InvalidValueError("session_id must be a non-empty string")
        if not isinstance(self.authority, ControlAuthority):
            raise InvalidValueError("authority must be ControlAuthority")
        if (
            self.authority.owner is not ControlOwner.APPLICATION
            or self.authority.lease_id is None
        ):
            raise InvalidValueError(
                "an ArmSession requires application-owned authority"
            )
        started = _finite(self.started_at, "started_at")
        expires = _finite(self.expires_at, "expires_at")
        if expires <= started:
            raise InvalidValueError("expires_at must be later than started_at")
        object.__setattr__(self, "started_at", started)
        object.__setattr__(self, "expires_at", expires)
        if not isinstance(self.checklist, SafetyChecklist):
            raise InvalidValueError("checklist must be SafetyChecklist")
        if not self.checklist.is_confirmed:
            raise InvalidValueError("an ArmSession requires a confirmed checklist")

    def is_active(self, now: float) -> bool:
        current = _finite(now, "now")
        return self.started_at <= current < self.expires_at


ArmingSession = ArmSession
