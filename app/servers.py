
from autobahn.websocket.compress import PerMessageDeflateOffer, PerMessageDeflateOfferAccept
from autobahn.twisted.websocket import WebSocketServerFactory
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.interfaces import IAddress
from twisted.web.server import Site
from typing import Optional

from .protocols.osu.ws import WebsocketOsuClient
from .protocols.osu.http import HttpOsuHandler
from .protocols.osu.tcp import TcpOsuClient
from .protocols.irc.tcp import TcpIrcProtocol

import app

class TcpBanchoFactory(Factory):
    protocol = TcpOsuClient

    def startFactory(self):
        app.session.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        app.session.logger.warning(f'Stopping factory: {self}')

    def buildProtocol(self, addr: IAddress) -> Optional[Protocol]:
        client = self.protocol(addr)
        client.factory = self
        return client

class HttpBanchoFactory(Site):
    def __init__(self):
        super().__init__(HttpOsuHandler())

    def startFactory(self):
        app.session.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        app.session.logger.warning(f'Stopping factory: {self}')

class WebsocketBanchoFactory(WebSocketServerFactory):
    def __init__(self):
        super().__init__()
        self.protocol = WebsocketOsuClient

        # Allow per-message deflate compression
        def accept_deflate(offers):
            for offer in offers:
                if isinstance(offer, PerMessageDeflateOffer):
                    return PerMessageDeflateOfferAccept(offer)

        self.setProtocolOptions(perMessageCompressionAccept=accept_deflate)

    def startFactory(self):
        app.session.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        app.session.logger.warning(f'Stopping factory: {self}')

class TcpIrcFactory(Factory):
    protocol = TcpIrcProtocol

    def startFactory(self):
        app.session.logger.info(f'Starting factory: {self}')

    def stopFactory(self):
        app.session.logger.warning(f'Stopping factory: {self}')

    def buildProtocol(self, addr: IAddress) -> TcpIrcProtocol:
        client = self.protocol(addr)
        client.factory = self
        return client
