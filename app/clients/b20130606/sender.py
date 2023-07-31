
from app.common.objects import UserPresence, UserQuit, UserStats
from app.clients.sender import BaseSender
from app.common.streams import StreamOut

from .constants import ResponsePacket
from .writer import Writer

from typing import List, Optional

class PacketSender(BaseSender):

    protocol_version = 18
    packets = ResponsePacket
    writer = Writer

    def send_login_reply(self, reply: int):
        self.player.send_packet(
            self.packets.LOGIN_REPLY,
            int(reply).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def send_protocol_version(self, version: int):
        self.player.send_packet(
            self.packets.PROTOCOL_VERSION,
            int(version).to_bytes(
                length=4,
                byteorder='little'
            )
        )

    def send_ping(self):
        self.player.send_packet(self.packets.PING)

    def send_announcement(self, message: str):
        stream = StreamOut()
        stream.string(message)

        self.player.send_packet(
            self.packets.ANNOUNCE,
            stream.get()
        )

    def send_menu_icon(self, image: Optional[str], url: Optional[str]):
        stream = StreamOut()
        stream.string(
            '|'.join([
                f'{image if image else ""}',
                f'{url if url else ""}'
            ])
        )

        self.player.send_packet(
            self.packets.ANNOUNCE,
            stream.get()
        )
