
from twisted.internet import reactor

from app.common.database.repositories import channels
from app.common.cache import status, usercount

from app.common.constants import ANCHOR_ASCII_ART
from app.common.logging import Console, File
from app.objects.channel import Channel
from app.objects.player import Player
from app.server import BanchoFactory
from app.jobs import (
    rank_indexing,
    activities,
    events,
    pings
)

import logging
import config
import signal
import app
import os

logging.basicConfig(
    handlers=[Console, File],
    level=logging.DEBUG
        if config.DEBUG
        else logging.INFO
)

def setup():
    app.session.logger.info(f'{ANCHOR_ASCII_ART}\n    anchor-{config.VERSION}\n')
    os.makedirs(config.DATA_PATH, exist_ok=True)

    app.session.logger.info('Loading channels...')

    for channel in channels.fetch_all():
        app.session.logger.info(f'  - {channel.name}')
        app.session.channels.append(
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

    app.session.players.append(
        bot_player := Player.bot_player()
    )
    app.session.bot_player = bot_player
    app.session.logger.info(f'  - {bot_player.name}')

    app.session.logger.info('Loading jobs...')
    app.session.jobs.submit(pings.ping_job)
    app.session.jobs.submit(events.event_listener)
    app.session.jobs.submit(rank_indexing.index_ranks)
    app.session.jobs.submit(activities.match_activity)

    # Reset usercount
    usercount.set(0)

def shutdown():
    # Reset usercount
    usercount.set(0)

    for player in app.session.players:
        status.delete(player.id)

    app.session.events.submit('shutdown')
    app.session.jobs.shutdown(cancel_futures=True, wait=False)

    def force_exit(signal, frame):
        app.session.logger.warning("Force exiting...")
        os._exit(0)

    signal.signal(signal.SIGINT, force_exit)

    for thread in app.session.pool.threads:
        app.session.logger.warning(f'Shutting down: "{thread.name}"')

def main():
    factory = BanchoFactory()

    for port in config.PORTS:
        reactor.listenTCP(port, factory)

    reactor.addSystemEventTrigger('before', 'startup', setup)
    reactor.addSystemEventTrigger('after', 'shutdown', shutdown)
    reactor.run()

if __name__ == "__main__":
    main()
