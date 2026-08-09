"""NaN circuit breaker — trip on consecutive non-finite steps."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BreakerState(str, Enum):
    CLOSED = "CLOSED"  # normal
    OPEN = "OPEN"      # tripped


@dataclass
class NanCircuitBreaker:
    trip_after: int = 3
    consecutive_bad: int = 0
    state: BreakerState = BreakerState.CLOSED

    def observe(self, finite: bool) -> BreakerState:
        if self.state is BreakerState.OPEN:
            return self.state
        if finite:
            self.consecutive_bad = 0
        else:
            self.consecutive_bad += 1
            if self.consecutive_bad >= self.trip_after:
                self.state = BreakerState.OPEN
        return self.state

    def allow_step(self) -> bool:
        return self.state is BreakerState.CLOSED

    def reset(self, token: str) -> None:
        if not token.startswith("reset:"):
            raise ValueError("BAD_RESET")
        self.state = BreakerState.CLOSED
        self.consecutive_bad = 0
