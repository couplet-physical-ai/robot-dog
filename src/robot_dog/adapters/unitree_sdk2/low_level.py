"""Explicit, injected Unitree Go2 SDK2 low-level motor boundary.

This module is deliberately separate from the repository's read-only probe.  It
contains the source-verified SDK2 paths for revision
``65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5``:

* ``unitree_sdk2py.core.channel`` for the DDS channel factory and channels;
* ``unitree_sdk2py.idl.default`` for the generated Go2 message constructors;
* ``unitree_sdk2py.idl.unitree_go.msg.dds_`` for the Go2 IDL types;
* ``unitree_sdk2py.utils.crc`` for the vendor CRC implementation; and
* ``unitree_sdk2py.comm.motion_switcher.motion_switcher_client`` for an
  optional, explicitly invoked high-level service release.

Nothing in this module imports the optional SDK or initializes DDS at import
 time.  Production bindings are loaded only when an operation is explicitly
started.  Tests inject all vendor objects and never need CycloneDDS.

Low-level output is not a safety or emergency-stop mechanism.  In particular,
``stop``/``cancel`` only suppresses future writes; silence, a closed publisher,
a DDS timeout, and a software exception must not be represented as a physical
safe state.  A physical commissioning approval, operator, observer, restraint,
and independently verified physical stop remain outside this adapter.
"""

from __future__ import annotations

import importlib
import math
import platform
import time
from collections.abc import Callable, Iterable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from numbers import Real
from threading import Event
from types import ModuleType
from typing import Any, TypeAlias, cast

from .errors import (
    UnitreeSdk2CompatibilityError,
    UnitreeSdk2ConfigurationError,
    UnitreeSdk2Error,
    UnitreeSdk2InitializationError,
    UnitreeSdk2UnavailableError,
)

SDK_REVISION = "65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5"
SDK_PACKAGE = "unitree_sdk2py"
LOW_CMD_TOPIC = "rt/lowcmd"
LOW_STATE_TOPIC = "rt/lowstate"
MOTOR_COUNT = 12
SDK_MOTOR_SLOT_COUNT = 20
DEFAULT_STATE_TIMEOUT = 1.0
DEFAULT_STATE_FRESHNESS = 0.25

# These are the official Go2 low-level example's protocol values.  They are
# finite sentinel values in the generated float fields, not a promise that a
# robot will hold position or stop when they are transmitted.
LOW_LEVEL_MODE = 0xFF
MOTOR_MODE = 0x01
POS_STOP_F = 2.146e9
VEL_STOP_F = 16000.0

_CHANNEL_MODULE = "unitree_sdk2py.core.channel"
_DEFAULT_IDL_MODULE = "unitree_sdk2py.idl.default"
_GO2_IDL_MODULE = "unitree_sdk2py.idl.unitree_go.msg.dds_"
_CRC_MODULE = "unitree_sdk2py.utils.crc"
_MOTION_SWITCHER_MODULE = "unitree_sdk2py.comm.motion_switcher.motion_switcher_client"

Importer: TypeAlias = Callable[[str], ModuleType]
Clock: TypeAlias = Callable[[], float]
Sleeper: TypeAlias = Callable[[float], None]
MotionCallback: TypeAlias = Callable[[], object]
OwnershipCallback: TypeAlias = Callable[[], bool]


class UnitreeLowLevelError(UnitreeSdk2Error):
    """Base class for failures in the low-level command boundary."""


class UnitreeLowLevelConfigurationError(UnitreeSdk2ConfigurationError):
    """The explicit interface, timing, or command configuration is invalid."""


class UnitreeLowLevelSafetyError(UnitreeSdk2Error):
    """A required low-level or control-authority gate was not satisfied."""


class UnitreeLowLevelInitializationError(UnitreeSdk2InitializationError):
    """DDS channels or an explicitly requested vendor client failed to initialize."""


class UnitreeLowLevelStateError(UnitreeLowLevelError):
    """A LowState sample was unavailable, malformed, or no longer fresh."""


class UnitreeLowLevelCrcError(UnitreeLowLevelError):
    """A LowCmd CRC could not be computed or was invalid."""


class UnitreeLowLevelPublishError(UnitreeLowLevelError):
    """The vendor publisher rejected or failed to write a LowCmd."""


class UnitreeLowLevelCancelled(UnitreeLowLevelError):
    """A caller requested cancellation before the next low-level write."""


@dataclass(frozen=True)
class MotorCommand:
    """One finite Go2 motor command.

    The order follows the application-facing contract (``q``, ``dq``,
    ``kp``, ``kd``, ``tau``, ``mode``), while the SDK IDL assigns ``mode``
    first.  No limits are silently clamped: the expert caller owns the
    approved bounds for the named robot and experiment.
    """

    q: float
    dq: float
    kp: float
    kd: float
    tau: float
    mode: int = MOTOR_MODE

    def __post_init__(self) -> None:
        for name in ("q", "dq", "kp", "kd", "tau"):
            value = getattr(self, name)
            if not isinstance(value, Real) or isinstance(value, bool):
                raise UnitreeLowLevelConfigurationError(
                    f"motor command {name} must be a real finite number"
                )
            numeric = float(value)
            if not math.isfinite(numeric):
                raise UnitreeLowLevelConfigurationError(
                    f"motor command {name} must be a real finite number"
                )
            object.__setattr__(self, name, numeric)

        if (
            not isinstance(self.mode, int)
            or isinstance(self.mode, bool)
            or not 0 <= self.mode <= 0xFF
        ):
            raise UnitreeLowLevelConfigurationError(
                "motor command mode must be an integer from 0 through 255"
            )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> MotorCommand:
        """Build a command from the six named fields used by the public API."""

        try:
            return cls(
                q=value["q"],
                dq=value["dq"],
                kp=value["kp"],
                kd=value["kd"],
                tau=value["tau"],
                mode=value.get("mode", MOTOR_MODE),
            )
        except KeyError as exc:
            raise UnitreeLowLevelConfigurationError(
                f"motor command is missing required field {exc.args[0]!r}"
            ) from exc


MotorCommandLike: TypeAlias = MotorCommand | Mapping[str, Any]
CommandIterable: TypeAlias = Iterable[MotorCommandLike]
CommandSource: TypeAlias = Callable[[Any], CommandIterable] | CommandIterable


@dataclass(frozen=True)
class UnitreeSdk2LowLevelBindings:
    """Injected vendor surface for the low-level adapter.

    ``low_cmd_factory`` and ``low_state_factory`` are the default constructors
    from the pinned SDK's ``idl.default`` module.  ``low_cmd_type`` and
    ``low_state_type`` are the matching generated IDL classes passed to the
    channel constructors.  ``crc`` may be a CRC instance or a callable that
    creates one; the production binding supplies the SDK's ``CRC`` class.
    """

    channel_factory_initialize: Callable[..., Any]
    channel_publisher: Callable[..., Any]
    channel_subscriber: Callable[..., Any]
    low_cmd_type: Any
    low_state_type: Any
    low_cmd_factory: Callable[[], Any]
    low_state_factory: Callable[[], Any]
    crc: Any
    motion_switcher_client: Callable[[], Any] | None = None

    @classmethod
    def load(
        cls,
        importer: Importer = importlib.import_module,
        *,
        include_motion_switcher: bool = False,
    ) -> UnitreeSdk2LowLevelBindings:
        """Lazily load the source-verified SDK2 symbols.

        The optional motion switcher import is omitted unless a caller asks for
        the explicit SDK-backed release helper.  A caller may instead inject a
        release callback or an already recorded confirmation and never import
        that service client.
        """

        try:
            channel = importer(_CHANNEL_MODULE)
            defaults = importer(_DEFAULT_IDL_MODULE)
            go2_idl = importer(_GO2_IDL_MODULE)
            crc_module = importer(_CRC_MODULE)
            motion_switcher = (
                importer(_MOTION_SWITCHER_MODULE) if include_motion_switcher else None
            )

            values = (
                channel.ChannelFactoryInitialize,
                channel.ChannelPublisher,
                channel.ChannelSubscriber,
                go2_idl.LowCmd_,
                go2_idl.LowState_,
                defaults.unitree_go_msg_dds__LowCmd_,
                defaults.unitree_go_msg_dds__LowState_,
                crc_module.CRC,
            )
            motion_factory = (
                motion_switcher.MotionSwitcherClient
                if motion_switcher is not None
                else None
            )
        except AttributeError as exc:
            raise UnitreeSdk2CompatibilityError(
                "the pinned Unitree SDK2 low-level modules do not expose the "
                "expected ChannelPublisher/ChannelSubscriber, Go2 LowCmd_/LowState_, "
                f"or CRC symbols; verify revision {SDK_REVISION}"
            ) from exc
        except Exception as exc:
            raise UnitreeSdk2UnavailableError(
                "Unitree SDK2 low-level bindings are unavailable; this is an "
                "optional Linux hardware profile. Install the pinned package "
                f"revision {SDK_REVISION} and CycloneDDS separately"
            ) from exc

        return cls(*values, motion_switcher_client=motion_factory)

    # Vendor-spelled aliases make the binding reviewable against the official
    # example without requiring those names to be imported at module import.
    @property
    def ChannelFactoryInitialize(self) -> Callable[..., Any]:
        return self.channel_factory_initialize

    @property
    def ChannelPublisher(self) -> Callable[..., Any]:
        return self.channel_publisher

    @property
    def ChannelSubscriber(self) -> Callable[..., Any]:
        return self.channel_subscriber

    @property
    def LowCmd_(self) -> Any:
        return self.low_cmd_type

    @property
    def LowState_(self) -> Any:
        return self.low_state_type

    @property
    def CRC(self) -> Any:
        return self.crc


# Short aliases are useful to composition roots and keep the explicit class
# available for code that wants the SDK2 provenance in its type name.
LowLevelBindings = UnitreeSdk2LowLevelBindings
UnitreeLowLevelBindings = UnitreeSdk2LowLevelBindings


@dataclass(frozen=True)
class TimedPublishResult:
    """Result of one bounded timed publishing run."""

    published: int
    cancelled: bool
    elapsed: float


class UnitreeGo2LowLevel:
    """A gated Go2 low-level publisher using the pinned SDK2 Python surface.

    Construction is offline and does not import the vendor package, initialize
    DDS, construct a channel, or call a service.  :meth:`initialize` is the
    first operation that can create those resources.  :meth:`publish_once` and
    :meth:`publish_timed` require all four explicit safety confirmations and an
    explicit motion-service release/ownership callback or confirmation.

    A timed run always has a finite, caller-supplied duration and period.  It
    does not send a guessed stop command at the end and does not claim that
    silence is safe.  Call :meth:`stop`/ :meth:`cancel` to suppress future
    writes, then use the approved physical stop procedure when required.
    """

    name = "unitree-go2-low-level"
    motor_count = MOTOR_COUNT

    def __init__(
        self,
        *,
        interface: str | None = None,
        network_interface: str | None = None,
        domain_id: int,
        hardware_enabled: bool,
        operator_confirmed: bool,
        expert_low_level_confirmed: bool,
        robot_restrained_confirmed: bool,
        bindings: UnitreeSdk2LowLevelBindings | None = None,
        importer: Importer = importlib.import_module,
        clock: Clock | None = None,
        sleep: Sleeper | None = None,
        platform_name: str | None = None,
        state_timeout: float = DEFAULT_STATE_TIMEOUT,
        state_freshness: float = DEFAULT_STATE_FRESHNESS,
        motion_service_release: MotionCallback | None = None,
        motion_ownership_confirmation: OwnershipCallback | None = None,
        motion_service_released: bool = False,
        motion_ownership_confirmed: bool = False,
    ) -> None:
        if interface is None:
            interface = network_interface
        elif network_interface is not None and interface != network_interface:
            raise UnitreeLowLevelConfigurationError(
                "interface and network_interface disagree; supply one interface"
            )
        self.interface = self._require_interface(interface or "")
        self.domain_id = self._require_domain(domain_id)
        self._require_bool("hardware_enabled", hardware_enabled)
        self._require_bool("operator_confirmed", operator_confirmed)
        self._require_bool("expert_low_level_confirmed", expert_low_level_confirmed)
        self._require_bool("robot_restrained_confirmed", robot_restrained_confirmed)
        self._require_bool("motion_service_released", motion_service_released)
        self._require_bool("motion_ownership_confirmed", motion_ownership_confirmed)

        self.hardware_enabled = hardware_enabled
        self.operator_confirmed = operator_confirmed
        self.expert_low_level_confirmed = expert_low_level_confirmed
        self.robot_restrained_confirmed = robot_restrained_confirmed
        self._motion_service_release = motion_service_release
        self._motion_ownership_confirmation = motion_ownership_confirmation
        self._motion_service_released = motion_service_released
        self._motion_ownership_confirmed = motion_ownership_confirmed

        self.state_timeout = self._require_positive_finite(
            "state_timeout", state_timeout
        )
        self.state_freshness = self._require_positive_finite(
            "state_freshness", state_freshness
        )
        self._bindings = bindings
        self._loaded_bindings: UnitreeSdk2LowLevelBindings | None = None
        self._importer = importer
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._platform_name = platform_name
        self._publisher: Any | None = None
        self._subscriber: Any | None = None
        self._initialized = False
        self._closed = False
        self._cancel_event = Event()
        self._last_state: Any | None = None
        self._last_state_at: float | None = None
        self._motion_boundary_checked = False

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()

    @property
    def last_state(self) -> Any | None:
        return self._last_state

    @property
    def last_state_age(self) -> float | None:
        if self._last_state_at is None:
            return None
        return max(0.0, self._now() - self._last_state_at)

    @property
    def bindings(self) -> UnitreeSdk2LowLevelBindings | None:
        return self._bindings or self._loaded_bindings

    def capabilities(self) -> dict[str, Any]:
        """Describe the explicit command boundary without touching the SDK."""

        return {
            "adapter": self.name,
            "sdk_revision": SDK_REVISION,
            "interface": self.interface,
            "domain_id": self.domain_id,
            "low_state_topic": LOW_STATE_TOPIC,
            "low_cmd_topic": LOW_CMD_TOPIC,
            "motor_count": MOTOR_COUNT,
            "hardware_enabled": self.hardware_enabled,
            "timed_duration_required": True,
            "physical_stop_required": True,
        }

    get_capabilities = capabilities

    def initialize(self) -> None:
        """Initialize the explicit DDS interface and low-state channels."""

        if self._initialized:
            return
        if self._closed:
            raise UnitreeLowLevelInitializationError(
                "the low-level session was closed and cannot be reinitialized"
            )
        if (
            self._bindings is None
            and (self._platform_name or platform.system()) != "Linux"
        ):
            raise UnitreeSdk2InitializationError(
                "the Unitree SDK2 low-level runtime is supported only on Linux; "
                "inject fakes for offline tests"
            )

        bindings = self._ensure_bindings()
        publisher: Any | None = None
        subscriber: Any | None = None
        try:
            result = bindings.channel_factory_initialize(self.domain_id, self.interface)
            if result is False:
                raise RuntimeError("ChannelFactoryInitialize returned false")

            # Create the subscriber before the publisher.  A publish operation
            # will still perform a new Read immediately before every write.
            subscriber = bindings.channel_subscriber(
                LOW_STATE_TOPIC, bindings.low_state_type
            )
            self._call_init(subscriber, "subscriber", None, 0)
            publisher = bindings.channel_publisher(LOW_CMD_TOPIC, bindings.low_cmd_type)
            self._call_init(publisher, "publisher")
        except UnitreeLowLevelError:
            self._close_resource(subscriber)
            self._close_resource(publisher)
            raise
        except Exception as exc:
            self._close_resource(subscriber)
            self._close_resource(publisher)
            raise UnitreeLowLevelInitializationError(
                "Unitree SDK2 low-level DDS channel initialization failed for "
                f"interface {self.interface!r}, domain {self.domain_id}, and "
                f"topics {LOW_STATE_TOPIC!r}/{LOW_CMD_TOPIC!r}"
            ) from exc

        self._subscriber = subscriber
        self._publisher = publisher
        self._initialized = True

    init = initialize

    def close(self) -> None:
        """Close vendor channels and permanently end this session."""

        if self._closed:
            return
        self._cancel_event.set()
        self._close_resource(self._subscriber)
        self._close_resource(self._publisher)
        self._subscriber = None
        self._publisher = None
        self._initialized = False
        self._closed = True

    def stop(self) -> None:
        """Suppress future writes; this is not a physical stop or safe state."""

        self._cancel_event.set()

    cancel = stop

    def read_low_state(self, timeout: float | None = None) -> Any:
        """Read and return one fresh LowState sample from ``rt/lowstate``."""

        self._ensure_initialized()
        self._check_not_cancelled()
        timeout_value = (
            self.state_timeout
            if timeout is None
            else self._require_positive_finite("state timeout", timeout)
        )
        subscriber = self._subscriber
        if subscriber is None:  # pragma: no cover - guarded by initialize
            raise UnitreeLowLevelStateError("low-state subscriber is not available")
        reader = getattr(subscriber, "Read", None)
        if not callable(reader):
            reader = getattr(subscriber, "read", None)
        if not callable(reader):
            raise UnitreeLowLevelStateError(
                "the injected ChannelSubscriber has no Read/read method"
            )

        try:
            state = reader(timeout_value)
        except Exception as exc:
            self._cancel_event.set()
            raise UnitreeLowLevelStateError(
                "reading rt/lowstate failed; no command was sent"
            ) from exc
        if state is None:
            self._cancel_event.set()
            raise UnitreeLowLevelStateError(
                "rt/lowstate returned no sample before the explicit timeout"
            )

        motor_state = getattr(state, "motor_state", None)
        if motor_state is None:
            self._cancel_event.set()
            raise UnitreeLowLevelStateError(
                "LowState has no usable motor_state sequence"
            )
        try:
            motor_slots = len(motor_state)
        except (TypeError, AttributeError) as exc:
            self._cancel_event.set()
            raise UnitreeLowLevelStateError(
                "LowState has no usable motor_state sequence"
            ) from exc
        if motor_slots < MOTOR_COUNT:
            self._cancel_event.set()
            raise UnitreeLowLevelStateError(
                f"LowState motor_state has {motor_slots} slots; expected at least "
                f"{MOTOR_COUNT} for Go2"
            )

        self._last_state = state
        self._last_state_at = self._now()
        return state

    read_state = read_low_state
    low_state = read_low_state

    def build_low_command(
        self,
        commands: CommandIterable,
    ) -> Any:
        """Construct a complete Go2 LowCmd and assign its CRC.

        Exactly twelve command records are accepted.  The generated Go2 IDL
        contains twenty motor slots; this adapter deliberately accepts exactly
        twelve Go2 joint records, initializes every available vendor slot to
        the official neutral sentinel, and rejects an accidental
        thirteen-to-twenty-joint command vector.
        """

        normalized = self._normalize_commands(commands)
        bindings = self._ensure_bindings()
        try:
            message = bindings.low_cmd_factory()
            motor_slots = message.motor_cmd
            if len(motor_slots) < MOTOR_COUNT:
                raise UnitreeLowLevelConfigurationError(
                    "LowCmd motor_cmd has fewer than 12 slots"
                )
            message.head[0] = 0xFE
            message.head[1] = 0xEF
            message.level_flag = LOW_LEVEL_MODE
            message.gpio = 0
            for motor in motor_slots:
                motor.mode = MOTOR_MODE
                motor.q = POS_STOP_F
                motor.dq = VEL_STOP_F
                motor.kp = 0.0
                motor.kd = 0.0
                motor.tau = 0.0
        except UnitreeLowLevelError:
            raise
        except Exception as exc:
            raise UnitreeSdk2CompatibilityError(
                "the injected/pinned LowCmd_ constructor did not provide a "
                "usable motor_cmd sequence"
            ) from exc

        for index, command in enumerate(normalized):
            motor = motor_slots[index]
            try:
                motor.mode = command.mode
                motor.q = command.q
                motor.dq = command.dq
                motor.kp = command.kp
                motor.kd = command.kd
                motor.tau = command.tau
            except Exception as exc:
                raise UnitreeSdk2CompatibilityError(
                    f"LowCmd motor slot {index} does not expose the pinned "
                    "mode/q/dq/kp/kd/tau fields"
                ) from exc

        try:
            message.crc = 0
            crc = bindings.crc
            if callable(crc) and not callable(getattr(crc, "Crc", None)):
                crc = crc()
            crc_method = getattr(crc, "Crc", None)
            if not callable(crc_method):
                raise TypeError("CRC binding has no Crc method")
            computed = crc_method(message)
        except UnitreeLowLevelError:
            raise
        except Exception as exc:
            raise UnitreeLowLevelCrcError(
                "the pinned Unitree CRC could not serialize or compute LowCmd"
            ) from exc
        if (
            not isinstance(computed, int)
            or isinstance(computed, bool)
            or not 0 <= computed <= 0xFFFFFFFF
        ):
            raise UnitreeLowLevelCrcError(
                "the CRC binding returned a value outside uint32"
            )
        message.crc = computed
        return message

    construct_command = build_low_command
    build_command = build_low_command

    def publish_once(
        self,
        commands: CommandSource,
        *,
        state_timeout: float | None = None,
    ) -> Any:
        """Read fresh LowState, build a full command, compute CRC, and write once."""

        self._assert_publish_authorized()
        # Reject missing authority/release before touching DDS.  Explicit
        # callbacks or an SDK MotionSwitcher may initialize what they need.
        self._ensure_motion_boundary()
        self._ensure_initialized()
        self._check_not_cancelled()
        state = self.read_low_state(state_timeout)
        self._require_fresh_state()
        if callable(commands):
            provider = cast(Callable[[Any], CommandIterable], commands)
            resolved: CommandIterable = provider(state)
        else:
            resolved = cast(CommandIterable, commands)
        message = self.build_low_command(resolved)
        # The command provider and CRC work happen after the read.  Recheck the
        # age immediately before Write so a slow provider cannot publish stale
        # state under the caller's originally fresh sample.
        self._require_fresh_state()
        self._check_not_cancelled()
        publisher = self._publisher
        if publisher is None:  # pragma: no cover - guarded by initialize
            raise UnitreeLowLevelPublishError("low-command publisher is not available")
        writer = getattr(publisher, "Write", None)
        if not callable(writer):
            writer = getattr(publisher, "write", None)
        if not callable(writer):
            raise UnitreeLowLevelPublishError(
                "the injected ChannelPublisher has no Write/write method"
            )
        try:
            result = writer(message)
        except Exception as exc:
            self._cancel_event.set()
            raise UnitreeLowLevelPublishError(
                "rt/lowcmd write failed; future writes are suppressed"
            ) from exc
        if result is False:
            self._cancel_event.set()
            raise UnitreeLowLevelPublishError(
                "rt/lowcmd publisher rejected the command; future writes are suppressed"
            )
        return message

    publish = publish_once
    write_once = publish_once

    def publish_timed(
        self,
        commands: CommandSource,
        period: float,
        duration: float,
        *,
        state_timeout: float | None = None,
    ) -> TimedPublishResult:
        """Publish at an explicit period for one finite, bounded duration.

        The first command is attempted immediately.  Each iteration obtains a
        new LowState before writing.  Cancellation stops the loop without
        inventing a final command; the caller must use the approved physical
        response and must not interpret silence as safe.
        """

        period_value = self._require_positive_finite("period", period)
        duration_value = self._require_positive_finite("duration", duration)
        started = self._now()
        deadline = started + duration_value
        if not math.isfinite(deadline):
            raise UnitreeLowLevelConfigurationError(
                "duration is too large to represent a bounded monotonic deadline"
            )
        next_publish = started
        published = 0
        cancelled = False

        try:
            while True:
                self._check_not_cancelled()
                now = self._now()
                if published > 0 and now >= deadline:
                    break
                if now < next_publish:
                    remaining = min(next_publish - now, max(0.0, deadline - now))
                    if remaining <= 0.0:
                        break
                    self._sleep(remaining)
                    continue
                self.publish_once(commands, state_timeout=state_timeout)
                published += 1
                next_publish += period_value
        except UnitreeLowLevelCancelled:
            cancelled = True
        elapsed = max(0.0, self._now() - started)
        return TimedPublishResult(
            published=published,
            cancelled=cancelled or self.cancelled,
            elapsed=elapsed,
        )

    run_timed = publish_timed
    publish_loop = publish_timed
    run = publish_timed

    def release_motion_service(self) -> None:
        """Explicitly release/check the SDK motion service before low-level use.

        A supplied callback is preferred because the application can perform
        its approved authority handoff.  If an injected/loaded
        ``MotionSwitcherClient`` is available, this method calls only its
        ``Init``, ``CheckMode``, and (when a mode is active) ``ReleaseMode``;
        it never calls ``SportClient`` or invents a stand/down motion.  The
        method is never called automatically by ``publish_once``.
        """

        self._assert_publish_authorized()
        self._ensure_initialized()
        if self._motion_service_release is not None:
            try:
                result = self._motion_service_release()
            except Exception as exc:
                raise UnitreeLowLevelSafetyError(
                    "the explicit motion-service release callback failed"
                ) from exc
            if result is False:
                raise UnitreeLowLevelSafetyError(
                    "the explicit motion-service release callback rejected release"
                )
            self._motion_service_released = True
            self._motion_ownership_confirmed = True
            self._motion_boundary_checked = True
            return

        bindings = self._ensure_bindings(include_motion_switcher=True)
        factory = bindings.motion_switcher_client
        if factory is None:
            raise UnitreeLowLevelSafetyError(
                "low-level publish requires an explicit motion-service release or "
                "ownership confirmation; provide motion_service_release, "
                "motion_service_released=True, or an injected MotionSwitcherClient"
            )
        try:
            client = factory()
            self._call_init(client, "motion switcher")
            check_mode = getattr(client, "CheckMode", None)
            release_mode = getattr(client, "ReleaseMode", None)
            if not callable(check_mode) or not callable(release_mode):
                raise TypeError("MotionSwitcherClient lacks CheckMode/ReleaseMode")
            check = cast(Callable[[], tuple[Any, Any]], check_mode)
            release = cast(Callable[[], tuple[Any, Any]], release_mode)
            status, mode = check()
            if status != 0 or not isinstance(mode, Mapping):
                raise RuntimeError("MotionSwitcherClient.CheckMode failed")
            if mode.get("name"):
                release_status, _ = release()
                if release_status != 0:
                    raise RuntimeError(
                        f"MotionSwitcherClient.ReleaseMode returned {release_status}"
                    )
        except UnitreeLowLevelError:
            raise
        except Exception as exc:
            raise UnitreeLowLevelSafetyError(
                "the explicit MotionSwitcherClient release/check failed; no "
                "low-level command was sent"
            ) from exc
        self._motion_service_released = True
        self._motion_ownership_confirmed = True
        self._motion_boundary_checked = True

    def confirm_motion_service_release(self, confirmed: bool = True) -> None:
        """Record an operator-approved release/ownership confirmation."""

        self._require_bool("confirmed", confirmed)
        self._motion_service_released = confirmed
        self._motion_ownership_confirmed = confirmed
        self._motion_boundary_checked = False

    def confirm_motion_ownership(self, confirmed: bool = True) -> None:
        """Record or clear the explicit low-level ownership confirmation."""

        self._require_bool("confirmed", confirmed)
        self._motion_ownership_confirmed = confirmed
        self._motion_boundary_checked = False

    def _assert_publish_authorized(self) -> None:
        required = (
            ("hardware_enabled", self.hardware_enabled),
            ("operator_confirmed", self.operator_confirmed),
            ("expert_low_level_confirmed", self.expert_low_level_confirmed),
            ("robot_restrained_confirmed", self.robot_restrained_confirmed),
        )
        missing = [name for name, value in required if value is not True]
        if missing:
            raise UnitreeLowLevelSafetyError(
                "low-level publishing requires explicit True confirmations for: "
                + ", ".join(missing)
            )

    def _ensure_motion_boundary(self) -> None:
        if self._motion_boundary_checked:
            return
        if self._motion_service_release is not None:
            self.release_motion_service()
        if self._motion_ownership_confirmation is not None:
            try:
                confirmed = self._motion_ownership_confirmation()
            except Exception as exc:
                raise UnitreeLowLevelSafetyError(
                    "the explicit motion-ownership confirmation callback failed"
                ) from exc
            if confirmed is not True:
                raise UnitreeLowLevelSafetyError(
                    "the explicit motion-ownership confirmation callback rejected "
                    "low-level ownership"
                )
            self._motion_ownership_confirmed = True
            self._motion_boundary_checked = True
            return
        if self._motion_service_released or self._motion_ownership_confirmed:
            self._motion_boundary_checked = True
            return
        raise UnitreeLowLevelSafetyError(
            "low-level publishing requires an explicit motion-service release or "
            "ownership callback/confirmation; silence is not a safe-state claim"
        )

    def _require_fresh_state(self) -> None:
        if self._last_state is None or self._last_state_at is None:
            raise UnitreeLowLevelStateError(
                "a fresh LowState sample is required immediately before publish"
            )
        age = self._now() - self._last_state_at
        if age < 0.0 or age > self.state_freshness:
            self._cancel_event.set()
            raise UnitreeLowLevelStateError(
                f"LowState is stale ({age:.6f}s old; "
                f"limit {self.state_freshness:.6f}s); no command was sent"
            )

    def _normalize_commands(
        self, commands: CommandIterable
    ) -> tuple[MotorCommand, ...]:
        if isinstance(commands, (str, bytes, Mapping)):
            raise UnitreeLowLevelConfigurationError(
                "commands must be an iterable of exactly 12 motor command records"
            )
        try:
            values = tuple(commands)
        except TypeError as exc:
            raise UnitreeLowLevelConfigurationError(
                "commands must be an iterable of exactly 12 motor command records"
            ) from exc
        if len(values) != MOTOR_COUNT:
            raise UnitreeLowLevelConfigurationError(
                f"exactly {MOTOR_COUNT} motor commands are required, got {len(values)}"
            )
        normalized: list[MotorCommand] = []
        for index, value in enumerate(values):
            if isinstance(value, MotorCommand):
                normalized.append(value)
            elif isinstance(value, Mapping):
                normalized.append(MotorCommand.from_mapping(value))
            else:
                raise UnitreeLowLevelConfigurationError(
                    f"motor command {index} must be MotorCommand or a field mapping"
                )
        return tuple(normalized)

    def _ensure_bindings(
        self,
        *,
        include_motion_switcher: bool = False,
    ) -> UnitreeSdk2LowLevelBindings:
        if self._bindings is not None:
            if (
                include_motion_switcher
                and self._bindings.motion_switcher_client is None
            ):
                raise UnitreeSdk2CompatibilityError(
                    "the injected bindings do not include MotionSwitcherClient"
                )
            return self._bindings
        if self._loaded_bindings is None or (
            include_motion_switcher
            and self._loaded_bindings.motion_switcher_client is None
        ):
            self._loaded_bindings = UnitreeSdk2LowLevelBindings.load(
                self._importer,
                include_motion_switcher=include_motion_switcher,
            )
        return self._loaded_bindings

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    def _check_not_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise UnitreeLowLevelCancelled(
                "low-level session was stopped/cancelled; no command was sent"
            )

    def _now(self) -> float:
        try:
            value = self._clock()
        except Exception as exc:
            raise UnitreeLowLevelError("the monotonic clock failed") from exc
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(float(value))
        ):
            raise UnitreeLowLevelError(
                "the monotonic clock returned a non-finite value"
            )
        return float(value)

    @staticmethod
    def _call_init(resource: Any, label: str, *args: Any) -> None:
        init = getattr(resource, "Init", None)
        if not callable(init):
            init = getattr(resource, "init", None)
        if not callable(init):
            raise UnitreeSdk2CompatibilityError(
                f"the injected {label} has no Init/init method"
            )
        init(*args)

    @staticmethod
    def _close_resource(resource: Any | None) -> None:
        if resource is None:
            return
        close = getattr(resource, "Close", None)
        if not callable(close):
            close = getattr(resource, "close", None)
        if callable(close):
            # Cleanup must never hide the initialization/publish failure.
            with suppress(Exception):
                close()

    @staticmethod
    def _require_interface(interface: str) -> str:
        if not isinstance(interface, str) or not interface.strip():
            raise UnitreeLowLevelConfigurationError(
                "interface is required; select the robot-facing interface explicitly"
            )
        if interface != interface.strip():
            raise UnitreeLowLevelConfigurationError(
                "interface must not contain leading or trailing whitespace"
            )
        return interface

    @staticmethod
    def _require_domain(domain_id: int) -> int:
        if (
            not isinstance(domain_id, int)
            or isinstance(domain_id, bool)
            or domain_id < 0
        ):
            raise UnitreeLowLevelConfigurationError(
                "domain_id must be an explicit non-negative integer"
            )
        return domain_id

    @staticmethod
    def _require_bool(name: str, value: bool) -> None:
        if not isinstance(value, bool):
            raise UnitreeLowLevelConfigurationError(f"{name} must be an explicit bool")

    @staticmethod
    def _require_positive_finite(name: str, value: float) -> float:
        if not isinstance(value, Real) or isinstance(value, bool):
            raise UnitreeLowLevelConfigurationError(f"{name} must be finite and > 0")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric <= 0.0:
            raise UnitreeLowLevelConfigurationError(f"{name} must be finite and > 0")
        return numeric


# Public aliases used by composition roots that prefer a shorter class name.
UnitreeSdk2LowLevel = UnitreeGo2LowLevel
Go2LowLevel = UnitreeGo2LowLevel
LowLevelController = UnitreeGo2LowLevel
UnitreeGo2LowLevelController = UnitreeGo2LowLevel
LowLevelMotorCommand = MotorCommand
Go2MotorCommand = MotorCommand

# Match the repository's other SDK2 adapters for callers that prefer the
# longer error names.
UnitreeSdk2LowLevelError = UnitreeLowLevelError
UnitreeSdk2LowLevelConfigurationError = UnitreeLowLevelConfigurationError
UnitreeSdk2LowLevelSafetyError = UnitreeLowLevelSafetyError
UnitreeSdk2LowLevelInitializationError = UnitreeLowLevelInitializationError
UnitreeSdk2LowLevelStateError = UnitreeLowLevelStateError
UnitreeSdk2LowLevelCrcError = UnitreeLowLevelCrcError
UnitreeSdk2LowLevelPublishError = UnitreeLowLevelPublishError


__all__ = [
    "CommandSource",
    "DEFAULT_STATE_FRESHNESS",
    "DEFAULT_STATE_TIMEOUT",
    "Go2LowLevel",
    "Go2MotorCommand",
    "LOW_CMD_TOPIC",
    "LOW_LEVEL_MODE",
    "LOW_STATE_TOPIC",
    "LowLevelBindings",
    "LowLevelController",
    "LowLevelMotorCommand",
    "MOTOR_COUNT",
    "MOTOR_MODE",
    "MotorCommand",
    "POS_STOP_F",
    "SDK_MOTOR_SLOT_COUNT",
    "SDK_PACKAGE",
    "SDK_REVISION",
    "TimedPublishResult",
    "UnitreeGo2LowLevel",
    "UnitreeGo2LowLevelController",
    "UnitreeLowLevel",
    "UnitreeLowLevelBindings",
    "UnitreeLowLevelCancelled",
    "UnitreeLowLevelConfigurationError",
    "UnitreeLowLevelCrcError",
    "UnitreeLowLevelError",
    "UnitreeLowLevelInitializationError",
    "UnitreeLowLevelPublishError",
    "UnitreeLowLevelSafetyError",
    "UnitreeLowLevelStateError",
    "UnitreeSdk2LowLevel",
    "UnitreeSdk2LowLevelConfigurationError",
    "UnitreeSdk2LowLevelCrcError",
    "UnitreeSdk2LowLevelError",
    "UnitreeSdk2LowLevelInitializationError",
    "UnitreeSdk2LowLevelPublishError",
    "UnitreeSdk2LowLevelSafetyError",
    "UnitreeSdk2LowLevelStateError",
    "UnitreeSdk2LowLevelBindings",
    "VEL_STOP_F",
]

# Keep the aliases in __all__ valid without introducing another implementation.
UnitreeLowLevel = UnitreeGo2LowLevel
