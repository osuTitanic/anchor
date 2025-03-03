
import app

@app.session.tasks.submit(interval=1)
def event_listener() -> None:
    """This will listen for redis pubsub events and call the appropriate functions."""
    message = app.session.events.poll()

    if not message:
        return

    func, args, kwargs = message

    # Use the task executor to prevent blocking the reactor
    app.session.tasks.executor.submit(func, *args, **kwargs)
