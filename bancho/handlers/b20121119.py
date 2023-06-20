
from .b20121223 import b20121223

from ..streams import StreamOut
from ..constants import (
    AvatarExtension,
    ResponsePacket,
    PresenceFilter,
    Permissions
)

class b20121119(b20121223):
    
    protocol_version = 11

    def enqueue_presence(self, player):
        if self.player.filter == PresenceFilter.NoPlayers:
            return

        if self.player.filter == PresenceFilter.Friends:
            if player.id not in self.player.friends:
                return

        utc = (
            player.client.ip.utc_offset
            if player.client.ip.utc_offset
            else player.client.utc_offset
        )

        stream = StreamOut()

        stream.s32(player.id)
        stream.string(player.name)
        stream.u8(AvatarExtension.NONE.value) # TODO
        stream.u8(utc + 24)
        stream.u8(player.client.ip.country_num)
        stream.string(player.client.ip.city if player.client.display_city else '')
        stream.u8(Permissions.pack(player.permissions))
        stream.float(player.client.ip.longitude)
        stream.float(player.client.ip.latitude)
        stream.s32(player.current_stats.rank)
        stream.u8(player.status.mode.value)

        self.player.sendPacket(
            ResponsePacket.USER_PRESENCE,
            stream.get()
        )
