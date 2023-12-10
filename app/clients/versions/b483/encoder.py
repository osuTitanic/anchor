
from app.common.objects import (
    bReplayFrameBundle,
    bUserPresence,
    bScoreFrame,
    bUserStats,
    bMatch
)

from typing import Callable, Optional

from . import ResponsePacket
from . import PACKETS
from . import Writer


def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[483][1][packet] = func
        PACKETS[402][1][packet] = func
        return func

    return wrapper

@register(ResponsePacket.NEW_MATCH)
def new_match(match: bMatch):
    writer = Writer()
    writer.write_match(match)
    return writer.stream.get()

@register(ResponsePacket.UPDATE_MATCH)
def update_match(match: bMatch):
    writer = Writer()
    writer.write_match(match)
    return writer.stream.get()

@register(ResponsePacket.MATCH_JOIN_SUCCESS)
def match_join_success(match: bMatch):
    writer = Writer()
    writer.write_match(match)
    return writer.stream.get()

@register(ResponsePacket.MATCH_START)
def match_start(match: bMatch):
    writer = Writer()
    writer.write_match(match)
    return writer.stream.get()

@register(ResponsePacket.USER_STATS)
def send_stats(stats: bUserStats, presence: Optional[bUserPresence] = None):
    writer = Writer()
    if presence:
        writer.write_presence(presence, stats)
    else:
        writer.write_stats(stats)
    return writer.stream.get()

@register(ResponsePacket.SPECTATE_FRAMES)
def spectate_frames(bundle: bReplayFrameBundle):
    writer = Writer()
    writer.write_replayframe_bundle(bundle)
    return writer.stream.get()

@register(ResponsePacket.MATCH_SCORE_UPDATE)
def score_update(score_frame: bScoreFrame):
    writer = Writer()
    writer.write_scoreframe(score_frame)
    return writer.stream.get()
