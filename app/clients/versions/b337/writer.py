
from ..b399 import Writer as BaseWriter

from app.common.constants import ClientStatus
from app.common.objects import (
    bStatusUpdate,
    bUserPresence,
    bUserQuit,
    bUserStats
)

class Writer(BaseWriter):
    def write_presence(self, presence: bUserPresence, stats: bUserStats):
        if stats.user_id <= 0:
            stats.user_id = -stats.user_id

        self.stream.s32(stats.user_id)
        self.stream.bool(True) # "newstats"
        self.stream.string(presence.username)

        # Stats
        self.stream.s64(stats.rscore)
        self.stream.float(stats.accuracy)
        self.stream.s32(stats.playcount)
        self.stream.s64(stats.tscore)
        self.stream.s32(stats.rank)

        # Presence
        self.stream.string(f'{stats.user_id}_000.png') # Avatar Filename
        self.stream.u8(presence.timezone + 24)
        self.stream.string(presence.city)

        self.write_status(stats.status, update=True)

    def write_stats(self, stats: bUserStats):
        if stats.user_id <= 0:
            stats.user_id = -stats.user_id

        self.stream.s32(stats.user_id)
        self.stream.bool(False) # "newstats"

        self.write_status(stats.status)

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

    def write_quit(self, state: bUserQuit):
        # The client expects a bUserStats type, so we just fill in random data
        self.stream.s32(state.user_id)
        self.stream.bool(False)
        self.write_status(state.stats.status)
