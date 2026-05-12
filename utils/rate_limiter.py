from __future__ import annotations

import threading
import time

from config import GEMINI_MIN_SECONDS_BETWEEN_REQUESTS


class RateLimiter:
    """Simple process-wide rate limiter based on a minimum interval."""

    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval_seconds = max(0.0, min_interval_seconds)
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        """Block until the next request is allowed."""

        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed:
                time.sleep(self._next_allowed - now)
            self._next_allowed = time.monotonic() + self._min_interval_seconds


_RATE_LIMITER = RateLimiter(GEMINI_MIN_SECONDS_BETWEEN_REQUESTS)


def get_rate_limiter() -> RateLimiter:
    """Return the shared Gemini rate limiter."""

    return _RATE_LIMITER
