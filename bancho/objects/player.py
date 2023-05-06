
from dataclasses import dataclass, field
from typing      import List, Optional

from ..streams import StreamIn

from ..protocol import BanchoProtocol, IPAddress

from ..handlers.b20130606 import b20130606
from ..handlers import BaseHandler

from .client import OsuClient

from ..common.objects import (
    DBStats,
    DBUser
)

from ..constants import (
    ResponsePacket,
    RequestPacket,
    ClientStatus,
    Permissions,
    Mode,
    Mod
)

import logging
import bancho
import bcrypt

Handlers = {
    20130606: b20130606, # Latest supported version
    -1: b20130606        # Default version
}

@dataclass
class Status:
    action: ClientStatus = ClientStatus.Idle
    text: str = ""
    checksum: str = ""
    mods: List[Mod] = field(default_factory=list) # = []
    mode: Mode = Mode.Osu

    def __repr__(self) -> str:
        return f'<Status ({self.action})>'

class Player(BanchoProtocol):
    version = -1

    client: Optional[OsuClient] = None
    object: Optional[DBUser]    = None
    stats:  Optional[DBStats]   = None
    status = Status()

    id   = -1
    name = ""
    pw   = ""

    away_message: Optional[str] = None

    handler: Optional[BaseHandler] = None

    def __init__(self, address: IPAddress) -> None:
        self.address = address
        self.logger  = logging.getLogger(self.address.host)

        from .collections import Players

        self.spectating: Optional[Player] = None
        self.spectators: Players = Players()

        self.in_lobby = False
        self.match    = None

    def __repr__(self) -> str:
        return f'<Player ({self.id})>'
    
    @property
    def silenced(self) -> bool:
        return False # TODO

    @property
    def permissions(self) -> Optional[List[Permissions]]:
        if not self.object:
            return
        
        return Permissions.list(self.object.permissions)
    
    @property
    def restricted(self) -> bool:
        return self.object.restricted
    
    def enqueue(self, data: bytes):
        self.logger.debug(f'{data} -> {self}')
        self.transport.write(data)
    
    def packetReceived(self, packet_id: int, stream: StreamIn):
        return self.handler.handle(packet_id, stream)

    def loginReceived(self, username: str, md5: str, client: OsuClient):
        self.client = client

        # Set client version
        if self.client.version.date in Handlers:
            self.version = self.client.version.date

        self.handler = Handlers[self.version](self)

        if not (user := bancho.services.database.user_by_name(username)):
            self.loginFailed(-1) # User does not exist
            return

        if not bcrypt.checkpw(md5.encode(), user.bcrypt.encode()):
            self.loginFailed(-1) # Password check failed
            return

        if self.client.version.date != self.version:
            self.loginFailed(-2) # Update needed
            return

        if user.restricted:
            self.loginFailed(-3) # User is banned
            return

        if not user.activated:
            self.loginFailed(-4) # User is not yet activated
            return
        
        # TODO: Check if user is online already
        # TODO: Test builds

        self.object = user
        self.id     = user.id
        self.name   = user.name
        self.stats  = user.stats
        self.pw     = user.bcrypt

        self.loginSuccess()
        
    def loginFailed(self, reason: int = -5, message = ""):
        self.sendError(reason, message)
        self.closeConnection()

    def loginSuccess(self):
        self.handler.login_reply(self.id)

    def announce(self, message: str):
        self.handler.announce(message)
