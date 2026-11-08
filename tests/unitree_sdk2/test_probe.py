"""Contract tests for the optional Unitree SDK2 read-only boundary.

Every test injects Python fakes.  No Unitree package, CycloneDDS runtime,
robot, socket, or network configuration is used.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import ModuleType

import pytest

from robot_dog.adapters.unitree_sdk2 import (
    UnitreeSdk2Bindings,
    UnitreeSdk2InitializationError,
    UnitreeSdk2Probe,
    UnitreeSdk2ProbeError,
    UnitreeSdk2ReadOnlyProbe,
    UnitreeSdk2UnavailableError,
    UnitreeSdk2UnsupportedPlatformError,
    UnitreeService,
)
from robot_dog.domain.health import HealthStatus
from robot_dog.domain.telemetry import RobotTelemetry


@dataclass
class FakeService:
    name: str
    status: int
    protect: bool


class FakeClient:
    def __init__(self, events: list[str]) -> None:
        events.append("client")
        self.events = events

    def Init(self) -> None:
        self.events.append("client-init")

    def GetApiVersion(self) -> str:
        self.events.append("api-version")
        return "1.0.0.1"

    def GetServerApiVersion(self) -> tuple[int, str]:
        self.events.append("server-api-version")
        return 0, "1.0.0.1"

    def ServiceList(self) -> tuple[int, list[FakeService]]:
        self.events.append("service-list")
        return 0, [FakeService("sport", 1, True), FakeService("imu", 0, False)]


def fake_bindings(events: list[str]) -> UnitreeSdk2Bindings:
    def initialize(domain_id: int, network_interface: str) -> None:
        events.append(f"factory:{domain_id}:{network_interface}")

    return UnitreeSdk2Bindings(
        channel_factory_initialize=initialize,
        robot_state_client=lambda: FakeClient(events),
    )


def test_importing_boundary_does_not_import_vendor_package() -> None:
    """The optional package is not imported as a side effect of this module."""

    imported = importlib.import_module("robot_dog.adapters.unitree_sdk2.probe")
    assert imported.SDK_PACKAGE not in imported.__dict__
    assert "unitree_sdk2py" not in imported.__dict__


def test_constructor_is_lazy_and_requires_explicit_interface() -> None:
    with pytest.raises(ValueError, match="network_interface is required"):
        UnitreeSdk2ReadOnlyProbe()

    calls: list[str] = []
    probe = UnitreeSdk2ReadOnlyProbe(
        network_interface="enp2s0",
        bindings=fake_bindings(calls),
    )
    assert calls == []
    assert probe.capabilities()["read_only"] is True
    assert probe.capabilities()["hardware_commands"] is False


def test_module_loader_can_inject_source_compatible_fakes() -> None:
    events: list[str] = []
    channel_module = ModuleType("fake_channel")
    channel_module.ChannelFactoryInitialize = lambda domain_id, network_interface: (
        events.append(f"factory:{domain_id}:{network_interface}")
    )
    state_module = ModuleType("fake_robot_state")
    state_module.RobotStateClient = lambda: FakeClient(events)
    modules = {
        "unitree_sdk2py.core.channel": channel_module,
        "unitree_sdk2py.go2.robot_state.robot_state_client": state_module,
    }

    result = UnitreeSdk2Probe(
        network_interface="enp2s0",
        importer=modules.__getitem__,
        platform_name="Linux",
    ).probe()

    assert result.api_version == "1.0.0.1"
    assert events[0] == "factory:0:enp2s0"


def test_factory_is_initialized_before_client_and_only_read_queries_run() -> None:
    events: list[str] = []
    probe = UnitreeSdk2Probe(
        network_interface="enp2s0",
        bindings=fake_bindings(events),
    )

    result = probe.probe()

    assert events == [
        "factory:0:enp2s0",
        "client",
        "client-init",
        "api-version",
        "server-api-version",
        "service-list",
    ]
    assert result.network_interface == "enp2s0"
    assert result.domain_id == 0
    assert result.api_version == "1.0.0.1"
    assert result.server_api_version == "1.0.0.1"
    assert result.services == (
        UnitreeService("sport", 1, True),
        UnitreeService("imu", 0, False),
    )
    assert result.read_only is True
    assert result.to_dict()["services"][0]["protected"] is True


def test_repeated_probe_reuses_read_only_client_without_reinitializing_dds() -> None:
    events: list[str] = []
    probe = UnitreeSdk2Probe(
        network_interface="eth0",
        bindings=fake_bindings(events),
    )

    probe.probe()
    probe.probe()

    assert events.count("factory:0:eth0") == 1
    assert events.count("client") == 1
    assert events.count("client-init") == 1
    assert events.count("service-list") == 2


def test_telemetry_fails_closed_without_inventing_vendor_health_or_battery() -> None:
    probe = UnitreeSdk2Probe(
        network_interface="eth0",
        bindings=fake_bindings([]),
        clock=lambda: 12.5,
    )

    telemetry = probe.read_telemetry()

    assert isinstance(telemetry, RobotTelemetry)
    assert telemetry.observed_at == 12.5
    assert telemetry.battery_percent is None
    assert telemetry.health.status is HealthStatus.UNKNOWN


def test_missing_sdk_error_is_actionable_and_import_is_lazy() -> None:
    imported: list[str] = []

    def missing_import(name: str) -> ModuleType:
        imported.append(name)
        raise ModuleNotFoundError("no module named unitree_sdk2py")

    probe = UnitreeSdk2Probe(
        network_interface="enp2s0",
        importer=missing_import,
        platform_name="Linux",
    )
    assert imported == []

    with pytest.raises(UnitreeSdk2UnavailableError) as raised:
        probe.probe()

    message = str(raised.value)
    assert imported == ["unitree_sdk2py.core.channel"]
    assert "requirements-unitree.txt" in message
    assert "unitree_sdk2py" in message
    assert "CycloneDDS 0.10.2" in message
    assert "supported Linux" in message


def test_non_linux_without_injected_sdk_is_rejected_before_import() -> None:
    imported: list[str] = []

    def unexpected_import(name: str) -> ModuleType:
        imported.append(name)
        raise AssertionError("vendor import must not occur on unsupported host")

    probe = UnitreeSdk2Probe(
        network_interface="enp2s0",
        importer=unexpected_import,
        platform_name="Darwin",
    )

    with pytest.raises(UnitreeSdk2UnsupportedPlatformError, match="Linux"):
        probe.probe()
    assert imported == []


def test_factory_failure_is_reported_as_initialization_error() -> None:
    def initialize(_domain_id: int, _network_interface: str) -> None:
        raise OSError("fake DDS failure")

    bindings = UnitreeSdk2Bindings(initialize, lambda: pytest.fail("not reached"))
    probe = UnitreeSdk2Probe(network_interface="enp2s0", bindings=bindings)

    with pytest.raises(
        UnitreeSdk2InitializationError, match="ChannelFactoryInitialize"
    ):
        probe.probe()


def test_malformed_read_only_response_fails_closed() -> None:
    class MalformedClient(FakeClient):
        def ServiceList(self) -> tuple[int, list[FakeService]]:
            return 7, []

    bindings = UnitreeSdk2Bindings(
        lambda _domain, _interface: None,
        lambda: MalformedClient([]),
    )
    probe = UnitreeSdk2Probe(network_interface="enp2s0", bindings=bindings)

    with pytest.raises(UnitreeSdk2ProbeError, match="service-list"):
        probe.probe()


def test_vendor_objects_are_not_returned_from_service_conversion() -> None:
    events: list[str] = []
    result = UnitreeSdk2Probe(
        network_interface="enp2s0",
        bindings=fake_bindings(events),
    ).probe()

    assert all(isinstance(service, UnitreeService) for service in result.services)
    assert all(
        type(service).__module__.startswith("robot_dog.") for service in result.services
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
