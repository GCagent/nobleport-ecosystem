import time
from dataclasses import dataclass, field


@dataclass
class CircuitBreaker:
    """Minimal in-process breaker. One per provider."""

    fail_threshold: int = 5
    reset_after_s: int = 30
    _fails: int = 0
    _opened_at: float = field(default=0.0)

    def allow(self) -> bool:
        if self._opened_at and (time.monotonic() - self._opened_at) >= self.reset_after_s:
            self._opened_at = 0.0
            self._fails = 0
        return self._opened_at == 0.0

    def record_success(self) -> None:
        self._fails = 0
        self._opened_at = 0.0

    def record_failure(self) -> None:
        self._fails += 1
        if self._fails >= self.fail_threshold and not self._opened_at:
            self._opened_at = time.monotonic()
