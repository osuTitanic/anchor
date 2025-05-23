
import app

@app.session.tasks.submit(interval=1, threaded=True)
def execute_task_queue():
    """Execute all tasks submitted via. tasks.do_later(...), e.g. database writes."""
    while True:
        try:
            _, _, func, args, kwargs = app.session.tasks.queue.get()
            func(*args, **kwargs)
        except Exception as e:
            app.session.logger.error(f"Failed to execute '{func.__name__}': {e}")
        finally:
            app.session.tasks.queue.task_done()

        if app.session.tasks.shutdown:
            app.session.logger.debug("Shutting down task queue.")
            break
