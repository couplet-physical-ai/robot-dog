"""Offline tests for the full-control Unitree CLI composition root."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from robot_dog.cli import main
from robot_dog.cli.unitree import AdapterFactories


class Result:
    def __init__(self, operation: str, **extra: object) -> None:
        self.operation = operation
        self.extra = extra
        self.value = extra.get("value")

    def to_dict(self) -> dict[str, object]:
        return {"ok": True, "operation": self.operation, **self.extra}


class FakeSport:
    def __init__(self, calls: list[object], **kwargs: object) -> None:
        calls.append(("sport_factory", kwargs))
        self.calls = calls

    def invoke(self, action: str, *args: object, **kwargs: object) -> Result:
        self.calls.append(("invoke", action, args, kwargs))
        return Result("sport_invoke", action=action, args=list(args), kwargs=kwargs)

    def run_bounded_move(self, *args: object, **kwargs: object) -> Result:
        self.calls.append(("bounded_move", args, kwargs))
        return Result("bounded_move")

    def close(self) -> None:
        self.calls.append(("sport_close",))


class FakeAuthority:
    def __init__(self, calls: list[object], **kwargs: object) -> None:
        calls.append(("authority_factory", kwargs))
        self.calls = calls

    def read_service_list(self, **kwargs: object) -> Result:
        self.calls.append(("service_list", kwargs))
        return Result("service_list")

    def switch_service(self, *args: object, **kwargs: object) -> Result:
        self.calls.append(("service_switch", args, kwargs))
        return Result("service_switch")

    def set_report_frequency(self, *args: object, **kwargs: object) -> Result:
        self.calls.append(("report_frequency", args, kwargs))
        return Result("report_frequency")

    def check_mode(self, **kwargs: object) -> Result:
        self.calls.append(("check_mode", kwargs))
        return Result("check_mode")

    def select_mode(self, *args: object, **kwargs: object) -> Result:
        self.calls.append(("select_mode", args, kwargs))
        return Result("select_mode")

    def release_mode(self, **kwargs: object) -> Result:
        self.calls.append(("release_mode", kwargs))
        return Result("release_mode")

    def close(self) -> None:
        self.calls.append(("authority_close",))


class FakeVideo:
    def get_image_sample(self, **kwargs: object) -> Result:
        return Result("video_capture", value=b"fake-image")


class FakeVui:
    def get_volume(self, **kwargs: object) -> Result:
        return Result("vui_get_volume")

    def set_volume(self, *args: object, **kwargs: object) -> Result:
        return Result("vui_set_volume", args=list(args), kwargs=kwargs)


class FakeObstacles:
    def move_to_increment_position(self, *args: object, **kwargs: object) -> Result:
        return Result("obstacles_move_increment", args=list(args), kwargs=kwargs)


class FakePeripherals:
    def __init__(self, calls: list[object], **kwargs: object) -> None:
        calls.append(("peripherals_factory", kwargs))
        self.video = FakeVideo()
        self.vui = FakeVui()
        self.obstacles = FakeObstacles()

    def close(self) -> None:
        pass


class FakeLowLevel:
    def __init__(self, calls: list[object], **kwargs: object) -> None:
        calls.append(("low_level_factory", kwargs))
        self.calls = calls

    def publish_once(self, commands: object, **kwargs: object) -> None:
        self.calls.append(("publish_once", commands, kwargs))

    def publish_timed(self, commands: object, **kwargs: object) -> Result:
        self.calls.append(("publish_timed", commands, kwargs))
        return Result("low_level_publish_timed")

    def close(self) -> None:
        self.calls.append(("low_level_close",))


class UnitreeCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list[object] = []
        self.factories = AdapterFactories(
            sport_client=lambda **kwargs: FakeSport(self.calls, **kwargs),
            authority=lambda **kwargs: FakeAuthority(self.calls, **kwargs),
            peripherals=lambda **kwargs: FakePeripherals(self.calls, **kwargs),
            low_level=lambda **kwargs: FakeLowLevel(self.calls, **kwargs),
        )

    def run_cli(self, *argv: str) -> tuple[int, str]:
        stream = io.StringIO()
        with patch("robot_dog.cli.unitree.DEFAULT_FACTORIES", self.factories):
            code = main(argv, stream=stream)
        return code, stream.getvalue()

    def common(self) -> tuple[str, ...]:
        return (
            "--interface",
            "fake0",
            "--domain-id",
            "7",
            "--hardware-enabled",
        )

    def test_catalog_needs_no_runtime_configuration_or_factory(self) -> None:
        code, output = self.run_cli("unitree", "catalog", "--json")
        self.assertEqual(code, 0)
        entries = json.loads(output)
        self.assertIn("FrontFlip", {entry["name"] for entry in entries})
        self.assertEqual(self.calls, [])

    def test_generic_sport_invocation_forwards_json_and_all_gates(self) -> None:
        code, output = self.run_cli(
            "unitree",
            "invoke",
            "stand_up",
            "--args",
            "[]",
            "--kwargs",
            '{"unused": 1}',
            *self.common(),
            "--operator-acknowledged",
            "--intentional",
        )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output)["ok"])
        invocation = next(call for call in self.calls if call[0] == "invoke")
        self.assertEqual(invocation[1], "stand_up")
        self.assertEqual(invocation[2], ())
        self.assertEqual(invocation[3]["intentional"], True)
        factory = self.calls[0][1]
        self.assertEqual(factory["network_interface"], "fake0")
        self.assertEqual(factory["domain_id"], 7)
        self.assertTrue(factory["hardware_enabled"])
        self.assertTrue(factory["operator_acknowledged"])

    def test_authority_mutation_forwards_exact_target_confirmation(self) -> None:
        code, _ = self.run_cli(
            "unitree",
            "service",
            "switch",
            "sport_mode",
            "--enabled",
            "false",
            *self.common(),
            "--operator-acknowledged",
            "--target-id",
            "robot-test",
            "--confirm",
            "robot-test",
        )
        self.assertEqual(code, 0)
        switch = next(call for call in self.calls if call[0] == "service_switch")
        self.assertEqual(switch[1], ("sport_mode", False))
        self.assertEqual(switch[2]["target_id"], "robot-test")
        self.assertEqual(switch[2]["confirm"], "robot-test")

    def test_peripheral_and_bounded_surfaces_are_factory_injectable(self) -> None:
        code, _ = self.run_cli("unitree", "vui", "get", "volume", *self.common())
        self.assertEqual(code, 0)
        code, _ = self.run_cli(
            "unitree",
            "obstacles",
            "move-increment",
            "1",
            "2",
            "3",
            *self.common(),
            "--operator-acknowledged",
        )
        self.assertEqual(code, 0)
        code, _ = self.run_cli(
            "unitree",
            "move",
            "0.1",
            "0",
            "0",
            "--duration",
            "0.5",
            "--session-id",
            "test-session",
            *self.common(),
            "--operator-acknowledged",
        )
        self.assertEqual(code, 0)
        self.assertTrue(any(call[0] == "bounded_move" for call in self.calls))

    def test_low_level_file_requires_exactly_twelve_records_and_forwards_gates(
        self,
    ) -> None:
        records = [
            {"q": 0, "dq": 0, "kp": 0, "kd": 0, "tau": 0, "mode": 1} for _ in range(12)
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "commands.json"
            path.write_text(json.dumps(records), encoding="utf-8")
            code, output = self.run_cli(
                "unitree",
                "low-level",
                "once",
                str(path),
                *self.common(),
                "--operator-confirmed",
                "--expert-low-level-confirmed",
                "--robot-restrained-confirmed",
                "--motion-service-released",
                "--motion-ownership-confirmed",
                "--json",
            )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output)["ok"])
        factory_call = next(
            call for call in self.calls if call[0] == "low_level_factory"
        )
        self.assertTrue(factory_call[1]["motion_service_released"])
        publish = next(call for call in self.calls if call[0] == "publish_once")
        self.assertEqual(len(publish[1]), 12)

    def test_video_capture_uses_the_injected_peripheral_factory(self) -> None:
        code, output = self.run_cli(
            "unitree",
            "video",
            "--output",
            "/tmp/robot-dog-test-image.bin",
            *self.common(),
        )
        self.assertEqual(code, 0)
        self.assertIn("video_capture", output)


if __name__ == "__main__":
    unittest.main()
