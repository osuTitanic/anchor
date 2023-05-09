
from twisted.internet.error   import ConnectionDone
from twisted.internet.address import IPv4Address
from twisted.python.failure   import Failure

from dataclasses import dataclass, field
from typing      import List, Optional
from datetime    import datetime

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
    PresenceFilter,
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
    20130303: b20130606,
    -1: b20130606        # Default version
}

@dataclass
class Status:
    action: ClientStatus = ClientStatus.Idle
    text: str = ""
    checksum: str = ""
    mods: List[Mod] = field(default_factory=list) # = []
    mode: Mode = Mode.Osu
    beatmap: int = -1

    def __repr__(self) -> str:
        return f'<Status ({self.action})>'

class Player(BanchoProtocol):
    def __init__(self, address: IPAddress) -> None:
        self.version = -1

        self.client: Optional[OsuClient] = None
        self.object: Optional[DBUser]    = None
        self.stats:  Optional[DBStats]   = None
        self.status = Status()

        self.id   = -1
        self.name = ""
        self.pw   = ""

        self.away_message: Optional[str] = None
        self.handler: Optional[BaseHandler] = None
        self.channels = []

        self.address = address
        self.logger  = logging.getLogger(self.address.host)

        self.last_response = datetime.now()
        self.filter = PresenceFilter.All

        from .collections import Players

        self.spectating: Optional[Player] = None
        self.spectators: Players = Players()

        self.in_lobby = False
        self.match    = None

        self.spectator_channel = None

    def __repr__(self) -> str:
        return f'<Player ({self.id})>'
    
    @classmethod
    def bot_player(cls):
        player = Player(
            IPv4Address('TCP', '127.0.0.1', 1337)
        )

        player.object = bancho.services.database.user_by_id(1)
        player.handler = BaseHandler(player)
        player.client = OsuClient.empty()

        player.id     = player.object.id
        player.name   = player.object.name
        player.stats  = player.object.stats

        return player
    
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
        if not self.object:
            return False

        return self.object.restricted
    
    @property
    def friends(self) -> List[int]:
        return [rel.target_id for rel in self.object.relationships if rel.status == 0]
    
    @property
    def current_stats(self) -> DBStats:
        return self.stats[self.status.mode.value]
    
    @property
    def is_bot(self) -> bool:
        # TODO: Maybe there is a better way of doing this
        return type(self.handler) == BaseHandler
    
    def reload_object(self) -> DBUser:
        self.object = bancho.services.database.user_by_id(self.id)
        return self.object

    def connectionLost(self, reason: Failure = Failure(ConnectionDone())):
        bancho.services.players.remove(self)
        bancho.services.players.exit(self)

        for channel in self.channels:
            channel.remove(self)

        bancho.services.channels.remove(self.spectator_channel)

        super().connectionLost(reason)

    def closeConnection(self, error: Optional[Exception] = None):
        self.connectionLost()
        super().closeConnection(error)
    
    def packetReceived(self, packet_id: int, stream: StreamIn):
        return self.handler.handle(packet_id, stream)

    def loginReceived(self, username: str, md5: str, client: OsuClient):
        self.client = client

        # Set client version
        if self.client.version.date in Handlers:
            self.version = self.client.version.date

        self.handler = Handlers[self.version](self)

        self.sendPacket(
            ResponsePacket.PROTOCOL_VERSION,
            int(21).to_bytes(4, 'little')
        )

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
        # TODO: Tourney clients
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
        from .channel import Channel

        self.spectator_channel = Channel(
            f'#spec_{self.id}',
            f"{self.name}'s spectator channel",
            1, 1,
            public=False
        )
        bancho.services.channels.append(self.spectator_channel)

        # Send user id
        self.handler.enqueue_login_reply(self.id)

        # Privileges
        self.handler.enqueue_privileges()

        # Enqueue presence and stats        
        self.handler.enqueue_presence(self)
        self.handler.enqueue_stats(self)

        bancho.services.players.append(self)

        # Friends
        self.handler.enqueue_friends()

        # All players that are online right now
        self.handler.enqueue_players(bancho.services.players)

        # Enqueue presence of bot
        self.handler.enqueue_presence(bancho.services.bot_player)
        self.handler.enqueue_stats(bancho.services.bot_player)

        # TODO: Remaining silence

        for channel in bancho.services.channels:
            if (
                channel.can_read(Permissions.pack(self.permissions)) and
                channel.public
               ):
                self.handler.enqueue_channel(channel)

        self.handler.enqueue_channel_info_end()

    def update(self):
        self.reload_object()
        bancho.services.players.enqueue_stats(self)
