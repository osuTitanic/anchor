
from concurrent.futures import Future
from contextlib import suppress
from app.common import officer
from app.session import tasks
from queue import Empty
import time

@tasks.submit(interval=1, threaded=True)
def execute_task_queue():
    """
    Execute all tasks submitted via. tasks.do_later(...), e.g. database writes.
    """
    while True:
        batch_size = execute_batch()

        if tasks.shutdown:
            tasks.logger.debug("Shutting down task queue.")
            break

        # Short sleep to reduce CPU usage and release GIL
        time.sleep(0.001 if batch_size <= 0 else 0.0001)

def execute_batch(max_batch: int = 10) -> int:
    """Execute a batch of tasks from the do_later queue"""
    batch_size = 0

    while batch_size < max_batch:
        # Check if we have capacity in the executor
        current_workers = tasks.do_later_executor._work_queue.qsize()

        if current_workers >= tasks.do_later_workers:
            has_capacity = tasks.do_later_executor._idle_semaphore.acquire(blocking=False)

            if not has_capacity:
                # No capacity, break from batch loop
                break

        try:
            # Get the latest task, sorted by priority
            _, _, func, args, kwargs = tasks.do_later_queue.get_nowait()
            
            # Submit task to executor
            tasks.do_later_executor.submit(func, *args, **kwargs)
            tasks.do_later_queue.task_done()
            batch_size += 1
        except Empty:
            # Queue is empty, break from batch loop
            break
        except Exception as e:
            officer.call(f"Failed to execute '{func.__name__}'.", exc_info=e)

            with suppress(Exception):
                tasks.do_later_queue.task_done()

    return batch_size
