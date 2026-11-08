"""Monotonic clock implementations used by the safety gate and tests."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from .errors import ClockInvalidError, InvalidValueError


class SystemMonotonicClock:
    """Production clock backed by :func:`time.monotonic`."""

    def monotonic(self) -> float:
        value = time.monotonic()
        if not math.isfinite(value):
            raise ClockInvalidError(
                "system monotonic clock returned a non-finite value"
            )
        return value


@dataclass
class ManualClock:
    """Small deterministic clock useful for adapters and unit tests."""

    value: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise InvalidValueError("clock value must be numeric")
        if not math.isfinite(float(self.value)):
            raise InvalidValueError("clock value must be finite")
        self.value = float(self.value)

    def monotonic(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
            raise InvalidValueError("clock advance must be numeric")
        if not math.isfinite(float(seconds)):
            raise InvalidValueError("clock advance must be finite")
        if seconds < 0:
            raise InvalidValueError("clock cannot move backwards")
        self.value += float(seconds)
