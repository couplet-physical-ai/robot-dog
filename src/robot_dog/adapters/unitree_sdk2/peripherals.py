"""Lazy Unitree SDK2 video, VUI, and obstacle-avoidance access.

This boundary is intentionally separate from the motion authority wrapper, but
uses the same safety gate: every read requires ``hardware_enabled=True`` and
every mutation additionally requires ``operator_acknowledged=True``.  No
client is constructed before ``ChannelFactoryInitialize`` has completed.

The module paths and method names are copied from the official
``unitree_sdk2_python`` source at revision
``65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5``:

* ``unitree_sdk2py.go2.video.video_client.VideoClient.GetImageSample``
* ``unitree_sdk2py.go2.vui.vui_client.VuiClient`` with switch, volume, and
  brightness get/set methods
* ``unitree_sdk2py.go2.obstacles_avoid.obstacles_avoid_client.ObstaclesAvoidClient``
  with switch get/set, move, absolute/incremental move, and remote-command
  selection

The video result is normalized to ``bytes``.  VUI and obstacle values are
plain Python scalars, and all RPC status values are exposed through
:class:`UnitreePeripheralResult`; no vendor client or response object escapes.
"""

from __future__ import annotations

import importlib
import math
import platform
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Generic, TypeVar

from .authority import (
    AuthoritySafetyAcknowledgements,
    UnitreeSdk2SafetyError,
)
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
_VIDEO_MODULE = "unitree_sdk2py.go2.video.video_client"
_VUI_MODULE = "unitree_sdk2py.go2.vui.vui_client"
_OBSTACLES_MODULE = "unitree_sdk2py.go2.obstacles_avoid.obstacles_avoid_client"

Importer = Callable[[str], ModuleType]
T = TypeVar("T")


class UnitreeSdk2PeripheralError(UnitreeSdk2Error):
    """A peripheral response could not be normalized at the SDK boundary."""


SafetyAcknowledgements = AuthoritySafetyAcknowledgements


@dataclass(frozen=True)
class UnitreeSdk2PeripheralBindings:
    """Injected vendor entry points for peripheral adapters."""

    channel_factory_initialize: Callable[..., Any]
    video_client: Callable[[], Any]
    vui_client: Callable[[], Any]
    obstacles_avoid_client: Callable[[], Any]

    @property
    def channel_factory(self) -> Callable[..., Any]:
        return self.channel_factory_initialize

    @property
    def video_client_type(self) -> Callable[[], Any]:
        return self.video_client

    @property
    def vui_client_type(self) -> Callable[[], Any]:
        return self.vui_client

    @property
    def obstacles_avoid_client_type(self) -> Callable[[], Any]:
        return self.obstacles_avoid_client

    @property
    def obstacles_client(self) -> Callable[[], Any]:
        """Short alias without changing the official client name."""

        return self.obstacles_avoid_client

    @classmethod
    def load(
        cls, importer: Importer = importlib.import_module
    ) -> UnitreeSdk2PeripheralBindings:
        """Load only the exact pinned SDK2 peripheral modules."""

        try:
            channel = importer(_CHANNEL_MODULE)
            video = importer(_VIDEO_MODULE)
            vui = importer(_VUI_MODULE)
            obstacles = importer(_OBSTACLES_MODULE)
        except Exception as exc:
            raise UnitreeSdk2UnavailableError(
                "Unitree SDK2 peripheral bindings are unavailable at revision "
                f"{SDK_REVISION}; expected {_CHANNEL_MODULE}, {_VIDEO_MODULE}, "
                f"{_VUI_MODULE}, and {_OBSTACLES_MODULE}: {exc}"
            ) from exc

        names = (
            (channel, "ChannelFactoryInitialize", _CHANNEL_MODULE),
            (video, "VideoClient", _VIDEO_MODULE),
            (vui, "VuiClient", _VUI_MODULE),
            (obstacles, "ObstaclesAvoidClient", _OBSTACLES_MODULE),
        )
        for module, name, path in names:
            if not callable(getattr(module, name, None)):
                raise UnitreeSdk2CompatibilityError(
                    f"Unitree SDK2 revision {SDK_REVISION} module {path!r} does "
                    f"not expose callable {name!r}"
                )

        return cls(
            channel_factory_initialize=channel.ChannelFactoryInitialize,
            video_client=video.VideoClient,
            vui_client=vui.VuiClient,
            obstacles_avoid_client=obstacles.ObstaclesAvoidClient,
        )


PeripheralBindings = UnitreeSdk2PeripheralBindings


@dataclass(frozen=True)
class UnitreePeripheralResult(Generic[T]):
    """Vendor-neutral status and value for one peripheral operation."""

    code: int
    value: T | None = None
    operation: str = ""

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

    @property
    def bytes(self) -> bytes | None:
        """Return binary data when this result contains the video sample."""

        return self.value if isinstance(self.value, bytes) else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "ok": self.ok,
            "operation": self.operation,
            "value": self.value,
        }


PeripheralResult = UnitreePeripheralResult


class _PeripheralSession:
    """Shared lazy DDS/client lifecycle for the facade and sub-adapters."""

    def __init__(
        self,
        network_interface: str,
        domain_id: int,
        bindings: UnitreeSdk2PeripheralBindings | None,
        importer: Importer,
        platform_name: str | None,
        timeout: float | None,
        acknowledgements: AuthoritySafetyAcknowledgements,
    ) -> None:
        self.network_interface = network_interface
        self.domain_id = domain_id
        self.bindings = bindings
        self.importer = importer
        self.platform_name = platform_name
        self.timeout = timeout
        self.acknowledgements = acknowledgements
        self.channel_initialized = False
        self.clients: dict[str, Any] = {}

    def ensure_channel(self) -> UnitreeSdk2PeripheralBindings:
        if self.channel_initialized:
            assert self.bindings is not None
            return self.bindings
        if self.bindings is None:
            _assert_linux(self.platform_name)
            self.bindings = UnitreeSdk2PeripheralBindings.load(self.importer)
        try:
            initialized = self.bindings.channel_factory_initialize(
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
        self.channel_initialized = True
        return self.bindings

    def ensure_client(self, kind: str) -> Any:
        cached = self.clients.get(kind)
        if cached is not None:
            return cached
        bindings = self.ensure_channel()
        factories = {
            "video": (bindings.video_client, "VideoClient"),
            "vui": (bindings.vui_client, "VuiClient"),
            "obstacles": (bindings.obstacles_avoid_client, "ObstaclesAvoidClient"),
        }
        try:
            factory, label = factories[kind]
        except KeyError as exc:  # pragma: no cover - fixed private callers
            raise UnitreeSdk2ConfigurationError(
                f"unknown peripheral client {kind!r}"
            ) from exc
        try:
            client = factory()
            set_timeout = getattr(client, "SetTimeout", None)
            if self.timeout is not None and callable(set_timeout):
                set_timeout(self.timeout)
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
        self.clients[kind] = client
        return client

    def call(
        self,
        kind: str,
        method_name: str,
        args: tuple[Any, ...],
        operation: str,
        *,
        binary: bool = False,
    ) -> UnitreePeripheralResult[Any]:
        client = self.ensure_client(kind)
        method = getattr(client, method_name, None)
        if not callable(method):
            raise UnitreeSdk2CompatibilityError(
                f"Unitree SDK2 revision {SDK_REVISION} client "
                f"{type(client).__name__} does not expose official method "
                f"{method_name!r} for {operation}"
            )
        try:
            response = method(*args)
        except Exception as exc:
            raise UnitreeSdk2PeripheralError(
                f"Unitree SDK2 peripheral call {method_name} failed"
            ) from exc

        if binary:
            code, value = _split_response(response, method_name)
            normalized = _normalize_bytes(value, method_name) if code == 0 else None
            return UnitreePeripheralResult(code, normalized, operation)
        if operation in _PAIR_READ_OPERATIONS:
            code, value = _split_response(response, method_name)
            return UnitreePeripheralResult(code, _copy_value(value), operation)
        if not isinstance(response, int) or isinstance(response, bool):
            raise UnitreeSdk2PeripheralError(
                f"Unitree SDK2 {method_name} returned {response!r}; expected "
                "integer status code"
            )
        return UnitreePeripheralResult(response, None, operation)


_PAIR_READ_OPERATIONS = frozenset(
    {"vui_get_switch", "vui_get_volume", "vui_get_brightness", "obstacles_get_switch"}
)


def _make_session(
    network_interface: str | None,
    interface: str | None,
    domain_id: int,
    bindings: UnitreeSdk2PeripheralBindings | None,
    importer: Importer,
    platform_name: str | None,
    timeout: float | None,
    acknowledgements: AuthoritySafetyAcknowledgements | None,
    hardware_enabled: bool | None,
    operator_acknowledged: bool | None,
    hardware_enabled_ack: bool | None,
    operator_ack: bool | None,
) -> _PeripheralSession:
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
    if not isinstance(domain_id, int) or isinstance(domain_id, bool) or domain_id < 0:
        raise UnitreeSdk2ConfigurationError("domain_id must be a non-negative integer")
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
            value is not None for value in (hardware_enabled, operator_acknowledged)
        )
        if supplied_any and direct_ack != acknowledgements:
            raise UnitreeSdk2ConfigurationError(
                "acknowledgements conflicts with individual acknowledgement fields"
            )
        selected_ack = acknowledgements
    else:
        selected_ack = direct_ack
    return _PeripheralSession(
        network_interface,
        domain_id,
        bindings,
        importer,
        platform_name,
        float(timeout) if timeout is not None else None,
        selected_ack,
    )


class _PeripheralAdapter:
    """Common constructor and acknowledgement helpers for sub-adapters."""

    def __init__(
        self,
        session: _PeripheralSession | None = None,
        *,
        network_interface: str | None = None,
        interface: str | None = None,
        domain_id: int = DEFAULT_DOMAIN_ID,
        bindings: UnitreeSdk2PeripheralBindings | None = None,
        importer: Importer = importlib.import_module,
        platform_name: str | None = None,
        timeout: float | None = None,
        acknowledgements: AuthoritySafetyAcknowledgements | None = None,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
        hardware_enabled_ack: bool | None = None,
        operator_ack: bool | None = None,
    ) -> None:
        if session is None:
            session = _make_session(
                network_interface,
                interface,
                domain_id,
                bindings,
                importer,
                platform_name,
                timeout,
                acknowledgements,
                hardware_enabled,
                operator_acknowledged,
                hardware_enabled_ack,
                operator_ack,
            )
        self._session = session

    @property
    def network_interface(self) -> str:
        return self._session.network_interface

    @property
    def domain_id(self) -> int:
        return self._session.domain_id

    @property
    def interface(self) -> str:
        return self.network_interface

    @property
    def initialized(self) -> bool:
        return bool(self._session.clients)

    def _read_gate(self, hardware_enabled: bool | None) -> None:
        effective = self._session.acknowledgements.hardware_enabled
        if hardware_enabled is not None:
            effective = _require_bool(hardware_enabled, "hardware_enabled")
        _require_hardware_enabled(effective)

    def _mutation_gate(
        self,
        hardware_enabled: bool | None,
        operator_acknowledged: bool | None,
    ) -> None:
        self._read_gate(hardware_enabled)
        effective = self._session.acknowledgements.operator_acknowledged
        if operator_acknowledged is not None:
            effective = _require_bool(operator_acknowledged, "operator_acknowledged")
        if not effective:
            raise UnitreeSdk2SafetyError(
                "mutation requires operator_acknowledged=True explicitly"
            )


class UnitreeSdk2VideoClient(_PeripheralAdapter):
    """Vendor-neutral wrapper around the pinned Go2 ``VideoClient``."""

    def get_image_sample(
        self, *, hardware_enabled: bool | None = None
    ) -> UnitreePeripheralResult[bytes]:
        self._read_gate(hardware_enabled)
        return self._session.call(
            "video",
            "GetImageSample",
            (),
            "video_get_image_sample",
            binary=True,
        )

    read_image = get_image_sample
    get_image = get_image_sample
    get_image_bytes = get_image_sample


class UnitreeSdk2VuiClient(_PeripheralAdapter):
    """Vendor-neutral wrapper around the pinned Go2 ``VuiClient``."""

    def get_switch(
        self, *, hardware_enabled: bool | None = None
    ) -> UnitreePeripheralResult[Any]:
        self._read_gate(hardware_enabled)
        return self._session.call("vui", "GetSwitch", (), "vui_get_switch")

    read_switch = get_switch

    def set_switch(
        self,
        enabled: bool,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
    ) -> UnitreePeripheralResult[None]:
        self._mutation_gate(hardware_enabled, operator_acknowledged)
        if not isinstance(enabled, bool):
            raise UnitreeSdk2ConfigurationError("enabled must be bool")
        return self._session.call("vui", "SetSwitch", (int(enabled),), "vui_set_switch")

    switch_set = set_switch

    def get_volume(
        self, *, hardware_enabled: bool | None = None
    ) -> UnitreePeripheralResult[Any]:
        self._read_gate(hardware_enabled)
        return self._session.call("vui", "GetVolume", (), "vui_get_volume")

    read_volume = get_volume

    def set_volume(
        self,
        level: int,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
    ) -> UnitreePeripheralResult[None]:
        self._mutation_gate(hardware_enabled, operator_acknowledged)
        _require_int(level, "volume level")
        return self._session.call("vui", "SetVolume", (level,), "vui_set_volume")

    volume_set = set_volume

    def get_brightness(
        self, *, hardware_enabled: bool | None = None
    ) -> UnitreePeripheralResult[Any]:
        self._read_gate(hardware_enabled)
        return self._session.call("vui", "GetBrightness", (), "vui_get_brightness")

    read_brightness = get_brightness

    def set_brightness(
        self,
        level: int,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
    ) -> UnitreePeripheralResult[None]:
        self._mutation_gate(hardware_enabled, operator_acknowledged)
        _require_int(level, "brightness level")
        return self._session.call(
            "vui", "SetBrightness", (level,), "vui_set_brightness"
        )

    brightness_set = set_brightness


class UnitreeSdk2ObstaclesAvoidClient(_PeripheralAdapter):
    """Vendor-neutral wrapper around the pinned obstacle-avoidance client."""

    def get_switch(
        self, *, hardware_enabled: bool | None = None
    ) -> UnitreePeripheralResult[Any]:
        self._read_gate(hardware_enabled)
        return self._session.call("obstacles", "SwitchGet", (), "obstacles_get_switch")

    read_switch = get_switch
    switch_get = get_switch

    def set_switch(
        self,
        enabled: bool,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
    ) -> UnitreePeripheralResult[None]:
        self._mutation_gate(hardware_enabled, operator_acknowledged)
        if not isinstance(enabled, bool):
            raise UnitreeSdk2ConfigurationError("enabled must be bool")
        return self._session.call(
            "obstacles", "SwitchSet", (enabled,), "obstacles_set_switch"
        )

    switch_set = set_switch

    def move(
        self,
        vx: float,
        vy: float,
        vyaw: float,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
    ) -> UnitreePeripheralResult[None]:
        self._mutation_gate(hardware_enabled, operator_acknowledged)
        values = (_finite(vx, "vx"), _finite(vy, "vy"), _finite(vyaw, "vyaw"))
        return self._session.call("obstacles", "Move", values, "obstacles_move")

    def move_to_absolute_position(
        self,
        vx: float,
        vy: float,
        vyaw: float,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
    ) -> UnitreePeripheralResult[None]:
        self._mutation_gate(hardware_enabled, operator_acknowledged)
        values = (_finite(vx, "vx"), _finite(vy, "vy"), _finite(vyaw, "vyaw"))
        return self._session.call(
            "obstacles",
            "MoveToAbsolutePosition",
            values,
            "obstacles_move_absolute",
        )

    move_absolute = move_to_absolute_position

    def move_to_increment_position(
        self,
        vx: float,
        vy: float,
        vyaw: float,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
    ) -> UnitreePeripheralResult[None]:
        self._mutation_gate(hardware_enabled, operator_acknowledged)
        values = (_finite(vx, "vx"), _finite(vy, "vy"), _finite(vyaw, "vyaw"))
        return self._session.call(
            "obstacles",
            "MoveToIncrementPosition",
            values,
            "obstacles_move_increment",
        )

    move_increment = move_to_increment_position

    def use_remote_command_from_api(
        self,
        enabled: bool,
        *,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
    ) -> UnitreePeripheralResult[None]:
        self._mutation_gate(hardware_enabled, operator_acknowledged)
        if not isinstance(enabled, bool):
            raise UnitreeSdk2ConfigurationError("enabled must be bool")
        return self._session.call(
            "obstacles",
            "UseRemoteCommandFromApi",
            (enabled,),
            "obstacles_use_remote_command_from_api",
        )

    set_remote_command_from_api = use_remote_command_from_api


class UnitreeSdk2Peripherals(_PeripheralAdapter):
    """Facade exposing all pinned video, VUI, and obstacle operations."""

    def __init__(
        self,
        network_interface: str | None = None,
        *,
        interface: str | None = None,
        domain_id: int = DEFAULT_DOMAIN_ID,
        bindings: UnitreeSdk2PeripheralBindings | None = None,
        importer: Importer = importlib.import_module,
        platform_name: str | None = None,
        timeout: float | None = None,
        acknowledgements: AuthoritySafetyAcknowledgements | None = None,
        hardware_enabled: bool | None = None,
        operator_acknowledged: bool | None = None,
        hardware_enabled_ack: bool | None = None,
        operator_ack: bool | None = None,
    ) -> None:
        session = _make_session(
            network_interface,
            interface,
            domain_id,
            bindings,
            importer,
            platform_name,
            timeout,
            acknowledgements,
            hardware_enabled,
            operator_acknowledged,
            hardware_enabled_ack,
            operator_ack,
        )
        super().__init__(session)
        self._video: UnitreeSdk2VideoClient | None = None
        self._vui: UnitreeSdk2VuiClient | None = None
        self._obstacles: UnitreeSdk2ObstaclesAvoidClient | None = None

    @property
    def video(self) -> UnitreeSdk2VideoClient:
        if self._video is None:
            self._video = UnitreeSdk2VideoClient(self._session)
        return self._video

    @property
    def vui(self) -> UnitreeSdk2VuiClient:
        if self._vui is None:
            self._vui = UnitreeSdk2VuiClient(self._session)
        return self._vui

    @property
    def obstacles(self) -> UnitreeSdk2ObstaclesAvoidClient:
        if self._obstacles is None:
            self._obstacles = UnitreeSdk2ObstaclesAvoidClient(self._session)
        return self._obstacles

    def capabilities(self) -> dict[str, Any]:
        """Describe all source-verified peripheral methods without importing DDS."""

        return {
            "adapter": "unitree-sdk2-peripherals",
            "sdk_package": SDK_PACKAGE,
            "sdk_revision": SDK_REVISION,
            "dds_version": DDS_VERSION,
            "network_access": True,
            "read_requires": ["hardware_enabled=True"],
            "mutation_requires": [
                "hardware_enabled=True",
                "operator_acknowledged=True",
            ],
            "video": {
                "module": _VIDEO_MODULE,
                "client": "VideoClient",
                "methods": ["GetImageSample"],
            },
            "vui": {
                "module": _VUI_MODULE,
                "client": "VuiClient",
                "methods": [
                    "GetSwitch",
                    "SetSwitch",
                    "GetVolume",
                    "SetVolume",
                    "GetBrightness",
                    "SetBrightness",
                ],
            },
            "obstacles_avoid": {
                "module": _OBSTACLES_MODULE,
                "client": "ObstaclesAvoidClient",
                "methods": [
                    "SwitchGet",
                    "SwitchSet",
                    "Move",
                    "MoveToAbsolutePosition",
                    "MoveToIncrementPosition",
                    "UseRemoteCommandFromApi",
                ],
            },
        }

    get_capabilities = capabilities

    def source_findings(self) -> dict[str, Any]:
        """Return exact pinned paths and complete exposed method inventories."""

        return {
            "revision": SDK_REVISION,
            "video": {
                "module": _VIDEO_MODULE,
                "class": "VideoClient",
                "methods": ["Init", "GetImageSample"],
            },
            "vui": {
                "module": _VUI_MODULE,
                "class": "VuiClient",
                "methods": [
                    "Init",
                    "SetSwitch",
                    "GetSwitch",
                    "SetVolume",
                    "GetVolume",
                    "SetBrightness",
                    "GetBrightness",
                ],
            },
            "obstacles_avoid": {
                "module": _OBSTACLES_MODULE,
                "class": "ObstaclesAvoidClient",
                "methods": [
                    "Init",
                    "SwitchSet",
                    "SwitchGet",
                    "Move",
                    "UseRemoteCommandFromApi",
                    "MoveToAbsolutePosition",
                    "MoveToIncrementPosition",
                ],
            },
        }

    # Facade aliases retain discoverable operation names without hiding the
    # sub-client grouping used by callers that want a narrower capability.
    def get_image_sample(self, **kwargs: Any) -> UnitreePeripheralResult[bytes]:
        return self.video.get_image_sample(**kwargs)

    get_image_bytes = get_image_sample


VideoClientAdapter = UnitreeSdk2VideoClient
VuiClientAdapter = UnitreeSdk2VuiClient
ObstaclesAvoidClientAdapter = UnitreeSdk2ObstaclesAvoidClient
UnitreeVideoClient = UnitreeSdk2VideoClient
UnitreeVuiClient = UnitreeSdk2VuiClient
UnitreeObstaclesAvoidClient = UnitreeSdk2ObstaclesAvoidClient


def _assert_linux(platform_name: str | None) -> None:
    if (platform_name or platform.system()) != "Linux":
        raise UnitreeSdk2ConfigurationError(
            "the Unitree SDK2 peripheral profile is supported only on Linux; "
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


def _require_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise UnitreeSdk2ConfigurationError(f"{label} must be an integer")
    return value


def _finite(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise UnitreeSdk2ConfigurationError(f"{label} must be numeric")
    converted = float(value)
    if not math.isfinite(converted):
        raise UnitreeSdk2ConfigurationError(f"{label} must be finite")
    return converted


def _split_response(response: Any, method_name: str) -> tuple[int, Any]:
    if not isinstance(response, tuple) or len(response) != 2:
        raise UnitreeSdk2PeripheralError(
            f"Unitree SDK2 {method_name} returned {response!r}; expected "
            "(status_code, value)"
        )
    code, value = response
    _require_int(code, f"{method_name} status code")
    return code, value


def _normalize_bytes(value: Any, method_name: str) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, (list, tuple)):
        if not all(
            isinstance(item, int) and not isinstance(item, bool) for item in value
        ):
            raise UnitreeSdk2PeripheralError(
                f"Unitree SDK2 {method_name} returned a binary sequence with "
                "non-integer data"
            )
        if not all(0 <= item <= 255 for item in value):
            raise UnitreeSdk2PeripheralError(
                f"Unitree SDK2 {method_name} returned binary data outside byte range"
            )
        return bytes(value)
    raise UnitreeSdk2PeripheralError(
        f"Unitree SDK2 {method_name} returned {type(value).__name__}; expected bytes"
    )


def _copy_value(value: Any) -> Any:
    """Copy scalar/mapping/list RPC values without leaking vendor objects."""

    if isinstance(value, Mapping):
        return {str(key): _copy_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_copy_value(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool, bytes)):
        return value
    raise UnitreeSdk2PeripheralError(
        f"Unitree SDK2 returned unsupported vendor value type {type(value).__name__}"
    )


__all__ = [
    "AuthoritySafetyAcknowledgements",
    "DDS_VERSION",
    "DEFAULT_DOMAIN_ID",
    "ObstaclesAvoidClientAdapter",
    "PeripheralBindings",
    "PeripheralResult",
    "SDK_PACKAGE",
    "SDK_REVISION",
    "SafetyAcknowledgements",
    "UnitreePeripheralResult",
    "UnitreeSdk2ObstaclesAvoidClient",
    "UnitreeSdk2PeripheralBindings",
    "UnitreeSdk2PeripheralError",
    "UnitreeObstaclesAvoidClient",
    "UnitreeSdk2Peripherals",
    "UnitreeSdk2SafetyError",
    "UnitreeSdk2VideoClient",
    "UnitreeSdk2VuiClient",
    "UnitreeVideoClient",
    "UnitreeVuiClient",
    "VideoClientAdapter",
    "VuiClientAdapter",
]
