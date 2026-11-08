"""Contract tests for the offline fake adapter."""

from __future__ import annotations

import unittest

from robot_dog.adapters import FakeRobotAdapter, ReadOnlyAdapterError
from robot_dog.domain.telemetry import RobotTelemetry


class FakeAdapterContractTests(unittest.TestCase):
    def test_is_offline_and_read_only(self) -> None:
        adapter = FakeRobotAdapter()
        capabilities = adapter.capabilities()
        self.assertTrue(capabilities["offline"])
        self.assertTrue(capabilities["read_only"])
        self.assertFalse(capabilities["hardware_commands"])
        self.assertFalse(capabilities["network_access"])

    def test_telemetry_is_deterministic(self) -> None:
        first = FakeRobotAdapter().telemetry_samples()
        second = FakeRobotAdapter().telemetry_samples()
        self.assertEqual(first, second)
        self.assertEqual([frame.sample for frame in first], [0, 1, 2])

    def test_read_telemetry_implements_typed_port(self) -> None:
        adapter = FakeRobotAdapter()
        first = adapter.read_telemetry()
        second = adapter.read_telemetry()
        third = adapter.read_telemetry()
        held = adapter.read_telemetry()
        self.assertIsInstance(first, RobotTelemetry)
        self.assertEqual(first.observed_at, 0.0)
        self.assertEqual(second.observed_at, 1.0)
        self.assertEqual(third.observed_at, 2.0)
        self.assertEqual(held.observed_at, 2.0)

    def test_commands_fail_before_doing_anything(self) -> None:
        adapter = FakeRobotAdapter()
        with self.assertRaises(ReadOnlyAdapterError):
            adapter.send_command("stand")
        self.assertEqual(adapter.read_telemetry().observed_at, 0.0)


if __name__ == "__main__":
    unittest.main()
