
from app.common.database import users, groups, stats, logins
from app.common.cache import usercount, status
from app.common.constants import strings
from app.objects.channel import Channel
from app.clients.base import Client

from chio import Permissions, LoginError, UserQuit, Message, QuitState
from twisted.words.protocols import irc
from typing import List, Any, Iterable
from copy import copy

import logging
import config
import time
import app

class IrcClient(Client):
    def __init__(self, address: str, port: int):
        super().__init__(address, port)
        self.presence.is_irc = True
        self.logged_in = False
        self.is_osu = False
        self.token = ""

    @property
    def local_prefix(self) -> str:
        return self.resolve_username(self)

    def on_command_received(self, command: str, prefix: str, params: List[str]) -> None:
        self.logger.debug(f"-> <{command}> {prefix} ({', '.join(params)})")
        self.last_response = time.time()

        if not (handler := app.session.irc_handlers.get(command)):
            return

        return handler(self, prefix, *params)
    
    def on_login_received(self) -> None:
        if self.logged_in:
            return

        self.logger = logging.getLogger(f'IRC "{self.name}"')
        self.logger.info(f'Login attempt as "{self.name}" with IRC.')

        with app.session.database.managed_session() as session:
            if not (user := users.fetch_by_safe_name(self.name, session)):
                self.logger.warning('Login Failed: User not found')
                self.on_login_failed(LoginError.InvalidLogin)
                return
            
            if user.irc_token != self.token:
                self.logger.warning('Login Failed: Invalid token')
                self.on_login_failed(LoginError.InvalidLogin)
                return

            self.name = user.name
            self.token = ""
            self.object = user
            self.update_object(user.preferred_mode)

            self.presence.permissions = Permissions(groups.get_player_permissions(self.id, session))
            self.groups = [group.name for group in groups.fetch_user_groups(self.id, True, session)]

            # Preload relationships
            self.object.target_relationships
            self.object.relationships
            self.object.groups

            if self.restricted:
                self.logger.warning('Login Failed: Restricted')
                self.on_login_failed(LoginError.UserBanned)
                return

            if not user.activated:
                self.logger.warning('Login Failed: Not activated')
                self.on_login_failed(LoginError.UserInactive)
                return

            if config.MAINTENANCE:
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
                self.object.stats = [stats.create(self.id, mode, session) for mode in range(4)]
                self.reload(self.object.preferred_mode)

            # Create login attempt in db
            logins.create(
                self.id,
                self.address,
                "irc",
                session
            )

            # Update cache
            self.update_leaderboard_stats()
            self.update_status_cache()
            self.reload_rankings()
            self.reload_rank()

        self.logged_in = True
        self.on_login_success()

    def on_login_success(self) -> None:
        self.update_activity()
        self.send_welcome_sequence()
        self.enqueue_infringement_length(self.remaining_silence)

        # Append to player collection
        app.session.players.add(self)

        # Update usercount
        usercount.set(len(app.session.players))

        # Enqueue all public channels
        for channel in app.session.channels.public:
            if not channel.can_read(self.permissions):
                continue

            # Check if channel should be autojoined
            if channel.name not in config.AUTOJOIN_CHANNELS:
                continue

            channel.add(self)

    def on_login_failed(self, reason: LoginError) -> None:
        mapping = {
            LoginError.InvalidLogin: self.send_token_error,
            LoginError.UserBanned: self.send_restricted_error,
            LoginError.UserInactive: self.send_inactive_error,
            LoginError.ServerError: self.send_server_error,
        }
        mapping.get(reason, self.send_server_error)()
        self.close_connection("Login failure")

    def close_connection(self, reason: Any = None) -> None:
        if reason is not None:
            self.logger.info(f'Closing connection -> <{self.address}> ({reason})')

        if not self.logged_in:
            return

        app.session.players.remove(self)
        self.logged_in = False

        for channel in copy(self.channels):
            channel.remove(self)

        usercount.set(len(app.session.players))
        status.delete(self.id)
        self.update_activity()

        # Check if there are any other remaining clients connected
        remaining_client = app.session.players.by_id(self.id)
        quit_state = QuitState.Gone

        if remaining_client:
            quit_state = (
                QuitState.IrcRemaining if remaining_client.is_irc else
                QuitState.OsuRemaining
            )

        user_quit = UserQuit(self, quit_state)
        app.session.players.send_user_quit(user_quit)

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
        self.token = self.object.irc_token
        self.on_login_received()

    def handle_osu_login_callback(self, token: str) -> None:
        if not self.is_osu:
            return

        self.token = token
        self.on_login_received()

    def update_status_cache(self) -> None:
        if self.is_osu:
            return super().update_status_cache()

    def send_welcome_sequence(self) -> None:
        self.enqueue_welcome()
        self.enqueue_motd(strings.ANCHOR_ASCII_ART)

    def send_token_error(self) -> None:
        if self.is_osu:
            self.enqueue_banchobot_message("The token you entered was invalid. Please try again!")
            return

        self.enqueue_motd(
            "Welcome to osu!Bancho.\n"
            "-\n"
            "- You are required to authenticate before accessing this service.\n"
            "- Please click the following link to receive your password:\n"
           f"- https://osu.{config.DOMAIN_NAME}/account/settings/security\n"
            "-"
        )
        self.enqueue_command(irc.ERR_PASSWDMISMATCH, params=[":Bad authentication token."])

    def send_restricted_error(self) -> None:
        if self.is_osu:
            self.enqueue_banchobot_message("You are banned from this server.")
            return

        self.enqueue_command(
            irc.ERR_BANNEDFROMCHAN,
            params=[":You are banned from this server."]
        )

    def send_inactive_error(self) -> None:
        if self.is_osu:
            self.enqueue_banchobot_message("Your account has not been activated.")
            return

        self.enqueue_command(
            irc.ERR_NOTREGISTERED,
            params=[":Your account has not been activated."]
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

    def enqueue_command(self, command: str, prefix: str = f"cho.{config.DOMAIN_NAME}", params: List[str] = [], tags: dict = {}) -> None:
        self.logger.debug(f"<- <{command}> {prefix} ({', '.join(params)}) {tags}")

    def enqueue_message(self, message: str, sender: "Client", target: str) -> None:
        self.logger.debug(f"<- <{target}> '{message}' ({sender})")

    def enqueue_message_object(self, message: Message) -> None:
        self.logger.debug(f"<- <{message.target}> '{message.content}' ({message.sender})")

    def enqueue_banchobot_message(self, message: str) -> None:
        self.enqueue_message(message, app.session.banchobot, "#osu")

    def enqueue_welcome(self) -> None:
        if self.is_osu:
            self.enqueue_banchobot_message("Welcome to osu!Bancho.")
            return

        self.enqueue_command(
            irc.RPL_WELCOME,
            params=[
                self.local_prefix,
                ":Welcome to osu!Bancho!"
            ]
        )

    def enqueue_motd(self, message: str) -> None:
        messages = message.splitlines()

        for index, line in enumerate(messages):
            self.enqueue_command(
                irc.RPL_MOTD,
                params=[self.local_prefix, ":" + line]
            )

        self.enqueue_command(
            irc.RPL_ENDOFMOTD,
            params=[self.local_prefix, ":End of /MOTD command."]
        )

    def enqueue_error(self, error: str) -> None:
        if self.is_osu:
            return self.enqueue_banchobot_message(error)

        self.enqueue_command("ERROR", params=[":" + error])

    def enqueue_announcement(self, message: str) -> None:
        if self.is_osu:
            return self.enqueue_banchobot_message(message)

        self.enqueue_command("NOTICE", params=[":" + message])

    def enqueue_server_restart(self, retry_in_ms: int) -> None:
        self.enqueue_announcement("Bancho is restarting, please wait...")

    def enqueue_channel(self, channel, autojoin = False):
        if not autojoin:
            return

        self.enqueue_channel_join_success(channel.name)

    def enqueue_players(self, players: Iterable[Client], channel: str = "#osu") -> None:
        self.enqueue_command(
            irc.RPL_NAMREPLY,
            params=[
                self.local_prefix, "=", channel,
                ":" + " ".join(self.resolve_username(player) for player in players)
            ]
        )
        self.enqueue_command(
            irc.RPL_ENDOFNAMES,
            params=[self.local_prefix, channel, ":End of /NAMES list."]
        )

    def enqueue_player(self, player: Client, channel: str = "#osu") -> None:
        self.enqueue_command(
            "JOIN",
            self.resolve_username(player),
            params=[f":{channel}"]
        )

    def enqueue_user_quit(self, quit: UserQuit) -> None:
        if quit != QuitState.Gone:
            return

        self.enqueue_command(
            "QUIT",
            self.resolve_username(quit.info),
            params=[":quit"]
        )

    def enqueue_channel_join_success(self, channel_name: str) -> None:
        if not (channel := app.session.channels.by_name(channel_name)):
            return

        self.enqueue_command(
            irc.RPL_TOPIC,
            params=[
                self.local_prefix, channel_name,
                ":" + channel.topic
            ]
        )
        self.enqueue_players(channel.users, channel.name)

    def enqueue_channel_revoked(self, channel: str):
        self.enqueue_command(irc.ERR_NOSUCHCHANNEL, params=[channel])

    def enqueue_mode(self, channel: Channel) -> None:
        self.enqueue_command(
            "MODE",
            params=[
                channel.name,
                channel.mode(self.permissions),
                self.local_prefix
            ]
        )

    def enqueue_infringement_length(self, duration_seconds: int) -> None:
        for channel in self.channels:
            self.enqueue_mode(channel)
