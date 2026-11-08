"""Offline contract tests for the gated Go2 high-level SDK2 adapter."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Any

import pytest

from robot_dog.adapters.unitree_sdk2.high_level import (
    Go2SportClient,
    Go2SportClientConfig,
    HazardousMotionAcknowledgementRequired,
    IntentionalInvocationRequired,
    MoveSessionError,
    SportCommandResult,
    UnitreeSdk2HighLevelBindings,
    UnitreeSdk2HighLevelConfigurationError,
    UnitreeSdk2HighLevelInitializationError,
    command_catalog,
)

PUBLIC_ACTIONS = {
    "Damp",
    "BalanceStand",
    "StopMove",
    "StandUp",
    "StandDown",
    "RecoveryStand",
    "Euler",
    "Move",
    "Sit",
    "RiseSit",
    "SpeedLevel",
    "Hello",
    "Stretch",
    "Content",
    "Dance1",
    "Dance2",
    "SwitchJoystick",
    "Pose",
    "Scrape",
    "FrontFlip",
    "FrontJump",
    "FrontPounce",
    "Heart",
    "StaticWalk",
    "TrotRun",
    "LeftFlip",
    "BackFlip",
    "HandStand",
    "FreeWalk",
    "FreeBound",
    "FreeJump",
    "FreeAvoid",
    "ClassicWalk",
    "WalkUpright",
    "CrossStep",
    "AutoRecoverySet",
    "AutoRecoveryGet",
    "SwitchAvoidMode",
}

HAZARDOUS_ACTIONS = {
    "Dance1",
    "Dance2",
    "FrontFlip",
    "FrontJump",
    "FrontPounce",
    "LeftFlip",
    "BackFlip",
    "HandStand",
    "FreeWalk",
    "FreeBound",
    "FreeJump",
    "FreeAvoid",
}


class FakeSportClient:
    def __init__(self, events: list[Any]) -> None:
        events.append("client")
        self.events = events
        self.timeout: float | None = None
        self.initialized = False

    def SetTimeout(self, timeout: float) -> None:
        self.events.append(("timeout", timeout))
        self.timeout = timeout

    def Init(self) -> None:
        self.events.append("init")
        self.initialized = True

    def StopMove(self) -> int:
        self.events.append("StopMove")
        return 0

    def AutoRecoveryGet(self) -> tuple[int, bool]:
        self.events.append("AutoRecoveryGet")
        return 0, True

    def __getattr__(self, name: str) -> Any:
        def action(*args: Any, **kwargs: Any) -> int:
            self.events.append((name, args, kwargs))
            return 0

        return action


def make_client(
    events: list[Any] | None = None,
    *,
    hardware_enabled: bool = True,
    operator_acknowledged: bool = True,
    hazardous_motion_acknowledged: bool = True,
    clock: Any = None,
    sleeper: Any = None,
) -> tuple[Go2SportClient, list[Any]]:
    events = [] if events is None else events

    def initialize(domain_id: int, interface: str) -> None:
        events.append(("factory", domain_id, interface))

    def make_sport_client() -> FakeSportClient:
        return FakeSportClient(events)

    bindings = UnitreeSdk2HighLevelBindings(initialize, make_sport_client)
    client = Go2SportClient(
        network_interface="fake0",
        domain_id=7,
        timeout_seconds=2.5,
        hardware_enabled=hardware_enabled,
        operator_acknowledged=operator_acknowledged,
        hazardous_motion_acknowledged=hazardous_motion_acknowledged,
        bindings=bindings,
        clock=clock,
        sleeper=sleeper,
    )
    return client, events


def test_import_is_lazy_and_catalog_is_complete() -> None:
    module = importlib.import_module("robot_dog.adapters.unitree_sdk2.high_level")
    assert "unitree_sdk2py" not in sys.modules
    assert {entry.name for entry in command_catalog()} == PUBLIC_ACTIONS
    assert {
        entry.name for entry in command_catalog() if entry.hazardous
    } == HAZARDOUS_ACTIONS
    assert module.SDK_REVISION == "65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5"


def test_configuration_requires_explicit_interface_and_domain() -> None:
    with pytest.raises(UnitreeSdk2HighLevelConfigurationError, match="interface"):
        Go2SportClient(domain_id=0)
    with pytest.raises(UnitreeSdk2HighLevelConfigurationError, match="domain_id"):
        Go2SportClient(network_interface="fake0")

    config = Go2SportClientConfig(network_interface="fake0", domain_id=0)
    assert config.interface == "fake0"
    client, _ = make_client()
    assert client.network_interface == "fake0"


def test_factory_precedes_client_and_timeout_precedes_init() -> None:
    client, events = make_client()
    assert events == []
    result = client.StandUp()
    assert result == SportCommandResult("StandUp", 0)
    assert events[:4] == [
        ("factory", 7, "fake0"),
        "client",
        ("timeout", 2.5),
        "init",
    ]


def test_common_acknowledgements_gate_every_command() -> None:
    for kwargs, expected in (
        ({"hardware_enabled": False}, "hardware-enabled"),
        ({"operator_acknowledged": False}, "operator acknowledgement"),
    ):
        client, events = make_client(**kwargs)
        with pytest.raises(PermissionError, match=expected):
            client.StandUp()
        assert events == []


def test_hazardous_actions_need_a_separate_second_ack() -> None:
    client, events = make_client(hazardous_motion_acknowledged=False)
    with pytest.raises(HazardousMotionAcknowledgementRequired):
        client.FrontFlip()
    assert events == []

    result = client.invoke(
        "FrontFlip", intentional=True, hazardous_motion_acknowledged=True
    )
    assert result.ok
    assert events[-1] == ("FrontFlip", (), {})


def test_generic_invocation_requires_intent_and_accepts_snake_case() -> None:
    client, events = make_client(hazardous_motion_acknowledged=False)
    with pytest.raises(IntentionalInvocationRequired):
        client.invoke("stand_up")
    result = client.invoke(
        "stand_up",
        intentional=True,
        hardware_enabled=True,
        operator_acknowledged=True,
    )
    assert result.ok
    assert events[-1] == ("StandUp", (), {})

    result = client.invoke(
        "front_flip",
        intentional=True,
        hardware_enabled=True,
        operator_acknowledged=True,
        hazardous_acknowledged=True,
    )
    assert result.ok
    assert events[-1] == ("FrontFlip", (), {})


def test_vendor_int_and_tuple_returns_are_normalized() -> None:
    client, _ = make_client()
    assert client.AutoRecoveryGet().data is True
    assert client.AutoRecoveryGet().status_code == 0


def test_every_catalog_action_is_reachable_through_intentional_invocation() -> None:
    client, events = make_client()
    arguments: dict[str, tuple[Any, ...]] = {
        "Euler": (0.0, 0.0, 0.0),
        "Move": (0.0, 0.0, 0.0),
        "SpeedLevel": (1,),
        "SwitchJoystick": (False,),
        "Pose": (False,),
        "FreeBound": (False,),
        "FreeJump": (False,),
        "FreeAvoid": (False,),
        "HandStand": (False,),
        "ClassicWalk": (False,),
        "WalkUpright": (False,),
        "CrossStep": (False,),
        "AutoRecoverySet": (False,),
    }
    for spec in command_catalog():
        client.invoke(
            spec.name,
            *arguments.get(spec.name, ()),
            intentional=True,
        )
    called = {
        item[0]
        for item in events
        if isinstance(item, tuple) and item and isinstance(item[0], str)
    }
    assert PUBLIC_ACTIONS - {"StopMove"} <= called | {"AutoRecoveryGet"}


def test_bounded_move_requires_session_and_limits_velocity() -> None:
    client, events = make_client()
    with pytest.raises(MoveSessionError):
        client.move_for(0.1, 0.0, 0.0, duration=1.0)
    with pytest.raises(UnitreeSdk2HighLevelConfigurationError):
        client.move_for(2.0, 0.0, 0.0, duration=1.0, session_id="s")
    assert events == []


def test_bounded_move_stops_on_context_exit_and_exception() -> None:
    client, events = make_client()
    with (
        pytest.raises(RuntimeError),
        client.move_for(0.1, 0.0, 0.0, duration=1.0, session_id="session-1"),
    ):
        assert events[-1] == ("Move", (0.1, 0.0, 0.0), {})
        raise RuntimeError("test body")
    assert events[-1] == "StopMove"


def test_run_bounded_move_refreshes_with_deadman_and_stops() -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    client, events = make_client(clock=clock, sleeper=sleep)
    client.run_bounded_move(
        0.1,
        0.0,
        0.0,
        duration=1.0,
        session_id="session-1",
        deadman_timeout_seconds=0.4,
        refresh_period_seconds=0.2,
    )
    assert (
        sum(1 for item in events if isinstance(item, tuple) and item[0] == "Move") >= 4
    )
    assert events[-1] == "StopMove"


def test_cleanup_stop_is_best_effort_and_does_not_initialize() -> None:
    client, events = make_client()
    assert client.best_effort_stop() is None
    assert events == []

    client.StandUp()
    assert client.best_effort_stop() is not None
    assert events[-1] == "StopMove"


def test_loader_can_inject_modules_without_importing_vendor_package() -> None:
    events: list[str] = []
    channel = ModuleType("fake_channel")
    channel.ChannelFactoryInitialize = lambda *_args: events.append("factory")
    sport = ModuleType("fake_sport")
    sport.SportClient = lambda: FakeSportClient(events)
    modules = {
        "unitree_sdk2py.core.channel": channel,
        "unitree_sdk2py.go2.sport.sport_client": sport,
    }
    client = Go2SportClient(
        network_interface="fake0",
        domain_id=0,
        hardware_enabled=True,
        operator_acknowledged=True,
        bindings=None,
        importer=modules.__getitem__,
        platform_name="Linux",
    )
    assert client.StandUp().ok
    assert events[0] == "factory"


def test_initialization_failure_is_reported() -> None:
    def fail(*_args: Any) -> None:
        raise OSError("fake DDS failure")

    bindings = UnitreeSdk2HighLevelBindings(fail, lambda: pytest.fail("not reached"))
    client = Go2SportClient(
        network_interface="fake0",
        domain_id=0,
        hardware_enabled=True,
        operator_acknowledged=True,
        bindings=bindings,
    )
    with pytest.raises(UnitreeSdk2HighLevelInitializationError, match="ChannelFactory"):
        client.StandUp()


def test_safety_acknowledgement_aliases_are_supported() -> None:
    client, _ = make_client(
        hardware_enabled=False,
        operator_acknowledged=False,
        hazardous_motion_acknowledged=False,
    )
    # The aliases are constructor-level booleans; construct a second client to
    # prove the public spelling without relying on a hardware runtime.
    events: list[Any] = []
    bindings = UnitreeSdk2HighLevelBindings(
        lambda *_args: None,
        lambda: FakeSportClient(events),
    )
    client = Go2SportClient(
        network_interface="fake0",
        domain_id=0,
        hardware_enabled_ack=True,
        operator_ack=True,
        hazardous_ack=True,
        bindings=bindings,
    )
    assert client.Damp().ok


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
