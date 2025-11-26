
from app.objects.executors import PriorityThreadPoolExecutor
from twisted.internet import reactor, threads
from twisted.internet.defer import Deferred
from typing import Callable, Dict, Tuple
from app.common import officer
from threading import Thread

import itertools
import logging
import config
import time

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
        self.do_later_workers = max(1, config.BANCHO_WORKERS // 3)
        self.do_later_executor = PriorityThreadPoolExecutor(self.do_later_workers)

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
            self.defer_to_reactor if not threaded
            else lambda func: self.defer_to_thread_loop(
                func, interval=interval
            )
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
        self.do_later_executor.submit(
            function, *args, priority=priority, **kwargs
        )

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

    def defer_to_thread_loop(self, func: Callable, *args, interval: int = 5, **kwargs) -> Deferred:
        """
        Internal function used to schedule a thread that runs a specified function in a loop.
        """
        def loop() -> None:
            while True:
                time.sleep(interval)
                func(*args, **kwargs)
                self.logger.debug(f'Task "{func.__name__}" loop finished')

        return self.defer_to_thread(loop, *args, **kwargs)

    def defer_to_reactor(self, func: Callable, *args, delay: int = 0, **kwargs) -> Deferred:
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
        reactor.callLater(delay, run, deferred, func, *args, **kwargs)
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
