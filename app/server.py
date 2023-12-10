
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.interfaces import IAddress
from typing import Optional

from .common.database.repositories import channels
from .common.cache import status, usercount
from .objects.channel import Channel
from .objects.player import Player

from .jobs import (
    rank_indexing,
    activities,
    events,
    pings
)

import signal
import app
import os

class BanchoFactory(Factory):
    protocol = Player

    def startFactory(self):
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

        app.session.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        app.session.logger.warning(f'Stopping factory: {self}')

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

    def buildProtocol(self, addr: IAddress) -> Optional[Protocol]:
        client = self.protocol(addr)
        client.factory = self

        return client
