
import app

def event_listener():
    """This will listen for redis pubsub events and call the appropriate functions."""
    events = app.session.events.listen()

    if app.session.tasks._shutdown:
        exit()

    for func, args, kwargs in events:
        func(*args, **kwargs)
