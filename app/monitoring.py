
from functools import cached_property
import collections
import threading
import time

class RateLimiter:
    """A simple rate limiter that allows a certain number of requests per period."""

    def __init__(self, limit: int, period: float, cooldown: float = 10.0) -> None:
        self.limit = limit
        self.period = period
        self.cooldown = cooldown
        self.allowance = float(limit)
        self.lock = threading.Lock()
        self.last_check = time.monotonic()
        self.cooldown_end = 0.0

    @cached_property
    def rate_per_second(self) -> float:
        return (
            self.limit / self.period
            if self.period > 0 else float('inf')
        )

    @property
    def is_on_cooldown(self) -> bool:
        if self.cooldown_end == 0.0:
            return False

        if time.monotonic() >= self.cooldown_end:
            self.cooldown_end = 0.0
            return False

        return True

    def allow(self) -> bool:
        current_time = time.monotonic()

        with self.lock:
            if self.cooldown_end > 0.0 and current_time < self.cooldown_end:
                return False

            if self.cooldown_end > 0.0:
                self.cooldown_end = 0.0

            elapsed = current_time - self.last_check

            # Replenish tokens based on elapsed time
            self.allowance = min(
                self.limit,
                self.allowance + elapsed * self.rate_per_second
            )
            self.last_check = current_time

            if self.allowance < 1.0:
                self.cooldown_end = current_time + self.cooldown
                return False

            self.allowance -= 1.0
            return True

class RequestCounter:
    """Class to count requests made over a certain time period."""

    def __init__(self, window: int = 60) -> None:
        # Queue will track counts of requests per second as (timestamp, count)
        self.requests = collections.deque()
        self.lock = threading.Lock()
        self.window = window

    @property
    def rate(self) -> float:
        now = time.time()
        with self.lock:
            self.cleanup(now)
            return sum(count for _, count in self.requests)

    def record(self) -> None:
        now = time.time()
        second = int(now)
        with self.lock:
            if self.requests and self.requests[-1][0] == second:
                self.requests[-1][1] += 1
                return

            self.requests.append([second, 1])
            self.cleanup(now)

    def cleanup(self, now: float) -> None:
        cutoff = now - self.window
        while self.requests and self.requests[0][0] <= cutoff:
            self.requests.popleft()
