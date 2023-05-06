
from bancho.common.objects import DBChannel
from bancho.constants import Permissions

import bancho

class Channel:
    def __init__(self, name: str, topic: str, read_perms: int, write_perms: int, public = True) -> None:
        self.name = name
        self.topic = topic

        self.read_perms = read_perms
        self.write_perms = write_perms

        self.public = public

        from .collections import Players

        self.users = Players()

    def __repr__(self) -> str:
        return f'[{self.name}]'

    @property
    def display_name(self):
        if self.name.startswith('#spec_'):
            return '#spectator'
        
        if self.name.startswith('#multi_'):
            return '#multiplayer'
        
        return self.name

    @property
    def user_count(self):
        return len(self.users)

    @classmethod
    def from_db(cls, channel: DBChannel):
        return Channel(
            channel.name,
            channel.topic,
            channel.read_permissions,
            channel.write_permissions,
            public=True
        )
    
    def can_read(self, perms: int):
        return perms > self.read_perms
    
    def can_write(self, perms: int):
        return perms >= self.write_perms
    
    def update(self):
        if self.public:
            bancho.services.players.enqueue_channel(self)
        else:
            self.users.enqueue_channel(self)
    
    def add(self, player) -> bool:
        if (
            not player.spectators
            and not player.spectating
            and self.name.startswith('#spec')
           ):
            # If player wants to join his spectator channel, but no one is spectating him
            return False
        
        if player in self.users:
            # Player has already joined the channel
            return True
        
        if self.can_read(Permissions.pack(player.permissions)):
            self.users.append(player)

            self.update()

            return True
        
        return False
    
    def remove(self, player) -> None:
        try:
            self.users.remove(player)
        except ValueError:
            pass

        self.update()
    
    def send_message(self, sender, message: str, ignore_privs=False):
        if (self.can_write(Permissions.pack(sender.permissions)) and not sender.silenced) or not ignore_privs:
            # Message can only be 128 characters long
            # because of the uleb128 size limit
            if len(message) > 127:
                message = message[:124] + '...'

            # TODO: DB Logs
            bancho.services.logger.info(f'{sender.name} {self}: {message}')

            # Filter out sender
            users = {user for user in self.users if user != sender}

            for user in users:
                user.handler.send_message(sender, message, self.display_name)
        else:
            sender.logger.warning(f'Failed to send message: "{message}".')
