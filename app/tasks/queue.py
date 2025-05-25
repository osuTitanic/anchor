
from app.session import tasks, logger
from app.common import officer

@tasks.submit(interval=1, threaded=True)
def execute_task_queue():
    """
    Execute all tasks submitted via. tasks.do_later(...), e.g. database writes.
    """
    while True:
        try:
            # Get the latest task, sorted by priority
            _, _, func, args, kwargs = tasks.do_later_queue.get()

            # Submit task to executor
            future = tasks.do_later_executor.submit(func, *args, **kwargs)
            tasks.do_later_futures.append(future)

            if len(tasks.do_later_futures) >= tasks.do_later_workers:
                # Wait for first future to complete, cancel it if necessary
                future = tasks.do_later_futures.pop(0)
                future.result(timeout=120)
        except Exception as e:
            officer.call(f"Failed to execute '{func.__name__}'.", exc_info=e)
        finally:
            tasks.do_later_queue.task_done()

        if tasks.shutdown:
            logger.debug("Shutting down task queue.")
            break
