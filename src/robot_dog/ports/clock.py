"""Clock port used to keep safety decisions deterministic."""

from __future__ import annotations

from typing import Protocol


class MonotonicClock(Protocol):
    """A clock whose values never depend on wall-clock adjustments."""

    def monotonic(self) -> float: ...
