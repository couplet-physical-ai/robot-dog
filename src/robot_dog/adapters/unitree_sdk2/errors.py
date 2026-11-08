"""Errors for the optional, read-only Unitree SDK2 boundary.

The adapter deliberately owns these errors instead of exposing import errors,
CycloneDDS exceptions, or vendor RPC result codes to the hardware-independent
core.  They are also useful to a hardware operator because each failure tells
which optional prerequisite or read-only step needs attention.
"""

from __future__ import annotations


class UnitreeSdk2Error(RuntimeError):
    """Base class for failures in the optional Unitree SDK2 boundary."""


class UnitreeSdk2ConfigurationError(ValueError, UnitreeSdk2Error):
    """The explicitly supplied hardware configuration is unsafe or invalid."""


class UnitreeSdk2UnsupportedPlatformError(UnitreeSdk2Error):
    """The optional SDK profile was requested on a non-Linux host."""


class UnitreeSdk2UnavailableError(UnitreeSdk2Error):
    """The optional SDK or one of its native runtime dependencies is missing."""


class UnitreeSdk2CompatibilityError(UnitreeSdk2Error):
    """The installed SDK does not match the pinned read-only boundary."""


class UnitreeSdk2InitializationError(UnitreeSdk2Error):
    """CycloneDDS/channel-factory initialization failed."""


class UnitreeSdk2ProbeError(UnitreeSdk2Error):
    """A read-only SDK query failed or returned an unsafe shape."""


__all__ = [
    "UnitreeSdk2CompatibilityError",
    "UnitreeSdk2ConfigurationError",
    "UnitreeSdk2Error",
    "UnitreeSdk2InitializationError",
    "UnitreeSdk2ProbeError",
    "UnitreeSdk2UnavailableError",
    "UnitreeSdk2UnsupportedPlatformError",
]
