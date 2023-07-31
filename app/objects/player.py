
from app.common.constants import PresenceFilter, LoginError
from app.protocol import BanchoProtocol, IPAddress
from app.common.database.repositories import users
from app.common.database import DBUser, DBStats
from app.objects import OsuClient, Status
from app.clients import BaseSender

from typing import Optional, Callable, Tuple, List, Dict
from enum import Enum

from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure

from app.clients.packets import PACKETS
from app.clients import DefaultPackets

import logging
import app

class Player(BanchoProtocol):
    def __init__(self, address: IPAddress) -> None:
        self.logger = logging.getLogger(address.host)
        self.address = address

        self.away_message: Optional[str] = None
        self.client: Optional[OsuClient] = None
        self.object: Optional[DBUser] = None
        self.stats:  Optional[List[DBStats]] = None
        self.status = Status()

        self.id = -1
        self.name = ""

        self.packets: Dict[Enum, Callable] = {}
        self.sender: Optional[BaseSender] = None

        self.channels = set() # TODO: Add type
        self.filter = PresenceFilter.All

        # TODO: Add spectator channel
        # TODO: Add spectator collection

        self.spectating: Optional[Player] = None

        # TODO: Add current match
        self.in_lobby = False

    def __repr__(self) -> str:
        return f'<Player ({self.id})>'

    def connectionLost(self, reason: Failure = Failure(ConnectionDone())):
        # TODO: Remove from player collection
        # TODO: Notify other clients
        # TODO: Remove from channels
        # TODO: Remove spectator channel from collection
        # TODO: Remove from match
        super().connectionLost(reason)

    def reload_object(self) -> DBUser:
        """Reload player stats from database"""
        self.object = users.fetch_by_id(self.id)
        self.stats = self.object.stats

        # TODO: Update leaderboard cache

        return self.object

    def close_connection(self, error: Optional[Exception] = None):
        self.connectionLost()
        super().close_connection(error)

    def send_error(self, reason=-5, message=""):
        if self.sender and message:
            self.sender.send_announcement(message)

        self.send_packet(
            DefaultPackets.LOGIN_REPLY,
            int(reason).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def login_failed(self, reason = LoginError.ServerError, message = ""):
        self.send_error(reason.value, message)
        self.close_connection()

    def get_client(self, version: int) -> Tuple[Dict[Enum, Callable], BaseSender]:
        """Figure out packet sender/decoder, closest to version of client"""

        packets, sender = PACKETS[
            min(PACKETS.keys(), key=lambda x:abs(x-version))
        ]

        return packets, sender(self)

    def login_received(self, username: str, md5: str, client: OsuClient):
        self.logger.info(f'Login attempt as "{username}" with {client.version.string}.')
        self.logger.name = f'Player "{username}"'

        self.packets, self.sender = self.get_client(client.version.date)

        self.login_failed(LoginError.ServerError, "Testmessage")
        self.close_connection()
