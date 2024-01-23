
from app.common.constants import ButtonState
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

from ..b1700.constants import Completeness
from ..writer import BaseWriter
from . import ResponsePacket

class Writer(BaseWriter):
    def __init__(self) -> None:
        self.stream = StreamOut()

    def write_header(self, packet: ResponsePacket, size: Optional[int] = None):
        if not size:
            size = self.stream.size()

        header = StreamOut()
        header.header(packet, size)

        self.stream.write_to_start(header.get())

    def write_intlist(self, list: List[int]):
        self.stream.s32(len(list))
        [self.stream.s32(num) for num in list]

    def write_channel(self, channel: bChannel):
        self.stream.string(channel.name)

    def write_message(self, msg: bMessage):
        self.stream.string(msg.sender)
        self.stream.string(msg.content)
        self.stream.string(msg.target)

    def write_presence(self, presence: bUserPresence, stats: Optional[bUserStats] = None):
        if stats.user_id <= 0:
            stats.user_id = -stats.user_id

        self.stream.s32(stats.user_id)
        self.stream.u8(Completeness.Full.value)
        self.write_status(stats.status)

        # Stats
        self.stream.s64(stats.rscore)
        self.stream.float(stats.accuracy)
        self.stream.s32(stats.playcount)
        self.stream.s64(stats.tscore)
        self.stream.u16(stats.rank)

        # Presence
        self.stream.string(presence.username)
        self.stream.string(f'{stats.user_id}_000.png') # Avatar Filename
        self.stream.u8(presence.timezone + 24)
        self.stream.string(presence.city)
        self.stream.u8(presence.permissions.value)

    def write_stats(self, stats: bUserStats):
        if stats.user_id <= 0:
            stats.user_id = -stats.user_id

        self.stream.s32(stats.user_id)
        self.stream.u8(Completeness.Statistics.value)
        self.write_status(stats.status)

        # Stats
        self.stream.s64(stats.rscore)
        self.stream.float(stats.accuracy)
        self.stream.s32(stats.playcount)
        self.stream.s64(stats.tscore)
        self.stream.u16(stats.rank)

    def write_quit(self, state: bUserQuit):
        self.stream.s32(state.user_id)

    def write_status(self, status: bStatusUpdate):
        self.stream.u8(status.action.value)
        self.stream.bool(True) # Beatmap Update
        self.stream.string(status.text)
        self.stream.string(status.beatmap_checksum)
        self.stream.u16(status.mods.value)

    def write_beatmap_info(self, info: bBeatmapInfo):
        self.stream.s16(info.index)
        self.stream.s32(info.beatmap_id)
        self.stream.s32(info.beatmapset_id)
        self.stream.s32(info.thread_id)
        self.stream.u8(info.ranked)
        self.stream.u8(info.osu_rank.value)
        self.stream.string(info.checksum)

    def write_beatmap_info_reply(self, reply: bBeatmapInfoReply):
        self.stream.s32(len(reply.beatmaps))
        [self.write_beatmap_info(info) for info in reply.beatmaps]

    def write_match(self, match: bMatch):
        self.stream.u8(match.id)

        self.stream.bool(match.in_progress)
        self.stream.u8(match.type.value)
        self.stream.u16(match.mods.value)

        self.stream.string(match.name)
        self.stream.string(match.beatmap_text)
        self.stream.s32(match.beatmap_id)
        self.stream.string(match.beatmap_checksum)

        [self.stream.u8(slot.status.value) for slot in match.slots]
        [self.stream.s32(slot.player_id) for slot in match.slots if slot.has_player]

    def write_replayframe(self, frame: bReplayFrame):
        self.stream.bool(
            (ButtonState.Left1 in frame.button_state) or
            (ButtonState.Left2 in frame.button_state)
        ) # "mouseLeft"
        self.stream.bool(
            (ButtonState.Right1 in frame.button_state) or
            (ButtonState.Right2 in frame.button_state)
        ) # "mouseRight"
        self.stream.float(frame.mouse_x)
        self.stream.float(frame.mouse_y)
        self.stream.s32(frame.time)

    def write_scoreframe(self, frame: bScoreFrame):
        self.stream.s32(frame.time)
        self.stream.u8(frame.id)
        self.stream.u16(frame.c300)
        self.stream.u16(frame.c100)
        self.stream.u16(frame.c50)
        self.stream.u16(frame.cGeki)
        self.stream.u16(frame.cKatu)
        self.stream.u16(frame.cMiss)
        self.stream.s32(frame.total_score)
        self.stream.u16(frame.max_combo)
        self.stream.u16(frame.current_combo)
        self.stream.bool(frame.perfect)
        self.stream.u8(frame.hp)

    def write_replayframe_bundle(self, bundle: bReplayFrameBundle):
        self.stream.u16(len(bundle.frames))
        [self.write_replayframe(frame) for frame in bundle.frames]
        self.stream.u8(bundle.action.value)

        if bundle.score_frame:
            self.write_scoreframe(bundle.score_frame)
