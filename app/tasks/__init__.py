
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures._base import Future
from typing import Callable

from . import activities
from . import events
from . import pings

import logging
import time

class Tasks(ThreadPoolExecutor):
    def __init__(self) -> None:
        super().__init__(thread_name_prefix='task')
        self.logger = logging.getLogger('anchor')

    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit a task to the threadpool"""
        future = super().submit(fn, *args, **kwargs)
        future.add_done_callback(self.future_callback)
        self.logger.info(f'  - Starting task: "{fn.__name__}"')
        return future

    def sleep(self, seconds: int, interval: int = 1):
        """Custom sleep function to check for application shutdowns"""
        for _ in range(0, seconds, interval):
            if self._shutdown:
                exit()

            time.sleep(interval)

    def future_callback(self, future: Future):
        """Callback function for a task/future"""
        if e := future.exception():
            if isinstance(e, SystemExit):
                return

            self.logger.error(
                f'Future {future.__repr__()} raised an exception: {e}',
                exc_info=e
            )

        self.logger.debug(
            f'Result for task {future.__repr__()}: {future.result()}'
        )
