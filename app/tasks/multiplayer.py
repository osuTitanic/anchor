
import time
import app

MATCH_TIMEOUT_MINUTES = 15
MATCH_TIMEOUT_MINUTES_PERSISTENT = 60*4

MATCH_TIMEOUT_SECONDS = MATCH_TIMEOUT_MINUTES * 60
MATCH_TIMEOUT_SECONDS_PERSISTENT = MATCH_TIMEOUT_MINUTES_PERSISTENT * 60

@app.session.tasks.submit(interval=MATCH_TIMEOUT_SECONDS)
def match_activity() -> None:
    """This task will close any matches that have not been active in the last 15 minutes."""
    for match in app.session.matches.active:
        last_activity = (
            time.time() - match.last_activity
        )

        timeout = (
            MATCH_TIMEOUT_SECONDS_PERSISTENT
            if match.persistent else MATCH_TIMEOUT_SECONDS
        )

        if last_activity < timeout:
            continue

        match.logger.warning(
            f'Match was not active in the last {timeout // 60} minutes. Closing...'
        )
        match.close()
