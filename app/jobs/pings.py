
import time
import app

PING_INTERVAL = 30
TIMEOUT_SECS  = 45

def ping():
    next_ping = time.time() - PING_INTERVAL

    for player in app.session.players:
        if player.is_bot:
            continue

        # Enqueue ping if needed
        if (next_ping > player.last_response):
            player.enqueue_ping()

        last_response = (time.time() - player.last_response)

        # Check timeout
        if (last_response >= TIMEOUT_SECS):
            player.logger.warning('Client timed out...')
            player.close_connection()

def ping_job():
    while True:
        if app.session.jobs._shutdown:
            exit()

        time.sleep(1)
        ping()