"""Offline contract tests for Unitree SDK2 authority access."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import ModuleType

import pytest

from robot_dog.adapters.unitree_sdk2.authority import (
    AuthoritySafetyAcknowledgements,
    UnitreeMotionModeResult,
    UnitreeSdk2Authority,
    UnitreeSdk2AuthorityBindings,
    UnitreeSdk2OperationError,
    UnitreeSdk2SafetyError,
    UnitreeServiceListResult,
    UnitreeServiceState,
)


@dataclass
class FakeService:
    name: str
    status: int
    protect: bool


class FakeRobotStateClient:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        events.append(("robot-client", None))
        self.events = events

    def SetTimeout(self, timeout: float) -> None:
        self.events.append(("robot-timeout", timeout))

    def Init(self) -> None:
        self.events.append(("robot-init", None))

    def ServiceList(self):
        self.events.append(("service-list", None))
        return 0, [FakeService("sport_mode", 1, True), FakeService("vui", 0, False)]

    def ServiceSwitch(self, name: str, enabled: bool) -> int:
        self.events.append(("service-switch", (name, enabled)))
        return 0

    def SetReportFreq(self, interval: int, duration: int) -> int:
        self.events.append(("report-frequency", (interval, duration)))
        return 0


class FakeMotionSwitcherClient:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        events.append(("motion-client", None))
        self.events = events

    def Init(self) -> None:
        self.events.append(("motion-init", None))

    def CheckMode(self):
        self.events.append(("check-mode", None))
        return 0, {"name": "normal", "owner": "fake"}

    def SelectMode(self, name: str):
        self.events.append(("select-mode", name))
        return 0, None

    def ReleaseMode(self):
        self.events.append(("release-mode", None))
        return 0, None


def fake_bindings(events: list[tuple[str, object]]) -> UnitreeSdk2AuthorityBindings:
    def initialize(domain_id: int, interface: str) -> None:
        events.append(("factory", (domain_id, interface)))

    return UnitreeSdk2AuthorityBindings(
        channel_factory_initialize=initialize,
        robot_state_client=lambda: FakeRobotStateClient(events),
        motion_switcher_client=lambda: FakeMotionSwitcherClient(events),
    )


def test_import_is_lazy_and_does_not_import_vendor_package() -> None:
    module = importlib.import_module("robot_dog.adapters.unitree_sdk2.authority")
    assert "unitree_sdk2py" not in module.__dict__


def test_construction_is_lazy_and_requires_explicit_interface() -> None:
    with pytest.raises(ValueError, match="network_interface is required"):
        UnitreeSdk2Authority()

    events: list[tuple[str, object]] = []
    authority = UnitreeSdk2Authority(
        network_interface="enp2s0", bindings=fake_bindings(events)
    )
    assert events == []
    assert authority.capabilities()["robot_state"]["report_frequency_get"] is False


def test_constructor_acknowledgements_can_arm_reads_without_arming_mutations() -> None:
    events: list[tuple[str, object]] = []
    authority = UnitreeSdk2Authority(
        network_interface="enp2s0",
        bindings=fake_bindings(events),
        acknowledgements=AuthoritySafetyAcknowledgements(hardware_enabled=True),
    )
    assert authority.read_service_list().ok
    with pytest.raises(UnitreeSdk2SafetyError, match="operator_acknowledged"):
        authority.set_report_frequency(1, 1)


def test_factory_precedes_each_client_and_reads_are_hardware_gated() -> None:
    events: list[tuple[str, object]] = []
    authority = UnitreeSdk2Authority(
        network_interface="enp2s0",
        bindings=fake_bindings(events),
        timeout=3.0,
    )

    with pytest.raises(UnitreeSdk2SafetyError, match="hardware_enabled=True"):
        authority.read_service_list()
    assert events == []

    result = authority.read_service_list(hardware_enabled=True)

    assert isinstance(result, UnitreeServiceListResult)
    assert result.ok
    assert result.services == (
        UnitreeServiceState("sport_mode", 1, True),
        UnitreeServiceState("vui", 0, False),
    )
    assert events[:4] == [
        ("factory", (0, "enp2s0")),
        ("robot-client", None),
        ("robot-timeout", 3.0),
        ("robot-init", None),
    ]
    assert events[4:] == [("service-list", None)]


def test_service_mutation_requires_operator_ack_target_and_exact_confirmation() -> None:
    events: list[tuple[str, object]] = []
    authority = UnitreeSdk2Authority(
        network_interface="enp2s0", bindings=fake_bindings(events)
    )

    with pytest.raises(UnitreeSdk2SafetyError, match="operator_acknowledged"):
        authority.switch_service(
            "sport_mode",
            False,
            hardware_enabled=True,
            target_id="robot-test-01",
            confirmation="robot-test-01",
        )
    assert events == []

    with pytest.raises(UnitreeSdk2SafetyError, match="target_id"):
        authority.switch_service(
            "sport_mode",
            False,
            hardware_enabled=True,
            operator_acknowledged=True,
        )
    assert events == []

    with pytest.raises(UnitreeSdk2SafetyError, match="exactly equal"):
        authority.switch_service(
            "sport_mode",
            False,
            hardware_enabled=True,
            operator_acknowledged=True,
            target_id="robot-test-01",
            confirmation="other-target",
        )
    assert events == []

    result = authority.switch_service(
        "sport_mode",
        False,
        hardware_enabled=True,
        operator_acknowledged=True,
        target_id="robot-test-01",
        confirmation="robot-test-01",
    )
    assert result.ok
    assert result.target_id == "robot-test-01"
    assert ("service-switch", ("sport_mode", False)) in events


def test_report_frequency_forwards_official_setter_and_no_getter_is_claimed() -> None:
    events: list[tuple[str, object]] = []
    authority = UnitreeSdk2Authority(
        network_interface="enp2s0", bindings=fake_bindings(events)
    )
    result = authority.set_report_frequency(
        20,
        1000,
        hardware_enabled=True,
        operator_acknowledged=True,
    )
    assert result.ok
    assert ("report-frequency", (20, 1000)) in events
    assert (
        "GetReportFreq" in authority.source_findings()["robot_state_client"]["absent"]
    )
    assert not hasattr(FakeRobotStateClient, "GetReportFreq")


def test_motion_check_is_read_only_but_select_and_release_are_confirmed_mutations() -> (
    None
):
    events: list[tuple[str, object]] = []
    authority = UnitreeSdk2Authority(
        network_interface="enp2s0", bindings=fake_bindings(events)
    )
    checked = authority.check_mode(hardware_enabled=True)
    assert isinstance(checked, UnitreeMotionModeResult)
    assert checked.mode == {"name": "normal", "owner": "fake"}

    selected = authority.select_mode(
        "ai",
        hardware_enabled=True,
        operator_acknowledged=True,
        target_id="robot-test-01",
        confirm="robot-test-01",
    )
    released = authority.release_mode(
        hardware_enabled=True,
        operator_acknowledged=True,
        target_id="robot-test-01",
        confirmation="robot-test-01",
    )
    assert selected.ok and released.ok
    assert ("select-mode", "ai") in events
    assert ("release-mode", None) in events
    assert events.index(("factory", (0, "enp2s0"))) < events.index(
        ("motion-client", None)
    )


def test_injected_module_loader_uses_exact_official_paths() -> None:
    events: list[tuple[str, object]] = []
    imported: list[str] = []
    channel = ModuleType("channel")
    channel.ChannelFactoryInitialize = lambda *_args: None
    state = ModuleType("state")
    state.RobotStateClient = lambda: FakeRobotStateClient(events)
    motion = ModuleType("motion")
    motion.MotionSwitcherClient = lambda: FakeMotionSwitcherClient(events)
    modules = {
        "unitree_sdk2py.core.channel": channel,
        "unitree_sdk2py.go2.robot_state.robot_state_client": state,
        "unitree_sdk2py.comm.motion_switcher.motion_switcher_client": motion,
    }

    def importer(name: str) -> ModuleType:
        imported.append(name)
        return modules[name]

    bindings = UnitreeSdk2AuthorityBindings.load(importer)
    assert imported == list(modules)
    authority = UnitreeSdk2Authority(
        network_interface="enp2s0", bindings=bindings, platform_name="Linux"
    )
    assert authority.check_mode(hardware_enabled=True).ok


def test_malformed_or_missing_official_response_fails_closed() -> None:
    class Malformed(FakeRobotStateClient):
        def ServiceList(self):
            return "not-a-pair"

    bindings = UnitreeSdk2AuthorityBindings(
        lambda *_args: None,
        lambda: Malformed([]),
        lambda: FakeMotionSwitcherClient([]),
    )
    authority = UnitreeSdk2Authority(network_interface="enp2s0", bindings=bindings)
    with pytest.raises(
        UnitreeSdk2OperationError, match=r"expected \(status_code, value\)"
    ):
        authority.read_service_list(hardware_enabled=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
