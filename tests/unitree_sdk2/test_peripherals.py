"""Offline contract tests for Unitree SDK2 peripheral access."""

from __future__ import annotations

import importlib
from types import ModuleType

import pytest

from robot_dog.adapters.unitree_sdk2.peripherals import (
    AuthoritySafetyAcknowledgements,
    UnitreeSdk2ObstaclesAvoidClient,
    UnitreeSdk2PeripheralBindings,
    UnitreeSdk2PeripheralError,
    UnitreeSdk2Peripherals,
    UnitreeSdk2SafetyError,
    UnitreeSdk2VideoClient,
    UnitreeSdk2VuiClient,
)


class FakeVideoClient:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        events.append(("video-client", None))
        self.events = events

    def Init(self) -> None:
        self.events.append(("video-init", None))

    def GetImageSample(self):
        self.events.append(("image", None))
        return 0, [0, 1, 2, 255]


class FakeVuiClient:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        events.append(("vui-client", None))
        self.events = events

    def Init(self) -> None:
        self.events.append(("vui-init", None))

    def GetSwitch(self):
        self.events.append(("vui-get-switch", None))
        return 0, True

    def SetSwitch(self, enabled: int) -> int:
        self.events.append(("vui-set-switch", enabled))
        return 0

    def GetVolume(self):
        self.events.append(("vui-get-volume", None))
        return 0, 7

    def SetVolume(self, level: int) -> int:
        self.events.append(("vui-set-volume", level))
        return 0

    def GetBrightness(self):
        self.events.append(("vui-get-brightness", None))
        return 0, 9

    def SetBrightness(self, level: int) -> int:
        self.events.append(("vui-set-brightness", level))
        return 0


class FakeObstaclesClient:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        events.append(("obstacles-client", None))
        self.events = events

    def Init(self) -> None:
        self.events.append(("obstacles-init", None))

    def SwitchGet(self):
        self.events.append(("obstacles-get-switch", None))
        return 0, False

    def SwitchSet(self, enabled: bool) -> int:
        self.events.append(("obstacles-set-switch", enabled))
        return 0

    def Move(self, vx: float, vy: float, vyaw: float) -> int:
        self.events.append(("move", (vx, vy, vyaw)))
        return 0

    def MoveToAbsolutePosition(self, vx: float, vy: float, vyaw: float) -> int:
        self.events.append(("move-absolute", (vx, vy, vyaw)))
        return 0

    def MoveToIncrementPosition(self, vx: float, vy: float, vyaw: float) -> int:
        self.events.append(("move-increment", (vx, vy, vyaw)))
        return 0

    def UseRemoteCommandFromApi(self, enabled: bool) -> int:
        self.events.append(("remote-api", enabled))
        return 0


def fake_bindings(events: list[tuple[str, object]]) -> UnitreeSdk2PeripheralBindings:
    def initialize(domain_id: int, interface: str) -> None:
        events.append(("factory", (domain_id, interface)))

    return UnitreeSdk2PeripheralBindings(
        channel_factory_initialize=initialize,
        video_client=lambda: FakeVideoClient(events),
        vui_client=lambda: FakeVuiClient(events),
        obstacles_avoid_client=lambda: FakeObstaclesClient(events),
    )


def test_import_is_lazy_and_does_not_import_vendor_package() -> None:
    module = importlib.import_module("robot_dog.adapters.unitree_sdk2.peripherals")
    assert "unitree_sdk2py" not in module.__dict__


def test_constructor_acknowledgements_gate_facade_reads_and_mutations() -> None:
    events: list[tuple[str, object]] = []
    peripherals = UnitreeSdk2Peripherals(
        network_interface="enp2s0",
        bindings=fake_bindings(events),
        acknowledgements=AuthoritySafetyAcknowledgements(hardware_enabled=True),
    )
    assert peripherals.video.get_image_sample().ok
    with pytest.raises(UnitreeSdk2SafetyError, match="operator_acknowledged"):
        peripherals.vui.set_volume(3)


def test_video_requires_hardware_ack_and_normalizes_binary_result() -> None:
    events: list[tuple[str, object]] = []
    video = UnitreeSdk2VideoClient(
        network_interface="enp2s0", bindings=fake_bindings(events)
    )
    with pytest.raises(UnitreeSdk2SafetyError, match="hardware_enabled=True"):
        video.get_image_sample()
    assert events == []

    result = video.get_image_sample(hardware_enabled=True)
    assert result.ok
    assert result.value == b"\x00\x01\x02\xff"
    assert result.bytes == b"\x00\x01\x02\xff"
    assert events[:3] == [
        ("factory", (0, "enp2s0")),
        ("video-client", None),
        ("video-init", None),
    ]


def test_vui_reads_and_mutations_cover_all_official_methods() -> None:
    events: list[tuple[str, object]] = []
    vui = UnitreeSdk2VuiClient(
        network_interface="enp2s0", bindings=fake_bindings(events)
    )

    assert vui.get_switch(hardware_enabled=True).value is True
    assert vui.get_volume(hardware_enabled=True).value == 7
    assert vui.get_brightness(hardware_enabled=True).value == 9

    with pytest.raises(UnitreeSdk2SafetyError, match="operator_acknowledged"):
        vui.set_volume(4, hardware_enabled=True)
    assert vui.set_switch(False, hardware_enabled=True, operator_acknowledged=True).ok
    assert vui.set_volume(4, hardware_enabled=True, operator_acknowledged=True).ok
    assert vui.set_brightness(5, hardware_enabled=True, operator_acknowledged=True).ok

    assert ("vui-set-switch", 0) in events
    assert ("vui-set-volume", 4) in events
    assert ("vui-set-brightness", 5) in events


def test_obstacle_client_exposes_switch_move_absolute_increment_and_remote_api() -> (
    None
):
    events: list[tuple[str, object]] = []
    obstacles = UnitreeSdk2ObstaclesAvoidClient(
        network_interface="enp2s0", bindings=fake_bindings(events)
    )
    assert obstacles.get_switch(hardware_enabled=True).value is False

    for operation in (
        lambda: obstacles.set_switch(
            True, hardware_enabled=True, operator_acknowledged=True
        ),
        lambda: obstacles.move(
            0.1, -0.2, 0.3, hardware_enabled=True, operator_acknowledged=True
        ),
        lambda: obstacles.move_to_absolute_position(
            1.0, 2.0, 3.0, hardware_enabled=True, operator_acknowledged=True
        ),
        lambda: obstacles.move_to_increment_position(
            4.0, 5.0, 6.0, hardware_enabled=True, operator_acknowledged=True
        ),
        lambda: obstacles.use_remote_command_from_api(
            True, hardware_enabled=True, operator_acknowledged=True
        ),
    ):
        assert operation().ok

    assert ("obstacles-set-switch", True) in events
    assert ("move", (0.1, -0.2, 0.3)) in events
    assert ("move-absolute", (1.0, 2.0, 3.0)) in events
    assert ("move-increment", (4.0, 5.0, 6.0)) in events
    assert ("remote-api", True) in events


def test_facade_shares_dds_initialization_and_reports_complete_source_findings() -> (
    None
):
    events: list[tuple[str, object]] = []
    peripherals = UnitreeSdk2Peripherals(
        network_interface="enp2s0", bindings=fake_bindings(events)
    )
    assert peripherals.capabilities()["video"]["methods"] == ["GetImageSample"]
    assert peripherals.source_findings()["vui"]["methods"] == [
        "Init",
        "SetSwitch",
        "GetSwitch",
        "SetVolume",
        "GetVolume",
        "SetBrightness",
        "GetBrightness",
    ]

    assert peripherals.video.get_image_sample(hardware_enabled=True).ok
    assert peripherals.vui.get_switch(hardware_enabled=True).ok
    assert peripherals.obstacles.get_switch(hardware_enabled=True).ok
    assert events.count(("factory", (0, "enp2s0"))) == 1


def test_loader_uses_exact_official_module_paths() -> None:
    imported: list[str] = []
    modules: dict[str, ModuleType] = {}
    for path, name, value in (
        ("unitree_sdk2py.core.channel", "ChannelFactoryInitialize", lambda *_: None),
        ("unitree_sdk2py.go2.video.video_client", "VideoClient", FakeVideoClient),
        ("unitree_sdk2py.go2.vui.vui_client", "VuiClient", FakeVuiClient),
        (
            "unitree_sdk2py.go2.obstacles_avoid.obstacles_avoid_client",
            "ObstaclesAvoidClient",
            FakeObstaclesClient,
        ),
    ):
        module = ModuleType(path)
        setattr(module, name, value)
        modules[path] = module

    def importer(name: str) -> ModuleType:
        imported.append(name)
        return modules[name]

    bindings = UnitreeSdk2PeripheralBindings.load(importer)
    assert imported == list(modules)
    assert callable(bindings.video_client)
    assert callable(bindings.vui_client)
    assert callable(bindings.obstacles_client)


def test_malformed_video_result_fails_closed_without_returning_vendor_value() -> None:
    class MalformedVideo(FakeVideoClient):
        def GetImageSample(self):
            return 0, object()

    bindings = UnitreeSdk2PeripheralBindings(
        lambda *_: None,
        lambda: MalformedVideo([]),
        lambda: FakeVuiClient([]),
        lambda: FakeObstaclesClient([]),
    )
    video = UnitreeSdk2VideoClient(network_interface="enp2s0", bindings=bindings)
    with pytest.raises(UnitreeSdk2PeripheralError, match="expected bytes"):
        video.get_image_sample(hardware_enabled=True)


def test_mutation_arguments_are_validated_before_dds() -> None:
    events: list[tuple[str, object]] = []
    obstacles = UnitreeSdk2ObstaclesAvoidClient(
        network_interface="enp2s0", bindings=fake_bindings(events)
    )
    with pytest.raises(ValueError, match="finite"):
        obstacles.move(
            float("nan"),
            0.0,
            0.0,
            hardware_enabled=True,
            operator_acknowledged=True,
        )
    assert events == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
