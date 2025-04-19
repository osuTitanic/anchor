
from chio import Message, Channel as bChannel
from typing import TYPE_CHECKING, List, Set

if TYPE_CHECKING:
    from app.objects.multiplayer import Match
    from app.clients import Client

from app.common.database.repositories import messages
from app.common.constants.strings import BAD_WORDS
from app.common.constants import Permissions
from app.objects.locks import LockedSet
from app.common import officer

import logging
import app

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
        self.users: LockedSet["Client"] = LockedSet()

    def __repr__(self) -> str:
        return f'<{self.name} - {self.topic}>'

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other) -> bool:
        return self.name == other.name

    @property
    def user_count(self) -> int:
        return len(self.users)

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def bancho_channel(self) -> bChannel:
        return bChannel(
            self.display_name,
            self.topic,
            self.owner,
            self.user_count
        )

    def can_read(self, perms: Permissions):
        return perms.value >= self.read_perms

    def can_write(self, perms: Permissions):
        return perms.value >= self.write_perms

    def add(self, player: "Client", no_response: bool = False) -> None:
        # Update player's silence duration
        player.silenced

        if not self.can_read(player.permissions):
            # Player does not have read access
            self.logger.warning(f'{player} tried to join channel but does not have read access.')
            player.enqueue_channel_revoked(self.display_name)

        if player in self.users and not player.is_tourney_client:
            # Player has already joined the channel
            if no_response:
                return

            player.enqueue_channel_join_success(self.display_name)
            return

        player.channels.add(self)
        self.users.add(player)
        self.update()

        if not no_response:
            player.enqueue_channel_join_success(self.display_name)

        self.logger.info(f'{player.name} joined')

    def remove(self, player: "Client") -> None:
        self.users.remove(player)
        self.update()

        if self in player.channels:
            player.channels.remove(self)

    def update(self) -> None:
        if not self.public:
            # Only enqueue to users in this channel
            for player in self.users:
                player.enqueue_channel(
                    self,
                    autojoin=False
                )
            return

        for player in app.session.players:
            if self.can_read(player.permissions):
                player.enqueue_channel(
                    self,
                    autojoin=False
                )

    def broadcast_message(self, message: Message, users: List["Client"]) -> None:
        self.logger.info(f'[{message.sender}]: {message.content}')

        for user in users:
            user.enqueue_message_object(message)

    def send_message(
        self,
        sender: "Client",
        message: str,
        ignore_privileges=False,
        ignore_commands=False
    ) -> None:
        if sender not in self.users and not sender.is_bot:
            # Player did not join this channel
            sender.enqueue_channel_revoked(self.display_name)
            sender.logger.warning(
                f'Failed to send message: "{message}" on {self.name}, '
                'because player did not join the channel.'
            )
            return

        if self.moderated and sender != app.session.banchobot:
            allowed_groups = [
                'Admins',
                'Developers',
                'Beatmap Approval Team',
                'Global Moderator Team',
                'Tournament Manager Team'
            ]

            if not any([group in sender.groups for group in allowed_groups]):
                return

        if sender.silenced:
            sender.logger.warning('Failed to send message: Sender was silenced.')
            return

        if not self.can_write(sender.permissions) and not ignore_privileges:
            sender.logger.warning(f'Failed to send message: "{message}".')
            return

        if message.startswith('!') and not ignore_commands:
            # A command was executed
            return app.session.banchobot.send_command_response(
                *app.session.banchobot.process_command(message, sender, self)
            )

        has_bad_words = any([
            word in message.lower()
            for word in BAD_WORDS
        ])

        if has_bad_words and not sender.is_bot:
            sender.silence(
                duration_sec=60 * 10,
                reason='Auto-silenced for using bad words in chat.'
            )
            officer.call(f'Message: {message}')
            return

        # Limit message size to 512 characters
        if len(message) > 512:
            message = message[:497] + '... (truncated)'

        # Filter out sender
        users = {user for user in self.users if user != sender}

        self.broadcast_message(
            Message(
                sender.name,
                message,
                self.display_name,
                sender.id
            ),
            users=users
        )

        messages.create(
            sender.name,
            self.name,
            message[:512]
        )

    def handle_external_message(
        self,
        message: str,
        sender: str,
        sender_id: int
    ) -> None:
        self.broadcast_message(
            Message(
                sender,
                message,
                self.display_name,
                sender_id
            ),
            users=self.users
        )

class SpectatorChannel(Channel):
    def __init__(self, player: "Client") -> None:
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

    def add(self, player: "Client", no_response: bool = False) -> None:
        # Update player's silence duration
        player.silenced

        if not self.can_read(player.permissions):
            # Player does not have read access
            self.logger.warning(f'{player} tried to join channel but does not have read access.')
            player.enqueue_channel_revoked(self.resolve_name(player))

        if player in self.users and not player.is_tourney_client:
            # Player has already joined the channel
            if no_response:
                return

            player.enqueue_channel_join_success(self.resolve_name(player))
            return

        player.channels.add(self)
        self.users.add(player)
        self.update()

        if not no_response:
            player.enqueue_channel_join_success(self.resolve_name(player))

        self.logger.info(f'{player.name} joined')

    def update(self) -> None:
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
