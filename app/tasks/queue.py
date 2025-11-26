
from contextlib import suppress
from app.common import officer
from app.session import tasks

@tasks.submit(interval=1, threaded=True)
def execute_task_queue():
    """
    Execute all tasks submitted via. tasks.do_later(...), e.g. database writes.
    """
    while True:
        # Wait for an available worker in the executor
        wait_for_worker()

        # Wait for a task & submit it to the executor
        submit_task()

        if tasks.shutdown:
            tasks.logger.debug("Shutting down task queue.")
            break

def wait_for_worker() -> None:
    current_workers = tasks.do_later_executor._work_queue.qsize()

    if current_workers < tasks.do_later_workers:
        return

    with suppress(ValueError):
        # If the number of workers is at maximum, wait for an idle worker
        tasks.do_later_executor._idle_semaphore.acquire()
        tasks.logger.debug("Worker available, continuing task execution.")

def submit_task() -> None:
    try:
        # Get the latest task, sorted by priority
        _, _, func, args, kwargs = tasks.do_later_queue.get()

        # Submit task to executor
        tasks.do_later_executor.submit(func, *args, **kwargs)
        tasks.do_later_queue.task_done()
    except Exception as e:
        officer.call(f"Failed to execute '{func.__name__}'.", exc_info=e)
