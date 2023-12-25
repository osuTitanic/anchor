
from app.common.objects import (
    bMatch,
    bScoreFrame,
    bSlot
)

from app.common.constants import (
    MatchScoringTypes,
    MatchScoringTypes,
    MatchTeamTypes,
    SlotStatus,
    MatchType,
    SlotTeam,
    GameMode,
    Mods
)

from ..b337 import Reader as BaseReader
from typing import List

import config

class Reader(BaseReader):
    def read_match(self) -> bMatch:
        match_id = self.stream.u8()
        in_progress = self.stream.bool()
        match_type = MatchType(self.stream.u8())

        name = self.stream.string()
        password = ''

        beatmap_text = self.stream.string()
        beatmap_id   = self.stream.s32()
        beatmap_hash = self.stream.string()

        slot_open = self.read_booleans(config.MULTIPLAYER_MAX_SLOTS)
        slot_used = self.read_booleans(config.MULTIPLAYER_MAX_SLOTS)
        slot_ready = self.read_booleans(config.MULTIPLAYER_MAX_SLOTS)

        slot_id = [self.stream.s32() if slot_used[i] else -1 for i in range(config.MULTIPLAYER_MAX_SLOTS)]

        # Convert legacy slot booleans to SlotStatus enum
        slot_status = [
            (
                # Slot is used
                SlotStatus.Ready
                if slot_ready[i]
                else SlotStatus.NotReady
            )
            if slot_used[i]
            else (
                # Slot is not used
                SlotStatus.Open
                if slot_open[i]
                else SlotStatus.Locked
            )
            for i in range(config.MULTIPLAYER_MAX_SLOTS)
        ]

        slots = [
            bSlot(
                slot_id[i],
                slot_status[i],
                [SlotTeam.Neutral for _ in range(config.MULTIPLAYER_MAX_SLOTS)],
                [Mods.NoMod for _ in range(config.MULTIPLAYER_MAX_SLOTS)]
            )
            for i in range(config.MULTIPLAYER_MAX_SLOTS)
        ]

        return bMatch(
            match_id,
            in_progress,
            match_type,
            Mods.NoMod,
            name,
            password,
            beatmap_text,
            beatmap_id,
            beatmap_hash,
            slots,
            host_id=-1,
            mode=GameMode.Osu,
            scoring_type=MatchScoringTypes.Combo,
            team_type=MatchTeamTypes.HeadToHead,
            freemod=False,
            seed=0
        )

    def read_booleans(self, size: int = 8) -> List[bool]:
        byte = self.stream.u8()
        return [((byte >> index) & 1) > 0 for index in range(size)]

    def read_scoreframe(self) -> bScoreFrame:
        self.stream.string() # "checksum"

        return bScoreFrame(
            time=self.stream.s32(),
            id=self.stream.u8(),
            c300=self.stream.u16(),
            c100=self.stream.u16(),
            c50=self.stream.u16(),
            cGeki=self.stream.u16(),
            cKatu=self.stream.u16(),
            cMiss=self.stream.u16(),
            total_score=self.stream.s32(),
            max_combo=self.stream.u16(),
            current_combo=self.stream.u16(),
            perfect=self.stream.bool(),
            hp=self.stream.u8()
        )
