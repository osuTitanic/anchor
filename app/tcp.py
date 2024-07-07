
from __future__ import annotations

from twisted.internet.address import IPv4Address, IPv6Address
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Protocol
from twisted.internet import threads, reactor
from twisted.python.failure import Failure

from app.common.helpers import location
from app.common.streams import StreamIn
from app.objects.player import Player
from app.objects import OsuClient

import config
import gzip

IPAddress = IPv4Address | IPv6Address

class TcpBanchoProtocol(Player, Protocol):
    """This class implements the tcp bancho connection."""

    request_timeout = 20
    buffer = b""
    busy = False

    def __init__(self, address: IPAddress) -> None:
        super().__init__(address.host, address.port)
        self.is_local = location.is_local_ip(address.host)
        self.protocol = 'tcp'

    def connectionMade(self):
        if not self.is_local or config.DEBUG:
            self.logger.info(
                f'-> <{self.address}:{self.port}>'
            )

    def connectionLost(self, reason: Failure = Failure(ConnectionDone())):
        super().connectionLost(reason)

        if reason != None and reason.type != ConnectionDone:
            self.logger.warning(
                f'<{self.address}> -> Lost connection: "{reason.getErrorMessage()}".'
            )
            return

        if not self.is_local or config.DEBUG:
            self.logger.info(
                f'<{self.address}> -> Connection done.'
            )

    def enqueue(self, data: bytes):
        try:
            self.transport.write(data)
        except Exception as e:
            self.logger.error(
                f'Could not write to transport layer: {e}',
                exc_info=e
            )

    def close_connection(self, error: Exception | None = None):
        if not self.is_local or config.DEBUG:
            if error:
                self.logger.warning(f'Closing connection -> <{self.address}>')
                self.send_error()
            else:
                self.logger.info(f'Closing connection -> <{self.address}>')

        self.transport.loseConnection()
        super().connectionLost(error)

    def dataReceived(self, data: bytes):
        """
        Will handle the initial login request and then switch to
        packetDataReceived to handle bancho packets.
        """

        if data.startswith(b'GET /'):
            self.handleHttpRequest(data)
            return

        if self.busy:
            self.buffer += data
            return

        try:
            self.buffer += data.replace(b'\r', b'')
            self.busy = True

            if self.buffer.count(b'\n') < 3:
                return

            self.logger.debug(
                f'-> Received login: {self.buffer}'
            )

            # Login received
            username, password, client, self.buffer = self.buffer.split(b'\n', 3)

            self.client = OsuClient.from_string(
                client.decode(),
                self.address
            )

            if not self.client:
                self.logger.warning(
                    f'Failed to parse client: "{client.decode()}"'
                )
                self.close_connection()
                return

            # We now expect bancho packets from the client
            self.dataReceived = self.packetDataReceived

            deferred = threads.deferToThread(
                super().login_received,
                username.decode(),
                password.decode(),
                self.client
            )

            deferred.addErrback(
                lambda f: (
                    self.logger.error(f'Error on login: {f.getErrorMessage()}', exc_info=f.value),
                    self.close_connection(f.value)
                )
            )
        except Exception as e:
            self.logger.error(
                f'Error on login: {e}',
                exc_info=e
            )
            self.close_connection(e)

        finally:
            self.busy = False

    def packetDataReceived(self, data: bytes):
        """Will handle the bancho packets, after the client login was successful."""
        if self.busy:
            self.buffer += data
            return

        try:
            self.busy = True
            self.buffer += data

            while self.buffer:
                stream = StreamIn(self.buffer)

                try:
                    packet = stream.u16()

                    if self.client.version.date > 323:
                        compression = stream.bool()
                    else:
                        # In version b323 and below, the compression is enabled by default
                        compression = True

                    payload = stream.read(stream.u32())
                except OverflowError:
                    # Wait for next buffer
                    break

                if compression:
                    # gzip compression is only used in very old clients
                    payload = gzip.decompress(payload)

                # Update buffer
                self.buffer = stream.readall()

                deferred = threads.deferToThread(
                    self.packet_received,
                    packet_id=packet,
                    stream=StreamIn(payload)
                )

                deferred.addErrback(
                    lambda f: (
                        self.logger.error(f'Error while processing packet: {f.getErrorMessage()}', exc_info=f.value),
                        self.close_connection(f.value)
                    )
                )
        except Exception as e:
            self.logger.error(
                f'Error while receiving packet: {e}',
                exc_info=e
            )
            self.close_connection(e)

        finally:
            self.busy = False

    def handleHttpRequest(self, data: bytes) -> None:
        self.logger.debug(f'Recieved http request: {data}')
        self.enqueue(b'HTTP/1.1 302 Found\r\n')
        self.enqueue(f'Location: http://c.{config.DOMAIN_NAME}\r\n'.encode())
        self.close_connection()
