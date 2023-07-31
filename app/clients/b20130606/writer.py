
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

from typing import Optional

from .constants import ResponsePacket
from ..writer import BaseWriter

class Writer(BaseWriter):
    def __init__(self, stream: StreamOut) -> None:
        self.stream = stream

    def write_header(self, packet: ResponsePacket, size: Optional[int] = None):
        if not size:
            size = self.stream.size()

        header = StreamOut()
        header.header(packet, size)

        self.stream.write_to_start(header.get())

    def write_channel(self, channel: Channel):
        self.stream.string(channel.name)
        self.stream.string(channel.topic)
        self.stream.u16(channel.user_count)

    def write_message(self, msg: Message):
        self.stream.string(msg.sender)
        self.stream.string(msg.content)
        self.stream.string(msg.target)
        self.stream.s32(msg.sender_id)

    def write_presence(self, presence: UserPresence):
        self.stream.s32(presence.user_id)
        self.stream.string(presence.username)
        self.stream.u8(presence.timezone - 24)
        self.stream.u8(presence.country_code)
        self.stream.u8(presence.permissions.value | presence.mode.value << 5)
        self.stream.float(presence.longitude)
        self.stream.float(presence.latitude)
        self.stream.s32(presence.rank)

    def write_stats(self, stats: UserStats):
        pass

    def write_quit(self, state: UserQuit):
        pass

    def write_status(self, status: StatusUpdate):
        pass

    def write_beatmap_info(self, info: BeatmapInfo):
        pass

    def write_beatmap_info_reply(self, reply: BeatmapInfoReply):
        pass

    def write_match(self, match: Match):
        pass

    def write_replayframe(self, frame: ReplayFrame):
        pass

    def write_scoreframe(self, frame: ScoreFrame):
        pass

    def write_replayframe_bundle(self, bundle: ReplayFrameBundle):
        pass
