
from app.clients.sender import BaseSender
from app.common.streams import StreamOut

from .constants import ResponsePacket

class PacketSender(BaseSender):

    protocol_version = 18

    def send_login_reply(self, reply: int):
        self.player.send_packet(
            ResponsePacket.LOGIN_REPLY,
            int(reply).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def send_protocol_version(self, version: int):
        self.player.send_packet(
            ResponsePacket.PROTOCOL_VERSION,
            int(version).to_bytes(
                length=4,
                byteorder='little'
            )
        )

    def send_ping(self):
        self.player.send_packet(ResponsePacket.PING)

    def send_announcement(self, message: str):
        stream = StreamOut()
        stream.string(message)

        self.player.send_packet(
            ResponsePacket.ANNOUNCE,
            stream.get()
        )
