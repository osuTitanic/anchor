
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.interfaces import IAddress
from typing import Optional

from .objects.player import Player

import bancho

class BanchoFactory(Factory):
    protocol = Player

    def startFactory(self):
        bancho.services.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        bancho.services.logger.warning(f'Stopping factory: {self}')

    def buildProtocol(self, addr: IAddress) -> Optional[Protocol]:
        client = self.protocol(addr)
        client.factory = self

        return client
