
from app.common.objects import bUserPresence, bUserStats

from ..b1700.writer import Writer as BaseWriter
from ..b1700.constants import Completeness

from typing import Optional

class Writer(BaseWriter):
    def write_presence(self, presence: bUserPresence, stats: Optional[bUserStats] = None):
        if stats.user_id <= 0:
            stats.user_id = -stats.user_id

        self.stream.s32(stats.user_id)
        self.stream.u8(Completeness.Full.value)
        self.write_status(stats.status)

        # Stats
        self.stream.s64(stats.rscore)
        self.stream.float(stats.accuracy)
        self.stream.s32(stats.playcount)
        self.stream.s64(stats.tscore)
        self.stream.s32(stats.rank)

        # Presence
        self.stream.string(presence.username)
        self.stream.string(f'{stats.user_id}') # Avatar Filename
        self.stream.u8(presence.timezone + 24)
        self.stream.string(presence.city)
        self.stream.u8(presence.permissions.value)
