
import threading
import time

class RateLimiter:
    """A simple rate limiter that allows a certain number of requests per period."""

    def __init__(self, limit: int, period: float, cooldown: float = 10.0) -> None:
        self.allowance = limit
        self.limit = limit
        self.period = period
        self.cooldown = cooldown
        self.lock = threading.Lock()
        self.last_check = time.monotonic()
        self.cooldown_end = None

    @property
    def rate_per_second(self) -> float:
        return (
            self.limit / self.period
            if self.period > 0 else float('inf')
        )
        
    @property
    def is_on_cooldown(self) -> bool:
        if self.cooldown_end is None:
            return False

        if time.monotonic() >= self.cooldown_end:
            self.cooldown_end = None
            return False

        return True

    def allow(self) -> bool:
        with self.lock:
            if self.is_on_cooldown:
                return False

            current_time = time.monotonic()
            elapsed = current_time - self.last_check

            self.last_check = current_time
            self.allowance += elapsed * self.rate_per_second

            if self.allowance > self.limit:
                self.allowance = self.limit

            if self.allowance < 1:
                self.cooldown_end = current_time + self.cooldown
                return False

            self.allowance -= 1
            return True
