
from typing import Callable, Dict, Tuple, List
from twisted.internet import reactor, threads
from twisted.internet.defer import Deferred
from queue import PriorityQueue
from app.common import officer

import itertools
import logging

class Tasks:
    """
    A task manager that utilizes Twisted's reactor to schedule tasks.
    """

    def __init__(self) -> None:
        self.tasks: Dict[str, Tuple[int, Callable, bool]] = {}
        self.logger = logging.getLogger('anchor')
        self.counter = itertools.count()
        self.queue = PriorityQueue()
        self.shutdown = False

    def submit(self, interval: int, threaded: bool = False) -> Callable:
        """
        Decorator to register a task with a given interval and threading option.
        """
        def wrapper(func: Callable) -> Callable:
            self.logger.info(f'Registered task: "{func.__name__}"')
            self.tasks[func.__name__] = (interval, func, threaded)
            return func
        return wrapper

    def do_later(
        self,
        function: Callable,
        *args,
        priority: int = 0,
        **kwargs
    ) -> None:
        """
        Schedule a function to be called later with a given priority.
        Lower numbers indicate higher priority.
        """
        if self.queue.empty():
            # Reset counter if the queue is empty
            self.counter = itertools.count()

        count = next(self.counter)
        self.queue.put((priority, count, function, args, kwargs))

    def start(self) -> None:
        """
        Start the task loop by scheduling all registered tasks.
        """
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
        """
        Internal method to start a task with the given name, interval, and function.
        It will use the deferred system of twisted to handle the task execution & callbacks.
        """
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
