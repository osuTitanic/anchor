
from app.common.objects import bStatusUpdate, bMatch

from ..b20121008 import Writer as BaseWriter

class Writer(BaseWriter):
    def write_status(self, status: bStatusUpdate):
        self.stream.u8(status.action.value)
        self.stream.string(status.text)
        self.stream.string(status.beatmap_checksum)
        self.stream.u16(status.mods.value)
        self.stream.u8(status.mode.value)
        self.stream.s32(status.beatmap_id)

    def write_match(self, match: bMatch):
        self.stream.u16(match.id)

        self.stream.bool(match.in_progress)
        self.stream.u8(match.type.value)
        self.stream.u16(match.mods.value)

        self.stream.string(match.name)
        self.stream.string(match.password)
        self.stream.string(match.beatmap_text)
        self.stream.s32(match.beatmap_id)
        self.stream.string(match.beatmap_checksum)

        [self.stream.u8(slot.status.value) for slot in match.slots]
        [self.stream.u8(slot.team.value) for slot in match.slots]
        [self.stream.s32(slot.player_id) for slot in match.slots if slot.has_player]

        self.stream.s32(match.host_id)
        self.stream.u8(match.mode.value)
        self.stream.u8(match.scoring_type.value)
        self.stream.u8(match.team_type.value)
