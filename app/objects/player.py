
from app.protocol import BanchoProtocol, IPAddress
from app.common.database import DBUser, DBStats
from app.common.constants import PresenceFilter
from app.clients import BaseReader, BaseWriter
from app.objects import OsuClient, Status

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
