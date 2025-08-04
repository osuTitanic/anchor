
from chio import PacketType

import config
import time
import app

PING_INTERVAL_IRC = 60
PING_TIMEOUT_IRC = 360
PING_INTERVAL_OSU = 5
PING_TIMEOUT_OSU = 260

@app.session.tasks.submit(interval=PING_INTERVAL_OSU, threaded=True)
def osu_tcp_pings() -> None:
    """
    This task will handle client pings and timeouts for tcp & ws clients.
    Pings are required for tcp clients, to keep them connected.
    """
    targets = {'tcp', 'ws'}

    for player in app.session.players.osu_clients:
        if player.protocol not in targets:
            continue

        if not player.logged_in:
            continue

        last_response = (time.time() - player.last_response)
        last_ping = (time.time() - player.last_ping)

        if last_ping < player.ping_interval:
            continue

        player.enqueue_packet(PacketType.BanchoPing)
        player.last_ping = time.time()

        if last_response >= PING_TIMEOUT_OSU:
            player.close_connection('Client timed out')

@app.session.tasks.submit(interval=PING_TIMEOUT_OSU, threaded=True)
def osu_http_pings() -> None:
    """
    This task will handle client timeouts for http clients.
    Http clients do not require pings, but we still want to
    check if they are still connected.
    """
    for player in app.session.players.http_osu_clients:
        last_response = (time.time() - player.last_response)

        if not player.connected:
            # Why the heck is this player even in the collection
            player.logger.warning('Tried to ping player, but was not connected?')
            player.close_connection()
            continue

        if last_response >= PING_TIMEOUT_OSU:
            player.close_connection('Client timed out')

@app.session.tasks.submit(interval=PING_INTERVAL_IRC, threaded=True)
def irc_pings() -> None:
    """
    This task will handle client pings and timeouts for irc clients.
    Pings are required for irc clients, to keep them connected.
    """
    for player in app.session.players.irc_clients:
        if player.protocol == 'internal':
            continue

        player.enqueue_command_raw("PING", "", [f"cho.{config.DOMAIN_NAME}"])
        last_response = (time.time() - player.last_response)

        if last_response >= PING_TIMEOUT_IRC:
            player.close_connection('Client timed out')
