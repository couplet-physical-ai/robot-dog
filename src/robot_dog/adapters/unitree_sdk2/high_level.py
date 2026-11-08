"""Explicit, gated Go2 high-level SportClient adapter.

The vendor boundary in this module is intentionally lazy.  Importing it does
not import ``unitree_sdk2py``, create a DDS participant, or select a robot.
Production construction requires an explicit interface and DDS domain; tests
can inject :class:`UnitreeSdk2HighLevelBindings` and remain entirely offline.

The action names and argument shapes below are from the pinned official
``unitree_sdk2_python`` revision ``65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5``.
This wrapper does not hide the vendor's special motions.  They are present in
the catalog and remain available after the explicit safety gates pass.
"""

from __future__ import annotations

import importlib
import math
import platform
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType
from typing import Any

SDK_REVISION = "65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5"
SDK_PACKAGE = "unitree_sdk2py"
DEFAULT_TIMEOUT_SECONDS = 10.0

_CHANNEL_MODULE = "unitree_sdk2py.core.channel"
_SPORT_MODULE = "unitree_sdk2py.go2.sport.sport_client"

Importer = Callable[[str], ModuleType]
Clock = Callable[[], float]
Sleeper = Callable[[float], None]


class UnitreeSdk2HighLevelError(RuntimeError):
    """Base class for failures at the Go2 SportClient boundary."""


class UnitreeSdk2HighLevelConfigurationError(ValueError, UnitreeSdk2HighLevelError):
    """The explicit DDS, timeout, or movement configuration is invalid."""


class UnitreeSdk2HighLevelUnavailableError(UnitreeSdk2HighLevelError):
    """The optional Unitree SDK or one of its native dependencies is absent."""


class UnitreeSdk2HighLevelInitializationError(UnitreeSdk2HighLevelError):
    """ChannelFactory or SportClient initialization failed."""


class UnitreeSdk2HighLevelCompatibilityError(UnitreeSdk2HighLevelError):
    """The loaded SDK does not expose the pinned SportClient surface."""


class UnitreeSdk2HighLevelSafetyError(PermissionError, UnitreeSdk2HighLevelError):
    """An explicit high-level command gate was not satisfied."""


class HazardousMotionAcknowledgementRequired(UnitreeSdk2HighLevelSafetyError):
    """A special-motion action needs the separate hazardous-motion acknowledgement."""


class IntentionalInvocationRequired(UnitreeSdk2HighLevelSafetyError):
    """Generic invocation requires the caller to opt in explicitly."""


class UnitreeSdk2HighLevelCommandError(UnitreeSdk2HighLevelError):
    """A vendor call returned a value that cannot be normalized."""


class MoveSessionError(UnitreeSdk2HighLevelSafetyError):
    """A bounded Move deadman/session is missing, inactive, or expired."""


# Short names are useful to callers without losing the descriptive exceptions.
HighLevelSafetyError = UnitreeSdk2HighLevelSafetyError
HighLevelConfigurationError = UnitreeSdk2HighLevelConfigurationError
HighLevelInitializationError = UnitreeSdk2HighLevelInitializationError


def _require_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise UnitreeSdk2HighLevelConfigurationError(f"{name} must be a bool")
    return value


def _finite_positive(value: object, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise UnitreeSdk2HighLevelConfigurationError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise UnitreeSdk2HighLevelConfigurationError(
            f"{name} must be finite and greater than zero"
        )
    return result


def _finite_nonnegative(value: object, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise UnitreeSdk2HighLevelConfigurationError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise UnitreeSdk2HighLevelConfigurationError(
            f"{name} must be finite and non-negative"
        )
    return result


def _resolve_bool(
    primary: bool | None,
    aliases: tuple[tuple[str, bool | None], ...],
    name: str,
) -> bool:
    values: list[tuple[str, bool]] = []
    if primary is not None:
        values.append((name, _require_bool(primary, name)))
    for alias_name, value in aliases:
        if value is not None:
            values.append((alias_name, _require_bool(value, alias_name)))
    if not values:
        return False
    first = values[0][1]
    if any(value != first for _, value in values[1:]):
        supplied = ", ".join(f"{field}={value!r}" for field, value in values)
        raise UnitreeSdk2HighLevelConfigurationError(
            f"conflicting acknowledgement values: {supplied}"
        )
    return first


@dataclass(frozen=True)
class SportClientSafetyAcknowledgements:
    """The three independent acknowledgements required by this adapter.

    ``hardware_enabled`` and ``operator_acknowledged`` gate every command.
    ``hazardous_motion_acknowledged`` is a separate second gate for flips,
    jumps, handstand, dance, and free-mode actions.  All values default to
    false; no command-capable object is implicitly armed.
    """

    hardware_enabled: bool = False
    operator_acknowledged: bool = False
    hazardous_motion_acknowledged: bool = False

    def __post_init__(self) -> None:
        _require_bool(self.hardware_enabled, "hardware_enabled")
        _require_bool(self.operator_acknowledged, "operator_acknowledged")
        _require_bool(
            self.hazardous_motion_acknowledged,
            "hazardous_motion_acknowledged",
        )

    @property
    def hardware_enabled_ack(self) -> bool:
        return self.hardware_enabled

    @property
    def operator_ack(self) -> bool:
        return self.operator_acknowledged

    @property
    def hazardous_ack(self) -> bool:
        return self.hazardous_motion_acknowledged


SafetyAcknowledgements = SportClientSafetyAcknowledgements


@dataclass(frozen=True)
class Go2SportClientConfig:
    """Explicit process-level configuration for one Go2 SportClient."""

    network_interface: str
    domain_id: int
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_move_duration_seconds: float = 10.0
    max_forward_mps: float = 1.0
    max_lateral_mps: float = 1.0
    max_yaw_rad_s: float = 1.0
    enable_lease: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.network_interface, str) or not self.network_interface:
            raise UnitreeSdk2HighLevelConfigurationError(
                "network_interface is required and must be non-empty"
            )
        if self.network_interface != self.network_interface.strip():
            raise UnitreeSdk2HighLevelConfigurationError(
                "network_interface must not contain surrounding whitespace"
            )
        if not isinstance(self.domain_id, int) or isinstance(self.domain_id, bool):
            raise UnitreeSdk2HighLevelConfigurationError(
                "domain_id must be an explicit non-negative integer"
            )
        if self.domain_id < 0:
            raise UnitreeSdk2HighLevelConfigurationError(
                "domain_id must be an explicit non-negative integer"
            )
        for field in (
            "timeout_seconds",
            "max_move_duration_seconds",
            "max_forward_mps",
            "max_lateral_mps",
            "max_yaw_rad_s",
        ):
            value = getattr(self, field)
            if field.endswith("duration_seconds") or field == "timeout_seconds":
                _finite_positive(value, field)
            else:
                _finite_nonnegative(value, field)
        _require_bool(self.enable_lease, "enable_lease")

    @property
    def interface(self) -> str:
        """Alias matching the Unitree documentation's interface wording."""

        return self.network_interface


@dataclass(frozen=True)
class UnitreeSdk2HighLevelBindings:
    """Injected vendor entry points for the high-level adapter.

    ``sport_client`` is the pinned ``SportClient`` class.  Supplying this
    dataclass is the supported offline-test seam; it avoids importing the SDK
    and avoids creating DDS objects.
    """

    channel_factory_initialize: Callable[..., Any]
    sport_client: Callable[..., Any]

    @property
    def channel_factory(self) -> Callable[..., Any]:
        return self.channel_factory_initialize

    @property
    def sport_client_type(self) -> Callable[..., Any]:
        return self.sport_client

    @classmethod
    def load(
        cls, importer: Importer = importlib.import_module
    ) -> UnitreeSdk2HighLevelBindings:
        """Load only the channel and Go2 SportClient modules lazily."""

        try:
            channel_module = importer(_CHANNEL_MODULE)
            sport_module = importer(_SPORT_MODULE)
            initialize = channel_module.ChannelFactoryInitialize
            client_type = sport_module.SportClient
        except Exception as exc:
            raise UnitreeSdk2HighLevelUnavailableError(
                "the pinned Unitree SDK2 Python package is unavailable; install "
                f"{SDK_PACKAGE} revision {SDK_REVISION} and its native DDS "
                "dependencies from requirements-unitree.txt"
            ) from exc
        if not callable(initialize) or not callable(client_type):
            raise UnitreeSdk2HighLevelCompatibilityError(
                "the pinned SDK does not expose ChannelFactoryInitialize and "
                f"SportClient at revision {SDK_REVISION}"
            )
        return cls(initialize, client_type)


# A concise alias is convenient for integrations that name the profile simply
# "SportClient" while keeping the vendor class lazy and unshadowed internally.
SportClientBindings = UnitreeSdk2HighLevelBindings


@dataclass(frozen=True)
class SportActionSpec:
    """One source-verified public SportClient action."""

    name: str
    parameters: tuple[str, ...]
    hazardous: bool = False
    requires_hazardous_acknowledgement: bool = False

    @property
    def method_name(self) -> str:
        return self.name

    @property
    def requires_hazardous_ack(self) -> bool:
        return self.requires_hazardous_acknowledgement


# This is deliberately a tuple, rather than a filtered "safe" subset.  The
# pinned source registers all of these actions and exposes all of these methods.
_ACTION_DEFINITIONS: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    ("Damp", (), False),
    ("BalanceStand", (), False),
    ("StopMove", (), False),
    ("StandUp", (), False),
    ("StandDown", (), False),
    ("RecoveryStand", (), False),
    ("Euler", ("roll", "pitch", "yaw"), False),
    ("Move", ("vx", "vy", "vyaw"), False),
    ("Sit", (), False),
    ("RiseSit", (), False),
    ("SpeedLevel", ("level",), False),
    ("Hello", (), False),
    ("Stretch", (), False),
    ("Content", (), False),
    ("Dance1", (), True),
    ("Dance2", (), True),
    ("SwitchJoystick", ("on",), False),
    ("Pose", ("flag",), False),
    ("Scrape", (), False),
    ("FrontFlip", (), True),
    ("FrontJump", (), True),
    ("FrontPounce", (), True),
    ("Heart", (), False),
    ("StaticWalk", (), False),
    ("TrotRun", (), False),
    ("LeftFlip", (), True),
    ("BackFlip", (), True),
    ("HandStand", ("flag",), True),
    ("FreeWalk", (), True),
    ("FreeBound", ("flag",), True),
    ("FreeJump", ("flag",), True),
    ("FreeAvoid", ("flag",), True),
    ("ClassicWalk", ("flag",), False),
    ("WalkUpright", ("flag",), False),
    ("CrossStep", ("flag",), False),
    ("AutoRecoverySet", ("enabled",), False),
    ("AutoRecoveryGet", (), False),
    ("SwitchAvoidMode", (), False),
)

SPORT_COMMAND_CATALOG: tuple[SportActionSpec, ...] = tuple(
    SportActionSpec(name, parameters, hazardous, hazardous)
    for name, parameters, hazardous in _ACTION_DEFINITIONS
)
COMMAND_CATALOG = SPORT_COMMAND_CATALOG
_ACTIONS_BY_NAME = {entry.name: entry for entry in SPORT_COMMAND_CATALOG}
_ACTIONS_BY_NORMALIZED_NAME = {
    "".join(character for character in entry.name.lower() if character.isalnum()): entry
    for entry in SPORT_COMMAND_CATALOG
}


def command_catalog() -> tuple[SportActionSpec, ...]:
    """Return every source-verified public Go2 SportClient action."""

    return SPORT_COMMAND_CATALOG


def _normalize_action_name(action: str) -> SportActionSpec:
    if not isinstance(action, str) or not action.strip():
        raise UnitreeSdk2HighLevelConfigurationError(
            "action name must be a non-empty SportClient catalog name"
        )
    normalized = "".join(character for character in action if character.isalnum())
    spec = _ACTIONS_BY_NORMALIZED_NAME.get(normalized.lower())
    if spec is None:
        raise UnitreeSdk2HighLevelConfigurationError(
            f"unknown Go2 SportClient action {action!r}; use command_catalog()"
        )
    return spec


def _normalize_code(value: object, action: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise UnitreeSdk2HighLevelCommandError(
            f"{action} returned a non-integer vendor status code"
        )
    return int(value)


@dataclass(frozen=True)
class SportCommandResult:
    """Stable result shape for both ``int`` and ``(code, data)`` vendor returns."""

    action: str
    code: int
    data: Any = None
    error: str | None = None

    @property
    def status_code(self) -> int:
        return self.code

    @property
    def return_code(self) -> int:
        return self.code

    @property
    def ok(self) -> bool:
        return self.error is None and self.code == 0

    @property
    def success(self) -> bool:
        return self.ok

    @property
    def accepted(self) -> bool:
        return self.ok

    def __int__(self) -> int:
        return self.code

    def __bool__(self) -> bool:
        return self.ok

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "action": self.action,
            "code": self.code,
            "data": self.data,
            "ok": self.ok,
        }
        if self.error is not None:
            value["error"] = self.error
        return value


NormalizedSportResult = SportCommandResult


def _normalize_vendor_result(action: str, value: object) -> SportCommandResult:
    if isinstance(value, tuple):
        if len(value) != 2:
            raise UnitreeSdk2HighLevelCommandError(
                f"{action} returned an unexpected tuple; expected (code, data)"
            )
        code, data = value
        return SportCommandResult(action, _normalize_code(code, action), data)
    return SportCommandResult(action, _normalize_code(value, action))


class BoundedMove:
    """A context-managed, deadman-protected bounded ``Move`` operation.

    The initial command is sent by ``__enter__``.  ``refresh()`` is the only
    way to renew it, and both the movement duration and the deadman timeout are
    finite.  ``__exit__`` always attempts ``StopMove``; the helper also does so
    if the initial command raises and in ``run()``'s ``finally`` block.
    """

    def __init__(
        self,
        client: Go2SportClient,
        vx: float,
        vy: float,
        vyaw: float,
        duration_seconds: float,
        session_id: str,
        deadman_timeout_seconds: float,
        refresh_period_seconds: float,
    ) -> None:
        self._client = client
        self.vx = vx
        self.vy = vy
        self.vyaw = vyaw
        self.duration_seconds = duration_seconds
        self.session_id = session_id
        self.deadman_timeout_seconds = deadman_timeout_seconds
        self.refresh_period_seconds = refresh_period_seconds
        self._started_at: float | None = None
        self._last_refresh_at: float | None = None
        self._active = False
        self._stopped = False

    @property
    def active(self) -> bool:
        return self._active

    @property
    def deadline(self) -> float | None:
        if self._started_at is None:
            return None
        return self._started_at + self.duration_seconds

    def __enter__(self) -> BoundedMove:
        if self._active:
            raise MoveSessionError("bounded Move session is already active")
        now = self._client._now()
        self._started_at = now
        self._last_refresh_at = now
        self._stopped = False
        try:
            result = self._client._invoke_named(
                "Move", (self.vx, self.vy, self.vyaw), {}
            )
            if not result.ok:
                raise UnitreeSdk2HighLevelCommandError(
                    f"Move was rejected with vendor code {result.code}"
                )
            self._active = True
            return self
        except BaseException:
            self._client.best_effort_stop()
            raise

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        self.stop()
        return False

    def _check_live(self) -> float:
        if not self._active or self._started_at is None:
            raise MoveSessionError("bounded Move session is not active")
        now = self._client._now()
        deadline = self._started_at + self.duration_seconds
        last_refresh = self._last_refresh_at
        if now >= deadline:
            self.stop()
            raise MoveSessionError("bounded Move duration has expired")
        if last_refresh is None or now - last_refresh >= self.deadman_timeout_seconds:
            self.stop()
            raise MoveSessionError("bounded Move deadman has expired")
        return now

    def refresh(self) -> SportCommandResult:
        """Renew the deadman lease with one bounded Move command."""

        now = self._check_live()
        result = self._client._invoke_named("Move", (self.vx, self.vy, self.vyaw), {})
        if not result.ok:
            self.stop()
            raise UnitreeSdk2HighLevelCommandError(
                f"Move refresh was rejected with vendor code {result.code}"
            )
        self._last_refresh_at = now
        return result

    keepalive = refresh

    def stop(self) -> SportCommandResult | None:
        """Best-effort stop; repeated calls do not issue duplicate stops."""

        if self._stopped:
            return None
        self._active = False
        self._stopped = True
        return self._client.best_effort_stop()

    def run(self) -> SportCommandResult | None:
        """Run for the bounded duration while periodically refreshing the deadman."""

        with self:
            assert self._started_at is not None
            try:
                while True:
                    now = self._client._now()
                    remaining = self._started_at + self.duration_seconds - now
                    if remaining <= 0:
                        break
                    delay = min(self.refresh_period_seconds, remaining)
                    self._client._sleep(delay)
                    if self._client._now() < self._started_at + self.duration_seconds:
                        self.refresh()
            finally:
                # ``with`` also calls stop; this explicit finally is intentional
                # so a future refactor cannot accidentally remove the deadman.
                self.stop()
        return None


# The forward reference above is resolved at runtime when the class is used.
MoveGuard = BoundedMove
MoveSession = BoundedMove


class Go2SportClient:
    """Gated wrapper for every public Go2 SportClient action in the pinned SDK.

    Construction is lazy and side-effect free.  The first action initializes
    ``ChannelFactory`` with the explicit domain/interface, constructs the
    vendor client, sets its timeout, and then calls ``Init`` in that order.
    """

    name = "unitree-go2-sport"
    sdk_revision = SDK_REVISION

    def __init__(
        self,
        network_interface: str | None = None,
        *,
        interface: str | None = None,
        domain_id: int | None = None,
        config: Go2SportClientConfig | None = None,
        timeout_seconds: float | None = None,
        max_move_duration_seconds: float = 10.0,
        max_forward_mps: float = 1.0,
        max_lateral_mps: float = 1.0,
        max_yaw_rad_s: float = 1.0,
        enable_lease: bool = False,
        acknowledgements: SportClientSafetyAcknowledgements | None = None,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
        hazardous_motion_acknowledged: bool | None = None,
        hardware_enabled_ack: bool | None = None,
        operator_ack: bool | None = None,
        hazardous_motion_ack: bool | None = None,
        hazardous_ack: bool | None = None,
        bindings: UnitreeSdk2HighLevelBindings | None = None,
        importer: Importer = importlib.import_module,
        platform_name: str | None = None,
        clock: Clock | None = None,
        sleeper: Sleeper | None = None,
    ) -> None:
        if config is not None:
            if any(
                value is not None
                for value in (network_interface, interface, domain_id, timeout_seconds)
            ):
                raise UnitreeSdk2HighLevelConfigurationError(
                    "config cannot be combined with explicit interface, domain, "
                    "or timeout"
                )
            self.config = config
        else:
            selected_interface = network_interface
            if selected_interface is None:
                selected_interface = interface
            elif interface is not None and interface != selected_interface:
                raise UnitreeSdk2HighLevelConfigurationError(
                    "network_interface and interface disagree"
                )
            if selected_interface is None:
                raise UnitreeSdk2HighLevelConfigurationError(
                    "network_interface/interface must be explicit"
                )
            if domain_id is None:
                raise UnitreeSdk2HighLevelConfigurationError(
                    "domain_id must be explicit; use 0 when selecting the SDK default"
                )
            self.config = Go2SportClientConfig(
                network_interface=selected_interface,
                domain_id=domain_id,
                timeout_seconds=(
                    DEFAULT_TIMEOUT_SECONDS
                    if timeout_seconds is None
                    else timeout_seconds
                ),
                max_move_duration_seconds=max_move_duration_seconds,
                max_forward_mps=max_forward_mps,
                max_lateral_mps=max_lateral_mps,
                max_yaw_rad_s=max_yaw_rad_s,
                enable_lease=enable_lease,
            )

        if not isinstance(self.config, Go2SportClientConfig):
            raise UnitreeSdk2HighLevelConfigurationError(
                "config must be Go2SportClientConfig"
            )
        if acknowledgements is not None and not isinstance(
            acknowledgements, SportClientSafetyAcknowledgements
        ):
            raise UnitreeSdk2HighLevelConfigurationError(
                "acknowledgements must be SportClientSafetyAcknowledgements"
            )
        direct_ack = SportClientSafetyAcknowledgements(
            hardware_enabled=_resolve_bool(
                hardware_enabled,
                (("hardware_enabled_ack", hardware_enabled_ack),),
                "hardware_enabled",
            ),
            operator_acknowledged=_resolve_bool(
                operator_acknowledged,
                (("operator_ack", operator_ack),),
                "operator_acknowledged",
            ),
            hazardous_motion_acknowledged=_resolve_bool(
                hazardous_motion_acknowledged,
                (
                    ("hazardous_motion_ack", hazardous_motion_ack),
                    ("hazardous_ack", hazardous_ack),
                ),
                "hazardous_motion_acknowledged",
            ),
        )
        if acknowledgements is not None:
            supplied_any = any(
                value is not None
                for value in (
                    hardware_enabled,
                    operator_acknowledged,
                    hazardous_motion_acknowledged,
                    hardware_enabled_ack,
                    operator_ack,
                    hazardous_motion_ack,
                    hazardous_ack,
                )
            )
            if supplied_any and direct_ack != acknowledgements:
                raise UnitreeSdk2HighLevelConfigurationError(
                    "acknowledgements conflicts with individual acknowledgement fields"
                )
            self.acknowledgements = acknowledgements
        else:
            self.acknowledgements = direct_ack

        self._bindings = bindings
        self._importer = importer
        self._platform_name = platform_name
        self._clock = clock or time.monotonic
        self._sleeper = sleeper or time.sleep
        self._client: Any | None = None
        self._initialization_lock = threading.RLock()

    @property
    def network_interface(self) -> str:
        return self.config.network_interface

    @property
    def interface(self) -> str:
        return self.config.network_interface

    @property
    def domain_id(self) -> int:
        return self.config.domain_id

    @property
    def timeout_seconds(self) -> float:
        return self.config.timeout_seconds

    @property
    def initialized(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> Any | None:
        """Return the injected/vendor client after initialization, if any."""

        return self._client

    @property
    def commands(self) -> tuple[SportActionSpec, ...]:
        return SPORT_COMMAND_CATALOG

    @property
    def command_catalog(self) -> tuple[SportActionSpec, ...]:
        return SPORT_COMMAND_CATALOG

    def capabilities(self) -> dict[str, Any]:
        """Describe the complete gated surface without importing or contacting DDS."""

        return {
            "adapter": self.name,
            "sdk_package": SDK_PACKAGE,
            "sdk_revision": SDK_REVISION,
            "network_access": True,
            "sdk_required": True,
            "hardware_commands": True,
            "read_only": False,
            "commands": tuple(spec.name for spec in SPORT_COMMAND_CATALOG),
            "hazardous_commands": tuple(
                spec.name for spec in SPORT_COMMAND_CATALOG if spec.hazardous
            ),
            "network_interface": self.network_interface,
            "domain_id": self.domain_id,
            "initialized": self.initialized,
        }

    get_capabilities = capabilities

    def catalog(self) -> tuple[SportActionSpec, ...]:
        return SPORT_COMMAND_CATALOG

    available_commands = catalog
    available_actions = catalog

    def _now(self) -> float:
        value = self._clock()
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise MoveSessionError("monotonic clock returned a non-numeric value")
        result = float(value)
        if not math.isfinite(result):
            raise MoveSessionError("monotonic clock returned a non-finite value")
        return result

    def _sleep(self, seconds: float) -> None:
        self._sleeper(seconds)

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        with self._initialization_lock:
            if self._client is not None:
                return self._client
            if self._bindings is None:
                host = self._platform_name or platform.system()
                if host != "Linux":
                    raise UnitreeSdk2HighLevelUnavailableError(
                        "the Unitree SDK2 high-level profile is supported only on "
                        "Linux; inject bindings for offline tests"
                    )
                bindings = UnitreeSdk2HighLevelBindings.load(self._importer)
            else:
                bindings = self._bindings

            try:
                initialized = bindings.channel_factory_initialize(
                    self.domain_id, self.network_interface
                )
                if initialized is False:
                    raise RuntimeError("ChannelFactoryInitialize returned false")
            except Exception as exc:
                raise UnitreeSdk2HighLevelInitializationError(
                    "ChannelFactoryInitialize failed before SportClient creation "
                    f"for interface {self.network_interface!r}, DDS domain "
                    f"{self.domain_id!r}"
                ) from exc

            try:
                if self.config.enable_lease:
                    client = bindings.sport_client(True)
                else:
                    client = bindings.sport_client()
            except Exception as exc:
                raise UnitreeSdk2HighLevelInitializationError(
                    "SportClient construction failed after ChannelFactory "
                    "initialization"
                ) from exc

            set_timeout = getattr(client, "SetTimeout", None)
            init = getattr(client, "Init", None)
            if not callable(set_timeout) or not callable(init):
                raise UnitreeSdk2HighLevelCompatibilityError(
                    "the pinned SportClient must expose SetTimeout and Init"
                )
            try:
                set_timeout(self.timeout_seconds)
                initialized = init()
                if initialized is False:
                    raise RuntimeError("SportClient.Init returned false")
            except Exception as exc:
                raise UnitreeSdk2HighLevelInitializationError(
                    "SportClient.SetTimeout/Init failed after channel initialization"
                ) from exc
            self._client = client
            return client

    def _require_gate(
        self,
        spec: SportActionSpec,
        hazardous_motion_acknowledged: bool | None,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
    ) -> None:
        hardware_ack = self.acknowledgements.hardware_enabled
        if hardware_enabled is not None:
            hardware_ack = _require_bool(hardware_enabled, "hardware_enabled")
        if not hardware_ack:
            raise UnitreeSdk2HighLevelSafetyError(
                f"hardware-enabled acknowledgement is required before {spec.name}"
            )
        operator_ack = self.acknowledgements.operator_acknowledged
        if operator_acknowledged is not None:
            operator_ack = _require_bool(operator_acknowledged, "operator_acknowledged")
        if not operator_ack:
            raise UnitreeSdk2HighLevelSafetyError(
                f"operator acknowledgement is required before {spec.name}"
            )
        if hazardous_motion_acknowledged is not None:
            _require_bool(
                hazardous_motion_acknowledged,
                "hazardous_motion_acknowledged",
            )
            hazardous_ack = hazardous_motion_acknowledged
        else:
            hazardous_ack = self.acknowledgements.hazardous_motion_acknowledged
        if spec.requires_hazardous_acknowledgement and not hazardous_ack:
            raise HazardousMotionAcknowledgementRequired(
                f"{spec.name} requires the separate hazardous-motion acknowledgement"
            )

    def _invoke_named(
        self,
        action: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        hazardous_motion_acknowledged: bool | None = None,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
    ) -> SportCommandResult:
        spec = _normalize_action_name(action)
        self._require_gate(
            spec,
            hazardous_motion_acknowledged,
            hardware_enabled,
            operator_acknowledged,
        )
        client = self._ensure_client()
        method = getattr(client, spec.name, None)
        if not callable(method):
            raise UnitreeSdk2HighLevelCompatibilityError(
                f"SportClient is missing source-verified action {spec.name}"
            )
        value = method(*args, **kwargs)
        return _normalize_vendor_result(spec.name, value)

    def invoke(
        self,
        action: str,
        *args: Any,
        intentional: bool = False,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
        hazardous_motion_acknowledged: bool | None = None,
        hazardous_acknowledged: bool | None = None,
        hardware_enabled_ack: bool | None = None,
        operator_ack: bool | None = None,
        **kwargs: Any,
    ) -> SportCommandResult:
        """Invoke a catalog action only with explicit generic intent.

        ``intentional=True`` is required so a dynamically selected action is
        never an accidental ``getattr`` escape hatch.  The optional per-call
        hazardous acknowledgement is useful for one-off special motions while
        the constructor acknowledgement remains the normal session-level gate.
        """

        if not isinstance(intentional, bool) or not intentional:
            raise IntentionalInvocationRequired(
                "generic SportClient invocation requires intentional=True"
            )
        if (
            hazardous_motion_acknowledged is not None
            and hazardous_acknowledged is not None
            and hazardous_motion_acknowledged != hazardous_acknowledged
        ):
            raise UnitreeSdk2HighLevelConfigurationError(
                "conflicting hazardous-motion acknowledgement values"
            )
        if (
            hardware_enabled is not None
            and hardware_enabled_ack is not None
            and hardware_enabled != hardware_enabled_ack
        ):
            raise UnitreeSdk2HighLevelConfigurationError(
                "conflicting hardware-enabled acknowledgement values"
            )
        if (
            operator_acknowledged is not None
            and operator_ack is not None
            and operator_acknowledged != operator_ack
        ):
            raise UnitreeSdk2HighLevelConfigurationError(
                "conflicting operator acknowledgement values"
            )
        hazard_ack = (
            hazardous_motion_acknowledged
            if hazardous_motion_acknowledged is not None
            else hazardous_acknowledged
        )
        hardware_ack = (
            hardware_enabled if hardware_enabled is not None else hardware_enabled_ack
        )
        operator_ack_value = (
            operator_acknowledged if operator_acknowledged is not None else operator_ack
        )
        spec = _normalize_action_name(action)
        return self._invoke_named(
            spec.name,
            args,
            kwargs,
            hazardous_motion_acknowledged=hazard_ack,
            hardware_enabled=hardware_ack,
            operator_acknowledged=operator_ack_value,
        )

    call = invoke
    invoke_action = invoke

    def best_effort_stop(self) -> SportCommandResult | None:
        """Attempt StopMove during cleanup without initializing a new session."""

        client = self._client
        if client is None:
            return None
        try:
            value = client.StopMove()
            return _normalize_vendor_result("StopMove", value)
        except Exception as exc:
            return SportCommandResult(
                action="StopMove",
                code=-1,
                error=f"{type(exc).__name__}: {exc}",
            )

    stop_best_effort = best_effort_stop

    def close(self) -> SportCommandResult | None:
        """Best-effort software stop for use in application shutdown."""

        return self.best_effort_stop()

    def __enter__(self) -> Go2SportClient:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        self.best_effort_stop()
        return False

    def move_for(
        self,
        vx: float,
        vy: float,
        vyaw: float,
        *,
        duration_seconds: float | None = None,
        duration: float | None = None,
        session_id: str | None = None,
        session: str | None = None,
        deadman_timeout_seconds: float | None = None,
        refresh_period_seconds: float | None = None,
    ) -> BoundedMove:
        """Create a bounded Move context with an explicit deadman/session.

        This helper is intentionally separate from the source-compatible
        ``Move`` action.  Raw vendor access remains available through ``Move``
        or ``invoke(..., intentional=True)`` after the normal gates, while
        this convenience path adds configurable velocity and duration bounds.
        """

        if duration_seconds is not None and duration is not None:
            raise UnitreeSdk2HighLevelConfigurationError(
                "supply only one of duration_seconds or duration"
            )
        selected_duration = (
            duration_seconds if duration_seconds is not None else duration
        )
        if selected_duration is None:
            raise UnitreeSdk2HighLevelConfigurationError(
                "bounded Move duration_seconds is required"
            )
        selected_duration = _finite_positive(selected_duration, "duration_seconds")
        if selected_duration > self.config.max_move_duration_seconds:
            raise UnitreeSdk2HighLevelConfigurationError(
                "bounded Move duration exceeds max_move_duration_seconds"
            )
        selected_session = session_id if session_id is not None else session
        if not isinstance(selected_session, str) or not selected_session.strip():
            raise MoveSessionError("bounded Move requires a non-empty session_id")
        if session_id is not None and session is not None and session_id != session:
            raise UnitreeSdk2HighLevelConfigurationError(
                "session_id and session disagree"
            )
        if not isinstance(vx, (int, float)) or isinstance(vx, bool):
            raise UnitreeSdk2HighLevelConfigurationError("vx must be a number")
        if not isinstance(vy, (int, float)) or isinstance(vy, bool):
            raise UnitreeSdk2HighLevelConfigurationError("vy must be a number")
        if not isinstance(vyaw, (int, float)) or isinstance(vyaw, bool):
            raise UnitreeSdk2HighLevelConfigurationError("vyaw must be a number")
        values = (
            (vx, self.config.max_forward_mps, "vx"),
            (vy, self.config.max_lateral_mps, "vy"),
            (vyaw, self.config.max_yaw_rad_s, "vyaw"),
        )
        for value, limit, name in values:
            converted = float(value)
            if not math.isfinite(converted) or abs(converted) > limit:
                raise UnitreeSdk2HighLevelConfigurationError(
                    f"{name} exceeds its configured bounded Move limit"
                )
        deadman = (
            selected_duration
            if deadman_timeout_seconds is None
            else _finite_positive(deadman_timeout_seconds, "deadman_timeout_seconds")
        )
        period = (
            min(deadman / 2.0, selected_duration)
            if refresh_period_seconds is None
            else _finite_positive(refresh_period_seconds, "refresh_period_seconds")
        )
        if period > deadman:
            raise UnitreeSdk2HighLevelConfigurationError(
                "refresh_period_seconds cannot exceed deadman_timeout_seconds"
            )
        return BoundedMove(
            self,
            float(vx),
            float(vy),
            float(vyaw),
            selected_duration,
            selected_session,
            deadman,
            period,
        )

    bounded_move = move_for
    move_context = move_for
    move_session = move_for

    def run_bounded_move(self, *args: Any, **kwargs: Any) -> SportCommandResult | None:
        """Run a bounded Move and retain a final best-effort StopMove guarantee."""

        handle = self.move_for(*args, **kwargs)
        try:
            return handle.run()
        finally:
            handle.stop()

    # Source-compatible public action methods.  Hazardous methods accept an
    # optional per-call acknowledgement in addition to the session-level one.
    def Damp(self) -> SportCommandResult:
        return self._invoke_named("Damp", (), {})

    def BalanceStand(self) -> SportCommandResult:
        return self._invoke_named("BalanceStand", (), {})

    def StopMove(self) -> SportCommandResult:
        return self._invoke_named("StopMove", (), {})

    def StandUp(self) -> SportCommandResult:
        return self._invoke_named("StandUp", (), {})

    def StandDown(self) -> SportCommandResult:
        return self._invoke_named("StandDown", (), {})

    def RecoveryStand(self) -> SportCommandResult:
        return self._invoke_named("RecoveryStand", (), {})

    def Euler(self, roll: float, pitch: float, yaw: float) -> SportCommandResult:
        return self._invoke_named("Euler", (roll, pitch, yaw), {})

    def Move(self, vx: float, vy: float, vyaw: float) -> SportCommandResult:
        return self._invoke_named("Move", (vx, vy, vyaw), {})

    def Sit(self) -> SportCommandResult:
        return self._invoke_named("Sit", (), {})

    def RiseSit(self) -> SportCommandResult:
        return self._invoke_named("RiseSit", (), {})

    def SpeedLevel(self, level: int) -> SportCommandResult:
        return self._invoke_named("SpeedLevel", (level,), {})

    def Hello(self) -> SportCommandResult:
        return self._invoke_named("Hello", (), {})

    def Stretch(self) -> SportCommandResult:
        return self._invoke_named("Stretch", (), {})

    def Content(self) -> SportCommandResult:
        return self._invoke_named("Content", (), {})

    def Dance1(self) -> SportCommandResult:
        return self._hazardous("Dance1")

    def Dance2(self) -> SportCommandResult:
        return self._hazardous("Dance2")

    def SwitchJoystick(self, on: bool) -> SportCommandResult:
        return self._invoke_named("SwitchJoystick", (on,), {})

    def Pose(self, flag: bool) -> SportCommandResult:
        return self._invoke_named("Pose", (flag,), {})

    def Scrape(self) -> SportCommandResult:
        return self._invoke_named("Scrape", (), {})

    def FrontFlip(self) -> SportCommandResult:
        return self._hazardous("FrontFlip")

    def FrontJump(self) -> SportCommandResult:
        return self._hazardous("FrontJump")

    def FrontPounce(self) -> SportCommandResult:
        return self._hazardous("FrontPounce")

    def Heart(self) -> SportCommandResult:
        return self._invoke_named("Heart", (), {})

    def LeftFlip(self) -> SportCommandResult:
        return self._hazardous("LeftFlip")

    def BackFlip(self) -> SportCommandResult:
        return self._hazardous("BackFlip")

    def FreeWalk(self) -> SportCommandResult:
        return self._hazardous("FreeWalk")

    def FreeBound(self, flag: bool) -> SportCommandResult:
        return self._hazardous("FreeBound", flag)

    def FreeJump(self, flag: bool) -> SportCommandResult:
        return self._hazardous("FreeJump", flag)

    def FreeAvoid(self, flag: bool) -> SportCommandResult:
        return self._hazardous("FreeAvoid", flag)

    def StaticWalk(self) -> SportCommandResult:
        return self._invoke_named("StaticWalk", (), {})

    def TrotRun(self) -> SportCommandResult:
        return self._invoke_named("TrotRun", (), {})

    def HandStand(self, flag: bool) -> SportCommandResult:
        return self._hazardous("HandStand", flag)

    def ClassicWalk(self, flag: bool) -> SportCommandResult:
        return self._invoke_named("ClassicWalk", (flag,), {})

    def WalkUpright(self, flag: bool) -> SportCommandResult:
        return self._invoke_named("WalkUpright", (flag,), {})

    def CrossStep(self, flag: bool) -> SportCommandResult:
        return self._invoke_named("CrossStep", (flag,), {})

    def AutoRecoverySet(self, enabled: bool) -> SportCommandResult:
        return self._invoke_named("AutoRecoverySet", (enabled,), {})

    def AutoRecoveryGet(self) -> SportCommandResult:
        return self._invoke_named("AutoRecoveryGet", (), {})

    def SwitchAvoidMode(self) -> SportCommandResult:
        return self._invoke_named("SwitchAvoidMode", (), {})

    def _hazardous(self, action: str, *args: Any) -> SportCommandResult:
        return self._invoke_named(action, args, {})


# Familiar names for callers that treat the adapter as a Go2-specific control
# object rather than a generic profile.
UnitreeGo2SportClient = Go2SportClient
UnitreeSportClient = Go2SportClient
UnitreeSdk2HighLevelClient = Go2SportClient
UnitreeSdk2HighLevel = Go2SportClient
UnitreeSdk2HighLevelAdapter = Go2SportClient
HighLevelSportClient = Go2SportClient
SportClientAdapter = Go2SportClient

# The vendor class is intentionally not imported; these names document the
# wrapper's role without creating a second transport path.
Go2HighLevelClient = Go2SportClient
UnitreeSdk2HighLevelConfig = Go2SportClientConfig
UnitreeSdk2SportBindings = UnitreeSdk2HighLevelBindings
UnitreeSdk2CommandResult = SportCommandResult

__all__ = [
    "COMMAND_CATALOG",
    "DEFAULT_TIMEOUT_SECONDS",
    "Go2HighLevelClient",
    "Go2SportClient",
    "Go2SportClientConfig",
    "HazardousMotionAcknowledgementRequired",
    "HighLevelConfigurationError",
    "HighLevelInitializationError",
    "HighLevelSafetyError",
    "HighLevelSportClient",
    "IntentionalInvocationRequired",
    "SportClientAdapter",
    "MoveGuard",
    "MoveSession",
    "MoveSessionError",
    "NormalizedSportResult",
    "SDK_PACKAGE",
    "SDK_REVISION",
    "SafetyAcknowledgements",
    "SportActionSpec",
    "SportClientBindings",
    "SportClientSafetyAcknowledgements",
    "SportCommandResult",
    "SPORT_COMMAND_CATALOG",
    "UnitreeGo2SportClient",
    "UnitreeSdk2CommandResult",
    "UnitreeSdk2HighLevel",
    "UnitreeSdk2HighLevelAdapter",
    "UnitreeSdk2HighLevelBindings",
    "UnitreeSdk2HighLevelClient",
    "UnitreeSdk2HighLevelCommandError",
    "UnitreeSdk2HighLevelCompatibilityError",
    "UnitreeSdk2HighLevelConfigurationError",
    "UnitreeSdk2HighLevelError",
    "UnitreeSdk2HighLevelInitializationError",
    "UnitreeSdk2HighLevelSafetyError",
    "UnitreeSdk2HighLevelUnavailableError",
    "UnitreeSdk2HighLevelConfig",
    "UnitreeSdk2SportBindings",
    "UnitreeSportClient",
    "command_catalog",
]
