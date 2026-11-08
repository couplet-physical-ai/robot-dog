from __future__ import annotations

import math
import unittest

from robot_dog.domain.authority import ControlAuthority, ControlOwner
from robot_dog.domain.clock import ManualClock
from robot_dog.domain.commands import HighLevelVelocityCommand, VelocityLimits
from robot_dog.domain.errors import InvalidValueError
from robot_dog.domain.health import Health, HealthStatus
from robot_dog.domain.safety import ArmSession, SafetyChecklist
from robot_dog.domain.telemetry import Freshness, FreshnessState, RobotTelemetry


class DomainValueTests(unittest.TestCase):
    def test_telemetry_normalizes_health_status_and_has_bounded_battery(self) -> None:
        telemetry = RobotTelemetry(10, 75, HealthStatus.HEALTHY)
        self.assertEqual(telemetry.observed_at, 10.0)
        self.assertEqual(telemetry.battery_percent, 75.0)
        self.assertEqual(telemetry.health, Health(HealthStatus.HEALTHY))
        self.assertEqual(telemetry.battery_pct, 75.0)

        for battery in (-0.01, 100.01, math.inf, math.nan):
            with self.subTest(battery=battery), self.assertRaises(InvalidValueError):
                RobotTelemetry(10, battery, HealthStatus.HEALTHY)

    def test_missing_battery_and_unknown_health_are_representable_but_not_healthy(
        self,
    ) -> None:
        telemetry = RobotTelemetry(10)
        self.assertIsNone(telemetry.battery_percent)
        self.assertEqual(telemetry.health.status, HealthStatus.UNKNOWN)
        self.assertFalse(telemetry.health.is_healthy)

    def test_telemetry_rejects_non_finite_sample_time_and_bad_health(self) -> None:
        for timestamp in (math.inf, -math.inf, math.nan, True, "10"):
            with (
                self.subTest(timestamp=timestamp),
                self.assertRaises(InvalidValueError),
            ):
                RobotTelemetry(timestamp, 50, HealthStatus.HEALTHY)
        with self.assertRaises(InvalidValueError):
            RobotTelemetry(10, 50, "healthy")  # type: ignore[arg-type]

    def test_freshness_is_deterministic_and_future_samples_are_not_fresh(self) -> None:
        fresh = Freshness.evaluate(observed_at=10, now=10.5, max_age_seconds=1)
        stale = Freshness.evaluate(observed_at=10, now=11.01, max_age_seconds=1)
        future = Freshness.evaluate(observed_at=11, now=10.5, max_age_seconds=1)
        self.assertEqual(fresh.state, FreshnessState.FRESH)
        self.assertTrue(fresh.is_fresh)
        self.assertEqual(stale.state, FreshnessState.STALE)
        self.assertFalse(stale.is_fresh)
        self.assertEqual(future.state, FreshnessState.STALE)
        self.assertEqual(future.age_seconds, -0.5)

        with self.assertRaises(InvalidValueError):
            Freshness.evaluate(0, 0, -1)
        with self.assertRaises(InvalidValueError):
            Freshness.evaluate(math.nan, 0, 1)

    def test_velocity_values_are_finite_and_limits_are_explicit(self) -> None:
        limits = VelocityLimits(
            max_forward_mps=0.5, max_lateral_mps=0.25, max_yaw_rad_s=0.75
        )
        command = HighLevelVelocityCommand(0.5, -0.25, 0.75)
        self.assertTrue(command.within(limits))
        self.assertEqual(command.linear_x_mps, 0.5)
        self.assertEqual(command.angular_z_rad_s, 0.75)
        self.assertTrue(HighLevelVelocityCommand.zero().is_zero)

        for value in (math.inf, -math.inf, math.nan, True, "0.1"):
            with self.subTest(value=value), self.assertRaises(InvalidValueError):
                HighLevelVelocityCommand(value, 0, 0)  # type: ignore[arg-type]
        with self.assertRaises(InvalidValueError):
            VelocityLimits(max_forward_mps=-0.1)
        with self.assertRaises(InvalidValueError):
            command.validate_against(VelocityLimits(max_forward_mps=0.1))

    def test_authority_is_explicit_and_unknown_by_default(self) -> None:
        self.assertEqual(ControlAuthority().owner, ControlOwner.UNKNOWN)
        self.assertFalse(ControlAuthority().is_known)
        self.assertFalse(
            ControlAuthority(ControlOwner.APPLICATION).is_application_owned
        )
        self.assertTrue(ControlAuthority.application("lease-1").is_application_owned)
        with self.assertRaises(InvalidValueError):
            ControlAuthority(ControlOwner.APPLICATION, "  ")

    def test_checklist_and_session_default_to_safe_values(self) -> None:
        checklist = SafetyChecklist()
        self.assertFalse(checklist.is_confirmed)
        with self.assertRaises(InvalidValueError):
            ArmSession(
                "session",
                ControlAuthority.application("lease"),
                0,
                1,
                checklist,
            )

        confirmed = SafetyChecklist(operator_confirmed=True, safety_confirmed=True)
        session = ArmSession(
            "session",
            ControlAuthority.application("lease"),
            0,
            1,
            confirmed,
        )
        self.assertTrue(session.is_active(0))
        self.assertTrue(session.is_active(0.999))
        self.assertFalse(session.is_active(1))

    def test_manual_clock_rejects_backwards_or_non_finite_movement(self) -> None:
        clock = ManualClock(4)
        clock.advance(0.5)
        self.assertEqual(clock.monotonic(), 4.5)
        with self.assertRaises(InvalidValueError):
            clock.advance(-0.1)
        with self.assertRaises(InvalidValueError):
            clock.advance(math.nan)


if __name__ == "__main__":
    unittest.main()
