
from ..b323 import Writer as BaseWriter

from app.common.constants import ClientStatus
from app.common.objects import (
    bStatusUpdate,
    bUserPresence,
    bUserQuit,
    bUserStats,
    bMessage
)

class Writer(BaseWriter):
    def write_presence(self, presence: bUserPresence, stats: bUserStats, update: bool = False):
        self.stream.u32(presence.user_id)
        self.stream.string(presence.username)

        self.stream.s64(stats.rscore)
        self.stream.double(stats.accuracy)
        self.stream.s32(stats.playcount)
        self.stream.s64(stats.tscore)
        self.stream.s32(stats.rank)

        self.stream.string(f'{stats.user_id}_000.png') # Avatar Filename
        self.write_status(stats.status, update)
        self.stream.u8(presence.timezone + 24)
        self.stream.string(presence.city)

    def write_status(self, status: bStatusUpdate, update: bool = False):
        if update:
            # Set to "StatusUpdate"
            status.action = ClientStatus.Paused
        elif status.action > 9:
            # Workaround because of different enum values
            status.action = ClientStatus(status.action - 1)

        self.stream.u8(status.action.value)
        self.stream.string(status.text)
        self.stream.string(status.beatmap_checksum)
        self.stream.u16(status.mods.value)

    def write_message(self, msg: bMessage):
        if msg.is_private:
            self.stream.string(msg.target)
        else:
            self.stream.string(msg.sender)

        self.stream.string(msg.content)
        self.stream.bool(msg.is_private)

    def write_quit(self, state: bUserQuit):
        self.write_presence(
            state.presence,
            state.stats
        )
