
from bancho.constants import RequestPacket, ResponsePacket, Permissions
from bancho.streams   import StreamIn, StreamOut

from . import BaseHandler

import bancho

class b20130606(BaseHandler):
    def enqueue_ping(self):
        self.player.sendPacket(ResponsePacket.PING)

    def enqueue_login_reply(self, response: int):
        self.player.sendPacket(
            ResponsePacket.LOGIN_REPLY,
            int(response).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def enqueue_announce(self, message: str):
        stream = StreamOut()
        stream.string(message)

        self.player.sendPacket(
            ResponsePacket.ANNOUNCE,
            stream.get()
        )

    def enqueue_privileges(self):
        self.player.sendPacket(
            ResponsePacket.LOGIN_PERMISSIONS,
            int(
                Permissions.pack(self.player.permissions)
            ).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def enqueue_message(self, sender, message: str, target_name: str):
        stream = StreamOut()

        stream.string(sender.name)
        stream.string(message)
        stream.string(target_name)
        stream.s32(sender.id)

        self.player.sendPacket(
            ResponsePacket.SEND_MESSAGE,
            stream.get()
        )

    def enqueue_channel(self, channel):
        stream = StreamOut()

        stream.string(channel.display_name)
        stream.string(channel.topic)
        stream.u16(channel.user_count)

        self.player.sendPacket(
            ResponsePacket.CHANNEL_AVAILABLE,
            stream.get()
        )

    def enqueue_channel_info_end(self):
        self.player.sendPacket(
            ResponsePacket.CHANNEL_INFO_COMPLETE
        )

    def enqueue_silence_info(self, remaining_silence: int):
        self.player.sendPacket(
            ResponsePacket.SILENCE_INFO,
            int(remaining_silence).to_bytes(
                length=4,
                byteorder='little',
                signed=True
            )
        )

    def enqueue_friends(self):
        stream = StreamOut()
        stream.intlist(self.player.friends)

        self.player.sendPacket(
            ResponsePacket.FRIENDS_LIST,
            stream.get()
        )

    def enqueue_presence(self, player):
        stream = StreamOut()

        stream.s32(player.id)
        stream.string(player.name)
        stream.u8(player.client.utc_offset + 24)
        stream.u8(player.client.ip.country_num)
        stream.u8((Permissions.pack(player.permissions) | (player.status.mode.value << 5)))
        stream.float(player.client.ip.longitude)
        stream.float(player.client.ip.latitude)
        stream.u32(player.current_stats.rank)

        self.player.sendPacket(
            ResponsePacket.USER_PRESENCE,
            stream.get()
        )

    def enqueue_stats(self, player):
        stream = StreamOut()

        stream.s32(player.id)
        stream.status(player)
        stream.u64(player.current_stats.rscore)
        stream.float(player.current_stats.acc)
        stream.u32(player.current_stats.playcount)
        stream.u64(player.current_stats.tscore)
        stream.u32(player.current_stats.rank)
        stream.u16(round(player.current_stats.pp))

        self.player.sendPacket(
            ResponsePacket.USER_STATS,
            stream.get()
        )
