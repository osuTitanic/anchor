

from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.websocket.protocol import ConnectionRequest
from twisted.internet import reactor
from chio import PacketType

from app.protocols.osu.streams import ByteStream
from app.clients.osu import OsuClient
from app.common.helpers import ip
from app.tasks import logins

import logging
import app

class WebsocketOsuClient(WebSocketServerProtocol):
    """This class implements the websocket osu connection, mainly used for oldsu! clients."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('websockets')
        self.player = OsuClient(None, None)
        self.stream = ByteStream(self)
        self.player.protocol = 'ws'

    @property
    def address(self):
        return self.player.address if self.player else 'unknown'

    def onConnect(self, request: ConnectionRequest):
        self.player.address = ip.resolve_ip_address_autobahn(request)
        self.player.logger = logging.getLogger(self.address)
        self.player.port = request.peer.split(":")[2]
        self.player.enqueue_packet = self.enqueue_packet
        self.logger.info(f'-> <{self.address}>')

        if hash(self.address) in app.session.blocked_connections:
            self.logger.warning(f'Blocked connection from {self.address}')
            self.close_connection('Blocked IP')

    def onClose(self, wasClean: bool, code: int, reason: str):
        app.session.tasks.defer_to_queue(
            self.player.on_connection_lost,
            reason, wasClean
        )

    def onMessage(self, payload: bytes, isBinary: bool):
        # Client may use \r\n or \n as a separator
        self.stream += payload.strip()

        if self.stream.count(b'\n') != 2:
            return

        username, password, client = (
            self.stream.split(b'\n', 3)
        )
        username, password, client = (
            username.strip(),
            password.strip(),
            client.strip()
        )

        if len(password) != 32:
            # osu! clients only send MD5-hashed passwords
            self.logger.warning(f'Invalid login attempt: {username} / {password} / {client}')
            self.stream.clear()
            self.close_connection('Invalid login')
            return

        # Clear the login data
        self.stream.clear()

        # We now expect bancho packets from the client
        self.onMessage = self.onPacketMessage

        deferred = logins.manager.submit(
            self.player.on_login_received,
            username.decode(),
            password.decode(),
            client.decode()
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

        try:
            while self.stream.available() >= self.player.io.header_size:
                packet, data = self.player.io.read_packet(self.stream)

                # Clear the data that was read
                self.stream.reset()

                deferred = app.session.tasks.defer_to_reactor_thread(
                    self.player.on_packet_received,
                    packet, data
                )

                deferred.addErrback(
                    lambda f: (
                        self.logger.error(f'Error while processing packet: {f.getErrorMessage()}', exc_info=f.value),
                        self.close_connection(f.getErrorMessage())
                    )
                )
        except OverflowError:
            # Wait for more data
            self.stream.seek(0)

        except Exception as e:
            self.logger.error(f'Error while receiving packet: {e}', exc_info=e)
            self.close_connection('Request processing error')

    def enqueue_packet(self, packet: PacketType, *args) -> None:
        self.player.io.write_packet(self.stream, packet, *args)
        self.logger.debug(f'<- "{packet.name}": {list(args)}')

    def enqueue(self, data: bytes):
        reactor.callFromThread(self.do_enqueue, data) # type: ignore

    def close_connection(self, reason: str = ""):
        reactor.callFromThread(self.do_close, reason) # type: ignore
        self.player.close_connection(reason)

    def do_enqueue(self, data: bytes):
        if self.state != self.STATE_OPEN:
            self.logger.debug('Cannot send data to a closed channel')
            self.player.close_connection()
            return

        self.sendMessage(data, isBinary=True)

    def do_close(self, reason: str | None = "") -> None:
        if self.state == self.STATE_CLOSED:
            # Connection is already closed
            return

        if self.state == self.STATE_OPEN:
            code = self.CLOSE_STATUS_CODE_NORMAL if reason else None
            reason = reason or None
            self.sendClose(code, reason)
            return

        if (transport := getattr(self, 'transport', None)):
            # If the connection is not open, we can just close the transport immediately
            transport.loseConnection()
