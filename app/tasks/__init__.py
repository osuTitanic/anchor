
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Dict, Tuple, List
from twisted.internet import reactor, threads
from twisted.internet.defer import Deferred
from queue import PriorityQueue
from app.common import officer
from threading import Thread

import itertools
import logging
import config

class Tasks:
    """
    A task manager that utilizes Twisted's reactor to schedule tasks, as well
    as a queue for tasks that can be executed later, to offload work from the main threads.
    """

    def __init__(self) -> None:
        self.tasks: Dict[str, Tuple[int, Callable, bool]] = {}
        self.logger = logging.getLogger('anchor')
        self.counter = itertools.count()
        self.shutdown = False

        # Initialize "do later" queue which offloads tasks
        # that don't need to be executed immediately
        self.do_later_workers = max(1, config.BANCHO_WORKERS // 2)
        self.do_later_executor = ThreadPoolExecutor(max_workers=self.do_later_workers)
        self.do_later_futures: List[Future] = []
        self.do_later_queue = PriorityQueue()

    def submit(self, interval: int, threaded: bool = False) -> Callable:
        """
        Decorator to register a task with a given interval and threading option.
        """
        def wrapper(func: Callable) -> Callable:
            self.logger.info(f'Registered task: "{func.__name__}"')
            self.tasks[func.__name__] = (interval, func, threaded)
            return func
        return wrapper

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

            if interval <= 0 or self.shutdown:
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
        if self.do_later_queue.empty():
            # Reset counter if the queue is empty
            self.counter = itertools.count()

        count = next(self.counter)
        self.do_later_queue.put((priority, count, function, args, kwargs))

    def defer_to_thread(self, func: Callable, *args, **kwargs) -> Deferred:
        """
        Internal function used to defer a function call to a separate thread.
        This utilizes python's regular threading capabilities.
        """
        def run(deferred: Deferred, func: Callable, *args, **kwargs) -> None:
            try:
                result = func(*args, **kwargs)
                deferred.callback(result)
            except Exception as e:
                deferred.errback(e)

        deferred = Deferred()
        thread = Thread(target=run, args=(deferred, func) + args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return deferred

    def defer_to_reactor(self, func: Callable, *args, **kwargs) -> Deferred:
        """
        Internal function used to defer a function call to the reactor thread.
        Note that this will block the reactor until the function completes.
        """
        def run(deferred: Deferred, func: Callable, *args, **kwargs) -> None:
            try:
                result = func(*args, **kwargs)
                deferred.callback(result)
            except Exception as e:
                deferred.errback(e)

        deferred = Deferred()
        reactor.callLater(0, run, deferred, func, *args, **kwargs)
        return deferred

    def defer_to_reactor_thread(self, func: Callable, *args, **kwargs) -> Deferred:
        """
        Internal function used to defer a function call to a separate
        thread, using the reactor's thread pool.
        """
        return threads.deferToThread(func, *args, **kwargs)
    
    def defer_to_queue(
        self,
        function: Callable,
        *args,
        priority: int = 0,
        **kwargs
    ) -> Deferred:
        """
        Internal function used to defer a function call to the do_later queue.
        """
        deferred = Deferred()

        def execute():
            try:
                result = function(*args, **kwargs)
                deferred.callback(result)
            except Exception as e:
                deferred.errback(e)

        self.do_later(execute, priority=priority)
        return deferred
