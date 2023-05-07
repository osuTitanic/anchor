
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.interfaces import IAddress
from typing import Optional

from .objects.player import Player
from .objects.channel import Channel

import bancho

class BanchoFactory(Factory):
    protocol = Player

    def startFactory(self):
        bancho.services.logger.info('Loading channels...')

        # Loading channels
        for channel in bancho.services.database.channels():
            bancho.services.logger.info(f'- {channel.name}')
            bancho.services.channels.append(
                Channel.from_db(channel)
            )

        bancho.services.logger.info('Loading bot...')

        # Load bot player
        bancho.services.players.append(
            bot_player := Player.bot_player()
        )

        bancho.services.logger.info(f'- {bot_player.name}')

        # Load jobs
        bancho.services.logger.info('Loading jobs')

        from .jobs.pings import ping

        bancho.services.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        bancho.services.logger.warning(f'Stopping factory: {self}')
        bancho.services.jobs.shutdown(cancel_futures=True)

    def buildProtocol(self, addr: IAddress) -> Optional[Protocol]:
        client = self.protocol(addr)
        client.factory = self

        return client
