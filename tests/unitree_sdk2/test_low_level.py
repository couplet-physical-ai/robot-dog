"""Offline contract tests for the injected Go2 SDK2 low-level boundary."""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from robot_dog.adapters.unitree_sdk2.low_level import (
    LOW_CMD_TOPIC,
    LOW_STATE_TOPIC,
    MOTOR_COUNT,
    MotorCommand,
    TimedPublishResult,
    UnitreeGo2LowLevel,
    UnitreeLowLevelConfigurationError,
    UnitreeLowLevelCrcError,
    UnitreeLowLevelPublishError,
    UnitreeLowLevelSafetyError,
    UnitreeLowLevelStateError,
    UnitreeSdk2LowLevelBindings,
)


@dataclass
class FakeMotor:
    mode: int = 0
    q: float = 0.0
    dq: float = 0.0
    kp: float = 0.0
    kd: float = 0.0
    tau: float = 0.0


class FakeLowCmd:
    def __init__(self) -> None:
        self.head = [0, 0]
        self.level_flag = 0
        self.gpio = 0
        self.motor_cmd = [FakeMotor() for _ in range(20)]
        self.crc = 0


class FakeLowState:
    def __init__(self, motor_count: int = 20) -> None:
        self.motor_state = [
            SimpleNamespace(q=float(index)) for index in range(motor_count)
        ]
        self.tick = 1


class FakeCrc:
    def __init__(self, value: int = 0x12345678) -> None:
        self.value = value
        self.messages: list[FakeLowCmd] = []

    def Crc(self, message: FakeLowCmd) -> int:
        self.messages.append(message)
        return self.value


class FakePublisher:
    def __init__(self, topic: str, message_type: Any, events: list[str]) -> None:
        self.topic = topic
        self.message_type = message_type
        self.events = events
        self.writes: list[FakeLowCmd] = []
        self.initialized = False
        self.result: object = True

    def Init(self) -> None:
        self.events.append("publisher-init")
        self.initialized = True

    def Write(self, message: FakeLowCmd) -> object:
        self.events.append("write")
        self.writes.append(message)
        return self.result

    def Close(self) -> None:
        self.events.append("publisher-close")


class FakeSubscriber:
    def __init__(self, topic: str, message_type: Any, events: list[str]) -> None:
        self.topic = topic
        self.message_type = message_type
        self.events = events
        self.samples: list[FakeLowState | None] = []
        self.read_timeouts: list[float] = []
        self.initialized = False

    def Init(self, handler: object = None, queue_length: int = 0) -> None:
        assert handler is None
        assert queue_length == 0
        self.events.append("subscriber-init")
        self.initialized = True

    def Read(self, timeout: float) -> FakeLowState | None:
        self.events.append("read")
        self.read_timeouts.append(timeout)
        return self.samples.pop(0) if self.samples else None

    def Close(self) -> None:
        self.events.append("subscriber-close")


class FakeBus:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.publisher: FakePublisher | None = None
        self.subscriber: FakeSubscriber | None = None
        self.initializations: list[tuple[int, str]] = []
        self.crc = FakeCrc()

    def bindings(self) -> UnitreeSdk2LowLevelBindings:
        return UnitreeSdk2LowLevelBindings(
            channel_factory_initialize=self.initialize,
            channel_publisher=self.make_publisher,
            channel_subscriber=self.make_subscriber,
            low_cmd_type=FakeLowCmd,
            low_state_type=FakeLowState,
            low_cmd_factory=FakeLowCmd,
            low_state_factory=FakeLowState,
            crc=self.crc,
        )

    def initialize(self, domain_id: int, interface: str) -> None:
        self.events.append("factory-init")
        self.initializations.append((domain_id, interface))

    def make_publisher(self, topic: str, message_type: Any) -> FakePublisher:
        self.publisher = FakePublisher(topic, message_type, self.events)
        return self.publisher

    def make_subscriber(self, topic: str, message_type: Any) -> FakeSubscriber:
        self.subscriber = FakeSubscriber(topic, message_type, self.events)
        return self.subscriber


def commands(offset: float = 0.0) -> list[MotorCommand]:
    return [
        MotorCommand(
            q=offset + index + 0.1,
            dq=offset + index + 0.2,
            kp=offset + index + 0.3,
            kd=offset + index + 0.4,
            tau=offset + index + 0.5,
            mode=index,
        )
        for index in range(MOTOR_COUNT)
    ]


def make_controller(
    bus: FakeBus,
    *,
    clock: callable | None = None,
    sleep: callable | None = None,
    **overrides: Any,
) -> UnitreeGo2LowLevel:
    options: dict[str, Any] = {
        "interface": "fake-ethernet0",
        "domain_id": 7,
        "hardware_enabled": True,
        "operator_confirmed": True,
        "expert_low_level_confirmed": True,
        "robot_restrained_confirmed": True,
        "bindings": bus.bindings(),
        "motion_service_released": True,
        "state_timeout": 0.5,
        "state_freshness": 0.25,
    }
    if clock is not None:
        options["clock"] = clock
    if sleep is not None:
        options["sleep"] = sleep
    options.update(overrides)
    return UnitreeGo2LowLevel(**options)


def test_injected_bindings_keep_vendor_modules_lazy_and_load_exact_paths() -> None:
    imported: list[str] = []
    channel = ModuleType("channel")
    channel.ChannelFactoryInitialize = lambda *_args: None
    channel.ChannelPublisher = object
    channel.ChannelSubscriber = object
    defaults = ModuleType("default")
    defaults.unitree_go_msg_dds__LowCmd_ = FakeLowCmd
    defaults.unitree_go_msg_dds__LowState_ = FakeLowState
    go2_idl = ModuleType("go2_idl")
    go2_idl.LowCmd_ = FakeLowCmd
    go2_idl.LowState_ = FakeLowState
    crc = ModuleType("crc")
    crc.CRC = FakeCrc
    motion = ModuleType("motion")
    motion.MotionSwitcherClient = object
    modules = {
        "unitree_sdk2py.core.channel": channel,
        "unitree_sdk2py.idl.default": defaults,
        "unitree_sdk2py.idl.unitree_go.msg.dds_": go2_idl,
        "unitree_sdk2py.utils.crc": crc,
        "unitree_sdk2py.comm.motion_switcher.motion_switcher_client": motion,
    }

    def importer(name: str) -> ModuleType:
        imported.append(name)
        return modules[name]

    bindings = UnitreeSdk2LowLevelBindings.load(importer, include_motion_switcher=True)

    assert imported == [
        "unitree_sdk2py.core.channel",
        "unitree_sdk2py.idl.default",
        "unitree_sdk2py.idl.unitree_go.msg.dds_",
        "unitree_sdk2py.utils.crc",
        "unitree_sdk2py.comm.motion_switcher.motion_switcher_client",
    ]
    assert bindings.LowCmd_ is FakeLowCmd
    assert bindings.LowState_ is FakeLowState
    assert bindings.motion_switcher_client is object


def test_constructor_requires_explicit_interface_domain_and_boolean_gates() -> None:
    bus = FakeBus()
    base = {
        "domain_id": 0,
        "hardware_enabled": True,
        "operator_confirmed": True,
        "expert_low_level_confirmed": True,
        "robot_restrained_confirmed": True,
        "bindings": bus.bindings(),
    }
    with pytest.raises(UnitreeLowLevelConfigurationError, match="interface"):
        UnitreeGo2LowLevel(interface="", **base)
    with pytest.raises(UnitreeLowLevelConfigurationError, match="domain_id"):
        without_domain = {
            key: value for key, value in base.items() if key != "domain_id"
        }
        UnitreeGo2LowLevel(interface="fake0", domain_id=-1, **without_domain)
    with pytest.raises(UnitreeLowLevelConfigurationError, match="explicit bool"):
        UnitreeGo2LowLevel(interface="fake0", **{**base, "hardware_enabled": 1})


def test_build_assigns_all_twelve_fields_and_computes_crc_without_dds() -> None:
    bus = FakeBus()
    controller = make_controller(bus)

    message = controller.build_low_command(commands(10.0))

    assert bus.events == []
    assert bus.crc.messages == [message]
    assert message.crc == 0x12345678
    for index, expected in enumerate(commands(10.0)):
        actual = message.motor_cmd[index]
        assert (actual.mode, actual.q, actual.dq, actual.kp, actual.kd, actual.tau) == (
            expected.mode,
            expected.q,
            expected.dq,
            expected.kp,
            expected.kd,
            expected.tau,
        )
    assert message.head == [0xFE, 0xEF]
    assert message.level_flag == 0xFF
    assert message.gpio == 0
    assert all(
        (slot.mode, slot.q, slot.dq, slot.kp, slot.kd, slot.tau)
        == (1, 2.146e9, 16000.0, 0.0, 0.0, 0.0)
        for slot in message.motor_cmd[MOTOR_COUNT:]
    )


def test_publish_once_initializes_explicit_channels_reads_fresh_state_then_writes() -> (
    None
):
    bus = FakeBus()
    controller = make_controller(bus)
    controller.initialize()
    assert bus.subscriber is not None
    assert bus.publisher is not None
    bus.subscriber.samples.append(FakeLowState())

    message = controller.publish_once(commands())

    assert bus.initializations == [(7, "fake-ethernet0")]
    assert bus.subscriber.topic == LOW_STATE_TOPIC
    assert bus.publisher.topic == LOW_CMD_TOPIC
    assert bus.events.index("read") < bus.events.index("write")
    assert bus.subscriber.read_timeouts == [0.5]
    assert bus.publisher.writes == [message]


def test_publish_requires_all_safety_gates_and_explicit_motion_boundary() -> None:
    bus = FakeBus()
    controller = make_controller(
        bus,
        hardware_enabled=False,
        motion_service_released=False,
        motion_ownership_confirmed=False,
    )
    with pytest.raises(UnitreeLowLevelSafetyError, match="hardware_enabled"):
        controller.publish_once(commands())
    assert bus.events == []

    bus = FakeBus()
    controller = make_controller(
        bus,
        motion_service_released=False,
        motion_ownership_confirmed=False,
    )
    with pytest.raises(UnitreeLowLevelSafetyError, match="motion-service"):
        controller.publish_once(commands())
    assert bus.events == []


def test_release_callback_is_explicit_and_called_once_before_publish() -> None:
    bus = FakeBus()
    releases: list[str] = []
    controller = make_controller(
        bus,
        motion_service_released=False,
        motion_service_release=lambda: releases.append("release"),
    )
    assert bus.subscriber is None
    controller.initialize()
    assert bus.subscriber is not None
    bus.subscriber.samples.extend([FakeLowState(), FakeLowState()])

    controller.publish_once(commands())
    controller.publish_once(commands(1.0))

    assert releases == ["release"]
    assert bus.publisher is not None
    assert len(bus.publisher.writes) == 2


def test_ownership_confirmation_callback_is_required_and_used() -> None:
    bus = FakeBus()
    checks: list[str] = []
    controller = make_controller(
        bus,
        motion_service_released=False,
        motion_ownership_confirmed=False,
        motion_ownership_confirmation=lambda: checks.append("check") or True,
    )
    assert bus.subscriber is None
    controller.initialize()
    assert bus.subscriber is not None
    bus.subscriber.samples.append(FakeLowState())

    controller.publish_once(commands())

    assert checks == ["check"]
    assert bus.publisher is not None
    assert len(bus.publisher.writes) == 1


def test_state_failures_and_nonfinite_or_wrong_count_commands_fail_closed() -> None:
    bus = FakeBus()
    controller = make_controller(bus)
    with pytest.raises(UnitreeLowLevelConfigurationError, match="exactly 12"):
        controller.build_low_command(commands()[:-1])
    with pytest.raises(UnitreeLowLevelConfigurationError, match="finite"):
        controller.build_low_command(
            [MotorCommand(float("nan"), 0.0, 0.0, 0.0, 0.0) for _ in range(MOTOR_COUNT)]
        )

    controller.initialize()
    assert bus.subscriber is not None
    bus.subscriber.samples.append(None)
    with pytest.raises(UnitreeLowLevelStateError, match="no sample"):
        controller.publish_once(commands())
    assert bus.publisher is not None
    assert bus.publisher.writes == []
    assert controller.cancelled is True


def test_provider_that_outlives_fresh_state_is_rejected_before_write() -> None:
    bus = FakeBus()
    now = [0.0]
    controller = make_controller(bus, clock=lambda: now[0])
    controller.initialize()
    assert bus.subscriber is not None
    bus.subscriber.samples.append(FakeLowState())

    def stale_provider(_state: FakeLowState) -> list[MotorCommand]:
        now[0] = 1.0
        return commands()

    with pytest.raises(UnitreeLowLevelStateError, match="stale"):
        controller.publish_once(stale_provider)
    assert bus.publisher is not None
    assert bus.publisher.writes == []


def test_bad_crc_and_publisher_rejection_never_look_like_success() -> None:
    bus = FakeBus()
    bus.crc = FakeCrc(value=0x1_0000_0000)
    controller = make_controller(bus)
    with pytest.raises(UnitreeLowLevelCrcError, match="uint32"):
        controller.build_low_command(commands())

    bus = FakeBus()
    controller = make_controller(bus)
    controller.initialize()
    assert bus.subscriber is not None
    assert bus.publisher is not None
    bus.subscriber.samples.append(FakeLowState())
    bus.publisher.result = False
    with pytest.raises(UnitreeLowLevelPublishError, match="rejected"):
        controller.publish_once(commands())
    assert controller.cancelled is True


def test_timed_loop_honors_period_duration_and_cancel_without_final_command() -> None:
    bus = FakeBus()
    now = [0.0]

    def clock() -> float:
        return now[0]

    controller: UnitreeGo2LowLevel

    def sleep(seconds: float) -> None:
        now[0] += seconds
        if len(bus.publisher.writes) == 1:  # type: ignore[union-attr]
            controller.stop()

    controller = make_controller(bus, clock=clock, sleep=sleep)
    controller.initialize()
    assert bus.subscriber is not None
    bus.subscriber.samples.extend([FakeLowState(), FakeLowState(), FakeLowState()])

    result = controller.publish_timed(commands(), period=0.01, duration=0.05)

    assert isinstance(result, TimedPublishResult)
    assert result.published == 1
    assert result.cancelled is True
    assert bus.publisher is not None
    assert len(bus.publisher.writes) == 1
    assert now[0] == pytest.approx(0.01)


def test_motion_switcher_release_is_explicit_and_never_calls_sport() -> None:
    bus = FakeBus()
    calls: list[str] = []

    class Switcher:
        def Init(self) -> None:
            calls.append("init")

        def CheckMode(self) -> tuple[int, dict[str, str]]:
            calls.append("check")
            return 0, {"name": "sport"}

        def ReleaseMode(self) -> tuple[int, None]:
            calls.append("release")
            return 0, None

    bindings = bus.bindings()
    bindings = UnitreeSdk2LowLevelBindings(
        bindings.channel_factory_initialize,
        bindings.channel_publisher,
        bindings.channel_subscriber,
        bindings.low_cmd_type,
        bindings.low_state_type,
        bindings.low_cmd_factory,
        bindings.low_state_factory,
        bindings.crc,
        motion_switcher_client=Switcher,
    )
    controller = make_controller(
        bus,
        bindings=bindings,
        motion_service_released=False,
        motion_ownership_confirmed=False,
    )

    controller.release_motion_service()

    assert calls == ["init", "check", "release"]
