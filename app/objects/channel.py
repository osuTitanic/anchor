
from app.common.objects import bMessage, bChannel
from app.clients import DefaultResponsePacket
from app.common.constants import Permissions

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

        from .collections import Players

        self.users = Players()

    def __repr__(self) -> str:
        return f'<{self.name} - {self.topic}>'

    @property
    def display_name(self) -> str:
        """This is what will be shown to the client"""

        if self.name.startswith('#spec_'):
            return '#spectator'

        if self.name.startswith('#multi_'):
            return '#multiplayer'

        return self.name

    @property
    def user_count(self) -> int:
        return len(self.users)

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

    def update(self):
        if not self.public:
            for player in self.users:
                player.enqueue_channel(
                    self.bancho_channel,
                    autojoin=False
                )
            return

        for player in app.session.players:
            if self.can_read(player.permissions):
                player.enqueue_channel(
                    self.bancho_channel,
                    autojoin=False
                )

    def add(self, player, no_response: bool = False):
        # Update player's silence duration
        player.silenced

        if player in self.users and not player.is_tourney_client:
            # Player has already joined the channel
            if not no_response:
                player.join_success(self.display_name)
                return

        if not self.can_read(player.permissions):
            # Player does not have read access
            self.logger.warning(f'{player} tried to join channel but does not have read access.')
            player.revoke_channel(self.display_name)

        player.channels.add(self)
        self.users.append(player)
        self.update()

        if not no_response:
            player.join_success(self.display_name)

        self.logger.info(f'{player.name} joined')

    def remove(self, player) -> None:
        try:
            self.users.remove(player)
        except ValueError:
            pass

        if self in player.channels:
            player.channels.remove(self)

        self.update()

    def send_message(self, sender, message: str, ignore_privs=False, exclude_sender=True):
        if sender not in self.users and not sender.is_bot:
            # Player did not join this channel
            sender.revoke_channel(self.display_name)
            sender.logger.warning(
                f'Failed to send message: "{message}" on {self.name}, because player did not join the channel.'
            )
            return

        if self.moderated:
            allowed_permissions = [Permissions.Admin, Permissions.Friend]

            if not any([p in sender.permissions for p in allowed_permissions]):
                return

        if sender.silenced:
            sender.logger.warning(
                'Failed to send message: Sender was silenced'
            )
            return 

        if not self.can_write(sender.permissions) and not ignore_privs:
            sender.logger.warning(f'Failed to send message: "{message}".')
            return

        # Limit message size
        if len(message) > 512:
            message = message[:512] + '... (truncated)'

        self.logger.info(f'[{sender.name}]: {message}')

        if exclude_sender:
            # Filter out sender
            users = {user for user in self.users if user != sender}
        else:
            users = self.users

        for user in users:
            # Enqueue message to every user inside this channel
            user.enqueue_message(
                bMessage(
                    sender.name,
                    message,
                    self.display_name,
                    sender.id
                )
            )

            # Send to their tourney clients
            for client in app.session.players.get_all_tourney_clients(user.id):
                if client.address.port == user.address.port:
                    continue

                client.enqueue_message(
                    bMessage(
                        sender.name,
                        message,
                        self.display_name,
                        sender.id
                    )
                )
