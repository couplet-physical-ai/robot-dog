"""Control-authority read port."""

from __future__ import annotations

from typing import Protocol

from ..domain.authority import ControlAuthority


class ControlAuthorityReader(Protocol):
    """Read the current owner without granting or changing authority."""

    def read_control_authority(self) -> ControlAuthority: ...
