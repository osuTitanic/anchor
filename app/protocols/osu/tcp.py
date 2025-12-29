
from twisted.internet.address import IPv4Address, IPv6Address
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Protocol
from twisted.python.failure import Failure
from twisted.internet import reactor

from app.common.config import config_instance as config
from app.protocols.osu.streams import ByteStream
from app.common.helpers import location
from app.clients.osu import OsuClient
from app.tasks import logins

import app

IPAddress = IPv4Address | IPv6Address

class TcpOsuClient(OsuClient, Protocol):
    """This class implements the tcp osu connection"""

    def __init__(self, address: IPAddress) -> None:
        super().__init__(address.host, address.port)
        self.is_local = location.is_local_ip(address.host)
        self.stream = ByteStream(self)
        self.protocol = 'tcp'
        self.busy = False

    def connectionMade(self):
        if self.is_local and not config.DEBUG:
            self.logger.info(f'-> <{self.address}:{self.port}>')

        if hash(self.address) in app.session.blocked_connections:
            self.logger.warning(f'Blocked connection from {self.address}')
            self.close_connection('Blocked IP')

        # Enable TCP_NODELAY for lower latency &
        # set TCP keepalive for detecting dead connections
        self.transport.setTcpNoDelay(True)
        self.transport.setTcpKeepAlive(True)

    def connectionLost(self, reason: Failure = Failure(ConnectionDone())):
        app.session.tasks.defer_to_queue(
            self.on_connection_lost,
            reason.getErrorMessage(),
            was_clean=(reason.type == ConnectionDone)
        )

    def enqueue(self, data: bytes) -> None:
        try:
            self.transport.write(data)
        except Exception as e:
            self.logger.critical(f'Failed to write to transport layer: {e}', exc_info=e)
            self.close_connection('Transport write error')

    def enqueue_packet(self, packet, *args):
        self.io.write_packet(self.stream, packet, *args)
        self.logger.debug(f'<- "{packet.name}": {list(args)}')

    def close_connection(self, reason: str = "") -> None:
        reactor.callFromThread(self.transport.loseConnection)
        super().close_connection(reason)

    def dataReceived(self, data: bytes):
        """
        Will handle the initial login request and then switch to
        packetDataReceived to handle bancho packets.
        """
        if data.startswith(b'GET /'):
            self.handleHttpRequest(data)
            return

        if self.busy:
            self.stream += data.replace(b'\r', b'')
            return

        try:
            self.stream += data.replace(b'\r', b'')
            self.busy = True

            if self.stream.count(b'\n') < 3:
                return

            self.logger.debug(
                f'-> Received login: {self.stream}'
            )

            # Login received
            username, password, client, _ = (
                self.stream.split(b'\n', 3)
            )

            if len(password) != 32:
                # osu! clients only send MD5-hashed passwords
                self.logger.warning(f'Invalid login attempt: {username} / {password} / {client}')
                self.stream.clear()
                self.close_connection('Invalid login')
                return

            # We now expect bancho packets from the client
            self.dataReceived = self.packetDataReceived
            self.stream.clear()

            deferred = logins.manager.submit(
                super().on_login_received,
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
        except Exception as e:
            self.logger.error(f'Error on login: {e}', exc_info=e)
            self.close_connection('Login failure')
            self.stream.clear()

        finally:
            self.busy = False

    def packetDataReceived(self, data: bytes):
        """Will handle the bancho packets, after the client login was successful."""
        self.stream += data

        if self.busy:
            return

        try:
            self.busy = True

            while self.stream.available() >= self.io.header_size:
                packet, data = self.io.read_packet(self.stream)

                # Clear the data that was read
                self.stream.reset()

                deferred = app.session.tasks.defer_to_reactor_thread(
                    self.on_packet_received,
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

        finally:
            self.busy = False

    def handleHttpRequest(self, data: bytes) -> None:
        self.logger.debug(f'Recieved http request: {data}')
        self.enqueue(b'HTTP/1.1 302 Found\r\n')
        self.enqueue(f'Location: http://c.{config.DOMAIN_NAME}\r\n'.encode())
        self.close_connection()
