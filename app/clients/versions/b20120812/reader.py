
from app.common.objects import (
    bStatusUpdate,
    bMatch,
    bSlot
)

from app.common.constants import (
    MatchScoringTypes,
    MatchTeamTypes,
    MatchTeamTypes,
    ClientStatus,
    SlotStatus,
    MatchType,
    GameMode,
    SlotTeam,
    Mods
)

from ..b20130329 import Reader as BaseReader

import config

class Reader(BaseReader):
    def read_status(self) -> bStatusUpdate:
        return bStatusUpdate(
            action=ClientStatus(self.stream.u8()),
            text=self.stream.string(),
            beatmap_checksum=self.stream.string(),
            mods=Mods(self.stream.u16()),
            mode=GameMode(self.stream.u8()),
            beatmap_id=self.stream.s32()
        )

    def read_match(self) -> bMatch:
        match_id = self.stream.s16()

        in_progress = self.stream.bool()
        match_type = MatchType(self.stream.u8())
        mods = Mods(self.stream.u16())

        name = self.stream.string()
        password = self.stream.string()

        beatmap_text = self.stream.string()
        beatmap_id   = self.stream.s32()
        beatmap_hash = self.stream.string()

        slot_status = [SlotStatus(self.stream.u8()) for _ in range(config.MULTIPLAYER_MAX_SLOTS)]
        slot_team = [SlotTeam(self.stream.u8()) for _ in range(config.MULTIPLAYER_MAX_SLOTS)]
        slot_id = [
            self.stream.s32()
            if (slot_status[i] & SlotStatus.HasPlayer) > 0 else -1
            for i in range(len(slot_status))
        ]

        host_id = self.stream.s32()
        mode = GameMode(self.stream.u8())

        scoring_type = MatchScoringTypes(self.stream.u8())
        team_type = MatchTeamTypes(self.stream.u8())
        slot_mods = [Mods.NoMod for _ in range(config.MULTIPLAYER_MAX_SLOTS)]

        slots = [
            bSlot(
                slot_id[i],
                slot_status[i],
                slot_team[i],
                slot_mods[i]
            )
            for i in range(config.MULTIPLAYER_MAX_SLOTS)
        ]

        return bMatch(
            match_id,
            in_progress,
            match_type,
            mods,
            name,
            password,
            beatmap_text,
            beatmap_id,
            beatmap_hash,
            slots,
            host_id,
            mode,
            scoring_type,
            team_type,
            freemod=False,
            seed=0
        )
