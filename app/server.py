
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.interfaces import IAddress
from typing import Optional

from .tcp import BanchoProtocol

import app

class TcpBanchoFactory(Factory):
    protocol = BanchoProtocol

    def startFactory(self):
        app.session.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        app.session.logger.warning(f'Stopping factory: {self}')

    def buildProtocol(self, addr: IAddress) -> Optional[Protocol]:
        client = self.protocol(addr)
        client.factory = self

        return client
