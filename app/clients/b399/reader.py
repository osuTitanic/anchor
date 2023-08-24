
from app.common.objects import (
    bMatch,
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
    Mods,
)

from ..b535.reader import Reader as BaseReader

class Reader(BaseReader):
    def read_match(self) -> bMatch:
        match_id = self.stream.u8()

        in_progress = self.stream.bool()
        match_type = MatchType(self.stream.u8())
        mods = Mods(self.stream.u16())

        name = self.stream.string()
        password = ''

        beatmap_text = self.stream.string()
        beatmap_id   = self.stream.s32()
        beatmap_hash = self.stream.string()

        slot_status = [SlotStatus(self.stream.u8()) for _ in range(8)]

        slot_id = [
            self.stream.s32()
            if (slot_status[i] & SlotStatus.HasPlayer) > 0 else -1
            for i in range(len(slot_status))
        ]

        host_id = -1
        mode = GameMode.Osu

        scoring_type = MatchScoringTypes.Combo
        team_type = MatchTeamTypes.HeadToHead

        slot_team = [SlotTeam.Neutral for _ in range(8)]
        slot_mods = [Mods.NoMod for _ in range(8)]

        slots = [
            bSlot(
                slot_id[i],
                slot_status[i],
                slot_team[i],
                slot_mods[i]
            )
            for i in range(8)
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
