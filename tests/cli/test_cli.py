"""CLI tests that require no robot, SDK, ROS, or network."""

from __future__ import annotations

import io
import json
import unittest

from robot_dog.cli import main


class CliTests(unittest.TestCase):
    def run_cli(self, *argv: str) -> tuple[int, str]:
        stream = io.StringIO()
        code = main(argv, stream=stream)
        return code, stream.getvalue()

    def test_demo_is_deterministic_and_read_only(self) -> None:
        first = self.run_cli("demo")
        second = self.run_cli("demo")
        self.assertEqual(first, second)
        self.assertEqual(first[0], 0)
        self.assertIn("deterministic fake", first[1])
        self.assertIn("hardware commands: no", first[1])

    def test_demo_json_is_machine_readable(self) -> None:
        code, output = self.run_cli("demo", "--json")
        payload = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(payload["mode"], "offline-fake")
        self.assertEqual(len(payload["telemetry"]), 3)

    def test_capabilities_and_status_are_clear(self) -> None:
        code, capabilities = self.run_cli("capabilities")
        self.assertEqual(code, 0)
        self.assertIn("hardware commands", capabilities)
        code, status = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertIn("read-only", status)

    def test_negative_frame_count_is_rejected_without_side_effects(self) -> None:
        code, output = self.run_cli("demo", "--frames", "-1")
        self.assertEqual(code, 2)
        self.assertIn("must be non-negative", output)


if __name__ == "__main__":
    unittest.main()
