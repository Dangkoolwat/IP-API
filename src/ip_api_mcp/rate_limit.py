from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Callable


class RateLimitExceeded(RuntimeError):
    """Raised when the local request limit would be exceeded."""


class InMemoryRateLimiter:
    def __init__(
        self,
        max_calls: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_calls < 1:
            raise ValueError("max_calls must be at least 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")

        self._max_calls = max_calls
        self._window_seconds = window_seconds
        self._clock = clock
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = self._clock()
            cutoff = now - self._window_seconds

            while self._calls and self._calls[0] <= cutoff:
                self._calls.popleft()

            if len(self._calls) >= self._max_calls:
                raise RateLimitExceeded(
                    f"ip-api.com limit reached: {self._max_calls} calls per "
                    f"{self._window_seconds} seconds"
                )

            self._calls.append(now)
