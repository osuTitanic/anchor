
from bancho.streams import StreamIn

from .b20130606 import b20130606

class b20130329(b20130606):

    protocol_version = 17

    def handle_send_frames(self, stream: StreamIn):
        if self.player.restricted:
            return
        
        frames = stream.readall()
        extra = int(0).to_bytes(4, 'little')

        if self.player.spectating:
            extra = int(
                self.player.spectating.id
            ).to_bytes(4, 'little')

        for p in self.player.spectators:
            p.handler.enqueue_frames(
                extra + frames
                if p.handler.protocol_version >= 18 else
                frames
            )
