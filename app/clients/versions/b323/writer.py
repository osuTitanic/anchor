
from app.common.objects import (
    bScoreFrame,
    bMatch
)

from typing import List

from ..b337 import Writer as BaseWriter

class Writer(BaseWriter):
    def write_match(self, match: bMatch):
        self.stream.u8(match.id)
        self.stream.bool(match.in_progress)
        self.stream.u8(match.type.value)

        self.stream.string(match.name)
        self.stream.string(match.beatmap_text)
        self.stream.s32(match.beatmap_id)
        self.stream.string(match.beatmap_checksum)

        self.write_booleans([slot.is_open for slot in match.slots])
        self.write_booleans([slot.has_player for slot in match.slots])
        self.write_booleans([slot.is_ready for slot in match.slots])

        [self.stream.s32(slot.player_id) for slot in match.slots if slot.has_player]

    def write_booleans(self, bools: List[bool]):
        byte = 0
        for index in range(len(bools)-1, -1, -1):
            if bools[index]:
                byte |= 1
            if index > 0:
                byte = byte << 1
        self.stream.u8(byte)

    def write_scoreframe(self, frame: bScoreFrame):
        self.stream.string(frame.checksum)
        self.stream.s32(frame.time)
        self.stream.u8(frame.id)
        self.stream.u16(frame.c300)
        self.stream.u16(frame.c100)
        self.stream.u16(frame.c50)
        self.stream.u16(frame.cGeki)
        self.stream.u16(frame.cKatu)
        self.stream.u16(frame.cMiss)
        self.stream.s32(frame.total_score)
        self.stream.u16(frame.max_combo)
        self.stream.u16(frame.current_combo)
        self.stream.bool(frame.perfect)
        self.stream.u8(frame.hp)
