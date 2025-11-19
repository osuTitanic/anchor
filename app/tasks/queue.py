
from concurrent.futures import Future
from app.common import officer
from app.session import tasks

@tasks.submit(interval=1, threaded=True)
def execute_task_queue():
    """
    Execute all tasks submitted via. tasks.do_later(...), e.g. database writes.
    """
    while True:
        current_workers = tasks.do_later_executor._work_queue.qsize()

        if current_workers >= tasks.do_later_workers:
            # If the number of workers is at maximum, wait for an idle worker
            tasks.do_later_executor._idle_semaphore.acquire()

        try:
            # Get the latest task, sorted by priority
            _, _, func, args, kwargs = tasks.do_later_queue.get()

            # Submit task to executor
            tasks.do_later_executor.submit(func, *args, **kwargs)
        except TypeError as e:
            # Queue is fucked, no idea how this happens
            # "TypeError: '<' not supported between instances of 'TcpOsuClient' and 'TcpOsuClient'"
            tasks.do_later_queue.queue.pop()
        except Exception as e:
            officer.call(f"Failed to execute '{func.__name__}'.", exc_info=e)
        finally:
            tasks.do_later_queue.task_done()

        if tasks.shutdown:
            tasks.logger.debug("Shutting down task queue.")
            break
