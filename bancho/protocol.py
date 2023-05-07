
from twisted.internet.address import IPv4Address, IPv6Address
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Protocol
from twisted.python.failure import Failure

from typing import Optional, Union

from .constants import (
    ResponsePacket,
    WEB_RESPONSE
)

from .streams import StreamIn, StreamOut
from .objects.client import OsuClient

import traceback
import bancho

IPAddress = Union[IPv4Address, IPv6Address]

class BanchoProtocol(Protocol):

    """
    This class will receive and parse packets/logins.
    If a client has logged in, a handler will get chosen depending on their version.
    """

    buffer  = b""
    busy    = False
    proxied = False # TODO
    handler = None

    def __init__(self, address: IPAddress) -> None:
        self.address = address

    def connectionMade(self):
        bancho.services.logger.debug(
            f'-> <{self.address.host}:{self.address.port}>'
        )

    def connectionLost(self, reason: Failure = ...):
        if reason.type != ConnectionDone:
            bancho.services.logger.warning(
                f'<{self.address.host}> -> Lost connection: "{reason.getErrorMessage()}".'
            )
            return
        
        bancho.services.logger.info(
            f'<{self.address.host}> -> Connection done.'
        )

    def dataReceived(self, data: bytes):
        # For login data only
        # If client logged in, we will switch to _dataReceived

        if self.busy:
            self.buffer += data
            return
        
        try:
            self.busy = True
            self.buffer += data

            if self.buffer.startswith(b'GET /'):
                print(self.buffer)
                self.handleWeb()
                return

            if self.buffer.count(b'\r\n') >= 3:
                # Login received:
                # <username>\r\n<md5_password>\r\n<client_data>\r\n

                username, password, client, self.buffer = self.buffer.split(b'\r\n', 3)

                client = OsuClient.from_string(
                    client.decode(),
                    self.address.host
                )

                bancho.services.logger.info(f'<{self.address.host}> -> Login attempt as "{username.decode()}" with {client.version.string}.')

                self.loginReceived(
                    username.decode(), 
                    password.decode(), 
                    client
                )

                # We now expect packets from the client
                self.dataReceived = self.packetDataReceived

        except Exception as e:
            traceback.print_exc()
            bancho.services.logger.error(f'Error on login: {e}')

            self.closeConnection(e)

        finally:
            self.busy = False

    def packetDataReceived(self, data: bytes):
        # For bancho packets only
        # Will be used after login
        
        if self.busy:
            self.buffer += data
            return
        
        try:
            self.busy = True
            self.buffer += data

            while self.buffer:
                stream = StreamIn(self.buffer)

                packet = stream.u16()
                compression = stream.bool() # unused?
                payload = StreamIn(
                    stream.read(
                        stream.u32()
                    )
                )

                bancho.services.logger.debug(
                    '\n'.join([
                        f'<{self.address.host}> -> "{packet}"',
                        f'"""\n{payload.get()}\n"""'
                    ])
                )

                self.packetReceived(
                    packet,
                    payload
                )

                self.buffer = stream.readall()
        
        except Exception as e:
            traceback.print_exc()
            bancho.services.logger.error(f'Error while receiving packet: {e}')

            self.closeConnection(e)

        finally:
            self.busy = False

    def closeConnection(self, error: Optional[Exception] = None):
        if error:
            self.sendError()
            bancho.services.logger.warning(f'Closing connection -> <{self.address.host}>')
        else:
            bancho.services.logger.info(f'Closing connection -> <{self.address.host}>')

        self.transport.loseConnection()
    
    def enqueue(self, data: bytes):
        try:
            self.transport.write(data)
        except AttributeError as e:
            bancho.services.logger.error(
                f'Could not write to transport layer: {e}'
            )

    def sendError(self, reason = -5, message = ""):
        if message:
            stream = StreamOut()
            stream.string(message)

            # Send announcement if message is not empty
            self.sendPacket(
                ResponsePacket.ANNOUNCE,
                stream.get()
            )

        # Send login reply with error code
        self.sendPacket(
            ResponsePacket.LOGIN_REPLY,
            int(reason).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def sendPacket(self, packet_type: ResponsePacket, payload: bytes = b""):
        stream = StreamOut()
        stream.header(packet_type, len(payload))
        stream.write(payload)

        bancho.services.logger.debug(
            '\n'.join([
                f'<{self.address.host}> Sending packet -> {packet_type.name}',
                f'"""\n{payload}\n"""'
            ])
        )

        self.enqueue(stream.get())

    def handleWeb(self):
        # This will send a http response and close the connection after that
        self.transport.write(
            '\n'.join([
                'HTTP/2 200 OK',
                'Server: anchor',
                'Content-Type: text/html'
                '',
                WEB_RESPONSE
            ]).encode()
        )

        bancho.services.logger.info(f'<{self.address.host}> -> Got web request.')

        self.closeConnection()

    def packetReceived(self, packet_id: int, stream: StreamIn):
        ...

    def loginReceived(self, username: str, md5: str, client: str):
        ...

