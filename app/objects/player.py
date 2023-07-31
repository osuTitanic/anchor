
from app.protocol import BanchoProtocol, IPAddress
from app.common.database.repositories import users
from app.common.database import DBUser, DBStats
from app.common.constants import PresenceFilter
from app.clients import BaseReader, BaseWriter
from app.objects import OsuClient, Status

from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure

from typing import Optional, List

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

        self.reader: Optional[BaseReader] = None
        self.writer: Optional[BaseWriter] = None

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

    def closeConnection(self, error: Optional[Exception] = None):
        self.connectionLost()
        super().closeConnection(error)

    def loginReceived(self, username: str, md5: str, client: OsuClient):
        self.logger.info(f'Login attempt as "{username}" with {client.version.string}.')

        # TODO: Select packet decoder & writer
