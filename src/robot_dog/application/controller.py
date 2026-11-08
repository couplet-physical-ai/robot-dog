"""Application service enforcing the typed safety boundary."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable

from ..domain.authority import ControlAuthority
from ..domain.clock import SystemMonotonicClock
from ..domain.commands import HighLevelVelocityCommand
from ..domain.errors import (
    InvalidValueError,
    MotionWriterUnavailableError,
    error_for_decision,
)
from ..domain.policy import DenialReason, PolicyDecision
from ..domain.safety import ArmSession, SafetyChecklist
from ..domain.telemetry import RobotTelemetry
from ..ports.authority import ControlAuthorityReader
from ..ports.clock import MonotonicClock
from ..ports.motion import MotionWriter
from ..ports.telemetry import TelemetryReader
from .policy import SafetyPolicy


class RobotController:
    """Read telemetry and, only after explicit arming, write one motion stream.

    Constructing this service is read-only: the default policy denies all
    writes, and ``motion_writer`` is optional.  A writable deployment must
    explicitly provide both a writable :class:`SafetyPolicy` and one
    :class:`MotionWriter`.
    """

    def __init__(
        self,
        telemetry_reader: TelemetryReader,
        authority_reader: ControlAuthorityReader,
        motion_writer: MotionWriter | None = None,
        clock: MonotonicClock | None = None,
        policy: SafetyPolicy | None = None,
        session_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not callable(getattr(telemetry_reader, "read_telemetry", None)):
            raise TypeError("telemetry_reader must implement read_telemetry")
        if not callable(getattr(authority_reader, "read_control_authority", None)):
            raise TypeError("authority_reader must implement read_control_authority")
        if motion_writer is not None and not callable(
            getattr(motion_writer, "write_velocity", None)
        ):
            raise TypeError("motion_writer must implement write_velocity")
        if session_id_factory is not None and not callable(session_id_factory):
            raise TypeError("session_id_factory must be callable")
        self._telemetry_reader = telemetry_reader
        self._authority_reader = authority_reader
        self._motion_writer = motion_writer
        self._clock = clock if clock is not None else SystemMonotonicClock()
        self._policy = policy if policy is not None else SafetyPolicy()
        self._session_id_factory = session_id_factory or (lambda: uuid.uuid4().hex)
        self._session: ArmSession | None = None
        self._lock = threading.RLock()

    @property
    def policy(self) -> SafetyPolicy:
        return self._policy

    @property
    def active_session(self) -> ArmSession | None:
        with self._lock:
            return self._session

    def read_telemetry(self) -> RobotTelemetry:
        """Read one sample; this method never writes motion."""

        telemetry = self._telemetry_reader.read_telemetry()
        if not isinstance(telemetry, RobotTelemetry):
            raise InvalidValueError("telemetry reader returned the wrong type")
        return telemetry

    def arm(self, checklist: SafetyChecklist) -> ArmSession:
        """Create a short-lived motion session after every safety check passes."""

        if not isinstance(checklist, SafetyChecklist):
            raise InvalidValueError("checklist must be SafetyChecklist")
        with self._lock:
            now = self._now()
            telemetry = self.read_telemetry()
            authority = self._read_authority()
            decision = self._policy.check_arm(telemetry, authority, checklist, now)
            self._raise_if_denied(decision)
            if self._motion_writer is None:
                raise MotionWriterUnavailableError(
                    PolicyDecision.deny(
                        DenialReason.MOTION_WRITER_UNAVAILABLE,
                        "a writable policy requires one MotionWriter",
                    )
                )
            session = ArmSession(
                session_id=self._session_id_factory(),
                authority=authority,
                started_at=now,
                expires_at=now + self._policy.session_ttl_seconds,
                checklist=checklist,
            )
            self._session = session
            return session

    def send_velocity(self, command: HighLevelVelocityCommand) -> None:
        """Write one bounded high-level command through the sole motion writer."""

        if not isinstance(command, HighLevelVelocityCommand):
            raise InvalidValueError("command must be HighLevelVelocityCommand")
        with self._lock:
            if self._policy.read_only:
                self._raise_if_denied(
                    PolicyDecision.deny(
                        DenialReason.READ_ONLY,
                        "motion writes are disabled by the default read-only policy",
                    )
                )
            now = self._now()
            session = self._session
            if session is None:
                self._raise_if_denied(
                    PolicyDecision.deny(
                        DenialReason.SESSION_REQUIRED,
                        "arm must succeed before a velocity command can be sent",
                    )
                )
            # The local variable is narrowed for type checkers after the guard.
            assert session is not None
            telemetry = self.read_telemetry()
            authority = self._read_authority()
            decision = self._policy.check_velocity(
                telemetry=telemetry,
                authority=authority,
                checklist=session.checklist,
                session=session,
                command=command,
                now=now,
            )
            self._raise_if_denied(decision)
            if self._motion_writer is None:
                raise MotionWriterUnavailableError(
                    PolicyDecision.deny(
                        DenialReason.MOTION_WRITER_UNAVAILABLE,
                        "a writable policy requires one MotionWriter",
                    )
                )
            self._motion_writer.write_velocity(command)

    def disarm(self) -> None:
        """Invalidate the local session without issuing an implicit motion write."""

        with self._lock:
            self._session = None

    def _read_authority(self) -> ControlAuthority:
        authority = self._authority_reader.read_control_authority()
        if not isinstance(authority, ControlAuthority):
            raise InvalidValueError("authority reader returned the wrong type")
        return authority

    def _now(self) -> float:
        try:
            now = self._clock.monotonic()
        except Exception as exc:
            raise InvalidValueError("monotonic clock failed") from exc
        if not isinstance(now, (int, float)) or isinstance(now, bool):
            raise InvalidValueError("monotonic clock returned a non-numeric value")
        return float(now)

    @staticmethod
    def _raise_if_denied(decision: PolicyDecision) -> None:
        if not decision.allowed:
            raise error_for_decision(decision)


RobotControlApplication = RobotController
