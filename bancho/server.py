
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

        bancho.services.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        bancho.services.logger.warning(f'Stopping factory: {self}')

        # TODO: Disconnect all players

    def buildProtocol(self, addr: IAddress) -> Optional[Protocol]:
        client = self.protocol(addr)
        client.factory = self

        return client
