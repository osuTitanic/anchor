
import time
import app

PING_INTERVAL = 10
TIMEOUT_SECS  = 45

def ping():
    next_ping = time.time() - PING_INTERVAL

    for player in app.session.players.tcp_clients:
        if player.is_bot:
            continue

        if not player.connected:
            # Why the heck is this player even in the collection
            player.logger.warning('Tried to ping player, but was not connected?')
            player.connectionLost()
            continue

        # Enqueue ping if needed
        if (next_ping > player.last_response):
            player.enqueue_ping()

        last_response = (time.time() - player.last_response)

        if (last_response >= TIMEOUT_SECS):
            player.logger.warning('Client timed out...')
            player.close_connection()

    for player in app.session.players.http_clients:
        last_response = (time.time() - player.last_response)

        if last_response >= TIMEOUT_SECS:
            player.logger.warning('Client timed out...')
            player.close_connection()

def ping_job():
    while True:
        if app.session.jobs._shutdown:
            exit()

        time.sleep(1)
        ping()
