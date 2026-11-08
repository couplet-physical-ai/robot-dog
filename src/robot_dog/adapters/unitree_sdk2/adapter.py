"""Compatibility import surface for the read-only Unitree SDK2 adapter.

The implementation lives in :mod:`.probe`; this module keeps the conventional
``adapter`` import path without introducing a second vendor boundary.
"""

from .probe import (
    DDS_VERSION,
    DEFAULT_DOMAIN_ID,
    SDK_PACKAGE,
    SDK_REVISION,
    UnitreeAdapter,
    UnitreeReadOnlyProbe,
    UnitreeSdk2Adapter,
    UnitreeSdk2Bindings,
    UnitreeSdk2Config,
    UnitreeSdk2Probe,
    UnitreeSdk2ProbeResult,
    UnitreeSdk2ReadOnlyProbe,
    UnitreeService,
)

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
