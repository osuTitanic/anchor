
from app.common.constants import (
    PresenceFilter,
    Permissions,
    LoginError,
    QuitState,
    GameMode
)

from app.common.objects import (
    bReplayFrameBundle,
    bUserPresence,
    bStatusUpdate,
    bScoreFrame,
    bUserStats,
    bUserQuit,
    bMessage,
    bChannel,
    bMatch
)

from app.common.constants import strings
from app.common.cache import leaderboards
from app.common.cache import status

from app.common.database.repositories import (
    histories,
    clients,
    logins,
    scores,
    users,
    stats
)

from app.protocol import BanchoProtocol, IPAddress
from app.common.streams import StreamIn

from app.common.database import DBUser, DBStats
from app.objects import OsuClient, Status

from typing import Optional, Callable, Tuple, List, Dict, Set
from datetime import datetime, timedelta
from enum import Enum
from copy import copy

from twisted.internet.error import ConnectionDone
from twisted.internet.address import IPv4Address
from twisted.python.failure import Failure

from app.clients.packets import PACKETS
from app.clients import (
    DefaultResponsePacket,
    DefaultRequestPacket
)

import traceback
import hashlib
import timeago
import logging
import config
import bcrypt
import utils
import time
import app

class Player(BanchoProtocol):
    def __init__(self, address: IPAddress) -> None:
        self.is_local = utils.is_local_ip(address.host)
        self.logger = logging.getLogger(address.host)
        self.address = address

        self.away_message: Optional[str] = None
        self.client: Optional[OsuClient] = None
        self.object: Optional[DBUser] = None
        self.stats:  Optional[List[DBStats]] = None
        self.status = Status()

        self.id = 0
        self.name = ""

        self.request_packets = DefaultRequestPacket
        self.packets = DefaultResponsePacket
        self.decoders: Dict[Enum, Callable] = PACKETS[20130815][0]
        self.encoders: Dict[Enum, Callable] = PACKETS[20130815][1]

        from .collections import Players
        from .multiplayer import Match
        from .channel import Channel

        self.channels: Set[Channel] = set()
        self.filter = PresenceFilter.All

        self.spectators = Players()
        self.spectating: Optional[Player] = None
        self.spectator_chat: Optional[Channel] = None

        self.in_lobby = False
        self.match: Optional[Match] = None
        self.last_response = time.time()

    def __repr__(self) -> str:
        return f'<Player ({self.id})>'

    def __eq__(self, other) -> bool:
        return self.id == other.id

    def __hash__(self) -> int:
        return self.id

    @classmethod
    def bot_player(cls):
        player = Player(
            IPv4Address(
                'TCP',
                '127.0.0.1',
                1337
            )
        )

        player.object = users.fetch_by_id(1)
        player.client = OsuClient.empty()

        player.id = -player.object.id # Negative user id -> IRC Player
        player.name = player.object.name
        player.stats  = player.object.stats

        player.client.ip.country_code = "OC"
        player.client.ip.city = "w00t p00t!"

        return player

    @property
    def is_bot(self) -> bool:
        return True if self.id == -1 else False

    @property
    def silenced(self) -> bool:
        if self.object.silence_end:
            if self.remaining_silence > 0:
                return True
            else:
                # User is not silenced anymore
                self.unsilence()
                return False
        return False

    @property
    def remaining_silence(self) -> int:
        if self.object.silence_end:
            return self.object.silence_end.timestamp() - datetime.now().timestamp()
        return 0

    @property
    def supporter(self) -> bool:
        if config.FREE_SUPPORTER:
            return True

        if self.object.supporter_end:
            if self.remaining_supporter > 0:
                return True

            # Remove supporter
            self.object.supporter_end = None
            self.object.permissions = self.permissions & ~Permissions.Supporter

            # Update database
            users.update(self.id, {
                'supporter_end': None,
                'permissions': self.permissions.value
            })

            # Update client
            # NOTE: Client will exit after it notices a permission change
            self.enqueue_permissions()

        return False

    @property
    def remaining_supporter(self) -> int:
        if self.object.supporter_end:
            return self.object.supporter_end.timestamp() - datetime.now().timestamp()
        return 0

    @property
    def restricted(self) -> bool:
        if not self.object:
            return False
        return self.object.restricted

    @property
    def current_stats(self) -> Optional[DBStats]:
        for stats in self.stats:
            if stats.mode == self.status.mode.value:
                return stats
        return None

    @property
    def permissions(self) -> Optional[Permissions]:
        if not self.object:
            return
        return Permissions(self.object.permissions)

    @property
    def friends(self) -> List[int]:
        return [rel.target_id for rel in self.object.relationships if rel.status == 0]

    @property
    def online_friends(self):
        return [app.session.players.by_id(id) for id in self.friends if id in app.session.players]

    @property
    def user_presence(self) -> Optional[bUserPresence]:
        try:
            return bUserPresence(
                self.id,
                False,
                self.name,
                self.client.utc_offset,
                self.client.ip.country_index,
                self.permissions,
                self.status.mode,
                self.client.ip.longitude,
                self.client.ip.latitude,
                self.current_stats.rank,
                self.client.ip.city \
                    if self.client.display_city
                    else None
            )
        except AttributeError:
            return None

    @property
    def user_stats(self) -> Optional[bUserStats]:
        try:
            return bUserStats(
                self.id,
                bStatusUpdate(
                    self.status.action,
                    self.status.text,
                    self.status.mods,
                    self.status.mode,
                    self.status.checksum,
                    self.status.beatmap
                ),
                self.current_stats.rscore,
                self.current_stats.tscore,
                self.current_stats.acc,
                self.current_stats.playcount,
                self.current_stats.rank,
                self.current_stats.pp,
            )
        except AttributeError:
            return None

    def connectionLost(self, reason: Failure = Failure(ConnectionDone())):
        app.session.players.remove(self)

        status.delete(self.id)

        for channel in copy(self.channels):
            channel.remove(self)

        app.session.players.send_user_quit(
            bUserQuit(
                self.id,
                QuitState.Gone # TODO: IRC
            )
        )

        app.session.channels.remove(self.spectator_chat)

        if self.match:
            app.clients.handler.leave_match(self)

        super().connectionLost(reason)

    def reload_object(self) -> DBUser:
        """Reload player stats from database"""
        self.object = users.fetch_by_id(self.id)
        self.stats = self.object.stats

        self.update_leaderboard_stats()
        self.update_status_cache()
        self.reload_rank()

        return self.object

    def reload_rank(self) -> None:
        """Reload player rank from cache and update it if needed"""
        cached_rank = leaderboards.global_rank(self.id, self.status.mode.value)

        if cached_rank != self.current_stats.rank:
            self.current_stats.rank = cached_rank

            # Update rank in database
            stats.update(
                self.id,
                self.status.mode.value,
                {
                    'rank': cached_rank
                }
            )

            # Update rank history
            histories.update_rank(self.current_stats, self.object.country)

    def update_leaderboard_stats(self) -> None:
        leaderboards.update(
            self.id,
            self.status.mode.value,
            self.current_stats.pp,
            self.current_stats.rscore,
            self.object.country,
        )

    def update_status_cache(self) -> None:
        status.update(
            self.id,
            self.status.bancho_status
        )

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
        if self.is_bot:
            return

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

        decoders, encoders, self.request_packets, self.packets = PACKETS[
            min(
                PACKETS.keys(),
                key=lambda x:abs(x-version)
            )
        ]

        return decoders, encoders

    def login_received(self, username: str, md5: str, client: OsuClient):
        self.logger.info(f'Login attempt as "{username}" with {client.version.string}.')
        self.logger.name = f'Player "{username}"'
        self.last_response = time.time()

        # Get decoders and encoders
        self.decoders, self.encoders = self.get_client(client.version.date)

        # Send protocol version
        self.send_packet(self.packets.PROTOCOL_VERSION, config.PROTOCOL_VERSION)

        # Check adapters md5
        adapters_hash = hashlib.md5(client.hash.adapters.encode()).hexdigest()

        # TODO: Client hash verification

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

        self.id = user.id
        self.name = user.name
        self.stats = user.stats
        self.object = user

        if self.client.version.stream != 'tourney':
            if (other_user := app.session.players.by_id(user.id)):
                other_user.enqueue_announcement(strings.LOGGED_IN_FROM_ANOTHER_LOCATION)
                other_user.login_failed(LoginError.ServerError)
        else:
            if not self.supporter:
                # Trying to use tourney client without supporter
                self.login_failed(LoginError.Authentication)
                return

        self.status.mode = GameMode(self.object.preferred_mode)

        if not self.stats:
            self.stats = [stats.create(self.id, mode) for mode in range(4)]
            self.reload_object()
            self.enqueue_silence_info(-1)

        # Create login attempt in db
        logins.create(
            self.id,
            self.address.host,
            self.client.version.string
        )

        # Check for new hardware
        self.check_client()

        self.update_leaderboard_stats()
        self.update_status_cache()
        self.login_success()

    def login_success(self):
        from .channel import Channel

        self.spectator_chat = Channel(
            name=f'#spec_{self.id}',
            topic=f"{self.name}'s spectator channel",
            owner=self.name,
            read_perms=1,
            write_perms=1,
            public=False
        )
        app.session.channels.append(self.spectator_chat)

        # Update latest activity
        self.update_activity()

        # Protocol Version
        self.send_packet(self.packets.PROTOCOL_VERSION, 18)

        # User ID
        self.send_packet(self.packets.LOGIN_REPLY, self.id)

        # Menu Icon
        self.send_packet(
            self.packets.MENU_ICON,
            config.MENUICON_IMAGE,
            config.MENUICON_URL
        )

        # Permissions
        self.enqueue_permissions()

        # Presence
        self.enqueue_presence(self)
        self.enqueue_stats(self)

        # Bot presence
        self.enqueue_presence(app.session.bot_player)

        # Friends
        self.enqueue_friends()

        # Append to player collection
        app.session.players.append(self)

        # Enqueue other players
        self.enqueue_players(app.session.players)

        for channel in app.session.channels.public:
            if channel.can_read(self.permissions):
                if channel.name in config.AUTOJOIN_CHANNELS:
                    self.enqueue_channel(channel, autojoin=True)
                    channel.add(self)
                    continue

                self.enqueue_channel(channel)

        self.send_packet(self.packets.CHANNEL_INFO_COMPLETE)

        if self.silenced:
            self.enqueue_silence_info(
                self.remaining_silence
            )

    def check_client(self):
        client = clients.fetch_without_executable(
            self.id,
            self.client.hash.adapters_md5,
            self.client.hash.uninstall_id,
            self.client.hash.diskdrive_signature
        )

        if not client:
            # New hardware detected
            # TODO: Send email to user
            self.logger.warning(
                f'New hardware detected: {self.client.hash.string}'
            )

            clients.create(
                self.id,
                self.client.hash.md5,
                self.client.hash.adapters_md5,
                self.client.hash.uninstall_id,
                self.client.hash.diskdrive_signature
            )

        # TODO: Check banned hardware

    def packet_received(self, packet_id: int, stream: StreamIn):
        self.last_response = time.time()

        if self.is_bot:
            return

        try:
            packet = self.request_packets(packet_id)

            decoder = self.decoders[packet]
            args = decoder(stream)

            self.logger.debug(
                f'-> "{packet.name}": {args}'
            )
        except KeyError as e:
            self.logger.error(
                f'Could not find decoder for "{packet.name}": {e}'
            )
            return
        except ValueError as e:
            self.logger.error(
                f'Could not find packet with id "{packet_id}": {e}'
            )
            return

        try:
            handler_function = app.session.handlers[packet]
            handler_function(
               *[self, args] if args != None else
                [self]
            )
        except Exception as e:
            if config.DEBUG: traceback.print_exc()
            self.logger.error(f'Failed to execute handler for packet "{packet.name}": {e}')

    def silence(self, duration_sec: int, reason: str):
        duration = timedelta(seconds=duration_sec)

        if not self.object.silence_end:
            self.object.silence_end = datetime.now() + duration
        else:
            # Append duration, if user has been silenced already
            self.object.silence_end += duration

        # Update database
        users.update(self.id, {'silence_end': self.object.silence_end})

        # Enqueue to client
        self.enqueue_silence_info(duration_sec)

        self.logger.info(
            f'{self.name} was silenced for {timeago.format(datetime.now() + duration)}. Reason: "{reason}"'
        )

    def unsilence(self):
        self.object.silence_end = None
        self.enqueue_silence_info(0)

        # Update database
        users.update(self.id, {'silence_end': None})

    def restrict(self, reason: Optional[str] = None, autoban: bool = False):
        self.object.restricted = True
        self.object.permissions = 0

        # Update database
        users.update(self.id, {
            'restricted': True,
            'permissions': 0
        })

        # Update leaderboards
        leaderboards.remove(
            self.id,
            self.object.country
        )

        # Remove stats
        stats.delete_all(self.id)

        # Hide scores
        scores.hide_all(self.id)

        if reason:
            self.enqueue_announcement(
                f'You have been restricted for:\n{reason}'
            )

        # Update client
        self.login_failed(LoginError.Banned)

        # Update hardware
        clients.update_all(self.id, {'banned': True})

        self.logger.warning(
            f'{self.name} got {"auto-" if autoban else ""}restricted. Reason: {reason}'
        )

    # TODO: Unrestrict

    def update_activity(self):
        users.update(
            user_id=self.id,
            updates={
                'latest_activity': datetime.now()
            }
        )

    def enqueue_ping(self):
        self.send_packet(self.packets.PING)

    def enqueue_player(self, player):
        if self.client.version.date <= 1710:
            self.enqueue_presence(player)
            return

        if self.client.version.date <= 20121223:
            # USER_PRESENCE_SINGLE is not supported anymore
            self.enqueue_presence(player)
            return

        self.send_packet(
            self.packets.USER_PRESENCE_SINGLE,
            player.id
        )

    def enqueue_players(self, players, stats_only: bool = False):
        if self.client.version.date <= 1710:
            if stats_only:
                for player in players:
                    self.enqueue_stats(player)
            else:
                for player in players:
                    self.enqueue_presence(player)
            return

        if self.client.version.date <= 20121223:
            # USER_PRESENCE_BUNDLE is not supported anymore
            for player in players:
                self.enqueue_presence(player)
            return

        n = max(1, 150)

        # Split players into chunks to avoid any buffer overflows
        for chunk in (players[i:i+n] for i in range(0, len(players), n)):
            self.send_packet(
                self.packets.USER_PRESENCE_BUNDLE,
                [player.id for player in chunk]
            )

    def enqueue_presence(self, player):
        if self.client.version.date <= 1710:
            self.send_packet(
                self.packets.USER_STATS,
                player.user_stats,
                player.user_presence
            )
            return

        self.send_packet(
            self.packets.USER_PRESENCE,
            player.user_presence
        )

    def enqueue_stats(self, player):
        self.send_packet(
            self.packets.USER_STATS,
            player.user_stats
        )

    def enqueue_quit(self, user_quit: bUserQuit):
        self.send_packet(
            self.packets.USER_QUIT,
            user_quit
        )

    def enqueue_message(self, message: bMessage):
        self.send_packet(
            self.packets.SEND_MESSAGE,
            message
        )

    def enqueue_permissions(self):
        self.send_packet(
            self.packets.LOGIN_PERMISSIONS,
            self.permissions
        )

    def enqueue_channel(self, channel: bChannel, autojoin: bool = False):
        self.send_packet(
            self.packets.CHANNEL_AVAILABLE if not autojoin else \
            self.packets.CHANNEL_AVAILABLE_AUTOJOIN,
            channel
        )

    def join_success(self, name: str):
        self.send_packet(
            self.packets.CHANNEL_JOIN_SUCCESS,
            name
        )

    def revoke_channel(self, name: str):
        self.send_packet(
            self.packets.CHANNEL_REVOKED,
            name
        )

    def enqueue_blocked_dms(self, username: str):
        self.send_packet(
            self.packets.USER_DM_BLOCKED,
            bMessage(
                '',
                '',
                username,
                -1
            )
        )

    def enqueue_silenced_target(self, username: str):
        self.send_packet(
            self.packets.TARGET_IS_SILENCED,
            bMessage(
                '',
                '',
                username,
                -1
            )
        )

    def enqueue_silenced_user(self, user_id: int):
        self.send_packet(
            self.packets.USER_SILENCED,
            user_id
        )

    def enqueue_silence_info(self, remaining_time: int):
        self.send_packet(
            self.packets.SILENCE_INFO,
            remaining_time
        )

    def enqueue_friends(self):
        self.send_packet(
            self.packets.FRIENDS_LIST,
            self.friends
        )

    def enqueue_spectator(self, player_id: int):
        self.send_packet(
            self.packets.SPECTATOR_JOINED,
            player_id
        )

    def enqueue_spectator_left(self, player_id: int):
        self.send_packet(
            self.packets.SPECTATOR_LEFT,
            player_id
        )

    def enqueue_fellow_spectator(self, player_id: int):
        self.send_packet(
            self.packets.FELLOW_SPECTATOR_JOINED,
            player_id
        )

    def enqueue_fellow_spectator_left(self, player_id: int):
        self.send_packet(
            self.packets.FELLOW_SPECTATOR_LEFT,
            player_id
        )

    def enqueue_cant_spectate(self, player_id: int):
        self.send_packet(
            self.packets.CANT_SPECTATE,
            player_id
        )

    def enqueue_frames(self, bundle: bReplayFrameBundle):
        self.send_packet(
            self.packets.SPECTATE_FRAMES,
            bundle
        )

    def enqueue_lobby_join(self, player_id: int):
        self.send_packet(
            self.packets.LOBBY_JOIN,
            player_id
        )

    def enqueue_lobby_part(self, player_id: int):
        self.send_packet(
            self.packets.LOBBY_PART,
            player_id
        )

    def enqueue_matchjoin_success(self, match: bMatch):
        self.send_packet(
            self.packets.MATCH_JOIN_SUCCESS,
            match
        )

    def enqueue_matchjoin_fail(self):
        self.send_packet(self.packets.MATCH_JOIN_FAIL)

    def enqueue_match_disband(self, match_id: int):
        self.send_packet(
            self.packets.DISBAND_MATCH,
            match_id
        )

    def enqueue_match(
        self,
        match: bMatch,
        update: bool = False,
        send_password: bool = False
    ):
        if not send_password and match.password:
            match.password = ' '

        self.send_packet(
            self.packets.UPDATE_MATCH if update else \
            self.packets.NEW_MATCH,
            match
        )

    def enqueue_match_start(self, match: bMatch):
        self.send_packet(
            self.packets.MATCH_START,
            match
        )

    def enqueue_score_update(self, frame: bScoreFrame):
        self.send_packet(
            self.packets.MATCH_SCORE_UPDATE,
            frame
        )

    def enqueue_player_skipped(self, slot_id: int):
        self.send_packet(
            self.packets.MATCH_PLAYER_SKIPPED,
            slot_id
        )

    def enqueue_player_failed(self, slot_id: int):
        self.send_packet(
            self.packets.MATCH_PLAYER_FAILED,
            slot_id
        )

    def enqueue_match_all_players_loaded(self):
        self.send_packet(self.packets.MATCH_ALL_PLAYERS_LOADED)

    def enqueue_match_transferhost(self):
        self.send_packet(self.packets.MATCH_TRANSFER_HOST)

    def enqueue_match_skip(self):
        self.send_packet(self.packets.MATCH_SKIP)

    def enqueue_match_complete(self):
        self.send_packet(self.packets.MATCH_COMPLETE)

    def enqueue_invite(self, message: bMessage):
        if self.client.version.date <= 1710:
            # Invite packet not supported
            self.enqueue_message(message)
            return

        self.send_packet(
            self.packets.INVITE,
            message
        )

    def enqueue_announcement(self, message: str):
        self.send_packet(
            self.packets.ANNOUNCE,
            message
        )

    def enqueue_monitor(self):
        self.send_packet(self.packets.MONITOR)
