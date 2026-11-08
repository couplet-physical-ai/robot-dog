"""Application-owned control authority values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .errors import InvalidValueError


class ControlOwner(StrEnum):
    """The actor currently entitled to issue motion commands."""

    UNKNOWN = "unknown"
    OPERATOR = "operator"
    APPLICATION = "application"
    OTHER = "other"


@dataclass(frozen=True)
class ControlAuthority:
    """A control owner and its opaque lease identifier.

    The lease identifier is application-owned opaque data.  This layer does not
    infer semantics from a vendor's authority or mode fields.
    """

    owner: ControlOwner = ControlOwner.UNKNOWN
    lease_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.owner, ControlOwner):
            raise InvalidValueError("control owner must be a ControlOwner")
        if self.lease_id is not None and (
            not isinstance(self.lease_id, str) or not self.lease_id.strip()
        ):
            raise InvalidValueError("lease_id must be a non-empty string")

    @property
    def is_known(self) -> bool:
        return self.owner is not ControlOwner.UNKNOWN

    @property
    def is_application_owned(self) -> bool:
        return self.owner is ControlOwner.APPLICATION and self.lease_id is not None

    @classmethod
    def unknown(cls) -> ControlAuthority:
        return cls()

    @classmethod
    def application(cls, lease_id: str) -> ControlAuthority:
        return cls(owner=ControlOwner.APPLICATION, lease_id=lease_id)
