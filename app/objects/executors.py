
# Taken and modified from:
# https://github.com/oleglpts/PriorityThreadPoolExecutor/blob/master/PriorityThreadPoolExecutor/__init__.py

from concurrent.futures.thread import (
    ThreadPoolExecutor,
    _threads_queues,
    _python_exit,
    _WorkItem,
    _base
)

import threading
import weakref
import atexit
import random
import queue
import sys


class PriorityQueue(queue.PriorityQueue):
    def put(self, item, block = True, timeout = None):
        # An item can be "None" on shutdown signal
        # To make the executor shut down properly we
        # need to put a max priority item instead
        item = item or (sys.maxsize, sys.maxsize, tuple())
        return super().put(item, block, timeout)


class PriorityThreadPoolExecutor(ThreadPoolExecutor):
    """
    Thread pool executor with priority queue (priorities must be different, lowest first)
    """

    def __init__(self, max_workers=None):
        """
        Initializes a new PriorityThreadPoolExecutor instance

        :param max_workers: the maximum number of threads that can be used to execute the given calls
        :type max_workers: int
        """
        super(PriorityThreadPoolExecutor, self).__init__(max_workers)

        # Change work queue type to PriorityQueue
        self._work_queue = PriorityQueue()

    def submit(self, fn, *args, **kwargs):
        """
        Sending the function to the execution queue

        :param fn: function being executed
        :type fn: callable
        :param args: function's positional arguments
        :param kwargs: function's keywords arguments
        :return: future instance
        :rtype: _base.Future

        Added keyword:

        - priority (integer later sys.maxsize)
        """
        with self._shutdown_lock:
            if self._shutdown:
                raise RuntimeError('cannot schedule new futures after shutdown')

            if _shutdown:
                raise RuntimeError('cannot schedule new futures after interpreter shutdown')

            priority = kwargs.get('priority', 0)
            second_priority = random.randint(0, sys.maxsize-1)

            if 'priority' in kwargs:
                del kwargs['priority']

            f = _base.Future()

            if sys.version_info >= (3, 14):
                task = self._resolve_work_item_task(fn, args, kwargs)
                w = _WorkItem(f, task)
            else:
                w = _WorkItem(f, fn, args, kwargs)

            self._work_queue.put((priority, second_priority, w))
            self._adjust_thread_count()
            return f

    def _adjust_thread_count(self):
        """Attempt to start a new thread"""
        # When the executor gets lost, the weakref callback
        # will wake up the worker threads.
        def weak_ref_cb(_, q=self._work_queue):
            q.put(NULL_ENTRY)

        num_threads = len(self._threads)

        if num_threads < self._max_workers:
            thread_name = '%s_%d' % (
                self._thread_name_prefix or self,
                num_threads
            )

            if sys.version_info >= (3, 14):
                ctx = self._create_worker_context()
                args = (weakref.ref(self, weak_ref_cb), ctx, self._work_queue)
            else:
                args = (weakref.ref(self, weak_ref_cb), self._work_queue)

            t = threading.Thread(
                name=thread_name,
                target=_worker,
                args=args
            )

            t.daemon = True
            t.start()
            self._threads.add(t)
            _threads_queues[t] = self._work_queue

    def shutdown(self, wait=True):
        """
        Pool shutdown

        :param wait: if True wait for all threads to complete
        :type wait: bool
        """
        with self._shutdown_lock:
            self._shutdown = True
            self._work_queue.put(NULL_ENTRY)

        if wait:
            for t in self._threads:
                t.join()


def _worker(*args):
    """
    Worker

    :param executor_reference: executor function
    :type executor_reference: callable
    :param work_queue: work queue
    :type work_queue: queue.PriorityQueue
    """
    try:
        if sys.version_info >= (3, 14):
            executor_reference, ctx, work_queue = args
            runner = lambda work_item: work_item.run(ctx)
        else:
            executor_reference, work_queue = args
            runner = lambda work_item: work_item.run()

        while True:
            work_item = work_queue.get(block=True)

            if work_item and work_item[0] != sys.maxsize:
                work_item = work_item[2]
                runner(work_item)
                del work_item
                continue

            # We have received a shutdown signal
            executor = executor_reference()

            if _shutdown or executor is None or executor._shutdown:
                work_queue.put(NULL_ENTRY)
                return

            del executor
    except BaseException:
        _base.LOGGER.critical('Exception in worker', exc_info=True)


_shutdown = False
NULL_ENTRY = (sys.maxsize, sys.maxsize, tuple())
