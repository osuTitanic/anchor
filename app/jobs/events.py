
import app

def event_listener():
    events = app.session.events.listen(buffer_time=0.1)

    if app.session.jobs._shutdown:
        exit()

    for func, args, kwargs in events:
        func(*args, **kwargs)
