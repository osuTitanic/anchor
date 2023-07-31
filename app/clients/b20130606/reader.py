
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
        pass

    def read_replayframe(self) -> ReplayFrame:
        pass

    def read_replayframe_bundle(self) -> ReplayFrameBundle:
        pass

    def read_scoreframe(self) -> ScoreFrame:
        pass

    def read_match(self) -> Match:
        pass
