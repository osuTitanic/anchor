
from app.common.database import users, groups, stats, logins
from app.common.config import config_instance as config
from app.common.constants import UserActivity, strings
from app.common.helpers import activity
from app.common.cache import status
from app.objects.channel import Channel
from app.clients.base import Client

from chio import Permissions, LoginError, UserQuit, Message, QuitState
from typing import List, Any, Iterable
from twisted.words.protocols import irc
from twisted.internet import reactor
from functools import cached_property
from datetime import datetime
from copy import copy

import logging
import time
import app

class IrcClient(Client):
    def __init__(self, address: str, port: int):
        super().__init__(address, port)
        self.presence.is_irc = True
        self.connected = False
        self.logged_in = False
        self.is_osu = False
        self.token = ""

    @cached_property
    def local_prefix(self) -> str:
        return self.resolve_username(self)

    def __repr__(self) -> str:
        return f'<IrcClient "{self.name}" ({self.id})>'

    def on_command_received(self, command: str, prefix: str, params: List[str]) -> None:
        self.logger.debug(f"-> <{command}> {prefix} ({', '.join(params)})")
        self.last_response = time.time()
        app.session.packets_per_minute.record()

        if not (handler := app.session.irc_handlers.get(command)):
            return

        return handler(self, prefix, *params)
    
    def on_login_received(self) -> None:
        if self.logged_in:
            return

        self.logger = logging.getLogger(f'IRC "{self.name}"')
        self.logger.info(f'Login attempt as "{self.name}" with IRC.')
        app.session.logins_per_minute.record()

        if self.name == app.session.banchobot.name:
            self.logger.warning('Login Failed: Attempt to login as BanchoBot')
            self.on_login_failed(LoginError.InvalidLogin)
            return

        with app.session.database.managed_session() as session:
            if not (user := users.fetch_by_safe_name(self.name, session)):
                self.logger.warning('Login Failed: User not found')
                self.on_login_failed(LoginError.InvalidLogin)
                return

            if user.irc_token != self.token:
                self.logger.warning('Login Failed: Invalid token')
                self.on_login_failed(LoginError.InvalidLogin)
                return

            self.token = ""
            self.object = user
            self.name = user.name
            self.update_object(user.preferred_mode)
            self.update_geolocation()

            # Preload relationships
            self.object.target_relationships
            self.object.relationships
            self.object.groups

            # Reload permissions
            group_permissions = groups.fetch_bancho_permissions(self.id, session)
            self.presence.permissions = Permissions(group_permissions)

            if self.restricted:
                self.logger.warning('Login Failed: Restricted')
                self.on_login_failed(LoginError.UserBanned)
                return

            if not user.activated:
                self.logger.warning('Login Failed: Not activated')
                self.on_login_failed(LoginError.UserInactive)
                return

            if self.is_osu and not config.OSU_IRC_ENABLED and not self.has_preview_access:
                self.enqueue_banchobot_message("osu! IRC connections have been disabled. Please check back later!")
                self.close_connection("osu! IRC is disabled")
                return

            if config.BANCHO_MAINTENANCE:
                if not self.is_staff:
                    # Bancho is in maintenance mode
                    self.logger.warning('Login Failed: Maintenance')
                    self.send_maintenance_error()
                    self.close_connection("Maintenance mode")
                    return

                # Inform staff about maintenance mode
                self.enqueue_announcement(strings.MAINTENANCE_MODE_ADMIN)

            if (other_user := app.session.players.by_id_irc(user.id)):
                # Another user is online with this account on irc
                other_user.enqueue_error(strings.LOGGED_IN_FROM_ANOTHER_LOCATION)
                other_user.close_connection("Logged in from another location")
                return

            if not self.object.stats:
                self.object.stats = [
                    stats.create(self.id, mode, session)
                    for mode in range(4)
                ]
                session.commit()
                self.reload(self.object.preferred_mode)

            # Create login attempt in db
            app.session.tasks.do_later(
                logins.create,
                self.id,
                self.address,
                "irc",
                priority=4
            )

            activity.submit(
                self.id, None,
                UserActivity.UserLogin,
                {
                    'username': self.name,
                    'location': 'bancho',
                    'client': 'irc'
                },
                is_hidden=True,
                session=session
            )

            # Update rank, status & rankings
            self.update_cache()

        self.logged_in = True
        self.on_login_success()

    def on_login_success(self) -> None:
        self.update_activity_later()
        self.send_welcome_sequence()
        self.enqueue_infringement_length(self.remaining_silence)

        # Append to player collection
        app.session.players.add(self)

        # Update cached usercount
        app.session.tasks.do_later(
            app.session.players.update_usercount,
            priority=4
        )

        # Enqueue all public channels
        for channel in app.session.channels.public:
            if not channel.can_read(self):
                continue

            # Check if channel should be autojoined
            if channel.name not in config.AUTOJOIN_CHANNELS:
                continue

            channel.add(self)

        # Re-add matches that this player is a referee for
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

    def on_login_failed(self, reason: LoginError) -> None:
        mapping = {
            LoginError.InvalidLogin: self.send_token_error,
            LoginError.UserBanned: self.send_restricted_error,
            LoginError.UserInactive: self.send_inactive_error,
            LoginError.ServerError: self.send_server_error,
        }
        mapping.get(reason, self.send_server_error)()
        self.close_connection("Login failure")

    def on_user_restricted(
        self,
        reason: str | None = None,
        until: datetime | None = None,
        autoban: bool = False
    ) -> None:
        super().on_user_restricted(reason, until, autoban)
        self.send_restricted_error()
        self.close_connection("Restricted")

    def close_connection(self, reason: Any = None) -> None:
        self.connected = False

        if reason is not None:
            self.logger.info(f'Closing connection -> <{self.address}> ({reason})')

        if not self.logged_in:
            return

        app.session.players.remove(self)
        self.logged_in = False

        for channel in copy(self.channels):
            channel.remove(self)

        def update_cache():
            status.delete(self.id)
            users.update(self.id, {'latest_activity': datetime.now()})
            app.session.players.update_usercount()

        app.session.tasks.do_later(
            update_cache,
            priority=4
        )

        # Check if there are any other remaining clients connected
        remaining_client = app.session.players.by_id(self.id)
        quit_state = QuitState.Gone

        if remaining_client:
            quit_state = (
                QuitState.IrcRemaining if remaining_client.is_irc else
                QuitState.OsuRemaining
            )

        app.session.tasks.do_later(
            app.session.players.send_user_quit,
            UserQuit(self, quit_state),
            priority=2
        )

    def handle_osu_login(self) -> None:
        if not self.is_osu:
            return

        osu_login_ip = app.session.redis.get(
            f"bancho:irc_login:{self.safe_name}"
        )

        if (osu_login_ip or b"").decode() != self.address:
            self.enqueue_banchobot_message("Please enter your IRC token to proceed!")
            return

        # User has logged in via. /web/osu-login.php
        self.token = users.fetch_irc_token(self.safe_name)
        self.on_login_received()

    def handle_osu_login_callback(self, token: str) -> None:
        if not self.is_osu:
            return

        self.token = token
        self.on_login_received()

    def handle_timeout_callback(self) -> None:
        if not self.connected:
            return

        if self.logged_in or self.is_osu:
            return

        self.send_token_error()
        self.close_connection("No token provided")

    def update_status_cache(self) -> None:
        if self.is_osu:
            return super().update_status_cache()

    def send_welcome_sequence(self) -> None:
        self.enqueue_welcome()
        self.enqueue_motd(
            strings.ANCHOR_ASCII_ART +
            f'web:    https://osu.{config.DOMAIN_NAME}\n'
            f'status: https://status.{config.DOMAIN_NAME}\n'
            f'github: https://github.com/osuTitanic/\n\n'
        )

    def send_token_error(self) -> None:
        if self.is_osu:
            self.enqueue_banchobot_message("The token you entered was invalid. Please try again!")
            return

        self.enqueue_motd_raw(
            "Welcome to osu!Bancho.\n"
            "-\n"
            "- You are required to authenticate before accessing this service.\n"
            "- Please click the following link to receive your password:\n"
           f"- https://osu.{config.DOMAIN_NAME}/account/security\n"
            "-"
        )
        self.enqueue_command(irc.ERR_PASSWDMISMATCH, ":Bad authentication token.")

    def send_restricted_error(self) -> None:
        if self.is_osu:
            self.enqueue_banchobot_message("You are banned from this server.")
            return

        self.enqueue_command(
            irc.ERR_YOUREBANNEDCREEP,
            ":You are banned from this server."
        )

    def send_inactive_error(self) -> None:
        if self.is_osu:
            self.enqueue_banchobot_message("Your account has not been activated.")
            return

        self.enqueue_command(
            irc.ERR_NOTREGISTERED,
            ":Your account has not been activated."
        )

    def send_maintenance_error(self) -> None:
        self.enqueue_error("osu!Bancho is currently in maintenance mode.")

    def send_server_error(self) -> None:
        self.enqueue_error("A server-side error occurred.")

    def resolve_username(self, client: "Client") -> str:
        # osu! irc clients need a "-osu" suffix to know they are osu! clients
        return client.underscored_name + ("-osu" if client.is_osu and self.is_osu else "")

    def enqueue_line(self, line: str) -> None:
        self.logger.debug(f"-> {line}")

    def enqueue_command_raw(self, command: str, prefix: str = f"cho.{config.DOMAIN_NAME}", params: List[str] = [], tags: dict = {}) -> None:
        self.logger.debug(f"<- <{command}> {prefix} ({', '.join(params)}) {tags}")
        
    def enqueue_command(self, command: str, *params, **tags) -> None:
        self.enqueue_command_raw(
            command,
            params=[self.local_prefix] + list(params),
            tags=tags
        )

    def enqueue_message(self, message: str, sender: "Client", target: str) -> None:
        self.logger.debug(f"<- <{target}> '{message}' ({sender})")

    def enqueue_message_object(self, message: Message) -> None:
        self.logger.debug(f"<- <{message.target}> '{message.content}' ({message.sender})")

    def enqueue_banchobot_message(self, message: str) -> None:
        self.enqueue_message(message, app.session.banchobot, "#osu")

    def enqueue_welcome(self, message: str = "Welcome to osu!Bancho.") -> None:
        if self.is_osu:
            self.enqueue_banchobot_message(message)
            return

        self.enqueue_command(
            irc.RPL_WELCOME,
            f":{message}"
        )

    def enqueue_motd(self, message: str) -> None:
        messages = message.splitlines()

        if len(messages) <= 0:
            return

        if len(messages) <= 1:
            self.enqueue_command(
                irc.RPL_MOTDSTART,
                ":" + messages[0]
            )
            return

        first_message = messages.pop(0)
        last_message = messages.pop(-1)

        self.enqueue_command(
            irc.RPL_MOTDSTART,
            ":" + first_message
        )

        for index, line in enumerate(messages):
            self.enqueue_command(
                irc.RPL_MOTD,
                ":" + line
            )

        self.enqueue_command(
            irc.RPL_ENDOFMOTD,
            ":" + last_message
        )

    def enqueue_motd_raw(self, message: str) -> None:
        messages = message.splitlines()

        for index, line in enumerate(messages):
            self.enqueue_command(
                irc.RPL_MOTD,
                ":" + line
            )

    def enqueue_announcement(self, message: str) -> None:
        if self.is_osu:
            return self.enqueue_banchobot_message(message)

        messages = message.splitlines()

        for line in messages:
            self.enqueue_command("NOTICE", ":" + line)

    def enqueue_error(self, error: str = "") -> None:
        self.enqueue_announcement(error or "An unknown error occurred.")

    def enqueue_server_restart(self, retry_in_ms: int) -> None:
        self.enqueue_announcement("Bancho is restarting, please wait...")

    def enqueue_channel(self, channel: Channel, autojoin = False):
        if not autojoin:
            return

        self.enqueue_player(self, channel.name)

    def enqueue_players(self, players: Iterable[Client], channel: str = "#osu") -> None:
        chunk_size = 15
        chunk = []

        for player in players:
            if player.hidden and player != self:
                continue

            chunk.append(player.irc_prefix + self.resolve_username(player))

            if len(chunk) < chunk_size:
                continue

            self.enqueue_command(
                irc.RPL_NAMREPLY,
                "=", channel, ":" + " ".join(chunk)
            )
            chunk = []

        if chunk:
            # Send remaining players
            self.enqueue_command(
                irc.RPL_NAMREPLY,
                "=", channel, ":" + " ".join(chunk)
            )

        self.enqueue_command(
            irc.RPL_ENDOFNAMES,
            channel, ":End of /NAMES list."
        )

    def enqueue_player(self, player: Client, channel: str = "#osu") -> None:
        if player.hidden and player != self:
            return
        
        if player.is_tourney_client:
            # Don't send tourney clients to irc players
            return

        self.enqueue_command_raw(
            "JOIN",
            f"{self.resolve_username(player)}!cho@{config.DOMAIN_NAME}",
            params=[f":{channel}"]
        )

        if not player.irc_prefix:
            return

        if not app.session.banchobot:
            return

        modes = {
            '+': '+v',
            '@': '+o'
        }
        
        self.enqueue_command_raw(
            "MODE",
            app.session.banchobot.irc_formatted,
            params=[
                channel, modes.get(player.irc_prefix, ''),
                self.resolve_username(player)
            ]
        )

    def enqueue_part(self, player: Client, channel: str = "#osu") -> None:
        if player.hidden and player != self:
            return

        self.enqueue_command_raw(
            "PART",
            f"{self.resolve_username(player)}!cho@{config.DOMAIN_NAME}",
            params=[channel, ":part"]
        )

    def enqueue_user_quit(self, quit: UserQuit) -> None:
        if quit.state != QuitState.Gone:
            return
        
        if quit.info.hidden:
            return

        self.enqueue_command_raw(
            "QUIT",
            f"{self.resolve_username(quit.info)}!cho@{config.DOMAIN_NAME}",
            params=[":quit"]
        )

    def enqueue_channel_join_success(self, channel_name: str) -> None:
        if not (channel := app.session.channels.by_name(channel_name)):
            return

        def enqueue_topic() -> None:
            self.enqueue_command(
                irc.RPL_TOPIC,
                channel.name,
                ":" + channel.topic
            )
            self.enqueue_command(
                "333", # RPL_TOPICWHOTIME
                channel.name,
                channel.owner,
                f'{int(channel.created_at)}'
            )

        def enqueue_names() -> None:
            self.enqueue_players(channel.users, channel.name)

        # Send topic first, then names listing after a small delay
        # This ensures the client processes them in the correct order
        reactor.callLater(0.1, enqueue_topic)
        reactor.callLater(0.2, enqueue_names)

    def enqueue_channel_revoked(self, channel: str) -> None:
        self.enqueue_command(irc.ERR_NOSUCHCHANNEL, channel, ":No such channel")

    def enqueue_away_message(self, target: "Client") -> None:
        if self.id in target.away_senders:
            # Already sent the away message
            return

        self.enqueue_command(
            irc.RPL_AWAY,
            self.resolve_username(target),
            f":{target.away_message or ''}"
        )
        target.away_senders.add(self.id)

    def enqueue_infringement_length(self, duration_seconds: int) -> None:
        for channel in self.channels:
            self.enqueue_command(
                "MODE",
                channel.name,
                f"+q {self.resolve_username(self)}"
            )
