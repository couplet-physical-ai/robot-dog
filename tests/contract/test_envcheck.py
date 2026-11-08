"""Contract tests for safe, local-only environment diagnostics."""

from __future__ import annotations

import unittest

from robot_dog.envcheck import collect_environment, format_environment


class EnvironmentCheckContractTests(unittest.TestCase):
    def test_diagnostics_do_not_include_environment_values(self) -> None:
        secret = "do-not-print-this-secret"
        report = collect_environment(
            environ={"ROBOT_DOG_NIC": secret},
            interface_names=("en0",),
            sdk_finder=lambda _name: None,
        )
        rendered = format_environment(report)
        self.assertNotIn(secret, rendered)
        self.assertIn("Configured NIC", rendered)
        self.assertIn("redacted", rendered)

    def test_configured_nic_is_checked_without_sdk_imports(self) -> None:
        report = collect_environment(
            environ={"ROBOT_DOG_NIC": "en0"},
            interface_names=("en0",),
            sdk_finder=lambda _name: None,
        )
        nic = next(check for check in report.checks if check.name == "Configured NIC")
        self.assertEqual(nic.status, "PASS")

    def test_optional_sdk_absence_is_not_a_failure(self) -> None:
        report = collect_environment(sdk_finder=lambda _name: None)
        self.assertFalse(report.failed)


if __name__ == "__main__":
    unittest.main()
