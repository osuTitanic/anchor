
from twisted.python.failure import Failure
from twisted.web.http import Request

import config
import app

def thread_callback(error: Failure):
    app.session.logger.error(
        f'Failed to execute thread: {error.__str__()} ({error.getErrorMessage()})',
        exc_info=error.value
    )
