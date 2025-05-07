
from twisted.internet.address import IPv4Address, IPv6Address
from twisted.internet.error import ConnectionDone
from twisted.internet import reactor, threads
from twisted.words.protocols.irc import IRC
from twisted.python.failure import Failure
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
        self.connected = True

        if not config.IRC_ENABLED:
            self.enqueue_error("IRC connections have been disabled. Please check back later!")
            self.close_connection('IRC is disabled')

        # Ensure client is logged in after 8 seconds, else close connection
        reactor.callLater(8, self.handle_timeout_callback)

    def connectionLost(self, reason: Failure) -> None:
        self.logger.info(
            f'<{self.address}> -> Connection done.'
            if reason.type is ConnectionDone else
            f'<{self.address}> -> Lost connection: {reason.getErrorMessage()}'
        )
        self.close_connection()

    def dataReceived(self, data: Any) -> None:
        try:
            return super().dataReceived(data)
        except UnicodeDecodeError:
            self.logger.warning(f"Failed to decode irc request ({len(data)} bytes)")
            self.close_connection("Invalid data received")

    def handleCommand(self, command: str, prefix: str, params: List[str]) -> None:
        deferred = threads.deferToThread(
            self.on_command_received,
            command, prefix, params
        )

        deferred.addErrback(
            lambda f: (
                self.logger.error(f"Error processing command '{command}': {f.getErrorMessage()}", exc_info=f.value),
                self.close_connection('Request processing error')
            )
        )

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
