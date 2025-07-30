
from app.common.database.repositories import channels, wrapper
from app.common.constants import ANCHOR_ASCII_ART
from app.common.logging import Console, File
from app.common.cache import status, usercount
from twisted.internet import reactor

from app.objects.channel import Channel, PythonInterpreterChannel
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
    app.session.logger.info(ANCHOR_ASCII_ART.removesuffix("\n"))
    app.session.logger.info(f'Running anchor-{config.VERSION}')
    os.makedirs(config.DATA_PATH, exist_ok=True)

    app.session.logger.info('Loading bot...')
    app.session.players.add(bot_player := BanchoBot())
    app.session.banchobot = bot_player
    app.session.banchobot.update_activity()

    if not bot_player.object:
        # BanchoBot user object was not found inside the database
        bot_player.logger.warning("Failed to load BanchoBot!")
        app.session.players.remove(bot_player)

    app.session.logger.info(f'  - {bot_player.name}')
    app.session.logger.info('Loading channels...')

    for channel in channels.fetch_all():
        app.session.logger.info(f'  - {channel.name}')
        app.session.channels.add(
            channel := Channel(
                channel.name,
                channel.topic,
                'BanchoBot',
                channel.read_permissions,
                channel.write_permissions,
                public=True
            )
        )
        app.session.banchobot.channels.add(channel)

    if config.DEBUG:
        app.session.logger.info('  - #python')
        app.session.channels.add(channel := PythonInterpreterChannel())
        app.session.banchobot.channels.add(channel)

    app.session.logger.info('Loading tasks...')
    importlib.import_module('app.tasks.queue')
    importlib.import_module('app.tasks.pings')
    importlib.import_module('app.tasks.events')
    importlib.import_module('app.tasks.multiplayer')
    
    app.session.logger.info('Loading filters...')
    app.session.filters.populate()
    app.session.logger.info(f'  - {len(app.session.filters)} filters loaded')

    # Reset usercount
    usercount.set(1)

    # Reset player statuses
    for key in status.get_keys():
        player_id = key.split(':')[-1]
        status.delete(player_id)

def setup_tracy():
    if not config.DEBUG:
        return
    
    try:
        import pytracy
    except ImportError:
        app.session.logger.warning('"pytracy" module is not installed, tracy will not be available')
        return
    
    pytracy.enable_tracing(True)
    app.session.logger.info('Tracy profiler enabled')

def before_shutdown(*args):
    for player in app.session.players.tcp_osu_clients:
        # Enqueue server restart packet to all players
        # They should reconnect after 15 seconds
        player.enqueue_server_restart(15 * 1000)

    for player in app.session.players.irc_clients:
        player.enqueue_server_restart(0)

    reactor.callLater(0.5, reactor.stop)
    app.session.events.submit('shutdown')
    app.session.tasks.shutdown = True
    app.session.tasks.do_later(lambda: None)

signal.signal(signal.SIGINT, before_shutdown)

def shutdown():
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

    if not config.SSL_ENABLED:
        return

    context = app.ssl.setup(min_protocol=0)

    if not context:
        app.session.logger.warning('SSL support is not available, please install OpenSSL and try again.')
        return

    app.ssl.listen(config.IRC_PORT_SSL, irc_tcp_factory, context)
    app.session.logger.info(f'SSL connections enabled')

def main():
    reactor.addSystemEventTrigger('before', 'startup', setup)
    reactor.addSystemEventTrigger('before', 'startup', setup_servers)
    reactor.addSystemEventTrigger('after', 'startup', setup_tracy)
    reactor.addSystemEventTrigger('after', 'startup', app.session.tasks.start)
    reactor.addSystemEventTrigger('after', 'shutdown', shutdown)
    reactor.run()

if __name__ == "__main__":
    main()
