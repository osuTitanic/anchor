

from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.websocket.protocol import ConnectionRequest
from twisted.internet import threads

from app.protocols.osu.streams import ByteStream
from app.objects import OsuClientInformation
from app.common.streams import StreamIn
from app.clients.osu import OsuClient
from app.common.helpers import ip

import logging
import gzip

class WebsocketOsuClient(WebSocketServerProtocol):
    """This class implements the websocket osu connection, mainly used for oldsu! clients."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('websockets')
        self.player = OsuClient(None, None)
        self.stream = ByteStream(self)

    @property
    def address(self):
        return self.player.address if self.player else 'unknown'

    def onConnect(self, request: ConnectionRequest):
        self.player.address = ip.resolve_ip_address_autobahn(request)
        self.player.logger = logging.getLogger(self.address)
        self.player.port = request.peer.split(":")[2]
        self.player.enqueue = self.enqueue
        self.logger.info(f'-> <{self.address}>')

    def onClose(self, wasClean: bool, code: int, reason: str):
        self.player.on_connection_lost(reason, wasClean)

    def onMessage(self, payload: bytes, isBinary: bool):
        # Client may send \r\n or just \n, as well as trailing newlines
        payload = payload.replace(b'\r\n', b'\n').strip(b'\n')

        if payload.count(b'\n') != 2:
            self.logger.warning(f'Invalid login payload: "{payload}"')
            self.close_connection()
            return

        username, password, client = (
            payload.split(b'\n', 3)
        )

        self.player.info = OsuClientInformation.from_string(
            client.decode(),
            self.address
        )

        if not self.player.info:
            self.logger.warning(f'Failed to parse client: "{client.decode()}"')
            self.close_connection()
            return

        # We now expect bancho packets from the client
        self.onMessage = self.onPacketMessage

        deferred = threads.deferToThread(
            self.player.login_received,
            username.decode(),
            password.decode(),
            self.player.info
        )

        deferred.addErrback(
            lambda f: (
                self.logger.error(f'Error on login: {f.getErrorMessage()}', exc_info=f.value),
                self.close_connection(f.getErrorMessage())
            )
        )

    def onPacketMessage(self, payload: bytes, isBinary: bool):
        if not isBinary:
            return

        self.stream += payload

        while self.stream.available() >= self.player.io.header_size:
            packet, data = self.player.io.read_packet(self.stream)

            # Clear the data that was read
            self.stream.reset()

            deferred = threads.deferToThread(
                self.player.on_packet_received,
                packet, data
            )

            deferred.addErrback(
                lambda f: (
                    self.logger.error(f'Error while processing packet: {f.getErrorMessage()}', exc_info=f.value),
                    self.close_connection(f.getErrorMessage())
                )
            )

    def close_connection(self, reason: str = ""):
        self.player.close_connection(reason)

    def enqueue(self, data: bytes):
        if self.state != self.STATE_OPEN:
            self.logger.debug('Cannot send data to a closed channel')
            return

        self.sendMessage(data, isBinary=True)
