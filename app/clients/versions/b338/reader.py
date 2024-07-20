
from app.common.streams import StreamIn
from app.common.objects import (
    bBeatmapInfoRequest,
    bReplayFrameBundle,
    bStatusUpdate,
    bReplayFrame,
    bScoreFrame,
    bMatchJoin,
    bMessage,
    bMatch,
    bSlot
)

from app.common.constants import (
    MatchScoringTypes,
    MatchScoringTypes,
    MatchTeamTypes,
    ReplayAction,
    ClientStatus,
    ButtonState,
    SlotStatus,
    MatchType,
    SlotTeam,
    GameMode,
    Mods
)

from typing import List

from ..reader import BaseReader
from . import RequestPacket

import config

class Reader(BaseReader):
    def __init__(self, stream: StreamIn) -> None:
        self.stream = stream

    def read_intlist(self) -> List[int]:
        return [self.stream.s32() for _ in range(self.stream.s32())]

    def read_message(self) -> bMessage:
        message = bMessage(
            sender=self.stream.string(),
            content=self.stream.string(),
            target=self.stream.string()
        )

        return message

    def read_status(self) -> bStatusUpdate:
        action = ClientStatus(self.stream.u8())
        beatmap_update = self.stream.bool()

        if not beatmap_update:
            return bStatusUpdate(action)

        return bStatusUpdate(
            action,
            text=self.stream.string(),
            beatmap_checksum=self.stream.string(),
            mods=Mods(self.stream.u16())
        )

    def read_beatmap_request(self) -> bBeatmapInfoRequest:
        return bBeatmapInfoRequest(
            [self.stream.string() for m in range(self.stream.s32())],
            []
        )

    def read_beatmap_request(self) -> bBeatmapInfoRequest:
        return bBeatmapInfoRequest(
            [self.stream.string() for m in range(self.stream.s32())],
            [self.stream.s32() for m in range(self.stream.s32())]
        )

    def read_replayframe(self) -> bReplayFrame:
        button_state = ButtonState.NoButton

        if self.stream.bool(): button_state |= ButtonState.Left1
        if self.stream.bool(): button_state |= ButtonState.Right1

        return bReplayFrame(
            button_state=button_state,
            legacy_byte=0,
            mouse_x=self.stream.float(),
            mouse_y=self.stream.float(),
            time=self.stream.s32()
        )

    def read_scoreframe(self) -> bScoreFrame:
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

    def read_replayframe_bundle(self) -> bReplayFrameBundle:
        replay_frames = [self.read_replayframe() for f in range(self.stream.u16())]
        action = ReplayAction(self.stream.u8())

        try:
            score_frame = self.read_scoreframe()
        except OverflowError:
            score_frame = None

        return bReplayFrameBundle(
            0,
            action,
            replay_frames,
            score_frame
        )

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

        slot_status = [SlotStatus(self.stream.u8()) for _ in range(config.MULTIPLAYER_MAX_SLOTS)]

        slot_id = [
            self.stream.s32()
            if (slot_status[i] & SlotStatus.HasPlayer) > 0 else -1
            for i in range(len(slot_status))
        ]

        host_id = -1
        mode = GameMode.Osu

        scoring_type = MatchScoringTypes.Combo
        team_type = MatchTeamTypes.HeadToHead

        slot_team = [SlotTeam.Neutral for _ in range(config.MULTIPLAYER_MAX_SLOTS)]
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

    def read_matchjoin(self) -> bMatchJoin:
        return bMatchJoin(self.stream.s32())
