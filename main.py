
from app.common.database.repositories import channels, wrapper
from app.common.constants import ANCHOR_ASCII_ART
from app.common.logging import Console, File
from app.common.cache import status, usercount
from twisted.internet import reactor

from app.objects.channel import Channel
from app.banchobot import BanchoBot
from app.servers import *

import importlib
import logging
import config
import signal
import app
import os

logging.basicConfig(
    handlers=[Console, File],
    level=(
        logging.DEBUG
        if config.DEBUG
        else logging.INFO
    )
)

def setup():
    app.session.logger.info(f'{ANCHOR_ASCII_ART}')
    app.session.logger.info(f'Running anchor-{config.VERSION}')
    os.makedirs(config.DATA_PATH, exist_ok=True)
    app.session.logger.info('Loading channels...')

    for channel in channels.fetch_all():
        app.session.logger.info(f'  - {channel.name}')
        app.session.channels.add(
            Channel(
                channel.name,
                channel.topic,
                'BanchoBot',
                channel.read_permissions,
                channel.write_permissions,
                public=True
            )
        )

    app.session.logger.info('Loading bot...')
    app.session.players.add(bot_player := BanchoBot())
    app.session.banchobot = bot_player
    app.session.logger.info(f'  - {bot_player.name}')

    app.session.logger.info('Loading tasks...')
    importlib.import_module('app.tasks.pings')
    importlib.import_module('app.tasks.events')
    importlib.import_module('app.tasks.activities')

    # Reset usercount
    usercount.set(0)

    # Reset player statuses
    for key in status.get_keys():
        player_id = key.split(':')[-1]
        status.delete(player_id)

def before_shutdown(*args):
    for player in app.session.players.tcp_osu_clients:
        # Enqueue server restart packet to all players
        # They should reconnect after 15 seconds
        player.enqueue_server_restart(15 * 1000)

    reactor.callLater(0.5, reactor.stop)
    app.session.events.submit('shutdown')

signal.signal(signal.SIGINT, before_shutdown)

def shutdown():
    for player in app.session.players:
        status.delete(player.id)

    def force_exit(*args):
        app.session.logger.warning("Force exiting...")
        os._exit(0)

    signal.signal(signal.SIGINT, force_exit)

def on_startup_fail(e: Exception):
    app.session.logger.fatal(f'Failed to start server: "{e}"')
    reactor.stop()

@wrapper.exception_wrapper(on_startup_fail)
def setup_servers():
    osu_ws_factory = WebsocketBanchoFactory()
    osu_http_factory = HttpBanchoFactory()
    osu_tcp_factory = TcpBanchoFactory()
    irc_tcp_factory = TcpIrcFactory()

    reactor.suggestThreadPoolSize(config.BANCHO_WORKERS)
    reactor.listenTCP(config.HTTP_PORT, osu_http_factory)
    reactor.listenTCP(config.WS_PORT, osu_ws_factory)
    reactor.listenTCP(config.IRC_PORT, irc_tcp_factory)

    for port in config.TCP_PORTS:
        reactor.listenTCP(port, osu_tcp_factory)

def main():
    reactor.addSystemEventTrigger('before', 'startup', setup)
    reactor.addSystemEventTrigger('before', 'startup', setup_servers)
    reactor.addSystemEventTrigger('after', 'startup', app.session.tasks.start)
    reactor.addSystemEventTrigger('after', 'shutdown', shutdown)
    reactor.run()

if __name__ == "__main__":
    main()
