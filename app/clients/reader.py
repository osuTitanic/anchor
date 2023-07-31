
from app.common.streams import StreamIn
from app.common.objects import (
    BeatmapInfoRequest,
    ReplayFrameBundle,
    StatusUpdate,
    BanchoPacket,
    ReplayFrame,
    ScoreFrame,
    Message,
    Match
)

from typing import List
from abc import ABC

class BaseReader(ABC):
    def __init__(self, stream: StreamIn) -> None:
        self.stream = stream

    def read_header(self) -> BanchoPacket:
        ...

    def read_intlist(self) -> List[int]:
        ...

    def read_message(self) -> Message:
        ...

    def read_status(self) -> StatusUpdate:
        ...

    def read_beatmap_request(self) -> BeatmapInfoRequest:
        ...

    def read_replayframe(self) -> ReplayFrame:
        ...

    def read_replayframe_bundle(self) -> ReplayFrameBundle:
        ...

    def read_scoreframe(self) -> ScoreFrame:
        ...

    def read_match(self) -> Match:
        ...
