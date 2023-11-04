
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures._base import Future
from typing import Any, Callable, Tuple

from . import events
from . import pings

import logging
import time

class Jobs(ThreadPoolExecutor):
    def __init__(self, max_workers = None, thread_name_prefix: str = "job", initializer = None, initargs: Tuple[Any, ...] = ...) -> None:
        super().__init__(max_workers, thread_name_prefix, initializer, initargs)

        self.logger = logging.getLogger('anchor')

    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        future = super().submit(fn, *args, **kwargs)
        future.add_done_callback(self.__future_callback)
        self.logger.info(f'  - Starting job: "{fn.__name__}"')
        return future

    def sleep(self, seconds: float):
        for _ in range(seconds):
            if self._shutdown:
                # Exit thread
                exit()

            time.sleep(1)

    def __future_callback(self, future: Future):
        if e := future.exception():
            if isinstance(e, SystemExit):
                return

            self.logger.error(
                f'Future {future.__repr__()} raised an exception: {e}',
                exc_info=e
            )

        self.logger.debug(
            f'Result for job {future.__repr__()}: {future.result()}'
        )
