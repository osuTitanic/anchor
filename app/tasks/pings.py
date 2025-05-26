
from chio import PacketType

import time
import app

PING_INTERVAL = 15
PING_TIMEOUT = 180

@app.session.tasks.submit(interval=PING_INTERVAL)
def tcp_pings() -> None:
    """
    This task will handle client pings and timeouts for tcp clients.
    Pings are required for tcp clients, to keep them connected.
    """
    for player in app.session.players.tcp_osu_clients:
        if player.is_bot:
            continue

        player.enqueue_packet(PacketType.BanchoPing)

        if is_server_overloaded():
            continue

        last_response = (time.time() - player.last_response)

        if last_response >= PING_TIMEOUT:
            player.close_connection('Client timed out')

@app.session.tasks.submit(interval=PING_TIMEOUT)
def http_pings() -> None:
    """
    This task will handle client timeouts for http clients.
    Http clients do not require pings, but we still want to
    check if they are still connected.
    """
    for player in app.session.players.http_osu_clients:
        if player.is_bot:
            continue

        if is_server_overloaded():
            continue

        last_response = (time.time() - player.last_response)

        if not player.connected:
            # Why the heck is this player even in the collection
            player.logger.warning('Tried to ping player, but was not connected?')
            player.connectionLost()
            continue

        if last_response >= PING_TIMEOUT:
            player.close_connection('Client timed out')

def is_server_overloaded() -> bool:
    task_queue_size = app.session.tasks.do_later_queue.qsize()
    return task_queue_size >= 50
