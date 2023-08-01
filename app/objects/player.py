
from app.common.constants import (
    PresenceFilter,
    LoginError,
    GameMode
)

from app.common.database.repositories import users

from app.protocol import BanchoProtocol, IPAddress
from app.common.streams import StreamIn

from app.common.database import DBUser, DBStats
from app.objects import OsuClient, Status

from typing import Optional, Callable, Tuple, List, Dict
from enum import Enum

from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure

from app.clients.packets import PACKETS
from app.clients import (
    DefaultResponsePacket,
    DefaultRequestPacket
)

import hashlib
import logging
import bcrypt
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

        self.request_packets = DefaultRequestPacket
        self.packets = DefaultResponsePacket
        self.decoders: Dict[Enum, Callable] = {}
        self.encoders: Dict[Enum, Callable] = {}

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
        if self.encoders and message:
            self.send_packet(
                self.packets.ANNOUNCE,
                message
            )

        self.send_packet(
            self.packets.LOGIN_REPLY,
            reason
        )

    def send_packet(self, packet_type: Enum, *args):
        return super().send_packet(
            packet_type,
            self.encoders,
            *args
        )

    def login_failed(self, reason = LoginError.ServerError, message = ""):
        self.send_error(reason.value, message)
        self.close_connection()

    def get_client(self, version: int) -> Tuple[Dict[Enum, Callable], Dict[Enum, Callable]]:
        """Figure out packet sender/decoder, closest to version of client"""

        decoders, encoders = PACKETS[
            min(
                PACKETS.keys(),
                key=lambda x:abs(x-version)
            )
        ]

        return decoders, encoders

    def login_received(self, username: str, md5: str, client: OsuClient):
        self.logger.info(f'Login attempt as "{username}" with {client.version.string}.')
        self.logger.name = f'Player "{username}"'

        # TODO: Set packet enums

        # Get decoders and encoders
        self.decoders, self.encoders = self.get_client(client.version.date)

        # Send protocol version
        self.send_packet(self.packets.PROTOCOL_VERSION, 18) # TODO: Define constant

        # Check adapters md5
        adapters_hash = hashlib.md5(client.hash.adapters.encode()).hexdigest()

        if adapters_hash != client.hash.adapters_md5:
            self.transport.write('no.\r\n')
            self.close_connection()
            return

        if not (user := users.fetch_by_name(username)):
            self.logger.warning('Login Failed: User not found')
            self.login_failed(LoginError.Authentication)
            return

        if not bcrypt.checkpw(md5.encode(), user.bcrypt.encode()):
            self.logger.warning('Login Failed: Authentication error')
            self.login_failed(LoginError.Authentication)
            return

        if user.restricted:
            # TODO: Check ban time
            self.logger.warning('Login Failed: Restricted')
            self.login_failed(LoginError.Banned)
            return

        if not user.activated:
            self.logger.warning('Login Failed: Not activated')
            self.login_failed(LoginError.NotActivated)
            return

        if app.session.players.by_id(user.id):
            # TODO: Check connection of other user
            self.logger.warning('Login failed: Already Online')
            self.close_connection()
            return

        # TODO: Tournament clients

        self.id = user.id
        self.name = user.name
        self.stats = user.stats
        self.object = user

        self.status.mode = GameMode(self.object.preferred_mode)

        if not self.stats:
            # TODO: Create stats
                # Reload object
                # Reset ban info
            pass

        # TODO: Update leaderboards

        self.login_success()

    def login_success(self):
        # TODO: Create spectator channel

        self.send_packet(self.packets.LOGIN_REPLY, self.id)

    def packet_received(self, packet_id: int, stream: StreamIn):
        try:
            packet = self.request_packets(packet_id)
            decoder = self.decoders[packet]
            decoder(stream, self)
        except KeyError as e:
            self.logger.error(
                f'Could not find decoder for "{packet.name}": {e}'
            )
        except ValueError as e:
            self.logger.error(
                f'Could not find packet with id "{packet_id}": {e}'
            )
