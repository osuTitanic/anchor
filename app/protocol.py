
from twisted.internet.address import IPv4Address, IPv6Address
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Protocol
from twisted.python.failure import Failure

from typing import Union, Optional
from enum import Enum

from app.common.streams import StreamOut, StreamIn
from app.objects import OsuClient

import traceback
import logging
import struct
import socket

IPAddress = Union[IPv4Address, IPv6Address]

class BanchoProtocol(Protocol):
    """This class will be a base for receiving and parsing packets and logins."""

    buffer  = b""
    busy    = False
    proxied = False

    def __init__(self, address: IPAddress) -> None:
        self.logger = logging.getLogger(address.host)
        self.client: Optional[OsuClient] = None
        self.address = address

    @property
    def is_local(self) -> bool:
        private = (
            [ 2130706432, 4278190080 ], # 127.0.0.0
            [ 3232235520, 4294901760 ], # 192.168.0.0
            [ 2886729728, 4293918720 ], # 172.16.0.0
            [ 167772160,  4278190080 ], # 10.0.0.0
        )

        f = struct.unpack(
            '!I',
            socket.inet_pton(
                socket.AF_INET,
                self.address.host
            )
        )[0]

        for net in private:
            if (f & net[1]) == net[0]:
                return True

        return False

    def connectionMade(self):
        if not self.is_local:
            self.logger.info(
                f'-> <{self.address.host}:{self.address.port}>'
            )

    def connectionLost(self, reason: Failure = ...):
        if reason.type != ConnectionDone:
            self.logger.warning(
                f'<{self.address.host}> -> Lost connection: "{reason.getErrorMessage()}".'
            )
            return

        if not self.is_local:
            self.logger.info(
                f'<{self.address.host}> -> Connection done.'
            )

    def dataReceived(self, data: bytes):
        """For login data only. If client logged in, we will switch to packetDataReceived"""

        if self.busy:
            self.buffer += data
            return

        try:
            self.busy = True
            self.buffer += data

            if self.buffer.count(b'\r\n') < 3:
                return

            self.logger.debug(f'-> Received login: {self.buffer}')

            # Login received
            username, password, client, self.buffer = self.buffer.split(b'\r\n', 3)

            self.client = OsuClient.from_string(
                client.decode(),
                self.address.host
            )

            # We now expect bancho packets from the client
            self.dataReceived = self.packetDataReceived

            # Handle login
            self.login_received(
                username.decode(),
                password.decode(),
                self.client
            )
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f'Error on login: {e}')
            self.close_connection(e)

        finally:
            self.busy = False

    def packetDataReceived(self, data: bytes):
        """For bancho packets only and will be used after login"""

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
                    compression = stream.bool() # Gzip compression is only used in very old clients
                    payload = stream.read(stream.u32())
                except OverflowError:
                    # Wait for next buffer
                    break

                self.logger.debug(
                    f'-> {packet}: {payload}'
                )

                self.packet_received(
                    packet_id=packet,
                    stream=StreamIn(payload)
                )

                # Reset buffer
                self.buffer = stream.readall()
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f'Error while receiving packet: {e}')

            self.close_connection(e)

        finally:
            self.busy = False

    def enqueue(self, data: bytes):
        try:
            self.logger.debug(f'<- {data}')
            self.transport.write(data)
        except Exception as e:
            self.logger.error(
                f'Could not write to transport layer: {e}'
            )

    def close_connection(self, error: Optional[Exception] = None):
        if not self.is_local:
            if error:
                self.send_error()
                self.logger.warning(f'Closing connection -> <{self.address.host}>')
            else:
                self.logger.info(f'Closing connection -> <{self.address.host}>')

        self.transport.loseConnection()

    def send_packet(self, packet_type: Enum, encoders, *args):
        stream = StreamOut()
        encoder = encoders[packet_type]
        payload = encoder(*args)

        stream.header(packet_type, len(payload))
        stream.write(payload)

        self.enqueue(stream.get())

    def send_error(self, reason = -5, message = ""):
        ...

    def packet_received(self, packet_id: int, stream: StreamIn):
        ...

    def login_received(self, username: str, md5: str, client: OsuClient):
        ...
