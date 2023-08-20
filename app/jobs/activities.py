
import time
import app

MATCH_TIMEOUT_MINUTES = 15
MATCH_TIMEOUT_SECONDS = MATCH_TIMEOUT_MINUTES * 60

def match_activity():
    while True:
        if app.session.jobs._shutdown:
            exit()

        for match in app.session.matches.active:
            if match.in_progress:
                continue

            last_activity = (time.time() - match.last_activity)

            if last_activity > MATCH_TIMEOUT_SECONDS:
                match.logger.warning(
                    f'Match was not active in the last {MATCH_TIMEOUT_MINUTES} minutes. Closing...'
                )
                match.close()

        time.sleep(5)
