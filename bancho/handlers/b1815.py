
from .b20120704 import b20120704

class b1815(b20120704):

    protocol_version = 7

    def enqueue_channel(self, channel):
        super().enqueue_channel(channel)

        if channel.name == '#osu':
            # Client will not send a join request in older clients
            self.join_channel('#osu')
