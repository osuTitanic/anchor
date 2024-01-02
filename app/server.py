
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.interfaces import IAddress
from twisted.web.http import HTTPFactory
from typing import Optional

from .http import HttpBanchoProtocol
from .tcp import TcpBanchoProtocol

import app

class TcpBanchoFactory(Factory):
    protocol = TcpBanchoProtocol

    def startFactory(self):
        app.session.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        app.session.logger.warning(f'Stopping factory: {self}')

    def buildProtocol(self, addr: IAddress) -> Optional[Protocol]:
        client = self.protocol(addr)
        client.factory = self
        return client

class HttpBanchoFactory(HTTPFactory):
    protocol = HttpBanchoProtocol

    def startFactory(self):
        app.session.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        app.session.logger.warning(f'Stopping factory: {self}')

    def buildProtocol(self, addr: IAddress) -> Optional[Protocol]:
        client = self.protocol(addr)
        client.factory = self
        return client
