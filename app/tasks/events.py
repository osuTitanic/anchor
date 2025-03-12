
import app

@app.session.tasks.submit(interval=0, threaded=True)
def event_listener() -> None:
    """This will listen for redis pubsub events and call the appropriate functions."""
    for func, args, kwargs in app.session.events.listen():
        func(*args, **kwargs)
