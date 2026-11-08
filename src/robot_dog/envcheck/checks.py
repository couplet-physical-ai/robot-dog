"""Read-only local environment checks for ``robot-dog doctor``.

This module intentionally does not import vendor SDKs, ROS, or networking
clients.  Interface discovery uses the operating system's local interface
index only; it does not send packets or change network configuration.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import socket
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

# Values are never printed.  The names are limited to the supported
# configuration keys so a diagnostic cannot accidentally dump the environment.
NIC_ENV_VARS: tuple[str, ...] = (
    "ROBOT_DOG_NIC",
    "ROBOT_DOG_INTERFACE",
    "ROBOT_DOG_NETWORK_INTERFACE",
    "UNITREE_NIC",
    "UNITREE_INTERFACE",
    "UNITREE_NETWORK_INTERFACE",
)

OPTIONAL_SDKS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "Unitree SDK": ("unitree_sdk2py", "unitree_sdk2", "unitree_sdk"),
        "ROS 2 Python": ("rclpy",),
    }
)


@dataclass(frozen=True)
class CheckResult:
    """A safe, displayable diagnostic result.

    ``detail`` is authored by this module and never contains an environment
    value, an import path, or a socket address.
    """

    name: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class EnvironmentReport:
    checks: tuple[CheckResult, ...]
    offline: bool = True
    read_only: bool = True

    @property
    def failed(self) -> bool:
        return any(check.status == "FAIL" for check in self.checks)

    @property
    def warnings(self) -> int:
        return sum(check.status == "WARN" for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {
            "offline": self.offline,
            "read_only": self.read_only,
            "checks": [check.to_dict() for check in self.checks],
        }


def redact_value(_value: object) -> str:
    """Return a stable redaction marker for use by callers handling values."""

    return "<redacted>"


def environment_presence(
    environ: Mapping[str, str] | None = None,
) -> dict[str, bool]:
    """Report presence of supported settings without returning their values."""

    source = os.environ if environ is None else environ
    return {name: bool(source.get(name)) for name in NIC_ENV_VARS}


def _configured_nic(
    nic_name: str | None,
    environ: Mapping[str, str],
) -> tuple[str | None, str | None]:
    if nic_name is not None:
        return nic_name, "explicit option"
    for name in NIC_ENV_VARS:
        if environ.get(name):
            return environ[name], name
    return None, None


def _local_interfaces() -> tuple[str, ...]:
    """Return local interface names without opening a network connection."""

    try:
        return tuple(name for _index, name in socket.if_nameindex())
    except (AttributeError, OSError):
        # A caller can still use the rest of doctor on platforms without
        # if_nameindex.  The diagnostic reports this as a warning.
        return ()


def _sdk_present(
    module_names: Sequence[str],
    finder: Callable[[str], object | None] = importlib.util.find_spec,
) -> bool:
    for module_name in module_names:
        try:
            if finder(module_name) is not None:
                return True
        except (ImportError, ModuleNotFoundError, ValueError):
            # Broken optional installations should look unavailable, not make
            # an offline diagnostic crash.
            continue
    return False


def collect_environment(
    *,
    nic_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    interface_names: Iterable[str] | None = None,
    sdk_finder: Callable[[str], object | None] = importlib.util.find_spec,
) -> EnvironmentReport:
    """Collect safe local diagnostics.

    The optional arguments make the function deterministic and easy to test;
    production callers can use the defaults.  No value from ``environ`` is
    copied into the report.
    """

    source: Mapping[str, str] = os.environ if environ is None else environ
    checks: list[CheckResult] = [
        CheckResult(
            "OS",
            "PASS",
            f"{platform.system() or 'unknown'} {platform.release() or 'unknown'}",
        ),
        CheckResult(
            "Python",
            "PASS",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        ),
        CheckResult(
            "Architecture",
            "PASS",
            platform.machine() or "unknown",
        ),
    ]

    for label, module_names in OPTIONAL_SDKS.items():
        present = _sdk_present(module_names, sdk_finder)
        checks.append(
            CheckResult(
                label,
                "PASS" if present else "INFO",
                "available" if present else "not installed (optional for offline mode)",
            )
        )

    configured, _source_name = _configured_nic(nic_name, source)
    if configured is None:
        checks.append(
            CheckResult(
                "Configured NIC",
                "INFO",
                "not configured (not required for offline mode)",
            )
        )
    else:
        # Supplying a synthetic interface list is for tests only.  Otherwise,
        # this is an OS-local lookup and never a network scan.
        interfaces = (
            tuple(interface_names)
            if interface_names is not None
            else _local_interfaces()
        )
        if not interfaces:
            checks.append(
                CheckResult(
                    "Configured NIC",
                    "WARN",
                    "configured interface could not be checked locally",
                )
            )
        elif configured in interfaces:
            checks.append(
                CheckResult(
                    "Configured NIC",
                    "PASS",
                    "configured interface exists locally",
                )
            )
        else:
            checks.append(
                CheckResult(
                    "Configured NIC",
                    "FAIL",
                    "configured interface is not present locally (value redacted)",
                )
            )

    return EnvironmentReport(checks=tuple(checks))


def doctor_exit_code(report: EnvironmentReport) -> int:
    """Return a non-zero code only for an actual diagnostic failure."""

    return 1 if report.failed else 0


def format_environment(report: EnvironmentReport) -> str:
    """Render diagnostics without exposing configuration values."""

    lines = [
        "robot-dog doctor (offline, read-only)",
        "No network connections or hardware commands are used.",
    ]
    for check in report.checks:
        lines.append(f"  {check.status:<4} {check.name}: {check.detail}")
    lines.append("Environment values are not displayed.")
    return "\n".join(lines)


__all__ = [
    "CheckResult",
    "EnvironmentReport",
    "NIC_ENV_VARS",
    "OPTIONAL_SDKS",
    "collect_environment",
    "doctor_exit_code",
    "environment_presence",
    "format_environment",
    "redact_value",
]
