"""Lazy, explicitly configured, read-only Unitree SDK2 probe.

Only this module knows the vendor module paths and vendor object shapes.  The
rest of the repository receives small dataclasses or the repository-owned
``RobotTelemetry`` value.  Importing this module is safe on a laptop: the
optional SDK is imported only when a probe is actually run.

The bindings below were checked against Unitree SDK2 Python revision
``65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5``.  That revision provides
``ChannelFactoryInitialize`` in ``unitree_sdk2py.core.channel`` and the
read-only ``RobotStateClient`` service-list API in
``unitree_sdk2py.go2.robot_state.robot_state_client``.  It does not establish
``rt/sportmodestate`` as a Go2 topic, so this boundary intentionally does not
subscribe to that topic.
"""

from __future__ import annotations

import importlib
import math
import platform
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import ModuleType
from typing import Any

from .errors import (
    UnitreeSdk2CompatibilityError,
    UnitreeSdk2ConfigurationError,
    UnitreeSdk2InitializationError,
    UnitreeSdk2ProbeError,
    UnitreeSdk2UnavailableError,
    UnitreeSdk2UnsupportedPlatformError,
)

SDK_REVISION = "65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5"
SDK_PACKAGE = "unitree_sdk2py"
DDS_VERSION = "0.10.2"
DEFAULT_DOMAIN_ID = 0

# The source-verified APIs used by this module are intentionally enumerated in
# one place.  Do not add a publisher, actuator client, or service mutation API
# to this list without a new safety review.
_CHANNEL_MODULE = "unitree_sdk2py.core.channel"
_ROBOT_STATE_MODULE = "unitree_sdk2py.go2.robot_state.robot_state_client"

Importer = Callable[[str], ModuleType]
Clock = Callable[[], float]


@dataclass(frozen=True)
class UnitreeSdk2Bindings:
    """The tiny vendor surface needed by the read-only probe.

    Tests can construct this with pure-Python fakes.  Production callers use
    :meth:`load`, which lazily imports the pinned package paths.
    """

    channel_factory_initialize: Callable[..., Any]
    robot_state_client: Callable[[], Any]

    @classmethod
    def load(cls, importer: Importer = importlib.import_module) -> UnitreeSdk2Bindings:
        """Load only the source-verified, read-only SDK entry points."""

        try:
            channel_module = importer(_CHANNEL_MODULE)
            robot_state_module = importer(_ROBOT_STATE_MODULE)
            initialize = channel_module.ChannelFactoryInitialize
            client_type = robot_state_module.RobotStateClient
        except Exception as exc:
            raise UnitreeSdk2UnavailableError(_missing_sdk_message(exc)) from exc

        if not callable(initialize) or not callable(client_type):
            raise UnitreeSdk2CompatibilityError(
                "the installed Unitree SDK2 does not expose the pinned read-only "
                "ChannelFactoryInitialize/RobotStateClient API; reinstall "
                f"revision {SDK_REVISION} from requirements-unitree.txt"
            )
        return cls(initialize, client_type)


@dataclass(frozen=True)
class UnitreeSdk2Config:
    """Explicit DDS configuration for one read-only probe.

    A network interface is mandatory.  DDS domain zero is the official SDK
    default and is therefore the safe default here, while retaining an
    explicit override for a separately reviewed lab setup.
    """

    network_interface: str
    domain_id: int = DEFAULT_DOMAIN_ID

    def __post_init__(self) -> None:
        if (
            not isinstance(self.network_interface, str)
            or not self.network_interface.strip()
        ):
            raise UnitreeSdk2ConfigurationError(
                "network_interface is required; pass the robot-facing Linux "
                "interface explicitly (for example, enp2s0)"
            )
        if self.network_interface != self.network_interface.strip():
            raise UnitreeSdk2ConfigurationError(
                "network_interface must not contain leading or trailing whitespace"
            )
        if (
            not isinstance(self.domain_id, int)
            or isinstance(self.domain_id, bool)
            or self.domain_id < 0
        ):
            raise UnitreeSdk2ConfigurationError(
                "domain_id must be a non-negative integer; DDS domain 0 is the default"
            )


@dataclass(frozen=True)
class UnitreeService:
    """Repository-owned representation of one vendor service-list row."""

    name: str
    status: int
    protected: bool

    @property
    def protect(self) -> bool:
        """Compatibility spelling for the source field, without vendor types."""

        return self.protected

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "protected": self.protected,
        }


@dataclass(frozen=True)
class UnitreeSdk2ProbeResult:
    """Normalized output from one read-only SDK probe."""

    network_interface: str
    domain_id: int
    api_version: str
    server_api_version: str
    services: tuple[UnitreeService, ...]
    read_only: bool = True

    @property
    def service_list(self) -> tuple[UnitreeService, ...]:
        """Readable alias for callers that use the SDK API name."""

        return self.services

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": "unitree-sdk2",
            "network_interface": self.network_interface,
            "domain_id": self.domain_id,
            "api_version": self.api_version,
            "server_api_version": self.server_api_version,
            "services": [service.to_dict() for service in self.services],
            "read_only": self.read_only,
        }


class UnitreeSdk2ReadOnlyProbe:
    """One explicitly configured, read-only Unitree SDK2 session.

    Construction does no import, DDS initialization, client creation, or
    network access.  :meth:`probe` is the first operation that may touch the
    optional SDK.  The only client used is ``RobotStateClient`` and the only
    calls made on it are its initialization, API-version queries, and service
    list query.  No SDK object is returned to callers.

    ``bindings`` and ``importer`` are dependency-injection seams for tests.  A
    supplied ``bindings`` object represents a fake SDK and can therefore be
    used on any test host without installing or importing CycloneDDS.
    """

    name = "unitree-sdk2"
    read_only = True

    def __init__(
        self,
        network_interface: str | None = None,
        *,
        interface: str | None = None,
        domain_id: int = DEFAULT_DOMAIN_ID,
        bindings: UnitreeSdk2Bindings | None = None,
        importer: Importer = importlib.import_module,
        clock: Clock | None = None,
        platform_name: str | None = None,
    ) -> None:
        if network_interface is None:
            network_interface = interface
        elif interface is not None and interface != network_interface:
            raise UnitreeSdk2ConfigurationError(
                "network_interface and interface disagree; supply one interface"
            )
        self.config = UnitreeSdk2Config(network_interface or "", domain_id)
        self._bindings = bindings
        self._importer = importer
        self._clock = clock or time.monotonic
        self._platform_name = platform_name
        self._client: Any | None = None

    @property
    def network_interface(self) -> str:
        return self.config.network_interface

    @property
    def domain_id(self) -> int:
        return self.config.domain_id

    def capabilities(self) -> dict[str, Any]:
        """Describe this profile without importing or contacting the SDK."""

        return {
            "adapter": self.name,
            "read_only": True,
            "network_access": True,
            "sdk_required": True,
            "status": True,
            # No source-verified Go2 state topic is used by this boundary.
            "telemetry": False,
            "hardware_commands": False,
            "low_level_commands": False,
            "network_configuration_mutation": False,
            "dds_domain_id": self.domain_id,
        }

    get_capabilities = capabilities

    def probe(self) -> UnitreeSdk2ProbeResult:
        """Initialize DDS and perform only source-verified read queries."""

        client = self._ensure_client()

        api_version = self._read_text(client, "GetApiVersion", "local API version")
        server_api_version = self._read_server_api_version(client)
        services = self._read_service_list(client)
        return UnitreeSdk2ProbeResult(
            network_interface=self.network_interface,
            domain_id=self.domain_id,
            api_version=api_version,
            server_api_version=server_api_version,
            services=services,
        )

    probe_once = probe
    read_status = probe
    status = probe

    def read_telemetry(self) -> Any:
        """Return an intentionally conservative core telemetry value.

        This probe has no verified Go2 telemetry topic at the pinned source
        revision.  It therefore reports no battery value and unknown health;
        it never infers health from the service-list status integers.  The
        method exists to make accidental use in a typed read path fail closed
        instead of leaking a vendor object.
        """

        self.probe()
        from robot_dog.domain.health import HealthStatus
        from robot_dog.domain.telemetry import RobotTelemetry

        observed_at = self._read_clock()
        return RobotTelemetry(
            observed_at=observed_at,
            battery_percent=None,
            health=HealthStatus.UNKNOWN,
        )

    get_telemetry = read_telemetry
    telemetry = read_telemetry

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client

        self._assert_supported_platform()
        bindings = self._bindings
        if bindings is None:
            bindings = UnitreeSdk2Bindings.load(self._importer)

        # This call must remain before client construction.  The vendor
        # ChannelFactory is process-global and silently keeps its first setup.
        try:
            initialized = bindings.channel_factory_initialize(
                self.domain_id, self.network_interface
            )
            if initialized is False:
                raise RuntimeError("ChannelFactoryInitialize returned false")
        except Exception as exc:
            raise UnitreeSdk2InitializationError(
                "Unitree SDK2 ChannelFactoryInitialize failed for the explicitly "
                f"selected interface {self.network_interface!r} and DDS domain "
                f"{self.domain_id}; verify Linux, CycloneDDS {DDS_VERSION}, "
                "the isolated robot link, and the pinned SDK revision"
            ) from exc

        try:
            client = bindings.robot_state_client()
        except Exception as exc:
            raise UnitreeSdk2InitializationError(
                "Unitree SDK2 RobotStateClient could not be constructed after "
                "ChannelFactory initialization; check the pinned SDK and "
                f"CycloneDDS {DDS_VERSION} installation"
            ) from exc

        init = getattr(client, "Init", None)
        if not callable(init):
            raise UnitreeSdk2CompatibilityError(
                "the pinned RobotStateClient API has no Init method; reinstall "
                f"Unitree SDK2 Python revision {SDK_REVISION}"
            )
        try:
            initialized = init()
            if initialized is False:
                raise RuntimeError("RobotStateClient.Init returned false")
        except Exception as exc:
            raise UnitreeSdk2InitializationError(
                "Unitree SDK2 RobotStateClient.Init failed; confirm the isolated "
                "robot link, explicit interface, DDS domain, and CycloneDDS "
                f"{DDS_VERSION} runtime"
            ) from exc

        self._client = client
        return client

    def _assert_supported_platform(self) -> None:
        # Injected bindings are pure fakes in tests and do not install or load
        # the vendor runtime, so they remain usable in baseline/macOS CI.
        if self._bindings is not None:
            return
        host = self._platform_name or platform.system()
        if host != "Linux":
            raise UnitreeSdk2UnsupportedPlatformError(
                "the Unitree SDK2 profile is supported only on Linux; baseline "
                "and macOS/offline CI must use the fake adapter and must not "
                "install requirements-unitree.txt"
            )

    def _read_server_api_version(self, client: Any) -> str:
        value = self._call_read_method(
            client, "GetServerApiVersion", "server API version"
        )
        if not isinstance(value, tuple) or len(value) != 2:
            raise UnitreeSdk2ProbeError(
                "Unitree SDK2 GetServerApiVersion returned an unexpected shape; "
                "expected (status_code, version)"
            )
        code, version = value
        if code != 0:
            raise UnitreeSdk2ProbeError(
                f"Unitree SDK2 server API-version query returned status {code}"
            )
        return self._coerce_text(version, "server API version")

    def _read_service_list(self, client: Any) -> tuple[UnitreeService, ...]:
        value = self._call_read_method(client, "ServiceList", "service list")
        if not isinstance(value, tuple) or len(value) != 2:
            raise UnitreeSdk2ProbeError(
                "Unitree SDK2 ServiceList returned an unexpected shape; expected "
                "(status_code, services)"
            )
        code, entries = value
        if code != 0:
            raise UnitreeSdk2ProbeError(
                f"Unitree SDK2 service-list query returned status {code}"
            )
        if entries is None:
            return ()
        if isinstance(entries, (str, bytes, Mapping)):
            raise UnitreeSdk2ProbeError(
                "Unitree SDK2 ServiceList returned a non-sequence service payload"
            )
        try:
            return tuple(self._service_from_vendor(entry) for entry in entries)
        except TypeError as exc:
            raise UnitreeSdk2ProbeError(
                "Unitree SDK2 ServiceList returned a non-iterable payload"
            ) from exc

    @staticmethod
    def _service_from_vendor(entry: Any) -> UnitreeService:
        if isinstance(entry, Mapping):
            name = entry.get("name")
            status = entry.get("status")
            protected = entry.get("protect", entry.get("protected"))
        else:
            name = getattr(entry, "name", None)
            status = getattr(entry, "status", None)
            protected = getattr(entry, "protect", getattr(entry, "protected", None))
        if not isinstance(name, str) or not name:
            raise UnitreeSdk2ProbeError(
                "Unitree SDK2 ServiceList contained a row without a service name"
            )
        if not isinstance(status, int) or isinstance(status, bool):
            raise UnitreeSdk2ProbeError(
                f"Unitree SDK2 service {name!r} has an invalid status value"
            )
        if not isinstance(protected, bool):
            raise UnitreeSdk2ProbeError(
                f"Unitree SDK2 service {name!r} has an invalid protection flag"
            )
        return UnitreeService(name=name, status=status, protected=protected)

    @staticmethod
    def _call_read_method(client: Any, method_name: str, label: str) -> Any:
        method = getattr(client, method_name, None)
        if not callable(method):
            raise UnitreeSdk2CompatibilityError(
                f"the pinned RobotStateClient API does not expose the read-only "
                f"{method_name} method required for {label}; reinstall SDK2 "
                f"revision {SDK_REVISION}"
            )
        try:
            return method()
        except Exception as exc:
            raise UnitreeSdk2ProbeError(
                f"Unitree SDK2 read-only {label} query failed; verify the isolated "
                "robot link and DDS discovery"
            ) from exc

    @classmethod
    def _read_text(cls, client: Any, method_name: str, label: str) -> str:
        value = cls._call_read_method(client, method_name, label)
        return cls._coerce_text(value, label)

    @staticmethod
    def _coerce_text(value: Any, label: str) -> str:
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise UnitreeSdk2ProbeError(
                    f"Unitree SDK2 returned non-UTF-8 data for {label}"
                ) from exc
        if not isinstance(value, str) or not value:
            raise UnitreeSdk2ProbeError(
                f"Unitree SDK2 returned an invalid {label}; expected a non-empty string"
            )
        return value

    def _read_clock(self) -> float:
        try:
            clock = self._clock
            value = clock() if callable(clock) else clock.monotonic()  # type: ignore[attr-defined]
        except Exception as exc:
            raise UnitreeSdk2ProbeError(
                "the monotonic clock failed while creating vendor-neutral telemetry"
            ) from exc
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
        ):
            raise UnitreeSdk2ProbeError(
                "the monotonic clock returned a non-finite or non-numeric value"
            )
        return float(value)


def _missing_sdk_message(cause: BaseException) -> str:
    return (
        "Unitree SDK2 Python is unavailable or could not load its native runtime "
        f"({cause}). This is an optional hardware profile: run on supported Linux "
        "with Python >= 3.8, then run `python -m pip install -r "
        "requirements-unitree.txt` (the immutable profile) with package import "
        f"{SDK_PACKAGE}, CycloneDDS {DDS_VERSION}, and SDK revision "
        f"{SDK_REVISION}), and use the explicit robot-facing interface. Do not "
        "install this profile in baseline/macOS CI."
    )


# Short names are convenient for a composition root while the explicit names
# remain available to make the safety boundary obvious in reviews.
UnitreeSdk2Probe = UnitreeSdk2ReadOnlyProbe
UnitreeSdk2Adapter = UnitreeSdk2ReadOnlyProbe
UnitreeReadOnlyProbe = UnitreeSdk2ReadOnlyProbe
UnitreeAdapter = UnitreeSdk2ReadOnlyProbe


__all__ = [
    "DDS_VERSION",
    "DEFAULT_DOMAIN_ID",
    "SDK_PACKAGE",
    "SDK_REVISION",
    "UnitreeAdapter",
    "UnitreeReadOnlyProbe",
    "UnitreeSdk2Adapter",
    "UnitreeSdk2Bindings",
    "UnitreeSdk2Config",
    "UnitreeSdk2Probe",
    "UnitreeSdk2ProbeResult",
    "UnitreeSdk2ReadOnlyProbe",
    "UnitreeService",
]
