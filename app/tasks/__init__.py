
from typing import Callable, Dict, Tuple, List
from twisted.internet import reactor, threads
from twisted.internet.defer import Deferred
from app.common import officer
from queue import Queue

import logging
import time

class Tasks:
    """
    A task manager that utilizes Twisted's reactor to schedule tasks.
    """

    def __init__(self) -> None:
        self.tasks: Dict[str, Tuple[int, Callable, bool]] = {}
        self.logger = logging.getLogger('anchor')
        self.queue = Queue()
        self.shutdown = False

    def submit(self, interval: int, threaded: bool = False) -> Callable:
        def wrapper(func: Callable) -> Callable:
            self.logger.info(f'Registered task: "{func.__name__}"')
            self.tasks[func.__name__] = (interval, func, threaded)
            return func
        return wrapper

    def do_later(self, function: Callable, *args, **kwargs) -> None:
        self.queue.put((function, args, kwargs))

    def start(self) -> None:
        for name, (interval, func, threaded) in self.tasks.items():
            reactor.callLater(
                max(interval, 1), self.start_task,
                name, interval, func, threaded
            )

    def start_task(
        self,
        name: str,
        interval: int,
        func: Callable,
        threaded: bool
    ) -> Deferred:
        def on_task_done() -> None:
            self.logger.debug(f'Task "{name}" completed')

            if interval <= 0:
                return

            # Schedule the next run
            reactor.callLater(
                interval, self.start_task,
                name, interval, func, threaded
            )

        def on_task_failed(e: Exception) -> None:
            officer.call(f'Task "{name}" failed: {e!r}', exc_info=e)
            on_task_done()

        # Defer the task to a thread if specified
        # Otherwise, defer the task to the synchronous reactor
        defer_method = (
            self.defer_to_thread
            if threaded else
            self.defer_to_reactor
        )

        deferred = defer_method(func)
        deferred.addCallback(lambda _: on_task_done())
        deferred.addErrback(lambda f: on_task_failed(f.value))
        return deferred

    def defer_to_thread(self, func: Callable, *args, **kwargs) -> Deferred:
        return threads.deferToThread(func, *args, **kwargs)

    def defer_to_reactor(self, func: Callable, *args, **kwargs) -> Deferred:
        def run(deferred: Deferred, func: Callable, *args, **kwargs) -> None:
            try:
                result = func(*args, **kwargs)
                deferred.callback(result)
            except Exception as e:
                deferred.errback(e)

        deferred = Deferred()
        reactor.callLater(0, run, deferred, func, *args, **kwargs)
        return deferred
