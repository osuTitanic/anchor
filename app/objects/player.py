
from __future__ import annotations

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

from app.common.constants import strings, level
from app.common.cache import leaderboards
from app.common.cache import usercount
from app.common.cache import status
from app.common import officer

from app.common.database.repositories import (
    infringements,
    histories,
    clients,
    groups,
    logins,
    scores,
    users,
    stats
)

from app.common.helpers import analytics
from app.common.helpers import clients as client_utils
from app.common.streams import StreamIn, StreamOut
from app.common.database import DBUser, DBStats
from app.objects import OsuClient, Status
from app.common import mail

from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure

from dataclasses import asdict, is_dataclass
from typing import Callable, List, Dict, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from enum import Enum
from copy import copy

from app.clients import versions
from app.clients import (
    DefaultResponsePacket,
    DefaultRequestPacket
)

import itertools
import hashlib
import timeago
import logging
import config
import bcrypt
import time
import gzip
import app

class Player:
    def __init__(self, address: str, port: int) -> None:
        self.logger = logging.getLogger(address)
        self.protocol = ''
        self.address = address
        self.port = port

        self.stats:  List[DBStats] | None = None
        self.away_message: str | None = None
        self.client: OsuClient | None = None
        self.object: DBUser | None = None
        self.status = Status()

        self.id = 0
        self.name = ""

        self.packets = DefaultResponsePacket
        self.request_packets = DefaultRequestPacket
        self.decoders: Dict[Enum, Callable] = versions.get_next_version(20130815).decoders
        self.encoders: Dict[Enum, Callable] = versions.get_next_version(20130815).encoders

        from .collections import Players
        from .multiplayer import Match
        from .channel import Channel

        self.channels: Set[Channel] = set()
        self.filter = PresenceFilter.All

        self.spectators = Players()
        self.spectating: Player | None = None
        self.spectator_chat: Channel | None = None

        self.in_lobby = False
        self.logged_in = False
        self.match: Match | None = None
        self.last_response = time.time()

        self.recent_message_count = 0
        self.last_minute_stamp = time.time()

        self.permissions = Permissions.NoPermissions
        self.groups = []

    def __repr__(self) -> str:
        return f'<Player "{self.name}" ({self.id})>'

    def __hash__(self) -> int:
        return self.id

    def __eq__(self, other) -> bool:
        if isinstance(other, Player):
            return (
                self.id == other.id and
                self.port == other.port
            )
        return False

    @classmethod
    def bot_player(cls):
        with app.session.database.managed_session() as session:
            # TODO: Refactor bot related code to IRC client
            player = Player('127.0.0.1', 6969)
            player.object = users.fetch_by_id(1, session=session)
            player.client = OsuClient.empty()

            player.id = -player.object.id
            player.name = player.object.name
            player.stats  = player.object.stats

            player.permissions = Permissions(
                groups.get_player_permissions(1, session=session)
            )

            player.client.ip.country_code = "OC"
            player.client.ip.city = "w00t p00t!"

            return player

    @property
    def is_bot(self) -> bool:
        return (
            self.object.is_bot
            if self.object else False
        )

    @property
    def silenced(self) -> bool:
        if not self.object.silence_end:
            return False

        if self.remaining_silence < 0:
            # User is not silenced anymore
            self.unsilence()
            return False

        return True

    @property
    def remaining_silence(self) -> int:
        if not self.object.silence_end:
            return 0

        return (
            self.object.silence_end.timestamp() -
            datetime.now().timestamp()
        )

    @property
    def restricted(self) -> bool:
        if not self.object:
            return False

        if not self.object.restricted:
            return False

        if not (recent := infringements.fetch_recent_by_action(self.id, action=0)):
            self.unrestrict()
            return False

        if recent.is_permanent:
            return True

        remaining = (recent.length - datetime.now()).total_seconds()

        if remaining <= 0:
            self.unrestrict()
            return False

        return True

    @property
    def current_stats(self) -> DBStats | None:
        return next(
            (
                stats for stats in self.stats
                if stats.mode == self.status.mode.value
            ),
            None
        )

    @property
    def friends(self) -> List[int]:
        return [
            rel.target_id
            for rel in self.object.relationships
            if rel.status == 0
        ]

    @property
    def online_friends(self) -> List["Player"]:
        return [
            app.session.players.by_id(id)
            for id in self.friends if id in app.session.players.ids
        ]

    @property
    def user_presence(self) -> bUserPresence:
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
            self.rank,
            self.client.ip.city \
                if self.client.display_city
                else None
        )

    @property
    def user_stats(self) -> bUserStats:
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
            self.rank,
            self.current_stats.pp,
        )

    @property
    def level(self) -> int:
        score = self.current_stats.tscore
        added_score = 0
        index = 0

        while added_score + level.NEXT_LEVEL[index] < score:
            added_score += level.NEXT_LEVEL[index]
            index += 1

        return round(
            (index + 1) + (score - added_score) / level.NEXT_LEVEL[index]
        )

    @property
    def is_tourney_client(self) -> bool:
        return self.client.version.stream == 'tourney'

    @property
    def rank(self) -> int:
        return self.current_stats.rank

    @property
    def link(self) -> str:
        return f'[http://osu.{config.DOMAIN_NAME}/u/{self.id} {self.name}]'

    @property
    def is_supporter(self) -> bool:
        return 'Supporter' in self.groups

    @property
    def is_admin(self) -> bool:
        return 'Admins' in self.groups

    @property
    def is_dev(self) -> bool:
        return 'Developers' in self.groups

    @property
    def is_bat(self) -> bool:
        return 'Beatmap Approval Team' in self.groups

    @property
    def is_moderator(self) -> bool:
        return 'Global Moderator Team' in self.groups

    @property
    def has_preview_access(self) -> bool:
        return 'Preview' in self.groups

    @property
    def is_verified(self) -> bool:
        return 'Verified' in self.groups or self.is_staff

    @property
    def is_staff(self) -> bool:
        return any([self.is_admin, self.is_dev, self.is_moderator])

    def enqueue(self, data: bytes):
        """
        Enqueues the given data to the client.
        This needs to be implemented by the inheriting class.
        """
        ...

    def close_connection(self, error: Exception | None = None):
        """
        This will close the connection to the client.
        This needs to be implemented by the inheriting class.
        """
        self.connectionLost(error)

    def connectionLost(self, reason: Failure = Failure(ConnectionDone())):
        if not self.logged_in:
            return

        self.track(
            'bancho_disconnect',
            {'reason': str(reason)}
        )

        if self.spectating:
            if not self.spectating:
                return

            # Leave spectator channel
            self.spectating.spectator_chat.remove(self)

            # Remove from target
            self.spectating.spectators.remove(self)

            # Enqueue to others
            for p in self.spectating.spectators:
                p.enqueue_fellow_spectator_left(self.id)

            # Enqueue to target
            self.spectating.enqueue_spectator_left(self.id)

            # If target has no spectators anymore
            # kick them from the spectator channel
            if not self.spectating.spectators:
                self.spectating.spectator_chat.remove(
                    self.spectating
                )

            self.spectating = None

        for channel in copy(self.channels):
            channel.remove(self)

        app.session.channels.remove(self.spectator_chat)
        app.session.players.remove(self)

        status.delete(self.id)
        usercount.set(len(app.session.players.normal_clients))

        if self.match:
            app.clients.handler.leave_match(self)

        tourney_clients = app.session.players.get_all_tourney_clients(self.id)

        if len(tourney_clients) <= 0:
            app.session.players.send_user_quit(
                bUserQuit(
                    self.id,
                    self.user_presence,
                    self.user_stats,
                    QuitState.Gone
                )
            )

    def send_packet(self, packet: Enum, *args) -> None:
        try:
            stream = StreamOut()
            data = self.encoders[packet](*args)

            self.logger.debug(
                f'<- "{packet.name}": {str(list(args)).removeprefix("[").removesuffix("]")}'
            )

            if self.client.version.date <= 323:
                # In version b323 and below, the
                # compression is enabled by default
                data = gzip.compress(data)
                stream.legacy_header(packet, len(data))
            else:
                stream.header(packet, len(data))

            stream.write(data)
            self.enqueue(stream.get())
        except Exception as e:
            self.logger.error(
                f'Could not send packet "{packet.name}": {e}',
                exc_info=e
            )

    def send_error(self, reason=-5, message=""):
        """This will send a login reply packet with an optional message to the player"""
        if self.encoders and message:
            self.send_packet(
                self.packets.ANNOUNCE,
                message
            )

        self.send_packet(
            self.packets.LOGIN_REPLY,
            reason
        )

    def send_inactive_account_error(self):
        if self.client.version.date < 20130801:
            self.login_failed(LoginError.NotActivated)
            return

        # Versions after b20130801 show the
        # "NotActivated" error as being banned
        self.login_failed(
            LoginError.Authentication,
            strings.NOT_ACTIVATED
        )

    def login_failed(self, reason=LoginError.ServerError, message=""):
        self.send_error(reason.value, message)
        self.close_connection()

    def reload_object(self) -> DBUser:
        """Reload player object from database"""
        with app.session.database.managed_session() as session:
            self.object = users.fetch_by_id(self.id, session=session)
            self.stats = self.object.stats

            # Preload relationships
            self.object.target_relationships
            self.object.relationships
            self.object.groups

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
                {'rank': cached_rank}
            )

            # Update rank history
            histories.update_rank(
                self.current_stats,
                self.object.country
            )

    def update_leaderboard_stats(self) -> None:
        """Updates the player's stats inside the redis leaderboard"""
        leaderboards.update(
            self.current_stats,
            self.object.country.lower()
        )

    def update_status_cache(self) -> None:
        """Updates the player's status inside the cache"""
        status.update(
            self.id,
            self.status.bancho_status,
            self.client.hash.string,
            self.client.version.date
        )

    def get_client(self, version: int):
        """Figure out packet sender/decoder, closest to version of client"""
        client_version = versions.get_next_version(version)

        self.request_packets = client_version.request_packets
        self.packets = client_version.response_packets
        self.decoders = client_version.decoders
        self.encoders = client_version.encoders

        self.logger.debug(f'Assigned decoder with version b{client_version.version}')

    def login_received(self, username: str, md5: str, client: OsuClient):
        self.logger = logging.getLogger(f'Player "{username}"')
        self.logger.info(f'Login attempt as "{username}" with {client.version}.')
        self.last_response = time.time()
        self.client = client

        # Get decoders and encoders
        self.get_client(client.version.date)

        # Send protocol version
        self.send_packet(self.packets.PROTOCOL_VERSION, config.PROTOCOL_VERSION)

        if client.hash.adapters != 'runningunderwine':
            # Validate adapters md5
            adapters_hash = hashlib.md5(client.hash.adapters.encode()).hexdigest()

            if adapters_hash != client.hash.adapters_md5:
                officer.call(f'Player tried to log in with spoofed adapters: {adapters_hash}')
                self.close_connection()
                return

        with app.session.database.managed_session() as session:
            if not (user := users.fetch_by_name_case_insensitive(username, session)):
                self.logger.warning('Login Failed: User not found')
                self.login_failed(LoginError.Authentication)
                return

            self.id = user.id
            self.name = user.name
            self.stats = user.stats
            self.object = user

            # Preload relationships
            self.object.target_relationships
            self.object.relationships
            self.object.groups

            self.permissions = Permissions(groups.get_player_permissions(self.id, session))
            self.groups = [group.name for group in groups.fetch_user_groups(self.id, True, session)]

            if not bcrypt.checkpw(md5.encode(), user.bcrypt.encode()):
                self.logger.warning('Login Failed: Authentication error')
                self.login_failed(LoginError.Authentication)
                return

            if self.restricted:
                self.logger.warning('Login Failed: Restricted')
                self.login_failed(LoginError.Banned)
                return

            if not user.activated:
                self.logger.warning('Login Failed: Not activated')
                self.send_inactive_account_error()
                return

            if config.MAINTENANCE:
                if not self.is_staff:
                    # Bancho is in maintenance mode
                    self.logger.warning('Login Failed: Maintenance')
                    self.login_failed(
                        LoginError.ServerError,
                        message=strings.MAINTENANCE_MODE
                    )
                    return

                self.enqueue_announcement(strings.MAINTENANCE_MODE_ADMIN)

            check_client = (
                not config.DISABLE_CLIENT_VERIFICATION
                and not self.is_staff
                and not self.has_preview_access
            )

            # Check client's executable hash
            if check_client:
                is_valid = client_utils.is_valid_client_hash(
                    self.client.version.date,
                    self.client.hash.md5
                )

                if not is_valid:
                    self.logger.warning('Login Failed: Unsupported client')
                    self.login_failed(
                        LoginError.UpdateNeeded,
                        message=strings.UNSUPPORTED_HASH
                    )
                    officer.call(
                        f'Player tried to log in with an unsupported version: {self.client.version} ({self.client.hash.md5})'
                    )
                    self.close_connection()
                    return

            if not self.is_tourney_client:
                if (other_user := app.session.players.by_id(user.id)):
                    # Another user is online with this account
                    other_user.login_failed(
                        LoginError.Authentication,
                        strings.LOGGED_IN_FROM_ANOTHER_LOCATION
                    )

            elif not self.is_supporter:
                # Trying to use tourney client without supporter
                self.login_failed(LoginError.TestBuild)
                return

            else:
                # Check amount of tourney clients that are online
                tourney_clients = app.session.players.get_all_tourney_clients(self.id)

                if len(tourney_clients) >= config.MULTIPLAYER_MAX_SLOTS:
                    self.logger.warning(f'Tried to log in with more than {config.MULTIPLAYER_MAX_SLOTS} tourney clients')
                    self.close_connection()
                    return

            self.status.mode = GameMode(self.object.preferred_mode)

            if not self.stats:
                self.stats = [stats.create(self.id, mode, session) for mode in range(4)]
                self.reload_object()
                self.enqueue_silence_info(-1)

            # Create login attempt in db
            logins.create(
                self.id,
                self.address,
                self.client.version.string,
                session
            )

            # Check for new hardware
            self.check_client(session)

            if self.object.country.upper() == 'XX':
                # We failed to get the users country on registration
                self.object.country = self.client.ip.country_code.upper()
                leaderboards.remove_country(self.id, self.object.country)
                users.update(self.id, {'country': self.object.country}, session)

            # Update cache
            self.update_leaderboard_stats()
            self.update_status_cache()

        self.logged_in = True
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

        # Remove avatar so that it can be reloaded
        app.session.redis.delete(f'avatar:{self.id}')

        self.update_activity()
        self.send_packet(self.packets.PROTOCOL_VERSION, 18)
        self.send_packet(self.packets.LOGIN_REPLY, self.id)

        # Menu Icon
        self.send_packet(
            self.packets.MENU_ICON,
            config.MENUICON_IMAGE,
            config.MENUICON_URL
        )

        self.enqueue_permissions()
        self.enqueue_friends()

        # User & Bot Presence
        self.enqueue_presence(self)
        self.enqueue_stats(self)
        self.enqueue_irc_player(app.session.bot_player)

        # Append to player collection
        app.session.players.add(self)

        # Enqueue other players
        self.enqueue_players(app.session.players)

        # Update usercount
        usercount.set(len(app.session.players.normal_clients))

        # Enqueue all public channels
        for channel in app.session.channels.public:
            if not channel.can_read(self.permissions):
                continue

            # Check if channel should be autojoined
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

        # Enqueue players in lobby
        for player in app.session.players.in_lobby:
            self.enqueue_lobby_join(player.id)

        self.track(
            'bancho_login',
            {'login_type': self.protocol}
        )

    def check_client(self, session: Session | None = None):
        client = clients.fetch_without_executable(
            self.id,
            self.client.hash.adapters_md5,
            self.client.hash.uninstall_id,
            self.client.hash.diskdrive_signature,
            session=session
        )

        matches = clients.fetch_hardware_only(
            self.client.hash.adapters_md5,
            self.client.hash.uninstall_id,
            self.client.hash.diskdrive_signature,
            session=session
        )

        if not client:
            # New hardware detected
            self.logger.warning(
                f'New hardware detected: {self.client.hash.string}'
            )

            clients.create(
                self.id,
                self.client.hash.md5,
                self.client.hash.adapters_md5,
                self.client.hash.uninstall_id,
                self.client.hash.diskdrive_signature,
                session=session
            )

            user_matches = [match for match in matches if match.user_id == self.id]

            if self.current_stats.playcount > 0 and not user_matches:
                mail.send_new_location_email(
                    self.object,
                    self.client.ip.country_name
                )

        if config.ALLOW_MULTIACCOUNTING or self.is_bot:
            return

        # Reset multiaccounting lock
        app.session.redis.set(f'multiaccounting:{self.id}', 0)

        # Filter out current user
        other_matches = [match for match in matches if match.user_id != self.id]
        banned_matches = [match for match in other_matches if match.banned]

        if banned_matches and not self.is_verified:
            # User tries to log into an account with banned hardware matches
            self.restrict('Multiaccounting', autoban=True)
            return

        if other_matches:
            # User was detected to be multiaccounting
            # If user tries to submit a score, they will be restricted
            # Users who are verified will not be restricted
            officer.call(
                f'Multiaccounting detected for "{self.name}": '
                f'{self.client.hash.string} ({len(other_matches)} matches)'
            )

            if self.is_verified:
                return

            app.session.redis.set(f'multiaccounting:{self.id}', 1)
            self.enqueue_announcement(strings.MULTIACCOUNTING_DETECTED)

    def packet_received(self, packet_id: int, stream: StreamIn):
        self.last_response = time.time()

        try:
            packet = self.request_packets(packet_id)

            decoder = self.decoders[packet]
            args = decoder(stream)

            self.logger.debug(
                f'-> "{packet.name}": {args}'
            )
        except KeyError as e:
            self.logger.error(
                f'Could not find decoder for "{packet.name}": {e}',
                exc_info=e
            )
            return
        except ValueError as e:
            self.logger.error(
                f'Could not find packet with id "{packet_id}": {e}',
                exc_info=e
            )
            return

        if not self.logged_in:
            return

        self.track(
            f'bancho_packet',
            event_properties={
                'packet_name': packet.name,
                'content': (
                    asdict(args)
                    if is_dataclass(args)
                    else args
                )
            }
        )

        if not (handler_function := app.session.handlers.get(packet)):
            self.logger.warning(f'Could not find a handler function for "{packet}".')
            return

        if args != None:
            handler_function(self, args)
            return

        return handler_function(self)

    def silence(self, duration_sec: int, reason: str | None = None):
        if self.is_bot:
            return

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

        # Add entry inside infringements table
        infringements.create(
            self.id,
            action=1,
            length=(datetime.now() + duration),
            description=reason
        )

        officer.call(
            f'{self.name} was silenced for {timeago.format(datetime.now() + duration)}. Reason: "{reason}"'
        )

    def unsilence(self):
        self.object.silence_end = None
        self.enqueue_silence_info(0)

        # Update database
        users.update(self.id, {'silence_end': None})

        inf = infringements.fetch_recent_by_action(self.id, action=1)
        if inf: infringements.delete_by_id(inf.id)

    def restrict(
        self,
        reason: str | None = None,
        until: datetime | None = None,
        autoban: bool = False
    ) -> None:
        self.object.restricted = True

        # Update database
        users.update(self.id, {'restricted': True})

        # Remove permissions
        groups.delete_entry(self.id, 999)
        groups.delete_entry(self.id, 1000)

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
                f'\nYou will be able to play again {timeago.format(until)}.'
                if until else ''
            )

        if until:
            self.enqueue_silence_info(
                round(
                    (until - datetime.now()).total_seconds()
                )
            )

        # Update client
        self.login_failed(LoginError.Banned)

        # Update hardware
        clients.update_all(self.id, {'banned': True})

        # Add entry inside infringements table
        infringements.create(
            self.id,
            action=0,
            length=until,
            is_permanent=True
                    if not until
                    else False,
            description=f'{"Autoban: " if autoban else ""}{reason}'
        )

        officer.call(
            f'{self.name} was {"auto-" if autoban else ""}restricted. Reason: "{reason}"'
        )

    def unrestrict(self) -> None:
        users.update(self.id, {'restricted': False})
        self.object.restricted = False

        # Add to player & supporter group
        groups.create_entry(self.id, 999)
        groups.create_entry(self.id, 1000)

        # Update hardware
        clients.update_all(self.id, {'banned': False})

        # Update client
        self.enqueue_silence_info(-1)

    def update_activity(self):
        users.update(
            user_id=self.id,
            updates={
                'latest_activity': datetime.now()
            }
        )

    def track(self, event: str, event_properties: dict) -> None:
        analytics.track(
            event,
            user_id=self.id,
            ip=self.address,
            device_id=self.client.hash.device_id,
            app_version=self.client.version.string,
            platform='linux' if self.client.is_wine else 'windows',
            event_properties=event_properties,
            user_properties={
                'user_id': self.id,
                'username': self.name,
                'country': self.object.country,
                'groups': self.groups,
                'is_bot': self.is_bot
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

    def enqueue_players(self, players: list, stats_only: bool = False):
        if self.client.version.date <= 1717:
            action = (
                self.enqueue_stats
                if stats_only
                else self.enqueue_presence
            )

            for player in players:
                action(player)

            # Account for bUserStats update in b1717
            return

        if self.client.version.date <= 20121223:
            for player in players:
                self.enqueue_presence(player)

            # Presence bundle is not supported
            return

        player_chunks = itertools.zip_longest(
            *[iter(players)] * 128
        )

        # Send players in bundles of user ids
        for chunk in player_chunks:
            self.send_packet(
                self.packets.USER_PRESENCE_BUNDLE,
                [
                    player.id
                    for player in chunk
                    if player != None
                ]
            )

        # TODO: Enqueue irc players

    def enqueue_irc_player(self, player):
        if self.client.version.date <= 1710:
            self.send_packet(
                self.packets.IRC_JOIN,
                player.name
            )
            return

        self.enqueue_presence(player)

    def enqueue_irc_leave(self, player):
        if self.client.version.date <= 1710:
            self.send_packet(
                self.packets.IRC_QUIT,
                player.name
            )
            return

        quit_state = QuitState.Gone

        if (app.session.players.by_id(player.id)):
            quit_state = QuitState.OsuRemaining

        self.enqueue_quit(quit_state)

    def enqueue_presence(self, player, update: bool = False):
        if self.client.version.date <= 319:
            self.send_packet(
                self.packets.USER_STATS,
                player.user_stats,
                player.user_presence,
                update
            )
            return

        if self.client.version.date <= 1710:
            self.send_packet(
                self.packets.USER_STATS,
                player.user_stats,
                player.user_presence
            )
            return

        presence = player.user_presence

        if (
            self.client.version.date > 833 and
            self.current_stats.pp <= 0
        ):
            # Newer clients don't display rank 0
            presence.rank = 0

        self.send_packet(
            self.packets.USER_PRESENCE,
            presence
        )

    def enqueue_stats(self, player):
        if self.client.version.date <= 319:
            self.send_packet(
                self.packets.USER_STATS,
                player.user_stats,
                player.user_presence
            )
            return

        stats = player.user_stats

        if (
            self.client.version.date > 833 and
            stats.pp <= 0
        ):
            # Newer clients don't display rank 0
            stats.rank = 0

        self.send_packet(
            self.packets.USER_STATS,
            stats
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
            min(remaining_time, 2147483647)
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
        if self.client.version.date > 20130815:
            return

        self.send_packet(
            self.packets.LOBBY_JOIN,
            player_id
        )

    def enqueue_lobby_part(self, player_id: int):
        if self.client.version.date > 20130815:
            return

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

    def enqueue_server_restart(self, retry_ms: int):
        self.send_packet(
            self.packets.RESTART,
            retry_ms
        )

    def enqueue_monitor(self):
        self.send_packet(self.packets.MONITOR)
