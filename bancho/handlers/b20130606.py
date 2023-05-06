
from bancho.constants import RequestPacket, ResponsePacket
from bancho.streams   import StreamIn, StreamOut

from . import BaseHandler

import bancho

class b20130606(BaseHandler):
    def login_reply(self, response: int):
        self.player.sendPacket(
            ResponsePacket.LOGIN_REPLY,
            int(response).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def send_message(self, sender, message: str, target_name: str):
        pass
