
from bancho.constants import PresenceFilter, ResponsePacket
from bancho.streams import StreamOut

from .b20120725 import b20120725

class b20120704(b20120725):

    protocol_version = 7

    def enqueue_stats(self, player, force=False):
        if not player:
            return

        if not force:
            if self.player.filter == PresenceFilter.NoPlayers:
                return

            if self.player.filter == PresenceFilter.Friends:
                if player.id not in self.player.friends:
                    return

        stream = StreamOut()

        stream.s32(player.id)

        # Status
        stream.u8(player.status.action.value)
        stream.string(player.status.text)
        stream.string(player.status.checksum)
        stream.u16(sum([mod.value for mod in player.status.mods]))
        stream.s8(player.status.mode.value)
        stream.s32(player.status.beatmap)

        # Stats
        stream.s64(player.current_stats.rscore)
        stream.float(player.current_stats.acc)
        stream.s32(player.current_stats.playcount)
        stream.s64(player.current_stats.tscore)
        stream.s32(player.current_stats.rank)

        self.player.sendPacket(
            ResponsePacket.USER_STATS,
            stream.get()
        )
