
from app.common.streams import StreamOut
from app.common.objects import (
    ReplayFrameBundle,
    BeatmapInfoReply,
    StatusUpdate,
    UserPresence,
    BeatmapInfo,
    ReplayFrame,
    ScoreFrame,
    UserStats,
    UserQuit,
    Message,
    Channel,
    Match
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

    def write_channel(self, channel: Channel):
        ...

    def write_message(self, msg: Message):
        ...

    def write_presence(self, presence: UserPresence):
        ...

    def write_stats(self, stats: UserStats):
        ...

    def write_quit(self, state: UserQuit):
        ...

    def write_status(self, status: StatusUpdate):
        ...

    def write_beatmap_info(self, info: BeatmapInfo):
        ...

    def write_beatmap_info_reply(self, reply: BeatmapInfoReply):
        ...

    def write_match(self, match: Match):
        ...

    def write_replayframe(self, frame: ReplayFrame):
        ...

    def write_scoreframe(self, frame: ScoreFrame):
        ...

    def write_replayframe_bundle(self, bundle: ReplayFrameBundle):
        ...
