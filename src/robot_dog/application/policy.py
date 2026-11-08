"""Explicit deny-by-default motion policy."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..domain.authority import ControlAuthority, ControlOwner
from ..domain.commands import HighLevelVelocityCommand, VelocityLimits
from ..domain.health import Health, HealthStatus
from ..domain.policy import DenialReason, PolicyDecision
from ..domain.safety import ArmSession, SafetyChecklist
from ..domain.telemetry import RobotTelemetry


@dataclass(frozen=True)
class SafetyPolicy:
    """The complete gate for arming and high-level velocity writes.

    ``read_only`` intentionally defaults to true.  A caller must opt into a
    writable policy and still satisfy every other gate.  The bounds here are
    application policy, not claims about a particular robot's capabilities.
    """

    read_only: bool = True
    max_telemetry_age_seconds: float = 1.0
    minimum_battery_percent: float = 20.0
    velocity_limits: VelocityLimits = field(default_factory=VelocityLimits)
    session_ttl_seconds: float = 30.0
    permitted_health: frozenset[HealthStatus] = field(
        default_factory=lambda: frozenset((HealthStatus.HEALTHY,))
    )

    def __post_init__(self) -> None:
        if not isinstance(self.read_only, bool):
            raise ValueError("read_only must be bool")
        for name in (
            "max_telemetry_age_seconds",
            "minimum_battery_percent",
            "session_ttl_seconds",
        ):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"{name} must be numeric")
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if self.max_telemetry_age_seconds < 0:
            raise ValueError("max_telemetry_age_seconds cannot be negative")
        if not 0.0 <= self.minimum_battery_percent <= 100.0:
            raise ValueError("minimum_battery_percent must be between 0 and 100")
        if self.session_ttl_seconds <= 0:
            raise ValueError("session_ttl_seconds must be positive")
        if not isinstance(self.velocity_limits, VelocityLimits):
            raise ValueError("velocity_limits must be VelocityLimits")
        if not isinstance(self.permitted_health, frozenset):
            object.__setattr__(
                self, "permitted_health", frozenset(self.permitted_health)
            )
        if any(
            not isinstance(status, HealthStatus) for status in self.permitted_health
        ):
            raise ValueError("permitted_health must contain HealthStatus values")
        # Keep normalized floats so decisions do not depend on int/float input.
        object.__setattr__(
            self, "max_telemetry_age_seconds", float(self.max_telemetry_age_seconds)
        )
        object.__setattr__(
            self, "minimum_battery_percent", float(self.minimum_battery_percent)
        )
        object.__setattr__(self, "session_ttl_seconds", float(self.session_ttl_seconds))

    def check_arm(
        self,
        telemetry: RobotTelemetry,
        authority: ControlAuthority,
        checklist: SafetyChecklist,
        now: float,
    ) -> PolicyDecision:
        """Evaluate all conditions required to create an arming session."""

        if self.read_only:
            return PolicyDecision.deny(
                DenialReason.READ_ONLY,
                "motion writes are disabled by the default read-only policy",
            )
        base = self._check_telemetry(telemetry, now)
        if not base.allowed:
            return base
        owner = self._check_authority(authority)
        if not owner.allowed:
            return owner
        battery = self._check_battery(telemetry)
        if not battery.allowed:
            return battery
        health = self._check_health(telemetry)
        if not health.allowed:
            return health
        checklist_result = self._check_checklist(checklist)
        if not checklist_result.allowed:
            return checklist_result
        return PolicyDecision.allow()

    def check_velocity(
        self,
        telemetry: RobotTelemetry,
        authority: ControlAuthority,
        checklist: SafetyChecklist,
        session: ArmSession,
        command: HighLevelVelocityCommand,
        now: float,
    ) -> PolicyDecision:
        """Evaluate all conditions immediately before a velocity write."""

        if self.read_only:
            return PolicyDecision.deny(
                DenialReason.READ_ONLY,
                "motion writes are disabled by the default read-only policy",
            )
        if not isinstance(session, ArmSession):
            return PolicyDecision.deny(
                DenialReason.SESSION_REQUIRED, "an arming session is required"
            )
        try:
            active = session.is_active(now)
        except (TypeError, ValueError):
            return PolicyDecision.deny(
                DenialReason.CLOCK_INVALID, "monotonic clock value is invalid"
            )
        if not active:
            return PolicyDecision.deny(
                DenialReason.SESSION_EXPIRED, "arming session has expired"
            )

        base = self._check_telemetry(telemetry, now)
        if not base.allowed:
            return base
        owner = self._check_authority(authority)
        if not owner.allowed:
            return owner
        if authority != session.authority:
            return PolicyDecision.deny(
                DenialReason.CONTROL_NOT_OWNED,
                "current control authority differs from the arming session",
            )
        battery = self._check_battery(telemetry)
        if not battery.allowed:
            return battery
        health = self._check_health(telemetry)
        if not health.allowed:
            return health
        checklist_result = self._check_checklist(checklist)
        if not checklist_result.allowed:
            return checklist_result
        if not isinstance(command, HighLevelVelocityCommand):
            return PolicyDecision.deny(
                DenialReason.COMMAND_INVALID,
                "only HighLevelVelocityCommand is accepted by the motion port",
            )
        try:
            in_bounds = command.within(self.velocity_limits)
        except (TypeError, ValueError):
            return PolicyDecision.deny(
                DenialReason.COMMAND_INVALID, "velocity command is invalid"
            )
        if not in_bounds:
            return PolicyDecision.deny(
                DenialReason.COMMAND_OUT_OF_BOUNDS,
                "velocity command exceeds the configured policy limits",
            )
        return PolicyDecision.allow()

    def _check_telemetry(self, telemetry: RobotTelemetry, now: float) -> PolicyDecision:
        if not isinstance(telemetry, RobotTelemetry):
            return PolicyDecision.deny(
                DenialReason.TELEMETRY_INVALID, "telemetry has the wrong type"
            )
        try:
            freshness = telemetry.freshness(now, self.max_telemetry_age_seconds)
        except (TypeError, ValueError):
            return PolicyDecision.deny(
                DenialReason.TELEMETRY_INVALID, "telemetry freshness is invalid"
            )
        if not freshness.is_fresh:
            return PolicyDecision.deny(
                DenialReason.TELEMETRY_STALE,
                (
                    f"telemetry age {freshness.age_seconds:.3f}s exceeds the "
                    f"{freshness.max_age_seconds:.3f}s limit"
                ),
            )
        return PolicyDecision.allow()

    @staticmethod
    def _check_authority(authority: ControlAuthority) -> PolicyDecision:
        if not isinstance(authority, ControlAuthority):
            return PolicyDecision.deny(
                DenialReason.UNKNOWN_CONTROL_OWNER,
                "control authority is unavailable",
            )
        if authority.owner is ControlOwner.UNKNOWN:
            return PolicyDecision.deny(
                DenialReason.UNKNOWN_CONTROL_OWNER,
                "motion is denied when the control owner is unknown",
            )
        if (
            authority.owner is not ControlOwner.APPLICATION
            or authority.lease_id is None
        ):
            return PolicyDecision.deny(
                DenialReason.CONTROL_NOT_OWNED,
                "the application does not own the current control authority",
            )
        return PolicyDecision.allow()

    def _check_battery(self, telemetry: RobotTelemetry) -> PolicyDecision:
        if telemetry.battery_percent is None:
            return PolicyDecision.deny(
                DenialReason.BATTERY_UNAVAILABLE,
                "battery percentage is unavailable",
            )
        if telemetry.battery_percent < self.minimum_battery_percent:
            return PolicyDecision.deny(
                DenialReason.BATTERY_TOO_LOW,
                "battery percentage is below the configured motion threshold",
            )
        return PolicyDecision.allow()

    def _check_health(self, telemetry: RobotTelemetry) -> PolicyDecision:
        health = telemetry.health
        status = health.status if isinstance(health, Health) else health
        if status not in self.permitted_health:
            return PolicyDecision.deny(
                DenialReason.HEALTH_UNSAFE,
                "telemetry health is not explicitly permitted by policy",
            )
        return PolicyDecision.allow()

    @staticmethod
    def _check_checklist(checklist: SafetyChecklist) -> PolicyDecision:
        if not isinstance(checklist, SafetyChecklist) or not checklist.is_confirmed:
            return PolicyDecision.deny(
                DenialReason.CHECKLIST_UNCONFIRMED,
                "operator and safety checklist confirmation is required",
            )
        return PolicyDecision.allow()
