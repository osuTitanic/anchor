
from twisted.internet.address import IPv4Address, IPv6Address
from twisted.internet.error import ConnectionDone
from twisted.words.protocols.irc import IRC
from twisted.python.failure import Failure
from twisted.internet import reactor
from app.clients.irc import IrcClient
from app.clients import Client
from typing import List, Any
from chio import Message

import logging
import config
import app

IPAddress = IPv4Address | IPv6Address

class TcpIrcProtocol(IrcClient, IRC):
    """TCP protocol for IRC connections, currently just a placeholder"""

    def __init__(self, address: IPAddress) -> None:
        super().__init__(address.host, address.port)
        self.logger = logging.getLogger(address.host)
        self.protocol = 'tcp'

    def connectionMade(self) -> None:
        self.logger.info(f'-> <{self.address}:{self.port}> (IRC)')

    def connectionLost(self, reason: Failure) -> None:
        self.logger.info(
            f'<{self.address}> -> Connection done.'
            if reason.type is ConnectionDone else
            f'<{self.address}> -> Lost connection: {reason.getErrorMessage()}'
        )

    def handleCommand(self, command: str, prefix: str, params: List[str]) -> None:
        try:
            self.on_command_received(command, prefix, params)
        except Exception as e:
            self.logger.error(f'Error while processing command: {e}', exc_info=e)
            self.close_connection('Request processing error')

    def close_connection(self, reason: Any = None) -> None:
        super().close_connection(reason)
        reactor.callFromThread(self.transport.loseConnection)

    def enqueue_line(self, line: str) -> None:
        self.logger.debug(f"-> {line}")
        self.sendLine(line)

    def enqueue_command(self, command: str, prefix: str = f"cho.{config.DOMAIN_NAME}", params: List[str] = [], tags: dict = {}) -> None:
        self.logger.debug(f"<- <{command}> {prefix} ({', '.join(params)}) {tags}")
        self.sendCommand(command, params, prefix, tags)

    def enqueue_message(self, message: str, sender: "Client", target: str) -> None:
        self.logger.debug(f"<- <{target}> '{message}' ({sender})")
        self.sendMessage("PRIVMSG", target, ":" + message, prefix=sender.irc_prefix)

    def enqueue_message_object(self, message: Message) -> None:
        self.logger.debug(f"<- <{message.target}> '{message.content}' ({message.sender})")
        self.sendMessage("PRIVMSG", message.target, ":" + message.content, prefix=message.sender)
