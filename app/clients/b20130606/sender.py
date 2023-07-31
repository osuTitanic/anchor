
from app.clients.sender import BaseSender
from app.common.streams import StreamOut

from .constants import ResponsePacket

class PacketSender(BaseSender):
    def send_login_reply(self, reply: int):
        self.player.sendPacket(
            ResponsePacket.LOGIN_REPLY,
            int(reply).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def send_protocol_version(self, version: int):
        self.player.sendPacket(
            ResponsePacket.PROTOCOL_VERSION,
            int(version).to_bytes(
                length=4,
                byteorder='little'
            )
        )
