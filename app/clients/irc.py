
from app.common.database import users, groups, stats, logins
from app.common.cache import usercount, status
from app.common.constants import strings
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

    def close_connection(self, reason: Any = None) -> None:
        if not self.logged_in:
            return

        if reason is not None:
            self.logger.info(f'Closing connection -> <{self.address}> ({reason})')

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

    def send_welcome_sequence(self) -> None:
        self.enqueue_welcome()
        self.enqueue_motd(strings.ANCHOR_ASCII_ART)

    def send_token_error(self) -> None:
        if self.is_osu:
            self.enqueue_banchobot_message("The token you entered was invalid. Please try again!")
            self.close_connection("Login failure")
            return

        self.enqueue_motd("Welcome to osu!Bancho.")
        self.enqueue_motd("-")
        self.enqueue_motd("- You are required to authenticate before accessing this service.")
        self.enqueue_motd("- Please click the following link to receive your password:")
        self.enqueue_motd(f"- https://osu.{config.DOMAIN_NAME}/account/settings/security")
        self.enqueue_motd("-")
        self.enqueue_command(irc.ERR_PASSWDMISMATCH, params=[":Bad authentication token."])

    def send_restricted_error(self) -> None:
        self.enqueue_command(
            irc.ERR_BANNEDFROMCHAN,
            params=[":You are banned from this server."]
        )

    def send_inactive_error(self) -> None:
        self.enqueue_command(
            irc.ERR_NOTREGISTERED,
            params=[":Your account has not been activated."]
        )

    def send_maintenance_error(self) -> None:
        self.enqueue_error("osu!Bancho is currently in maintenance mode.")

    def send_server_error(self) -> None:
        self.enqueue_error("A server-side error occurred.")

    def enqueue_line(self, line: str) -> None:
        self.logger.debug(f"-> {line}")

    def enqueue_command(self, command: str, prefix: str = f"cho.{config.DOMAIN_NAME}", params: List[str] = [], tags: dict = {}) -> None:
        self.logger.debug(f"<- <{command}> {prefix} ({', '.join(params)}) {tags}")

    def enqueue_message(self, message: str, sender: "Client", target: str) -> None:
        self.logger.debug(f"<- <{target}> '{message}' ({sender})")

    def enqueue_message_object(self, message: Message) -> None:
        self.logger.debug(f"<- <{message.target}> '{message.content}' ({message.sender})")

    def enqueue_banchobot_message(self, message: str) -> None:
        self.enqueue_message(message, app.session.banchobot, app.session.banchobot.name)

    def enqueue_welcome(self) -> None:
        self.enqueue_command(
            irc.RPL_WELCOME,
            params=[
                self.underscored_name,
                ":Welcome to osu!Bancho!"
            ]
        )

    def enqueue_motd(self, message: str) -> None:
        messages = message.splitlines()

        for index, line in enumerate(messages):
            self.enqueue_command(
                irc.RPL_MOTD,
                params=[self.underscored_name, ":" + line]
            )

        self.enqueue_command(
            irc.RPL_ENDOFMOTD,
            params=[self.underscored_name, ":End of /MOTD command."]
        )

    def enqueue_error(self, error: str) -> None:
        self.enqueue_command("ERROR", params=[":" + error])

    def enqueue_announcement(self, message: str) -> None:
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
                self.underscored_name, "=", channel,
                ":" + " ".join(player.name for player in players)
            ]
        )
        self.enqueue_command(
            irc.RPL_ENDOFNAMES,
            params=[self.underscored_name, channel, ":End of /NAMES list."]
        )

    def enqueue_player(self, player: Client, channel: str = "#osu") -> None:
        self.enqueue_command(
            "JOIN",
            player.irc_prefix,
            params=[f":{channel}"]
        )

    def enqueue_user_quit(self, quit: UserQuit) -> None:
        if quit != QuitState.Gone:
            return

        self.enqueue_command(
            "QUIT",
            quit.info.irc_prefix,
            params=[
                ":quit"
            ]
        )

    def enqueue_channel_join_success(self, channel_name: str) -> None:
        if not (channel := app.session.channels.by_name(channel_name)):
            return

        self.enqueue_command(
            irc.RPL_TOPIC,
            params=[
                self.underscored_name, channel_name,
                ":" + channel.topic
            ]
        )
        self.enqueue_command(
            "MODE",
            params=[
                channel_name,
                channel.mode(self.permissions),
                self.underscored_name
            ]
        )
        self.enqueue_players(channel.users, channel.name)

    def enqueue_channel_revoked(self, channel: str):
        self.enqueue_command(irc.ERR_NOTONCHANNEL, params=[channel])
