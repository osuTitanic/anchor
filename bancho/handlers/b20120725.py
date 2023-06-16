
from bancho.constants import ResponsePacket
from bancho.streams import StreamOut

from .b20120812 import b20120812

class b20120725(b20120812):

    protocol_version = 8

    def enqueue_channel(self, channel):
        stream = StreamOut()
        stream.string(channel.display_name)

        self.player.sendPacket(
            ResponsePacket.CHANNEL_AVAILABLE,
            stream.get()
        )
