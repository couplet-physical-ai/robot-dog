from __future__ import annotations

import math
import unittest

from robot_dog.application.controller import RobotController
from robot_dog.application.policy import SafetyPolicy
from robot_dog.domain.authority import ControlAuthority, ControlOwner
from robot_dog.domain.clock import ManualClock
from robot_dog.domain.commands import HighLevelVelocityCommand, VelocityLimits
from robot_dog.domain.errors import (
    BatteryTooLowError,
    ChecklistNotConfirmedError,
    CommandOutOfBoundsError,
    ControlNotOwnedError,
    HealthUnsafeError,
    InvalidValueError,
    ReadOnlyError,
    SessionExpiredError,
    SessionRequiredError,
    TelemetryStaleError,
    UnknownControlOwnerError,
)
from robot_dog.domain.health import HealthStatus
from robot_dog.domain.safety import SafetyChecklist
from robot_dog.domain.telemetry import RobotTelemetry


class _Telemetry:
    def __init__(self, value: RobotTelemetry) -> None:
        self.value = value

    def read_telemetry(self) -> RobotTelemetry:
        return self.value


class _Authority:
    def __init__(self, value: ControlAuthority) -> None:
        self.value = value

    def read_control_authority(self) -> ControlAuthority:
        return self.value


class _Writer:
    def __init__(self) -> None:
        self.commands: list[HighLevelVelocityCommand] = []

    def write_velocity(self, command: HighLevelVelocityCommand) -> None:
        self.commands.append(command)


def _policy(**kwargs: object) -> SafetyPolicy:
    values: dict[str, object] = {
        "read_only": False,
        "max_telemetry_age_seconds": 1.0,
        "minimum_battery_percent": 20.0,
        "session_ttl_seconds": 5.0,
        "velocity_limits": VelocityLimits(0.5, 0.25, 0.75),
    }
    values.update(kwargs)
    return SafetyPolicy(**values)  # type: ignore[arg-type]


def _controller(
    telemetry: RobotTelemetry | None = None,
    authority: ControlAuthority | None = None,
    writer: _Writer | None = None,
    policy: SafetyPolicy | None = None,
    clock: ManualClock | None = None,
) -> tuple[RobotController, _Telemetry, _Authority, _Writer, ManualClock]:
    telemetry_reader = _Telemetry(
        telemetry or RobotTelemetry(0, 80, HealthStatus.HEALTHY)
    )
    authority_reader = _Authority(authority or ControlAuthority.application("lease-1"))
    motion_writer = writer or _Writer()
    manual_clock = clock or ManualClock(0)
    controller = RobotController(
        telemetry_reader,
        authority_reader,
        motion_writer,
        manual_clock,
        policy or _policy(),
        session_id_factory=lambda: "session-1",
    )
    return controller, telemetry_reader, authority_reader, motion_writer, manual_clock


class SafetyGateTests(unittest.TestCase):
    def test_default_controller_is_read_only_and_read_telemetry_has_no_write(
        self,
    ) -> None:
        controller, _, _, writer, _ = _controller(policy=SafetyPolicy())
        self.assertEqual(controller.read_telemetry().battery_percent, 80.0)
        with self.assertRaises(ReadOnlyError):
            controller.arm(SafetyChecklist(True, True))
        with self.assertRaises(ReadOnlyError):
            controller.send_velocity(HighLevelVelocityCommand.zero())
        self.assertEqual(writer.commands, [])

    def test_arm_requires_every_explicit_gate(self) -> None:
        cases = (
            (ControlAuthority(), SafetyChecklist(True, True), UnknownControlOwnerError),
            (
                ControlAuthority(ControlOwner.OPERATOR, "operator-lease"),
                SafetyChecklist(True, True),
                ControlNotOwnedError,
            ),
            (
                ControlAuthority.application("lease-1"),
                SafetyChecklist(),
                ChecklistNotConfirmedError,
            ),
        )
        for authority, checklist, expected in cases:
            with self.subTest(expected=expected.__name__):
                controller, _, _, writer, _ = _controller(authority=authority)
                with self.assertRaises(expected):
                    controller.arm(checklist)
                self.assertEqual(writer.commands, [])

    def test_stale_telemetry_is_rejected_before_motion(self) -> None:
        controller, telemetry, _, writer, clock = _controller(
            telemetry=RobotTelemetry(0, 80, HealthStatus.HEALTHY)
        )
        clock.advance(1.001)
        with self.assertRaises(TelemetryStaleError):
            controller.arm(SafetyChecklist(True, True))
        self.assertEqual(writer.commands, [])
        telemetry.value = RobotTelemetry(clock.monotonic(), 80, HealthStatus.HEALTHY)
        session = controller.arm(SafetyChecklist(True, True))
        self.assertEqual(session.session_id, "session-1")

    def test_low_battery_and_unhealthy_state_are_rejected(self) -> None:
        for telemetry, expected in (
            (RobotTelemetry(0, 19.99, HealthStatus.HEALTHY), BatteryTooLowError),
            (RobotTelemetry(0, None, HealthStatus.HEALTHY), BatteryTooLowError),
            (RobotTelemetry(0, 80, HealthStatus.DEGRADED), HealthUnsafeError),
            (RobotTelemetry(0, 80, HealthStatus.UNKNOWN), HealthUnsafeError),
        ):
            with self.subTest(expected=expected.__name__):
                controller, _, _, writer, _ = _controller(telemetry=telemetry)
                with self.assertRaises(expected):
                    controller.arm(SafetyChecklist(True, True))
                self.assertEqual(writer.commands, [])

    def test_valid_session_sends_only_one_high_level_command(self) -> None:
        controller, _, _, writer, _ = _controller()
        session = controller.arm(SafetyChecklist(True, True))
        command = HighLevelVelocityCommand(0.5, -0.25, 0.75)
        self.assertIs(controller.active_session, session)
        controller.send_velocity(command)
        self.assertEqual(writer.commands, [command])

    def test_out_of_bounds_command_is_rejected_without_writer_call(self) -> None:
        controller, _, _, writer, _ = _controller()
        controller.arm(SafetyChecklist(True, True))
        with self.assertRaises(CommandOutOfBoundsError):
            controller.send_velocity(HighLevelVelocityCommand(0.5001, 0, 0))
        self.assertEqual(writer.commands, [])

    def test_session_is_expiring_and_disarm_is_write_free(self) -> None:
        controller, _, _, writer, clock = _controller()
        controller.arm(SafetyChecklist(True, True))
        controller.disarm()
        with self.assertRaises(SessionRequiredError):
            controller.send_velocity(HighLevelVelocityCommand.zero())
        self.assertEqual(writer.commands, [])

        controller.arm(SafetyChecklist(True, True))
        clock.advance(5)
        with self.assertRaises(SessionExpiredError):
            controller.send_velocity(HighLevelVelocityCommand.zero())
        self.assertEqual(writer.commands, [])

    def test_authority_is_rechecked_for_each_write(self) -> None:
        controller, _, authority, writer, _ = _controller()
        controller.arm(SafetyChecklist(True, True))
        authority.value = ControlAuthority(ControlOwner.OPERATOR, "operator-lease")
        with self.assertRaises(ControlNotOwnedError):
            controller.send_velocity(HighLevelVelocityCommand(0.1, 0, 0))
        self.assertEqual(writer.commands, [])

    def test_policy_can_be_configured_but_invalid_policy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SafetyPolicy(minimum_battery_percent=101)
        with self.assertRaises(ValueError):
            SafetyPolicy(max_telemetry_age_seconds=math.inf)
        with self.assertRaises(ValueError):
            SafetyPolicy(session_ttl_seconds=0)

    def test_read_only_controller_without_writer_never_needs_a_motion_port(
        self,
    ) -> None:
        controller, _, _, _, _ = _controller(policy=SafetyPolicy())
        self.assertEqual(
            controller.read_telemetry().health.status, HealthStatus.HEALTHY
        )
        self.assertIsNone(controller.active_session)

    def test_invalid_reader_values_fail_closed(self) -> None:
        controller, telemetry, _, writer, _ = _controller()
        telemetry.value = "not telemetry"  # type: ignore[assignment]
        with self.assertRaises(InvalidValueError):
            controller.arm(SafetyChecklist(True, True))
        self.assertEqual(writer.commands, [])


if __name__ == "__main__":
    unittest.main()
