
import time
import app

PING_INTERVAL = 15
PING_TIMEOUT = 60

@app.session.tasks.submit(interval=15, threaded=True)
def ping() -> None:
    """
    This task will handle client pings and timeouts. Pings are required for tcp clients, to keep them connected.
    For http clients, we can just check if they have responded within the timeout period, and close the connection if not.
    """
    next_ping = (time.time() - PING_INTERVAL)

    for player in app.session.players.tcp_clients:
        if player.is_bot:
            continue

        # Enqueue ping if needed
        if (next_ping > player.last_response):
            player.enqueue_ping()

        last_response = (time.time() - player.last_response)

        if last_response >= PING_TIMEOUT:
            player.logger.warning('Client timed out.')
            player.close_connection()

    for player in app.session.players.http_clients:
        last_response = (time.time() - player.last_response)

        if not player.connected:
            # Why the heck is this player even in the collection
            player.logger.warning('Tried to ping player, but was not connected?')
            player.connectionLost()
            continue

        if last_response >= PING_TIMEOUT:
            player.logger.warning('Client timed out.')
            player.close_connection()
