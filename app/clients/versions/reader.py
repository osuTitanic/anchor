
from app.common.streams import StreamIn
from app.common.objects import (
    bBeatmapInfoRequest,
    bReplayFrameBundle,
    bStatusUpdate,
    bReplayFrame,
    bScoreFrame,
    bMatchJoin,
    bMessage,
    bMatch
)

from typing import List
from abc import ABC

class BaseReader(ABC):
    def __init__(self, stream: StreamIn) -> None:
        self.stream = stream

    def read_intlist(self) -> List[int]:
        ...

    def read_message(self) -> bMessage:
        ...

    def read_status(self) -> bStatusUpdate:
        ...

    def read_beatmap_request(self) -> bBeatmapInfoRequest:
        ...

    def read_replayframe(self) -> bReplayFrame:
        ...

    def read_replayframe_bundle(self) -> bReplayFrameBundle:
        ...

    def read_scoreframe(self) -> bScoreFrame:
        ...

    def read_match(self) -> bMatch:
        ...

    def read_matchjoin(self) -> bMatchJoin:
        ...
