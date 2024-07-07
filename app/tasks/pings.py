
from twisted.internet import reactor
from app.common import officer

import config
import time
import app

PING_INTERVAL = 10
TIMEOUT_SECS  = 45

def ping():
    """
    This task will handle client pings and timeouts. Pings are required for tcp clients, to keep them connected.
    For http clients, we can just check if they have responded within the timeout period, and close the connection if not.
    """
    threadpool = reactor.getThreadPool()
    disable_timeouts = len(threadpool.waiters) < config.BANCHO_WORKERS / 2

    next_ping = (time.time() - PING_INTERVAL)

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

        if (last_response >= TIMEOUT_SECS) and not disable_timeouts:
            player.logger.warning('Client timed out!')
            player.close_connection()

    for player in app.session.players.http_clients:
        last_response = (time.time() - player.last_response)

        if (last_response >= TIMEOUT_SECS) and not disable_timeouts:
            player.logger.warning('Client timed out!')
            player.close_connection()

def ping_task():
    while True:
        if app.session.tasks._shutdown:
            exit()

        try:
            ping()
            time.sleep(1)
        except Exception as e:
            officer.call(f'Ping task failed: {e}', exc_info=e)
