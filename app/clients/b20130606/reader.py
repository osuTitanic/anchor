
from app.common.streams import StreamIn

from app.common.objects import (
    BeatmapInfoRequest,
    ReplayFrameBundle,
    StatusUpdate,
    BanchoPacket,
    ReplayFrame,
    ScoreFrame,
    Message,
    Match,
    Slot
)

from app.common.constants import (
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

from .constants import RequestPacket
from ..reader import BaseReader

class Reader(BaseReader):
    def __init__(self, stream: StreamIn) -> None:
        self.stream = stream

    def read_header(self) -> BanchoPacket:
        return BanchoPacket(
            packet=RequestPacket(self.stream.u16()),
            compression=self.stream.bool(),
            payload=StreamIn(
                self.stream.read(
                    self.stream.u32()
                )
            )
        )

    def read_message(self) -> Message:
        return Message(
            sender=self.stream.string(),
            content=self.stream.string(),
            target=self.stream.string(),
            sender_id=self.stream.s32()
        )

    def read_status(self) -> StatusUpdate:
        return StatusUpdate(
            status=ClientStatus(self.stream.u8()),
            text=self.stream.string(),
            beatmap_checksum=self.stream.string(),
            mods=Mods(self.stream.u32()),
            mode=GameMode(self.stream.u8()),
            beatmap_id=self.stream.s32()
        )

    def read_beatmap_request(self) -> BeatmapInfoRequest:
        return BeatmapInfoRequest(
            [self.stream.string() for m in range(self.stream.s32())],
            [self.stream.s32() for m in range(self.stream.s32())]
        )

    def read_replayframe(self) -> ReplayFrame:
        return ReplayFrame(
            button_state=ButtonState(self.stream.u8()),
            taiko_byte=self.stream.u8(),
            mouse_x=self.stream.float(),
            mouse_y=self.stream.float(),
            time=self.stream.s32()
        )

    def read_scoreframe(self) -> ScoreFrame:
        return ScoreFrame(
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
            hp=self.stream.u8(),
            tag_byte=self.stream.u8()
        )

    def read_replayframe_bundle(self) -> ReplayFrameBundle:
        extra = self.stream.s32()
        replay_frames = [self.read_replayframe() for f in range(self.stream.u16())]
        action = ReplayAction(self.stream.u8())

        try:
            score_frame = self.read_scoreframe()
        except Exception:
            score_frame = None

        return ReplayFrameBundle(
            extra,
            action,
            replay_frames,
            score_frame
        )

    def read_match(self) -> Match:
        pass
