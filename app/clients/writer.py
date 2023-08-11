
from app.common.streams import StreamOut
from app.common.objects import (
    bReplayFrameBundle,
    bBeatmapInfoReply,
    bStatusUpdate,
    bUserPresence,
    bBeatmapInfo,
    bReplayFrame,
    bScoreFrame,
    bUserStats,
    bUserQuit,
    bMessage,
    bChannel,
    bMatch
)

from typing import Optional, List
from enum import Enum
from abc import ABC

class BaseWriter(ABC):
    def __init__(self) -> None:
        self.stream = StreamOut()

    def write_header(self, packet: Enum, size: Optional[int] = None):
        if not size:
            size = self.stream.size()

        header = StreamOut()
        header.header(packet, size)

        self.stream.write_to_start(header.get())

    def write_intlist(self, list: List[int]):
        ...

    def write_channel(self, channel: bChannel):
        ...

    def write_message(self, msg: bMessage):
        ...

    def write_presence(self, presence: bUserPresence):
        ...

    def write_stats(self, stats: bUserStats):
        ...

    def write_quit(self, state: bUserQuit):
        ...

    def write_status(self, status: bStatusUpdate):
        ...

    def write_beatmap_info(self, info: bBeatmapInfo):
        ...

    def write_beatmap_info_reply(self, reply: bBeatmapInfoReply):
        ...

    def write_match(self, match: bMatch):
        ...

    def write_replayframe(self, frame: bReplayFrame):
        ...

    def write_scoreframe(self, frame: bScoreFrame):
        ...

    def write_replayframe_bundle(self, bundle: bReplayFrameBundle):
        ...
