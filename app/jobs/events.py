
import app

def event_listener():
    events = app.session.events.listen()

    if app.session.jobs._shutdown:
        exit()

    for func, args, kwargs in events:
        func(*args, **kwargs)
