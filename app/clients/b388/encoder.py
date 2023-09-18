
from app.common.objects import bBeatmapInfoReply

from typing import Callable

from ..b399 import Writer
from . import ResponsePacket
from . import PACKETS

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[388][1][packet] = func
        PACKETS[339][1][packet] = func
        return func

    return wrapper

@register(ResponsePacket.BEATMAP_INFO_REPLY)
def beatmap_info_reply(reply: bBeatmapInfoReply):
    for info in reply.beatmaps:
        # Approved status does not exist
        info.ranked = {
            0: 0,
            1: 1,
            2: 1
        }[info.ranked]

    writer = Writer()
    writer.write_beatmap_info_reply(reply)
    return writer.stream.get()
