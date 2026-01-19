
from chio import Message, Channel as bChannel, Permissions
from typing import TYPE_CHECKING, List, Set
from code import InteractiveConsole

if TYPE_CHECKING:
    from app.objects.multiplayer import Match
    from app.clients.osu import OsuClient
    from app.clients import Client

from app.common.config import config_instance as config
from app.common.database.repositories import messages
from app.objects.locks import LockedSet
from app.common.webhooks import Webhook
from app.clients.irc import IrcClient
from app.common import officer

import threading
import logging
import time
import app
import sys
import io

class Channel:
    def __init__(
        self,
        name: str,
        topic: str,
        owner: str,
        read_perms: int,
        write_perms: int,
        public: bool = True
    ) -> None:
        self.name = name
        self.owner = owner
        self.topic = topic

        self.read_perms = read_perms
        self.write_perms = write_perms
        self.moderated = False
        self.public = public

        self.logger = logging.getLogger(self.name)
        self.users: Set["Client"] = LockedSet()
        self.users.add(app.session.banchobot)
        self.created_at = time.time()
        self.webhook_lock = threading.Lock()
        self.webhook_enabled = (
            config.CHAT_WEBHOOK_URL and
            name in config.CHAT_WEBHOOK_CHANNELS
        )
        self.update_scheduled = False

    def __repr__(self) -> str:
        return f'<{self.name} - {self.topic}>'

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other) -> bool:
        return self.name == other.name

    @property
    def is_channel(self) -> bool:
        return True

    @property
    def user_count(self) -> int:
        return len(self.users)

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def osu_users(self) -> List["OsuClient"]:
        return [user for user in self.users if user.is_osu]

    @property
    def irc_users(self) -> List["IrcClient"]:
        return [user for user in self.users if user.is_irc]

    @property
    def user_ids(self) -> Set[int]:
        return {user.id for user in self.users}

    @property
    def bancho_channel(self) -> bChannel:
        return bChannel(
            self.display_name,
            self.topic,
            self.owner,
            self.user_count
        )

    def can_read(self, client: "Client") -> bool:
        return client.permissions.value >= self.read_perms

    def can_write(self, client: "Client") -> bool:
        return client.permissions.value >= self.write_perms

    def add(self, client: "Client", no_response: bool = False) -> None:
        # Update player's silence duration
        client.silenced

        if not self.can_read(client):
            # Player does not have read access
            self.logger.warning(f'{client} tried to join channel but does not have read access.')
            client.enqueue_channel_revoked(self.display_name)
            return

        if client in self.users and not client.is_tourney_client:
            # Player has already joined the channel
            if no_response:
                return

            client.enqueue_channel_join_success(self.display_name)
            return

        client.channels.add(self)
        self.users.add(client)
        self.logger.info(f'{client.name} joined')
        app.session.tasks.do_later(self.broadcast_join, client, priority=1)

        if not no_response:
            client.enqueue_channel_join_success(self.display_name)

    def remove(self, client: "Client") -> None:
        client.channels.discard(self)
        self.users.discard(client)
        self.logger.info(f'{client.name} left')
        app.session.tasks.do_later(self.broadcast_part, client, priority=1)

    def broadcast_message(self, message: Message, users: List["Client"]) -> None:
        self.logger.info(f'[{message.sender}]: {message.content}')

        if "\n" in message.content:
            return self.handle_multiline_broadcast(message, users)

        for user in users:
            user.enqueue_message_object(message)

    def handle_multiline_broadcast(self, message: Message, users: List["Client"]) -> None:
        message_objects = [
            Message(
                message.sender,
                line,
                message.target,
                message.sender_id
            )
            for line in message.content.splitlines()
        ]

        for user in users:
            for object in message_objects:
                user.enqueue_message_object(object)

    def broadcast_message_to_webhook(self, message: Message) -> None:
        if not self.webhook_enabled:
            return

        # Prevent @ mentions from being parsed as mentions
        message_content = message.content.replace('@', '@\u200b')

        # Replace \x01ACTION with username
        message_content = message_content.replace('\x01ACTION ', f'*{message.sender}')
        message_content = message_content.removesuffix('\x01')

        if not self.webhook_lock.acquire(timeout=2.5):
            self.logger.warning('Failed to acquire webhook lock. Continuing anyways...')

        try:
            webhook = Webhook(
                config.CHAT_WEBHOOK_URL,
                message_content,
                message.sender,
                f'http://a.{config.DOMAIN_NAME}/{message.sender_id}'
            )
            webhook.post()
        finally:
            self.webhook_lock.release()

    def broadcast_join(self, client: "Client") -> None:
        self.schedule_osu_update()
        self.update_irc_clients(client, is_leaving=False)

    def broadcast_part(self, client: "Client") -> None:
        self.schedule_osu_update()
        self.update_irc_clients(client, is_leaving=True)

    def send_message(
        self,
        sender: "Client",
        message: str,
        ignore_commands: bool = False,
        do_later: bool = True
    ) -> None:
        is_banchobot = (
            sender == app.session.banchobot
        )

        is_valid_message = self.validate_message(
            sender,
            message
        )

        if not is_valid_message and not is_banchobot:
            # Message validation failed
            return

        if message.startswith('!') and not ignore_commands:
            # A command was executed
            return app.session.tasks.do_later(
                app.session.banchobot.process_and_send_response,
                message, sender, self, priority=3
            )

        if len(message) > 512:
            # Limit message size to 512 characters
            message = message[:497] + '... (truncated)'

        # Apply chat filters to the message
        message, timeout = app.session.filters.apply(message)

        if timeout is not None and not is_banchobot:
            sender.silence(timeout, f'Inappropriate discussion in {self.name}')
            officer.call(f"Message: {message}")
            return

        app.session.tasks.do_later(
            messages.create,
            sender.name,
            self.name,
            message[:512],
            priority=4
        )

        message_object = Message(
            sender.name,
            message,
            self.display_name,
            sender.id
        )

        # Filter out sender from the target users
        users = [user for user in self.users if user != sender]

        if not do_later:
            self.broadcast_message(message_object, users)
            self.broadcast_message_to_webhook(message_object)
            return

        app.session.tasks.do_later(
            self.broadcast_message,
            message_object,
            users=users,
            priority=2
        )

        if not self.webhook_enabled:
            return

        app.session.tasks.do_later(
            self.broadcast_message_to_webhook,
            message_object,
            priority=5
        )

    def validate_message(
        self,
        sender: "Client",
        message: str
    ) -> bool:
        if sender not in self.users:
            # Try to add them to the channel, if
            # they are not already in it
            self.add(sender)

            if sender not in self.users:
                sender.logger.warning(
                    f'Failed to send message: "{message}" on {self.name}, '
                    'because player did not join the channel.'
                )
                return False

        if self.moderated:
            is_allowed = [
                sender.object.is_moderator,
                sender.object.is_bat
            ]

            if not any(is_allowed):
                return False

        if sender.silenced:
            sender.logger.warning('Failed to send message: Sender was silenced.')
            return False

        if not self.can_write(sender):
            sender.logger.warning(f'Failed to send message: "{message}".')
            return False

        if not sender.is_bot and not sender.message_limiter.allow():
            sender.silence(60, 'Chat spamming')
            return False

        return True

    def handle_external_message(
        self,
        message: str,
        sender: str,
        sender_id: int,
        submit_to_webhook: bool = False
    ) -> None:
        message_object = Message(
            sender,
            message,
            self.display_name,
            sender_id
        )

        app.session.tasks.do_later(
            self.broadcast_message,
            message_object,
            users=self.users,
            priority=2
        )

        if not self.webhook_enabled or not submit_to_webhook:
            return

        app.session.tasks.do_later(
            self.broadcast_message_to_webhook,
            message_object,
            priority=5
        )

    def update_osu_clients(self) -> None:
        if self.public:
            app.session.players.send_channel(self)
            return

        # Only enqueue to users in this channel
        for player in self.osu_users:
            player.enqueue_channel(
                self,
                autojoin=False
            )

    def update_irc_clients(self, client: "Client", is_leaving: bool = False) -> None:
        if client.is_tourney_client:
            # Do not broadcast tourney clients to irc users
            return

        if self.find_other_player(client) is not None:
            if not client.is_irc:
                return

            if is_leaving:
                # User is still active, announcing part would
                # make them disappear from IRC
                return

            # We still want to make sure the IRC client got the feedback
            # that they joined the channel
            return client.enqueue_player(client, self.name)

        enqueue_method = (
            IrcClient.enqueue_part if is_leaving else
            IrcClient.enqueue_player
        )

        for user in self.irc_users:
            enqueue_method(user, client, self.name)

    def schedule_osu_update(self) -> None:
        if not self.update_scheduled:
            self.update_scheduled = True
            on_done = lambda _: setattr(self, 'update_scheduled', False)

            # Throttle channel updates to once every 8 seconds
            task = app.session.tasks.schedule_do_later(self.update_osu_clients, priority=2, delay=8)
            task.addBoth(on_done)

    def find_other_player(self, client: "Client") -> "Client | None":
        return next(
            (p for p in self.users if p.id == client.id and p != client),
            None
        )

class SpectatorChannel(Channel):
    def __init__(self, player: "OsuClient") -> None:
        super().__init__(
            name=f'#spec_{player.id}',
            topic=f"{player.name}'s spectator channel",
            owner=player.name,
            read_perms=1,
            write_perms=1,
            public=False
        )
        self.player = player

    @property
    def display_name(self) -> str:
        return '#spectator'

    def can_read(self, client: "Client") -> bool:
        if Permissions.Peppy in client.permissions:
            return True

        if client.id == self.player.id:
            return True

        if client.is_irc:
            return False

        if not super().can_read(client):
            return False

        return client.spectating == self.player

    def can_write(self, client: "Client") -> bool:
        if Permissions.Peppy in client.permissions:
            return True

        if client.id == self.player.id:
            return True

        if client.is_irc:
            return False

        if not super().can_write(client):
            return False

        return client.spectating == self.player

    def update_osu_clients(self) -> None:
        # NOTE: So apparently this would cause the client
        #       to always open #spectator chat, which is
        #       really annoying, so I'm disabling it for now.
        #       This has the side-effect of the user count
        #       not being updated on the client side.
        return None

class MultiplayerChannel(Channel):
    def __init__(self, match: "Match") -> None:
        super().__init__(
            name=f'#multi_{match.id}',
            topic=match.name,
            owner=match.host.name,
            read_perms=1,
            write_perms=1,
            public=False
        )
        self.match = match

    @property
    def display_name(self) -> str:
        return '#multiplayer'

    def resolve_name(self, player: "Client") -> str:
        return self.name if player.id in self.match.referee_players else self.display_name

    def can_read(self, client: "Client") -> bool:
        if not super().can_read(client):
            return False

        if Permissions.Peppy in client.permissions:
            return True

        if self.match.persistent and client.is_tourney_client:
            return True

        if client.id in self.match.referee_players:
            return True

        return client in self.match.players

    def can_write(self, client: "Client") -> bool:
        if not super().can_write(client):
            return False

        if Permissions.Peppy in client.permissions:
            return True

        if client.id in self.match.referee_players:
            return True

        return client in self.match.players

    def add(self, player: "Client", no_response: bool = False) -> None:
        # Update player's silence duration
        player.silenced

        if not self.can_read(player):
            # Player does not have read access
            self.logger.warning(f'{player} tried to join channel but does not have read access.')
            player.enqueue_channel_revoked(self.resolve_name(player))
            return

        if player in self.users and not player.is_tourney_client:
            # Player has already joined the channel
            if no_response:
                return

            player.enqueue_channel_join_success(self.resolve_name(player))
            return

        player.channels.add(self)
        self.users.add(player)
        self.broadcast_join(player)

        if not no_response:
            player.enqueue_channel_join_success(self.resolve_name(player))

        self.logger.info(f'{player.name} joined')

    def broadcast_join(self, player: "Client") -> None:
        self.update_osu_clients()

        for user in self.irc_users:
            user.enqueue_player(player, self.name)

    def broadcast_part(self, player: "Client") -> None:
        self.update_osu_clients()

        other_player = next(
            (p for p in self.users if p.id == player.id),
            None
        )

        # If another player is still in the channel,
        # do not broadcast part to irc users
        if other_player is not None:
            return

        for user in self.irc_users:
            user.enqueue_part(player, self.name)

    def update_osu_clients(self) -> None:
        channel_object = self.bancho_channel

        # Only enqueue to users in this channel
        for player in self.users:
            channel_object.name = self.resolve_name(player)
            player.enqueue_channel(channel_object)

    def broadcast_message(self, message: Message, users: List["Client"]) -> None:
        self.logger.info(f'[{message.sender}]: {message.content}')

        for user in users:
            message.target = self.resolve_name(user)
            user.enqueue_message_object(message)

class PythonInterpreterChannel(Channel):
    def __init__(self):
        super().__init__(
            "#python",
            "Debugging python interpreter channel",
            "BanchoBot",
            read_perms=Permissions.Peppy,
            write_perms=Permissions.Peppy
        )
        self.console = InteractiveConsole()
        assert config.DEBUG
        
    def broadcast_join(self, client: "Client") -> None:
        super().broadcast_join(client)

        # Send "Python 3.X.X (default, YYYY-MM-DD, HH:MM:SS) [GCC X.X.X]" message
        python_version = sys.version.splitlines()
        platform_info = sys.platform

        client.enqueue_message(
            f"Python {python_version[0]} on {platform_info}",
            app.session.banchobot,
            self.display_name,
        )
        client.enqueue_message(
            'Type "help", "copyright", "credits" or "license" for more information.',
            app.session.banchobot,
            self.display_name
        )

    def send_message(
        self,
        sender: "Client",
        message: str
    ) -> None:
        if not sender.object.is_admin:
            sender.enqueue_channel_revoked(self.display_name)
            return

        stdout = io.StringIO()
        stderr = io.StringIO()

        # Save original stdout/stderr
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = stdout, stderr

        try:
            self.console.push(message)
        except Exception as e:
            stderr.write(f'{e.__class__.__name__}: {e}\n')
        finally:
            # Restore original stdout/stderr
            sys.stdout, sys.stderr = old_stdout, old_stderr

        output = stdout.getvalue() + stderr.getvalue()
        output = output.strip()
        
        if not output:
            return

        for line in output.splitlines():
            return_message = Message(
                app.session.banchobot.name,
                line,
                self.display_name,
                sender.id
            )

            self.broadcast_message(
                return_message,
                self.users
            )
