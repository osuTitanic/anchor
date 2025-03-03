
import time
import app

MATCH_TIMEOUT_MINUTES = 15
MATCH_TIMEOUT_SECONDS = MATCH_TIMEOUT_MINUTES * 60

@app.session.tasks.submit(interval=MATCH_TIMEOUT_SECONDS)
def match_activity():
    """This task will close any matches that have not been active in the last 15 minutes."""
    for match in app.session.matches.active:
        last_activity = (time.time() - match.last_activity)

        if last_activity < MATCH_TIMEOUT_SECONDS:
            continue

        match.logger.warning(
            f'Match was not active in the last {MATCH_TIMEOUT_MINUTES} minutes. Closing...'
        )
        match.close()
