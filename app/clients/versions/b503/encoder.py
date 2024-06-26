
from app.common.objects import bBeatmapInfoReply, bUserStats, bUserPresence
from typing import Callable, Optional

from .. import register_encoder
from . import ResponsePacket
from . import Writer

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(503, packet, func)
        register_encoder(487, packet, func)
        return func

    return wrapper

@register(ResponsePacket.BEATMAP_INFO_REPLY)
def beatmap_info_reply(reply: bBeatmapInfoReply):
    writer = Writer()
    writer.write_beatmap_info_reply(reply)
    return writer.stream.get()

@register(ResponsePacket.USER_STATS)
def send_stats(stats: bUserStats, presence: Optional[bUserPresence] = None):
    # Add cap for total score to prevent client from crashing
    stats.tscore = min(stats.tscore, 17705429347)

    writer = Writer()
    if presence:
        writer.write_presence(presence, stats)
    else:
        writer.write_stats(stats)
    return writer.stream.get()
