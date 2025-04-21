
from app.common.constants import ANCHOR_ASCII_ART
from twisted.internet.address import IPv4Address, IPv6Address
from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure
from twisted.internet import reactor

import logging
import config
import app

IPAddress = IPv4Address | IPv6Address

class TcpIrcProtocol(LineOnlyReceiver):
    """TCP protocol for IRC connections, currently just a placeholder"""

    def __init__(self, address: IPAddress) -> None:
        self.logger = logging.getLogger(address.host)
        self.address = address.host
        self.port = address.port
        self.protocol = 'tcp'

    def connectionMade(self) -> None:
        self.logger.info(
            f'-> <{self.address}:{self.port}> (IRC)'
        )
        self.enqueue_error(
            "IRC connections are not supported yet. "
            "Please check back later!"
        )
        self.enqueue_error_message(
            "IRC connections are not supported yet. "
            "Please check back later!"
        )
        reactor.callLater(5, self.close_connection)

    def connectionLost(self, reason: Failure) -> None:
        self.logger.info(
            f'<{self.address}> -> Connection done.'
            if reason.type is ConnectionDone else
            f'<{self.address}> -> Lost connection: {reason.getErrorMessage()}'
        )

    def lineReceived(self, line: str) -> None:
        self.logger.debug(f"-> {line}")

    def close_connection(self, reason: str = "") -> None:
        reactor.callFromThread(self.transport.loseConnection)

    def enqueue_message(self, message: str) -> None:
        self.transport.write(f"{message}\r\n".encode('utf-8'))
        self.logger.debug(f"<- {message}")

    def enqueue_error_message(self, error: str) -> None:
        bot_prefix = f'{app.session.banchobot.name}!bot@{config.DOMAIN_NAME}'
        self.enqueue_message(f":{bot_prefix} PRIVMSG #osu :{error}")

    def enqueue_error(self, error: str) -> None:
        self.enqueue_message(f"ERROR :{error}")
