
from twisted.internet.defer import Deferred
from typing import Callable
import config
import app

class LoginManager:
    def __init__(self) -> None:
        self.packet_threshold = 5000 * (config.BANCHO_WORKERS // 8)
        self.login_threshold = 100 * (config.BANCHO_WORKERS // 8)
        self.login_priority = 1

    @property
    def queue_enabled(self) -> bool:
        return (
            app.session.logins_per_minute.rate > self.login_threshold or
            app.session.packets_per_minute.rate > self.packet_threshold
        )

    def submit(
        self,
        function: Callable,
        *args,
        **kwargs
    ) -> Deferred:
        """
        Wrapper function for submitting login tasks. This is required to
        ensure that the server won't be overloaded with login requests,
        after a certain amount of users have been reached.
        """
        if self.queue_enabled:
            return app.session.tasks.defer_to_queue(
                function, *args, **kwargs,
                priority=self.login_priority
            )

        return app.session.tasks.defer_to_reactor_thread(
            function,
            *args,
            **kwargs
        )

manager = LoginManager()
