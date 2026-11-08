"""Hardware-independent safety and control types for robot-dog.

This package deliberately contains no vendor SDK imports.  It defines the
small, typed boundary between an application and a hardware adapter.  The
normal control surface is limited to bounded planar velocity commands; vendor
specific, low-level, and hazardous special motions belong in a separately
reviewed adapter rather than this package.
"""

from .application.controller import RobotController
from .application.policy import SafetyPolicy
from .domain.authority import ControlAuthority, ControlOwner
from .domain.commands import HighLevelVelocityCommand, VelocityCommand, VelocityLimits
from .domain.errors import (
    BatteryTooLowError,
    ChecklistNotConfirmedError,
    CommandInvalidError,
    CommandOutOfBoundsError,
    ControlNotOwnedError,
    HealthUnsafeError,
    InvalidValueError,
    MotionWriterUnavailableError,
    PolicyDeniedError,
    ReadOnlyError,
    SessionExpiredError,
    SessionRequiredError,
    TelemetryStaleError,
    UnknownControlOwnerError,
)
from .domain.health import Health, HealthStatus, RobotHealth
from .domain.policy import DenialReason, PolicyDecision
from .domain.safety import ArmingSession, ArmSession, SafetyChecklist
from .domain.telemetry import (
    Freshness,
    FreshnessState,
    RobotTelemetry,
    Telemetry,
)
from .ports.authority import ControlAuthorityReader
from .ports.clock import MonotonicClock
from .ports.motion import MotionWriter
from .ports.telemetry import TelemetryReader

__all__ = [
    "ArmSession",
    "ArmingSession",
    "BatteryTooLowError",
    "ChecklistNotConfirmedError",
    "CommandOutOfBoundsError",
    "ControlAuthority",
    "ControlAuthorityReader",
    "ControlNotOwnedError",
    "ControlOwner",
    "CommandInvalidError",
    "Freshness",
    "FreshnessState",
    "DenialReason",
    "Health",
    "HealthStatus",
    "HealthUnsafeError",
    "HighLevelVelocityCommand",
    "InvalidValueError",
    "MonotonicClock",
    "MotionWriter",
    "MotionWriterUnavailableError",
    "PolicyDecision",
    "PolicyDeniedError",
    "ReadOnlyError",
    "RobotController",
    "RobotHealth",
    "RobotTelemetry",
    "SafetyChecklist",
    "SafetyPolicy",
    "SessionExpiredError",
    "SessionRequiredError",
    "Telemetry",
    "TelemetryReader",
    "TelemetryStaleError",
    "UnknownControlOwnerError",
    "VelocityCommand",
    "VelocityLimits",
]

__version__ = "0.1.0"
