

from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.websocket.protocol import ConnectionRequest
from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure
from twisted.internet import threads

from app.common.streams import StreamIn
from app.objects.player import Player
from app.common.helpers import ip
from app.objects import OsuClient

import logging
import config
import gzip

class WebsocketBanchoProtocol(WebSocketServerProtocol):
    """This class implements the websocket bancho connection."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('websockets')
        self.player = Player(None, None)

    @property
    def address(self):
        return self.player.address if self.player else 'unknown'

    def onOpen(self):
        self.logger.info(f'-> <{self.address}>')

    def onClose(self, wasClean: bool, code: int, reason: str):
        self.player.connectionLost()

        if not wasClean:
            self.logger.warning(f'<{self.address}> -> Lost connection: "{reason}".')
            return

        self.logger.info(f'<{self.address}> -> Connection done.')

    def onConnect(self, request: ConnectionRequest):
        self.logger.info(f'-> <{self.address}>')
        self.player.address = ip.resolve_ip_address_autobahn(request)
        self.player.logger = logging.getLogger(self.address)
        self.player.port = request.peer.split(":")[1]
        self.player.enqueue = self.enqueue

    def onMessage(self, payload: bytes, isBinary: bool):
        # Client may send \r\n or just \n
        payload = payload.replace(b'\r\n', b'\n')

        if payload.count(b'\n') < 2:
            self.logger.warning(f'Invalid login payload: "{payload}"')
            self.close_connection()
            return

        username, password, client = (
            payload.split(b'\n', 3)
        )

        self.player.client = OsuClient.from_string(
            client.decode(),
            self.address
        )

        if not self.player.client:
            self.logger.warning(f'Failed to parse client: "{client.decode()}"')
            self.close_connection()
            return

        # We now expect bancho packets from the client
        self.onMessage = self.onPacketMessage

        deferred = threads.deferToThread(
            self.player.login_received,
            username.decode(),
            password.decode(),
            self.player.client
        )

        deferred.addErrback(
            lambda f: (
                self.logger.error(f'Error on login: {f.getErrorMessage()}', exc_info=f.value),
                self.close_connection(f.value)
            )
        )

    def onPacketMessage(self, payload: bytes, isBinary: bool):
        if not isBinary:
            return
        
        stream = StreamIn(payload)

        while stream.available():
            packet = stream.u16()
            compression = True

            # In version b323 and below, the
            # compression is enabled by default
            if self.player.client.version.date > 323:
                compression = stream.bool()

            payload = stream.read(stream.u32())

            if compression:
                payload = gzip.decompress(payload)

            deferred = threads.deferToThread(
                self.player.packet_received,
                packet_id=packet,
                stream=StreamIn(payload)
            )

            deferred.addErrback(
                lambda f: (
                    self.logger.error(f'Error while processing packet: {f.getErrorMessage()}', exc_info=f.value),
                    self.close_connection(f.value)
                )
            )

    def close_connection(self, error: Exception | None = None):
        if error:
            self.player.send_error()

        self.logger.info(f'Closing connection -> <{self.address}>')
        self.player.connectionLost(Failure(error or ConnectionDone()))

    def enqueue(self, data: bytes):
        self.sendMessage(data, isBinary=True)
