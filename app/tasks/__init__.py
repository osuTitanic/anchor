
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Tuple
from twisted.internet import reactor

import logging
import time

class Tasks:
    """
    A task manager that utilizes Twisted's reactor to schedule tasks.
    """

    def __init__(self) -> None:
        self.tasks: Dict[str, Tuple[int, Callable, bool]] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.logger = logging.getLogger('anchor')

    def submit(self, interval: int, threaded: bool = False) -> Callable:
        def wrapper(func: Callable) -> Callable:
            self.logger.info(f'Registered task: "{func.__name__}"')
            self.tasks[func.__name__] = (interval, func, threaded)
            return func
        return wrapper

    def start(self) -> None:
        for name, (interval, func, threaded) in self.tasks.items():
            reactor.callLater(
                interval, self.start_task,
                name, interval, func, threaded
            )

    def start_task(
        self,
        name: str,
        interval: int,
        func: Callable,
        threaded: bool
    ) -> None:
        def on_task_done():
            if interval < 0:
                return

            # Schedule the next run
            reactor.callLater(
                interval, self.start_task,
                name, interval, func, threaded
            )

        if threaded:
            future = self.executor.submit(func)
            future.add_done_callback(lambda _: on_task_done())
            return

        func()
        on_task_done()
