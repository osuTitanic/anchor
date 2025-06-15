
from twisted.internet.defer import Deferred
from typing import Callable
import config
import app

class LoginManager:
    def __init__(self) -> None:
        self.queue_threshold = 400 * (config.BANCHO_WORKERS // 8)
        self.queue_enabled = False
        self.login_priority = 1

    def submit(
        self,
        function: Callable,
        username: str,
        password: str,
        client_data: str
    ) -> Deferred:
        """
        Wrapper function for submitting login tasks. This is required to
        ensure that the server won't be overloaded with login requests,
        after a certain amount of users have been reached.
        """
        if self.queue_enabled:
            return app.session.tasks.defer_to_queue(
                function,
                username,
                password,
                client_data,
                priority=self.login_priority
            )

        return app.session.tasks.defer_to_reactor_thread(
            function,
            username,
            password,
            client_data
        )

    def update_queue_status(self, user_count: int) -> None:
        """
        Enable the login queue if the current user
        count meets or exceeds the threshold.
        """
        self.queue_enabled = user_count >= self.queue_threshold

manager = LoginManager()
