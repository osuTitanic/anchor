
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
        self.stream.s32(stats.user_id)
        self.write_status(stats.status)
        self.stream.u64(stats.rscore)
        self.stream.float(stats.accuracy)
        self.stream.s32(stats.playcount)
        self.stream.u64(stats.tscore)
        self.stream.s32(stats.rank)
        self.stream.u16(stats.pp)

    def write_status(self, status: StatusUpdate):
        self.stream.u8(status.action.value)
        self.stream.string(status.text)
        self.stream.string(status.beatmap_checksum)
        self.stream.u32(status.mods.value)
        self.stream.u8(status.mode.value)
        self.stream.s32(status.beatmap_id)

    def write_quit(self, state: UserQuit):
        self.stream.s32(state.user_id)
        self.stream.u8(state.quit_state.value)

    def write_beatmap_info(self, info: BeatmapInfo):
        self.stream.s16(info.index)
        self.stream.s32(info.beatmap_id)
        self.stream.s32(info.beatmapset_id)
        self.stream.s32(info.thread_id)
        self.stream.u8(info.ranked)
        self.stream.u8(info.osu_rank.value)
        self.stream.u8(info.fruits_rank.value)
        self.stream.u8(info.taiko_rank.value)
        self.stream.u8(info.mania_rank.value)
        self.stream.string(info.checksum)

    def write_beatmap_info_reply(self, reply: BeatmapInfoReply):
        self.stream.s32(len(reply.beatmaps))
        [self.write_beatmap_info(info) for info in reply.beatmaps]

    def write_replayframe(self, frame: ReplayFrame):
        self.stream.u8(frame.button_state.value)
        self.stream.u8(frame.taiko_byte)
        self.stream.float(frame.mouse_x)
        self.stream.float(frame.mouse_y)
        self.stream.s32(frame.time)

    def write_scoreframe(self, frame: ScoreFrame):
        pass

    def write_replayframe_bundle(self, bundle: ReplayFrameBundle):
        pass
