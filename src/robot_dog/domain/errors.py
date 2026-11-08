"""Errors raised when the safety boundary denies an operation."""

from __future__ import annotations

from .policy import DenialReason, PolicyDecision


class RobotCoreError(Exception):
    """Base class for errors from the hardware-independent core."""


class InvalidValueError(ValueError, RobotCoreError):
    """A value cannot safely cross the typed core boundary."""


class PolicyDeniedError(RobotCoreError):
    """The explicit safety policy denied an operation."""

    def __init__(self, decision: PolicyDecision):
        if decision.allowed or decision.reason is None:
            raise ValueError("a denied decision is required")
        self.decision = decision
        message = decision.detail or decision.reason.value
        super().__init__(message)


class ReadOnlyError(PolicyDeniedError):
    """A write was attempted while the default read-only policy is active."""


class TelemetryStaleError(PolicyDeniedError):
    """The telemetry sample is older than the policy permits."""


class UnknownControlOwnerError(PolicyDeniedError):
    """The current control owner is unknown."""


class ControlNotOwnedError(PolicyDeniedError):
    """The application does not hold the current control authority."""


class BatteryTooLowError(PolicyDeniedError):
    """The battery is below the configured motion threshold or unavailable."""


class HealthUnsafeError(PolicyDeniedError):
    """The health state is not explicitly permitted for motion."""


class ChecklistNotConfirmedError(PolicyDeniedError):
    """The operator and safety checklist was not explicitly confirmed."""


class SessionRequiredError(PolicyDeniedError):
    """A valid arming session is required before a command can be sent."""


class SessionExpiredError(PolicyDeniedError):
    """The arming session is no longer active."""


class CommandOutOfBoundsError(PolicyDeniedError):
    """A velocity command exceeds the configured policy limits."""


class CommandInvalidError(PolicyDeniedError):
    """A velocity command contains a value the policy cannot accept."""


class MotionWriterUnavailableError(PolicyDeniedError):
    """No single high-level motion writer was supplied for a write operation."""


class ClockInvalidError(RobotCoreError):
    """The monotonic clock returned a non-finite value."""


# Kept as a type alias for callers that want to catch all policy failures while
# retaining the more specific exception classes above.
PolicyFailure = PolicyDeniedError


_ERROR_BY_REASON = {
    DenialReason.READ_ONLY: ReadOnlyError,
    DenialReason.TELEMETRY_STALE: TelemetryStaleError,
    DenialReason.UNKNOWN_CONTROL_OWNER: UnknownControlOwnerError,
    DenialReason.CONTROL_NOT_OWNED: ControlNotOwnedError,
    DenialReason.BATTERY_TOO_LOW: BatteryTooLowError,
    DenialReason.BATTERY_UNAVAILABLE: BatteryTooLowError,
    DenialReason.HEALTH_UNSAFE: HealthUnsafeError,
    DenialReason.CHECKLIST_UNCONFIRMED: ChecklistNotConfirmedError,
    DenialReason.SESSION_REQUIRED: SessionRequiredError,
    DenialReason.SESSION_EXPIRED: SessionExpiredError,
    DenialReason.COMMAND_OUT_OF_BOUNDS: CommandOutOfBoundsError,
    DenialReason.COMMAND_INVALID: CommandInvalidError,
    DenialReason.MOTION_WRITER_UNAVAILABLE: MotionWriterUnavailableError,
}


def error_for_decision(decision: PolicyDecision) -> PolicyDeniedError:
    """Turn a denied decision into its stable, specific exception type."""

    if decision.allowed or decision.reason is None:
        raise ValueError("a denied decision is required")
    error_type = _ERROR_BY_REASON.get(decision.reason, PolicyDeniedError)
    return error_type(decision)
