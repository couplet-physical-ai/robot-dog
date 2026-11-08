"""The sole normal motion-write port."""

from __future__ import annotations

from typing import Protocol

from ..domain.commands import HighLevelVelocityCommand


class MotionWriter(Protocol):
    """Write only an already-bounded high-level velocity command.

    There are intentionally no special-motion or low-level actuator methods in
    this normal port.  An application owns one writer instance; any vendor
    adapter behind it is outside this package.
    """

    def write_velocity(self, command: HighLevelVelocityCommand) -> None: ...
