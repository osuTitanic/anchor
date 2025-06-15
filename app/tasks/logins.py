
from twisted.internet.defer import Deferred
from typing import Callable
import config
import app

queue_threshold = 400 * (config.BANCHO_WORKERS // 8)
queue_enabled = False

def submit(
    function: Callable,
    username: str,
    password: str,
    client_data: str
) -> Deferred:
    """
    Wrapper function for submitting login tasks.
    This is required to ensure that the server won't be overloaded with
    login requests, after a certain amount of users have been reached.
    """
    global queue_enabled

    if queue_enabled:
        return app.session.tasks.defer_to_queue(
            function,
            username,
            password,
            client_data,
            priority=1
        )

    return app.session.tasks.defer_to_reactor_thread(
        function,
        username,
        password,
        client_data
    )

def update_queue_status(user_count: int) -> None:
    global queue_enabled
    queue_enabled = user_count >= queue_threshold
