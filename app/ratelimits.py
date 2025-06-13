
import threading
import time

class RateLimiter:
    """A simple rate limiter that allows a certain number of requests per period."""

    def __init__(self, limit: int, period: float) -> None:
        self.allowance = limit
        self.limit = limit
        self.period = period
        self.lock = threading.Lock()
        self.last_check = time.monotonic()

    @property
    def rate_per_second(self) -> float:
        return (
            self.limit / self.period
            if self.period > 0 else float('inf')
        )

    def allow(self) -> bool:
        with self.lock:
            current_time = time.monotonic()
            elapsed = current_time - self.last_check

            self.last_check = current_time
            self.allowance += elapsed * self.rate_per_second

            if self.allowance > self.limit:
                self.allowance = self.limit

            if self.allowance < 1:
                return False

            self.allowance -= 1
            return True
