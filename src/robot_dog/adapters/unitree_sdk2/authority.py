"""Explicit Unitree SDK2 authority and service wrappers.

The official Python SDK is an optional Linux profile.  This module keeps its
imports lazy, initializes the DDS channel before constructing a client, and
never returns vendor objects to callers.  All calls in this module are
intentional hardware operations: reads require ``hardware_enabled=True``;
mutations additionally require ``operator_acknowledged=True``.  Service and
motion-mode mutations require a named target and an exact confirmation of that
target.

The binding paths and methods below are source findings from Unitree
``unitree_sdk2_python`` revision
``65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5``:

* ``unitree_sdk2py.go2.robot_state.robot_state_client.RobotStateClient``
  exposes ``ServiceList``, ``ServiceSwitch`` and ``SetReportFreq``.
* ``unitree_sdk2py.comm.motion_switcher.motion_switcher_client.MotionSwitcherClient``
  exposes ``CheckMode``, ``SelectMode`` and ``ReleaseMode``.
* A report-frequency getter is not present at this revision.

No SDK import or DDS/network action occurs when this module is imported or a
wrapper is constructed.  Tests inject :class:`UnitreeSdk2AuthorityBindings`.
"""

from __future__ import annotations

import importlib
import platform
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Generic, TypeVar

from .errors import (
    UnitreeSdk2CompatibilityError,
    UnitreeSdk2ConfigurationError,
    UnitreeSdk2Error,
    UnitreeSdk2InitializationError,
    UnitreeSdk2UnavailableError,
)

SDK_REVISION = "65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5"
SDK_PACKAGE = "unitree_sdk2py"
DDS_VERSION = "0.10.2"
DEFAULT_DOMAIN_ID = 0

_CHANNEL_MODULE = "unitree_sdk2py.core.channel"
_ROBOT_STATE_MODULE = "unitree_sdk2py.go2.robot_state.robot_state_client"
_MOTION_SWITCHER_MODULE = "unitree_sdk2py.comm.motion_switcher.motion_switcher_client"

Importer = Callable[[str], ModuleType]
T = TypeVar("T")


class UnitreeSdk2SafetyError(PermissionError, UnitreeSdk2Error):
    """An explicit hardware/operator/target acknowledgement was missing."""


class UnitreeSdk2OperationError(UnitreeSdk2Error):
    """A vendor response could not be normalized at the adapter boundary."""


@dataclass(frozen=True)
class AuthoritySafetyAcknowledgements:
    """Explicit acknowledgements required before touching the SDK boundary."""

    hardware_enabled: bool = False
    operator_acknowledged: bool = False

    def __post_init__(self) -> None:
        _require_bool(self.hardware_enabled, "hardware_enabled")
        _require_bool(self.operator_acknowledged, "operator_acknowledged")

    @property
    def hardware_enabled_ack(self) -> bool:
        return self.hardware_enabled

    @property
    def operator_ack(self) -> bool:
        return self.operator_acknowledged


SafetyAcknowledgements = AuthoritySafetyAcknowledgements


@dataclass(frozen=True)
class UnitreeSdk2AuthorityBindings:
    """Injected vendor entry points for the authority boundary."""

    channel_factory_initialize: Callable[..., Any]
    robot_state_client: Callable[[], Any]
    motion_switcher_client: Callable[[], Any]

    @property
    def channel_factory(self) -> Callable[..., Any]:
        return self.channel_factory_initialize

    @property
    def robot_state_client_type(self) -> Callable[[], Any]:
        return self.robot_state_client

    @property
    def motion_switcher_client_type(self) -> Callable[[], Any]:
        return self.motion_switcher_client

    @classmethod
    def load(
        cls, importer: Importer = importlib.import_module
    ) -> UnitreeSdk2AuthorityBindings:
        """Load the exact pinned SDK2 modules only when a call needs them."""

        try:
            channel = importer(_CHANNEL_MODULE)
            robot_state = importer(_ROBOT_STATE_MODULE)
            motion_switcher = importer(_MOTION_SWITCHER_MODULE)
        except Exception as exc:
            raise UnitreeSdk2UnavailableError(
                "Unitree SDK2 authority bindings are unavailable at revision "
                f"{SDK_REVISION}; expected {_CHANNEL_MODULE}, {_ROBOT_STATE_MODULE}, "
                f"and {_MOTION_SWITCHER_MODULE}: {exc}"
            ) from exc

        names = (
            (channel, "ChannelFactoryInitialize", _CHANNEL_MODULE),
            (robot_state, "RobotStateClient", _ROBOT_STATE_MODULE),
            (motion_switcher, "MotionSwitcherClient", _MOTION_SWITCHER_MODULE),
        )
        for module, name, path in names:
            if not callable(getattr(module, name, None)):
                raise UnitreeSdk2CompatibilityError(
                    f"Unitree SDK2 revision {SDK_REVISION} module {path!r} does "
                    f"not expose callable {name!r}"
                )

        return cls(
            channel_factory_initialize=channel.ChannelFactoryInitialize,
            robot_state_client=robot_state.RobotStateClient,
            motion_switcher_client=motion_switcher.MotionSwitcherClient,
        )


# Short aliases make composition roots readable while retaining the explicit
# name for code review and dependency injection.
AuthorityBindings = UnitreeSdk2AuthorityBindings


@dataclass(frozen=True)
class UnitreeServiceState:
    """Vendor-neutral copy of one ``RobotStateClient.ServiceList`` row."""

    name: str
    status: int
    protected: bool

    @property
    def protect(self) -> bool:
        """Compatibility spelling used by the official ``ServiceState``."""

        return self.protected

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "protected": self.protected,
        }


# Friendly aliases for callers that do not need the SDK-specific type name.
ServiceState = UnitreeServiceState


@dataclass(frozen=True)
class UnitreeSdk2Result(Generic[T]):
    """Normalized result code and optional value from one SDK operation."""

    code: int
    value: T | None = None
    operation: str = ""
    target_id: str | None = None

    @property
    def status_code(self) -> int:
        return self.code

    @property
    def return_code(self) -> int:
        return self.code

    @property
    def ok(self) -> bool:
        return self.code == 0

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

    @property
    def data(self) -> T | None:
        return self.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "ok": self.ok,
            "operation": self.operation,
            "target_id": self.target_id,
            "value": self.value,
        }


@dataclass(frozen=True)
class UnitreeServiceListResult:
    """Normalized service-list response."""

    code: int
    services: tuple[UnitreeServiceState, ...]
    operation: str = "service_list"

    @property
    def status_code(self) -> int:
        return self.code

    @property
    def return_code(self) -> int:
        return self.code

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def success(self) -> bool:
        return self.ok

    @property
    def value(self) -> tuple[UnitreeServiceState, ...]:
        return self.services

    @property
    def data(self) -> tuple[UnitreeServiceState, ...]:
        return self.services

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "ok": self.ok,
            "operation": self.operation,
            "services": [service.to_dict() for service in self.services],
        }


@dataclass(frozen=True)
class UnitreeMotionModeResult:
    """Normalized ``MotionSwitcherClient.CheckMode`` response."""

    code: int
    mode: Mapping[str, Any] | None
    operation: str = "check_mode"

    @property
    def status_code(self) -> int:
        return self.code

    @property
    def return_code(self) -> int:
        return self.code

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def success(self) -> bool:
        return self.ok

    @property
    def value(self) -> Mapping[str, Any] | None:
        return self.mode

    @property
    def data(self) -> Mapping[str, Any] | None:
        return self.mode

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "ok": self.ok,
            "operation": self.operation,
            "mode": dict(self.mode) if self.mode is not None else None,
        }


AuthorityResult = UnitreeSdk2Result


class UnitreeSdk2Authority:
    """Lazy authority/service and motion-mode access for the pinned SDK2.

    ``network_interface`` is required even for an injected production binding;
    this prevents accidental DDS auto-detection.  A binding supplied by a test
    is treated as a pure fake and is allowed on non-Linux hosts.  Production
    loading remains Linux-only, matching the optional dependency profile.
    """

    name = "unitree-sdk2-authority"
    read_only = False

    def __init__(
        self,
        network_interface: str | None = None,
        *,
        interface: str | None = None,
        domain_id: int = DEFAULT_DOMAIN_ID,
        bindings: UnitreeSdk2AuthorityBindings | None = None,
        importer: Importer = importlib.import_module,
        platform_name: str | None = None,
        timeout: float | None = None,
        acknowledgements: AuthoritySafetyAcknowledgements | None = None,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
        hardware_enabled_ack: bool | None = None,
        operator_ack: bool | None = None,
    ) -> None:
        if network_interface is None:
            network_interface = interface
        elif interface is not None and interface != network_interface:
            raise UnitreeSdk2ConfigurationError(
                "network_interface and interface disagree; supply one interface"
            )
        if not isinstance(network_interface, str) or not network_interface.strip():
            raise UnitreeSdk2ConfigurationError(
                "network_interface is required; pass the robot-facing Linux "
                "interface explicitly"
            )
        if network_interface != network_interface.strip():
            raise UnitreeSdk2ConfigurationError(
                "network_interface must not contain leading or trailing whitespace"
            )
        if (
            not isinstance(domain_id, int)
            or isinstance(domain_id, bool)
            or domain_id < 0
        ):
            raise UnitreeSdk2ConfigurationError(
                "domain_id must be a non-negative integer"
            )
        if timeout is not None and (
            not isinstance(timeout, (int, float))
            or isinstance(timeout, bool)
            or timeout <= 0
        ):
            raise UnitreeSdk2ConfigurationError(
                "timeout must be a positive number when supplied"
            )

        direct_ack = AuthoritySafetyAcknowledgements(
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
        )
        if acknowledgements is not None and not isinstance(
            acknowledgements, AuthoritySafetyAcknowledgements
        ):
            # Accept the structurally identical high-level acknowledgement
            # object without importing that optional adapter module.
            try:
                acknowledgements = AuthoritySafetyAcknowledgements(
                    hardware_enabled=acknowledgements.hardware_enabled,
                    operator_acknowledged=acknowledgements.operator_acknowledged,
                )
            except (AttributeError, TypeError) as exc:
                raise UnitreeSdk2ConfigurationError(
                    "acknowledgements must expose hardware_enabled and "
                    "operator_acknowledged booleans"
                ) from exc
        if acknowledgements is not None:
            supplied_any = any(
                value is not None
                for value in (
                    hardware_enabled,
                    operator_acknowledged,
                    hardware_enabled_ack,
                    operator_ack,
                )
            )
            if supplied_any and direct_ack != acknowledgements:
                raise UnitreeSdk2ConfigurationError(
                    "acknowledgements conflicts with individual acknowledgement fields"
                )
            self.acknowledgements = acknowledgements
        else:
            self.acknowledgements = direct_ack

        self.network_interface = network_interface
        self.domain_id = domain_id
        self._bindings = bindings
        self._importer = importer
        self._platform_name = platform_name
        self._timeout = float(timeout) if timeout is not None else None
        self._channel_initialized = False
        self._clients: dict[str, Any] = {}

    @property
    def interface(self) -> str:
        return self.network_interface

    @property
    def initialized(self) -> bool:
        return bool(self._clients)

    def capabilities(self) -> dict[str, Any]:
        """Describe source-verified operations without importing or contacting DDS."""

        return {
            "adapter": self.name,
            "sdk_package": SDK_PACKAGE,
            "sdk_revision": SDK_REVISION,
            "dds_version": DDS_VERSION,
            "network_access": True,
            "read_requires": ["hardware_enabled=True"],
            "mutation_requires": [
                "hardware_enabled=True",
                "operator_acknowledged=True",
            ],
            "robot_state": {
                "module": _ROBOT_STATE_MODULE,
                "client": "RobotStateClient",
                "read": ["ServiceList"],
                "mutations": ["ServiceSwitch", "SetReportFreq"],
                "report_frequency_set": True,
                "report_frequency_get": False,
            },
            "motion_switcher": {
                "module": _MOTION_SWITCHER_MODULE,
                "client": "MotionSwitcherClient",
                "read": ["CheckMode"],
                "mutations": ["SelectMode", "ReleaseMode"],
            },
        }

    get_capabilities = capabilities

    def source_findings(self) -> dict[str, Any]:
        """Return exact pinned-revision paths and the known absent getter."""

        return {
            "revision": SDK_REVISION,
            "robot_state_client": {
                "module": _ROBOT_STATE_MODULE,
                "class": "RobotStateClient",
                "methods": [
                    "Init",
                    "ServiceList",
                    "ServiceSwitch",
                    "SetReportFreq",
                ],
                "absent": ["GetReportFreq"],
            },
            "motion_switcher_client": {
                "module": _MOTION_SWITCHER_MODULE,
                "class": "MotionSwitcherClient",
                "methods": ["Init", "CheckMode", "SelectMode", "ReleaseMode"],
                "absent": ["SetSilent", "GetSilent"],
            },
        }

    def read_service_list(
        self, *, hardware_enabled: bool | None = None
    ) -> UnitreeServiceListResult:
        """Read service state after an explicit hardware acknowledgement."""

        self._require_hardware(hardware_enabled)
        client = self._ensure_client("robot_state")
        response = _call(client, "ServiceList", (), "service list")
        code, entries = _split_response(response, "ServiceList")
        if entries is None:
            return UnitreeServiceListResult(code=code, services=())
        if isinstance(entries, (str, bytes, Mapping)):
            raise UnitreeSdk2OperationError(
                "RobotStateClient.ServiceList returned a non-sequence payload"
            )
        try:
            services = tuple(_service_state(entry) for entry in entries)
        except TypeError as exc:
            raise UnitreeSdk2OperationError(
                "RobotStateClient.ServiceList returned a non-iterable payload"
            ) from exc
        return UnitreeServiceListResult(code=code, services=services)

    service_list = read_service_list
    get_services = read_service_list

    def switch_service(
        self,
        name: str,
        enabled: bool,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
        target_id: str | None = None,
        confirmation: str | None = None,
        confirm: str | None = None,
    ) -> UnitreeSdk2Result[None]:
        """Enable/disable a named service with explicit target confirmation."""

        self._require_mutation(
            hardware_enabled=hardware_enabled,
            operator_acknowledged=operator_acknowledged,
        )
        target = _require_target(target_id, confirmation, confirm)
        _require_nonempty_text(name, "service name")
        if not isinstance(enabled, bool):
            raise UnitreeSdk2ConfigurationError("enabled must be bool")
        code = _call_code(
            self._ensure_client("robot_state"),
            "ServiceSwitch",
            (name, enabled),
            "service switch",
        )
        return UnitreeSdk2Result(
            code=code,
            operation="service_switch",
            target_id=target,
        )

    def service_switch(
        self,
        name: str,
        switch: bool | None = None,
        *,
        enabled: bool | None = None,
        **kwargs: Any,
    ) -> UnitreeSdk2Result[None]:
        """Official-spelling alias for :meth:`switch_service`."""

        if switch is None:
            switch = enabled
        elif enabled is not None and switch != enabled:
            raise UnitreeSdk2ConfigurationError(
                "switch and enabled disagree; supply one service state"
            )
        if switch is None:
            raise UnitreeSdk2ConfigurationError(
                "service_switch requires switch or enabled"
            )
        return self.switch_service(name, switch, **kwargs)

    def set_report_frequency(
        self,
        interval: int,
        duration: int,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
    ) -> UnitreeSdk2Result[None]:
        """Set the official report frequency; no getter exists at this pin."""

        self._require_mutation(
            hardware_enabled=hardware_enabled,
            operator_acknowledged=operator_acknowledged,
        )
        _require_int(interval, "interval")
        _require_int(duration, "duration")
        code = _call_code(
            self._ensure_client("robot_state"),
            "SetReportFreq",
            (interval, duration),
            "report frequency",
        )
        return UnitreeSdk2Result(code=code, operation="set_report_frequency")

    set_report_freq = set_report_frequency

    def check_mode(
        self, *, hardware_enabled: bool | None = None
    ) -> UnitreeMotionModeResult:
        """Read the currently selected motion mode."""

        self._require_hardware(hardware_enabled)
        response = _call(
            self._ensure_client("motion_switcher"), "CheckMode", (), "motion mode"
        )
        code, mode = _split_response(response, "CheckMode")
        if mode is not None and not isinstance(mode, Mapping):
            raise UnitreeSdk2OperationError(
                "MotionSwitcherClient.CheckMode returned a non-mapping mode payload"
            )
        copied = dict(mode) if mode is not None else None
        return UnitreeMotionModeResult(code=code, mode=copied)

    read_mode = check_mode
    check_motion_mode = check_mode

    def select_mode(
        self,
        name_or_alias: str,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
        target_id: str | None = None,
        confirmation: str | None = None,
        confirm: str | None = None,
    ) -> UnitreeSdk2Result[None]:
        """Select a motion mode after explicit target/operator confirmation."""

        self._require_mutation(
            hardware_enabled=hardware_enabled,
            operator_acknowledged=operator_acknowledged,
        )
        target = _require_target(target_id, confirmation, confirm)
        _require_nonempty_text(name_or_alias, "motion mode name or alias")
        code = _call_code_or_pair(
            self._ensure_client("motion_switcher"),
            "SelectMode",
            (name_or_alias,),
            "motion mode selection",
        )
        return UnitreeSdk2Result(
            code=code,
            operation="select_mode",
            target_id=target,
        )

    select_motion_mode = select_mode

    def release_mode(
        self,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
        target_id: str | None = None,
        confirmation: str | None = None,
        confirm: str | None = None,
    ) -> UnitreeSdk2Result[None]:
        """Release the current motion mode after explicit confirmation."""

        self._require_mutation(
            hardware_enabled=hardware_enabled,
            operator_acknowledged=operator_acknowledged,
        )
        target = _require_target(target_id, confirmation, confirm)
        code = _call_code_or_pair(
            self._ensure_client("motion_switcher"),
            "ReleaseMode",
            (),
            "motion mode release",
        )
        return UnitreeSdk2Result(
            code=code,
            operation="release_mode",
            target_id=target,
        )

    release_motion_mode = release_mode

    def _require_hardware(self, supplied: bool | None) -> None:
        effective = self.acknowledgements.hardware_enabled
        if supplied is not None:
            effective = _require_bool(supplied, "hardware_enabled")
        _require_hardware_enabled(effective)

    def _require_mutation(
        self,
        *,
        hardware_enabled: bool | None,
        operator_acknowledged: bool | None,
    ) -> None:
        self._require_hardware(hardware_enabled)
        effective = self.acknowledgements.operator_acknowledged
        if operator_acknowledged is not None:
            effective = _require_bool(operator_acknowledged, "operator_acknowledged")
        if not effective:
            raise UnitreeSdk2SafetyError(
                "mutation requires operator_acknowledged=True explicitly"
            )

    def _ensure_channel(self) -> UnitreeSdk2AuthorityBindings:
        if self._channel_initialized:
            # A binding is necessarily installed before this flag is set.
            assert self._bindings is not None
            return self._bindings
        if self._bindings is None:
            _assert_linux(self._platform_name)
            self._bindings = UnitreeSdk2AuthorityBindings.load(self._importer)

        try:
            initialized = self._bindings.channel_factory_initialize(
                self.domain_id, self.network_interface
            )
            if initialized is False:
                raise RuntimeError("ChannelFactoryInitialize returned false")
        except Exception as exc:
            raise UnitreeSdk2InitializationError(
                "Unitree SDK2 ChannelFactoryInitialize failed for explicitly "
                f"selected interface {self.network_interface!r} and DDS domain "
                f"{self.domain_id}; verify Linux, CycloneDDS {DDS_VERSION}, and "
                f"SDK revision {SDK_REVISION}"
            ) from exc
        self._channel_initialized = True
        return self._bindings

    def _ensure_client(self, kind: str) -> Any:
        cached = self._clients.get(kind)
        if cached is not None:
            return cached
        bindings = self._ensure_channel()
        if kind == "robot_state":
            factory = bindings.robot_state_client
            label = "RobotStateClient"
        elif kind == "motion_switcher":
            factory = bindings.motion_switcher_client
            label = "MotionSwitcherClient"
        else:  # pragma: no cover - private callers are fixed above
            raise UnitreeSdk2ConfigurationError(f"unknown authority client {kind!r}")
        try:
            client = factory()
            set_timeout = getattr(client, "SetTimeout", None)
            if self._timeout is not None and callable(set_timeout):
                set_timeout(self._timeout)
            init = getattr(client, "Init", None)
            if not callable(init):
                raise UnitreeSdk2CompatibilityError(
                    f"Unitree SDK2 revision {SDK_REVISION} {label} has no Init method"
                )
            initialized = init()
            if initialized is False:
                raise RuntimeError(f"{label}.Init returned false")
        except UnitreeSdk2CompatibilityError:
            raise
        except Exception as exc:
            raise UnitreeSdk2InitializationError(
                f"Unitree SDK2 {label}.Init failed after DDS initialization; "
                f"check the isolated link and SDK revision {SDK_REVISION}"
            ) from exc
        self._clients[kind] = client
        return client


# Conventional aliases for the adapter boundary.
UnitreeAuthority = UnitreeSdk2Authority
UnitreeSdk2AuthorityClient = UnitreeSdk2Authority
RobotStateAuthority = UnitreeSdk2Authority
MotionSwitcherAuthority = UnitreeSdk2Authority


def _assert_linux(platform_name: str | None) -> None:
    if (platform_name or platform.system()) != "Linux":
        raise UnitreeSdk2ConfigurationError(
            "the Unitree SDK2 authority profile is supported only on Linux; "
            "inject bindings for offline tests"
        )


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise UnitreeSdk2ConfigurationError(f"{label} must be bool")
    return value


def _resolve_bool(
    primary: bool | None,
    aliases: tuple[tuple[str, bool | None], ...],
    label: str,
) -> bool:
    values: list[tuple[str, bool]] = []
    if primary is not None:
        values.append((label, _require_bool(primary, label)))
    for alias, value in aliases:
        if value is not None:
            values.append((alias, _require_bool(value, alias)))
    if not values:
        return False
    first = values[0][1]
    if any(value != first for _, value in values[1:]):
        raise UnitreeSdk2ConfigurationError(
            "conflicting acknowledgement values: "
            + ", ".join(f"{name}={value!r}" for name, value in values)
        )
    return first


def _require_hardware_enabled(hardware_enabled: bool) -> None:
    if hardware_enabled is not True:
        raise UnitreeSdk2SafetyError(
            "hardware access is disabled; pass hardware_enabled=True explicitly"
        )


def _require_target(
    target_id: str | None,
    confirmation: str | None,
    confirm: str | None,
) -> str:
    if confirmation is not None and confirm is not None and confirmation != confirm:
        raise UnitreeSdk2SafetyError(
            "confirmation and confirm disagree; supply one exact target confirmation"
        )
    selected_confirmation = confirmation if confirmation is not None else confirm
    if not isinstance(target_id, str) or not target_id.strip():
        raise UnitreeSdk2SafetyError(
            "service/motion mutation requires a named target_id"
        )
    if target_id != target_id.strip():
        raise UnitreeSdk2SafetyError(
            "target_id must not contain surrounding whitespace"
        )
    if selected_confirmation != target_id:
        raise UnitreeSdk2SafetyError(
            "target confirmation must exactly equal the named target_id"
        )
    return target_id


def _require_nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UnitreeSdk2ConfigurationError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise UnitreeSdk2ConfigurationError(
            f"{label} must not contain surrounding whitespace"
        )
    return value


def _require_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise UnitreeSdk2ConfigurationError(f"{label} must be an integer")
    return value


def _call(client: Any, method_name: str, args: tuple[Any, ...], label: str) -> Any:
    method = getattr(client, method_name, None)
    if not callable(method):
        raise UnitreeSdk2CompatibilityError(
            f"Unitree SDK2 revision {SDK_REVISION} client {type(client).__name__} "
            f"does not expose official method {method_name!r} for {label}"
        )
    try:
        return method(*args)
    except Exception as exc:
        raise UnitreeSdk2OperationError(
            f"Unitree SDK2 {label} call {method_name} failed"
        ) from exc


def _call_code(client: Any, method_name: str, args: tuple[Any, ...], label: str) -> int:
    response = _call(client, method_name, args, label)
    if not isinstance(response, int) or isinstance(response, bool):
        raise UnitreeSdk2OperationError(
            f"Unitree SDK2 {method_name} returned {response!r}; expected "
            "an integer status code"
        )
    return response


def _call_code_or_pair(
    client: Any, method_name: str, args: tuple[Any, ...], label: str
) -> int:
    response = _call(client, method_name, args, label)
    if isinstance(response, int) and not isinstance(response, bool):
        return response
    code, _ = _split_response(response, method_name)
    return code


def _split_response(response: Any, method_name: str) -> tuple[int, Any]:
    if not isinstance(response, tuple) or len(response) != 2:
        raise UnitreeSdk2OperationError(
            f"Unitree SDK2 {method_name} returned {response!r}; expected "
            "(status_code, value)"
        )
    code, value = response
    _require_int(code, f"{method_name} status code")
    return code, value


def _service_state(entry: Any) -> UnitreeServiceState:
    if isinstance(entry, Mapping):
        name = entry.get("name")
        status = entry.get("status")
        protected = entry.get("protect", entry.get("protected"))
    else:
        name = getattr(entry, "name", None)
        status = getattr(entry, "status", None)
        protected = getattr(entry, "protect", getattr(entry, "protected", None))
    if not isinstance(name, str) or not name.strip():
        raise UnitreeSdk2OperationError(
            "Unitree SDK2 ServiceList contained a row without a service name"
        )
    if not isinstance(status, int) or isinstance(status, bool):
        raise UnitreeSdk2OperationError(
            f"Unitree SDK2 service {name!r} has an invalid status value"
        )
    if not isinstance(protected, bool):
        raise UnitreeSdk2OperationError(
            f"Unitree SDK2 service {name!r} has an invalid protection flag"
        )
    return UnitreeServiceState(name=name, status=status, protected=protected)


__all__ = [
    "AuthorityBindings",
    "AuthorityResult",
    "AuthoritySafetyAcknowledgements",
    "DDS_VERSION",
    "DEFAULT_DOMAIN_ID",
    "SDK_PACKAGE",
    "SDK_REVISION",
    "SafetyAcknowledgements",
    "ServiceState",
    "MotionSwitcherAuthority",
    "RobotStateAuthority",
    "UnitreeAuthority",
    "UnitreeMotionModeResult",
    "UnitreeSdk2Authority",
    "UnitreeSdk2AuthorityBindings",
    "UnitreeSdk2AuthorityClient",
    "UnitreeSdk2OperationError",
    "UnitreeSdk2Result",
    "UnitreeSdk2SafetyError",
    "UnitreeServiceListResult",
    "UnitreeServiceState",
]
