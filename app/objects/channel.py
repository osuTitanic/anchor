
from chio import Message, Channel as bChannel, Permissions
from typing import TYPE_CHECKING, List, Set

if TYPE_CHECKING:
    from app.objects.multiplayer import Match
    from app.clients.osu import OsuClient
    from app.clients.irc import IrcClient
    from app.clients import Client

from app.common.database.repositories import messages
from app.common.constants.strings import BAD_WORDS
from app.objects.locks import LockedSet
from app.common import officer

import logging
import time
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
        self.users.add(app.session.banchobot)
        self.created_at = time.time()

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
    def irc_users(self) -> List["IrcClient"]:
        return [user for user in self.users if user.is_irc]

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

    def mode(self, client: "Client") -> str:
        if client.silenced:
            return '-v'

        if Permissions.Peppy in client.permissions:
            return '+a'

        if Permissions.Friend in client.permissions:
            return '+o'

        if Permissions.BAT in client.permissions:
            return '+h'

        return '+v'

    def add(self, player: "Client", no_response: bool = False) -> None:
        # Update player's silence duration
        player.silenced

        if not self.can_read(player):
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
        self.logger.info(f'{player.name} joined')
        self.broadcast_join(player)

        if not no_response:
            player.enqueue_channel_join_success(self.display_name)

    def remove(self, player: "Client") -> None:
        self.users.remove(player)
        self.logger.info(f'{player.name} left')
        self.broadcast_part(player)

        if self in player.channels:
            player.channels.remove(self)

    def broadcast_message(self, message: Message, users: List["Client"]) -> None:
        self.logger.info(f'[{message.sender}]: {message.content}')

        for user in users:
            user.enqueue_message_object(message)

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

    def broadcast_join(self, player: "Client") -> None:
        self.update_osu_clients()

        if self.name == "#osu":
            return

        for user in self.irc_users:
            user.enqueue_player(player, self.name)

    def update_osu_clients(self) -> None:
        if not self.public:
            # Only enqueue to users in this channel
            for player in self.users:
                player.enqueue_channel(
                    self,
                    autojoin=False
                )
            return

        for player in app.session.players:
            if self.can_read(player):
                player.enqueue_channel(
                    self,
                    autojoin=False
                )

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
                message, sender, self, priority=1
            )

        if len(message) > 512:
            # Limit message size to 512 characters
            message = message[:497] + '... (truncated)'

        # Filter out sender
        users = [user for user in self.users if user != sender]

        app.session.tasks.do_later(
            messages.create,
            sender.name,
            self.name,
            message[:512],
            priority=2
        )

        message_object = Message(
            sender.name,
            message,
            self.display_name,
            sender.id
        )

        if not do_later:
            self.broadcast_message(message_object, users)
            return

        app.session.tasks.do_later(
            self.broadcast_message,
            message_object,
            users=users,
            priority=1
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
            allowed_groups = [
                'Admins',
                'Developers',
                'Beatmap Approval Team',
                'Global Moderator Team',
                'Tournament Manager Team'
            ]

            if not any([group in sender.groups for group in allowed_groups]):
                return False

        if sender.silenced:
            sender.logger.warning('Failed to send message: Sender was silenced.')
            return False

        if not self.can_write(sender):
            sender.logger.warning(f'Failed to send message: "{message}".')
            return False

        has_bad_words = any([
            word in message.lower()
            for word in BAD_WORDS
        ])

        if has_bad_words and not sender.is_bot:
            sender.silence(60 * 5, "Auto-silenced for using bad words in chat.")
            officer.call(f'Message: {message}')
            return False

        if not sender.is_bot and not sender.message_limiter.allow():
            sender.silence(60, 'Chat spamming')
            return False

        return True

    def handle_external_message(
        self,
        message: str,
        sender: str,
        sender_id: int
    ) -> None:
        app.session.tasks.do_later(
            self.broadcast_message,
            Message(
                sender,
                message,
                self.display_name,
                sender_id
            ),
            users=self.users,
            priority=1
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
        if not super().can_read(client):
            return False

        if Permissions.Peppy in client.permissions:
            return True

        if client.id == self.player.id:
            return True

        if client.is_irc:
            return False

        return client.spectating == self.player

    def can_write(self, client: "Client") -> bool:
        if not super().can_write(client):
            return False

        if Permissions.Peppy in client.permissions:
            return True
        
        if client.id == self.player.id:
            return True

        if client.is_irc:
            return False

        return client.spectating == self.player

    def add(self, player: "OsuClient", no_response: bool = False) -> None:
        if player != self.player:
            return super().add(player, no_response)

        if not player.spectators:
            # Player does not have any spectators -> revoke channel
            return player.enqueue_channel_revoked(self.display_name)

        return super().add(player, no_response)

    def update_osu_clients(self) -> None:
        for player in app.session.players:
            if self.can_read(player):
                player.enqueue_channel(
                    self.bancho_channel,
                    autojoin=False
                )

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
