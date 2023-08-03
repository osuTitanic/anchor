
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.interfaces import IAddress
from typing import Optional

from .common.database.repositories import channels
from .objects.channel import Channel
from .objects.player import Player

import app

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

        app.session.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        app.session.logger.warning(f'Stopping factory: {self}')

    def buildProtocol(self, addr: IAddress) -> Optional[Protocol]:
        client = self.protocol(addr)
        client.factory = self

        return client
