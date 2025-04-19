
from chio.constants import LoginError, QuitState, Permissions, PresenceFilter
from chio.types import UserQuit, Message, TitleUpdate
from chio import PacketType, BanchoIO

from typing import Set, Any, Iterable
from sqlalchemy.orm import Session
from datetime import datetime
from copy import copy

from app.common.database import users, groups, stats, logins, clients
from app.common.cache import status, usercount, leaderboards
from app.common.helpers import clients as client_utils
from app.common.constants import GameMode
from app.common.constants import strings
from app.common import officer, mail

from app.objects.channel import Channel, SpectatorChannel
from app.objects.client import OsuClientInformation
from app.objects.multiplayer import Match
from app.objects.locks import LockedSet
from app.clients import Client

import hashlib
import logging
import bcrypt
import config
import time
import chio
import app

class OsuClient(Client):
    def __init__(self, address: str, port: int):
        super().__init__(address, port)
        self.match: Match | None = None
        self.spectating: OsuClient | None = None
        self.spectator_chat: SpectatorChannel | None = None
        self.spectators: LockedSet[OsuClient] = LockedSet()
        self.info: OsuClientInformation = OsuClientInformation.empty()

        self.io: BanchoIO = chio.select_latest_client()
        self.referee_matches: Set[Match] = set()
        self.channels: Set[Channel] = set()

        self.filter = PresenceFilter.All
        self.logged_in = False
        self.in_lobby = False

    @property
    def is_tourney_client(self) -> bool:
        return self.client.version.stream == 'tourney'

    def __repr__(self) -> str:
        return f'<OsuClient "{self.name}" ({self.id})>'

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        if isinstance(other, OsuClient):
            return (
                self.id == other.id and
                self.port == other.port
            )
        return False

    def on_login_received(
        self,
        username: str,
        password: str,
        info: OsuClientInformation
    ) -> None:
        self.logger = logging.getLogger(f'Player "{username}"')
        self.logger.info(f'Login attempt as "{username}" with {info.version}.')
        self.last_response = time.time()
        self.info = info

        # Select the correct client/io object
        self.io = chio.select_client(info.version.date)

        # Send protocol version
        self.enqueue_packet(
            PacketType.BanchoProtocolNegotiation,
            self.io.protocol_version
        )

        if info.hash.adapters != 'runningunderwine':
            # Validate adapters md5
            adapters_hash = hashlib.md5(info.hash.adapters.encode()).hexdigest()

            if adapters_hash != info.hash.adapters_md5:
                officer.call(f'Player tried to log in with spoofed adapters: {adapters_hash}')
                self.close_connection()
                return

        with app.session.database.managed_session() as session:
            if not (user := users.fetch_by_name_case_insensitive(username, session)):
                self.logger.warning('Login Failed: User not found')
                self.on_login_failed(LoginError.Authentication)
                return

            self.object = user
            self.update_object(user.preferred_mode)

            self.presence.permissions = Permissions(groups.get_player_permissions(self.id, session))
            self.groups = [group.name for group in groups.fetch_user_groups(self.id, True, session)]

            # Preload relationships
            self.object.target_relationships
            self.object.relationships
            self.object.groups

            if not bcrypt.checkpw(password.encode(), user.bcrypt.encode()):
                self.logger.warning('Login Failed: Authentication error')
                self.on_login_failed(LoginError.Authentication)
                return

            if self.restricted:
                self.logger.warning('Login Failed: Restricted')
                self.on_login_failed(LoginError.Banned)
                return

            if not user.activated:
                self.logger.warning('Login Failed: Not activated')
                self.send_inactive_account_error()
                return

            if config.MAINTENANCE:
                if not self.is_staff:
                    # Bancho is in maintenance mode
                    self.logger.warning('Login Failed: Maintenance')
                    return self.on_login_failed(
                        LoginError.ServerError,
                        strings.MAINTENANCE_MODE
                    )

                # Inform staff about maintenance mode
                self.enqueue_announcement(strings.MAINTENANCE_MODE_ADMIN)

            check_client = (
                not config.DISABLE_CLIENT_VERIFICATION
                and not self.is_staff
                and not self.has_preview_access
            )

            # Check client's executable hash
            if check_client and not self.is_valid_client(session):
                self.logger.warning('Login Failed: Unverified client')
                self.on_login_failed(
                    LoginError.UpdateNeeded,
                    strings.UNSUPPORTED_HASH
                )
                officer.call(
                    f'"{self.name}" tried to log in with an unverified version: '
                    f'{self.client.version} ({self.client.hash.md5})'
                )
                self.close_connection()
                return

            if not self.is_tourney_client:
                if (other_user := app.session.players.by_id(user.id)):
                    # Another user is online with this account
                    other_user.on_login_failed(
                        LoginError.Authentication,
                        strings.LOGGED_IN_FROM_ANOTHER_LOCATION
                    )

            elif not self.is_supporter:
                # Trying to use tournament client without supporter
                self.on_login_failed(LoginError.TestBuild)
                return

            else:
                # Check amount of tournament clients that are online
                tourney_clients = app.session.players.tournament_clients(self.id)

                if len(tourney_clients) >= config.MULTIPLAYER_MAX_SLOTS + 2:
                    # Clear connection of oldest tournament client
                    tourney_clients.sort(key=lambda x: x.last_response)
                    tourney_clients[0].close_connection()

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
        self.on_login_success()

    def on_login_success(self) -> None:
        self.spectator_chat = SpectatorChannel(self)
        app.session.channels.add(self.spectator_chat)

        self.update_activity()
        self.enqueue_packet(PacketType.BanchoLoginReply, self.id)
        self.enqueue_packet(PacketType.BanchoLoginPermissions, self.permissions)
        self.enqueue_packet(PacketType.BanchoFriendsList, self.friends)

        # Menu Icon
        self.enqueue_packet(
            PacketType.BanchoTitleUpdate,
            TitleUpdate(
                config.MENUICON_IMAGE,
                config.MENUICON_URL
            )
        )

        # User & Bot Presence
        self.enqueue_presence(self)
        self.enqueue_stats(self)
        self.enqueue_player(app.session.banchobot)

        # Append to player collection
        app.session.players.add(self)

        # Enqueue other players
        self.enqueue_players(app.session.players)

        # Update usercount
        usercount.set(len(app.session.players))

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

        self.enqueue_packet(PacketType.BanchoChannelInfoComplete)
        self.enqueue_infringement_length(self.remaining_silence)

        # Enqueue players in lobby
        for player in app.session.players.osu_in_lobby:
            self.enqueue_packet(PacketType.BanchoLobbyJoin, player.id)

        # Potentially fix player referee state
        self.referee_matches.update([
            match for match in app.session.matches.persistent
            if self.id in match.referee_players
        ])

        for match in self.referee_matches:
            # Join the match channel automatically
            channel_object = match.chat.bancho_channel
            channel_object.name = match.chat.name
            self.enqueue_channel(channel_object, autojoin=True)
            match.chat.add(self)

    def on_login_failed(self, reason: LoginError, message: str = "") -> None:
        self.enqueue_error(reason, message)
        self.close_connection()

    def on_connection_lost(self, reason: Any, was_clean: bool = True) -> None:
        if was_clean:
            return self.close_connection()

        self.logger.warning(f'<{self.address}> -> Lost connection: "{reason}".')
        return self.close_connection(reason)

    def on_packet_received(self, packet: PacketType, data: Any) -> None:
        self.last_response = time.time()

        if not self.logged_in:
            return

        self.logger.debug(
            f'-> "{packet.name}": {data}'
        )

        if not (handler_function := app.session.handlers.get(packet)):
            self.logger.warning(f'Could not find a handler function for "{packet}".')
            return

        if data is None:
            return handler_function(self)

        return handler_function(self, data)

    def close_connection(self, reason: str = "") -> None:
        if not self.logged_in:
            return

        self.logger.info(
            f'Closing connection -> <{self.address}> ({reason})' if reason else
            f"<{self.address}> -> Connection done."
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

        usercount.set(len(app.session.players))
        status.delete(self.id)

        if self.match:
            self.match.kick_player(self)

        # Check if there are any tournament clients remaining
        tourney_clients = app.session.players.tournament_clients(self.id)

        if len(tourney_clients) <= 0:
            user_quit = UserQuit(self, QuitState.Gone)
            app.session.players.send_user_quit(user_quit)

    def is_valid_client(self, session: Session | None = None) -> bool:
        valid_identifiers = (
            'stable', 'test', 'tourney', 'cuttingedge', 'beta'
            'ubertest', 'ce45', 'peppy', 'dev', 'arcade',
            'fallback', 'a', 'b', 'c', 'd', 'e'
        )

        if self.client.version.identifier in valid_identifiers:
            return client_utils.is_valid_client_hash(
                self.client.version.date,
                self.client.hash.md5,
                session=session
            )
        
        return client_utils.is_valid_mod(
            self.client.version.identifier,
            self.client.hash.md5,
            session=session
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

    def restrict(
        self,
        reason: str | None = None,
        until: datetime | None = None,
        autoban: bool = False
    ) -> None:
        super().restrict(reason, until, autoban)
        self.on_login_failed(LoginError.Banned)
        self.close_connection("Restricted")

    def enqueue_packet(self, packet: PacketType, *args) -> None:
        self.logger.debug(f'<- "{packet.name}": {args}')
        # NOTE: The actual packet will be sent in the protocol implementation
        #       e.g. app.protocols.tcp or app.protocols.http

    def enqueue_error(self, error: LoginError = LoginError.ServerError, message: str = "") -> None:
        self.enqueue_packet(PacketType.BanchoLoginReply, error)

        if message:
            self.enqueue_packet(PacketType.BanchoAnnounce, message)

    def enqueue_player(self, player: "Client") -> None:
        self.enqueue_presence_single(player)

    def enqueue_players(self, players: Iterable["Client"]) -> None:
        self.enqueue_presence_bundle(players)

    def enqueue_presence(self, player: "Client") -> None:
        self.enqueue_packet(PacketType.BanchoUserPresence, player)

    def enqueue_presence_single(self, player: "Client") -> None:
        self.enqueue_packet(PacketType.BanchoUserPresenceSingle, player)

    def enqueue_presence_bundle(self, players: Iterable["Client"]) -> None:
        self.enqueue_packet(PacketType.BanchoUserPresenceBundle, players)

    def enqueue_stats(self, player: "Client") -> None:
        if player.is_irc:
            return

        self.enqueue_packet(PacketType.BanchoUserStats, player)

    def enqueue_announcement(self, message: str) -> None:
        self.enqueue_packet(PacketType.BanchoAnnounce, message)

    def enqueue_infringement_length(self, duration_seconds: int) -> None:
        self.enqueue_packet(PacketType.BanchoSilenceInfo, duration_seconds)

    def enqueue_channel(self, channel: Channel, autojoin: bool = False) -> None:
        packet = (
            PacketType.BanchoChannelAvailableAutojoin
            if autojoin else PacketType.BanchoChannelAvailable
        )
        self.enqueue_packet(packet, channel)

    def enqueue_channel_join_success(self, channel: str) -> None:
        self.enqueue_packet(PacketType.BanchoChannelJoinSuccess, channel)

    def enqueue_channel_revoked(self, channel: str) -> None:
        self.enqueue_packet(PacketType.BanchoChannelRevoked, channel)

    def enqueue_message(
        self,
        message: str,
        sender: "Client",
        target: str
    ) -> None:
        msg = Message(sender.name, message, target, sender.id)
        self.enqueue_message_object(msg)

    def enqueue_message_object(self, message: Message) -> None:
        self.enqueue_packet(PacketType.BanchoMessage, message)

    def enqueue_user_quit(self, player: "Client") -> None:
        self.enqueue_packet(PacketType.BanchoUserQuit, player)

    def enqueue_server_restart(self, retry_in_ms: int) -> None:
        self.enqueue_packet(PacketType.BanchoRestart, retry_in_ms)
